#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allocate whole invoices to actual bills without duplicating an invoice.

The result is a proposed mapping, NEVER evidence that a bank accepted the file.
For high-volume multi-bill groups install OR-Tools (CP-SAT). A small exact
stdlib fallback exists for skill evaluations and offline smoke tests.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from itertools import product

CENT=Decimal('0.01')
def cents(value):
    v=Decimal(str(value))
    if v <= 0 or not v.is_finite() or v.quantize(CENT)!=v:
        raise ValueError(f'金额必须为正数且精确到分：{value}')
    return int(v*100)

def _exact_small(rows,bills):
    """Exact enumeration with pruning; only for up to 17 invoices / 2 bills.
    Minimize selected total, then invoice count, then lexicographic mapping.
    """
    if len(rows)>12 or len(bills)>2:
        raise RuntimeError('较大规模自动分票需要 OR-Tools：py -m pip install ortools')
    invoice_cents=[cents(r['total']) for r in rows]
    targets=[cents(b['amount']) for b in bills]
    suffix=[0]*(len(rows)+1)
    for i in range(len(rows)-1,-1,-1):suffix[i]=suffix[i+1]+invoice_cents[i]
    best=None;assign=[-1]*len(rows);sums=[0]*len(bills)
    def search(i):
        nonlocal best
        if all(sums[j]>=targets[j] for j in range(len(bills))):
            chosen=sum(sums)
            count=sum(a>=0 for a in assign)
            key=(chosen,count,tuple(assign))
            if best is None or key<best[0]:best=(key,assign.copy())
            return
        if i==len(rows):return
        if any(sums[j]+suffix[i]<targets[j] for j in range(len(bills))):return
        if best is not None and sum(sums)>best[0][0]:return
        for j in range(len(bills)):
            if sums[j]>=targets[j]:continue  # one more invoice would only increase surplus
            sums[j]+=invoice_cents[i];assign[i]=j
            search(i+1)
            sums[j]-=invoice_cents[i]
        assign[i]=-1
        search(i+1)
    search(0)
    if best is None:raise ValueError('整张发票无法覆盖全部银票金额（或发票分割条件不满足），请调整选票/票面')
    return best[1], 'exact_small_fallback'

def _ortools(rows,bills):
    try:from ortools.sat.python import cp_model
    except ImportError:return None
    model=cp_model.CpModel();n=len(rows);m=len(bills)
    cash=[cents(r['total']) for r in rows];targets=[cents(b['amount']) for b in bills]
    x=[[model.NewBoolVar(f'x_{i}_{j}') for j in range(m)] for i in range(n)]
    for i in range(n):model.Add(sum(x[i][j] for j in range(m))<=1)
    for j in range(m):model.Add(sum(cash[i]*x[i][j] for i in range(n))>=targets[j])
    # Dominant term: minimize total invoice-face value used (less overcoverage).
    # Secondary: fewer invoices; deterministic invoice order ensures stable results.
    objective=sum((cash[i]*100 + 1)*x[i][j] for i in range(n) for j in range(m))
    model.Minimize(objective)
    solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=15.0
    solver.parameters.num_search_workers=1
    solver.parameters.random_seed=0
    status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        raise ValueError('指定时间内无法形成满足每张银票覆盖要求的整票方案，禁止输出不完整关联表')
    assignment=[]
    for i in range(n):
        value=next((j for j in range(m) if solver.Value(x[i][j])), -1)
        assignment.append(value)
    return assignment, 'optimal_cp_sat' if status==cp_model.OPTIMAL else 'feasible_cp_sat_not_proven_optimal'

def allocate(rows,bills):
    """rows: [{invoice_no,total,...}], bills:[{bi,payee,amount}]
    All rows from ONE payee only. May leave excess rows unassigned.
    """
    if not rows or not bills:raise ValueError('需要真实发票及银票明细')
    rows=sorted(rows,key=lambda r:(r['invoice_date'],r['invoice_no']))
    bills=sorted(bills,key=lambda b:b['bi'])
    if len({r['invoice_no'] for r in rows})!=len(rows):raise ValueError('存在重复发票号码，禁止关联')
    if len({b['bi'] for b in bills})!=len(bills):raise ValueError('重复BI序号')
    if sum(cents(r['total']) for r in rows)<sum(cents(b['amount']) for b in bills):
        raise ValueError('该交易对手的候选发票总额不足以覆盖所有银票')
    found=_ortools(rows,bills)
    if found is None:
        if len(bills)==1 and len(rows)>12:
            # Validated greedy single-BI fallback, NOT an optimization guarantee.
            target=cents(bills[0]['amount'])
            ranked=sorted(enumerate(rows),key=lambda v:(-cents(v[1]['total']),v[1]['invoice_no']))
            picked=[];total=0
            for idx,r in ranked:
                if total>=target:break
                picked.append(idx);total+=cents(r['total'])
            for idx in list(picked):
                if total-cents(rows[idx]['total'])>=target:
                    picked.remove(idx);total-=cents(rows[idx]['total'])
            if total<target:raise ValueError('未找到能覆盖单张银票的整票方案')
            found=([0 if i in picked else -1 for i in range(len(rows))], 'valid_single_bill_greedy_not_optimal')
        else:found=_exact_small(rows,bills)
    assignment,method=found
    chosen={};sums=defaultdict(int)
    for r,idx in zip(rows,assignment):
        if idx<0:continue
        bi=bills[idx]['bi'];chosen[r['invoice_no']]=bi;sums[bi]+=cents(r['total'])
    for b in bills:
        if sums[b['bi']]<cents(b['amount']):raise AssertionError('自动分票后出现覆盖不足，拒绝使用')
    return chosen,{'method':method,'bills':[{'bi':b['bi'],'payee':b['payee'],'bill_amount':str(b['amount']),
           'invoice_total':str(Decimal(sums[b['bi']])/100),'overage':str(Decimal(sums[b['bi']]-cents(b['amount']))/100),
           'invoice_count':sum(v==b['bi'] for v in chosen.values())} for b in bills],
           'unassigned_invoice_nos':[r['invoice_no'] for r in rows if r['invoice_no'] not in chosen]}