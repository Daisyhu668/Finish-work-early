#!/usr/bin/env python3
"""Local trade contract reconciliation; extracted fields require human verification."""
import argparse,json
from pathlib import Path
from decimal import Decimal
from datetime import date
from collections import defaultdict

def party(s):
    return str(s or '').replace('（','(').replace('）',')').replace(' ','').strip()

def money(v):
    d=Decimal(str(v))
    if not d.is_finite() or d<0 or d.quantize(Decimal('.01'))!=d:
        raise ValueError('金额须非负且精确到分')
    return d

def reconcile(data,bills=None):
    customer=party(data['customer'])
    if not customer or not data.get('case_id'): raise ValueError('缺客户或批次')
    contracts=data['contracts']
    if not contracts: raise ValueError('无合同')
    limits=defaultdict(Decimal); seen=set(); lines=[]
    for c in contracts:
        if c.get('verified') is not True: raise ValueError('合同字段须人工核实')
        if party(c['buyer'])!=customer: raise ValueError('合同购方跨客户')
        seller=party(c['seller']); no=str(c['number']).strip()
        if not seller or not no or (seller,no) in seen: raise ValueError('缺交易对手/编号或合同重复')
        seen.add((seller,no)); date.fromisoformat(c['date'])
        amount=money(c['amount']); unpaid=money(c['unpaid'])
        if amount<=0 or unpaid>amount: raise ValueError('合同金额/未付款余额异常')
        limits[seller]+=unpaid
        lines.append(f"交易对手：{c['seller']}\n购销合同编号：{no}\n合同签订日期：{c['date']}\n合同金额：{amount:.2f}元\n已核实未付款金额：{unpaid:.2f}元")
    if bills is not None:
        if party(bills['customer'])!=customer or bills['case_id']!=data['case_id']: raise ValueError('BI与合同客户/批次不一致')
        totals=defaultdict(Decimal)
        for b in bills['bills']:
            if not b.get('bi'): raise ValueError('缺真实BI')
            date.fromisoformat(b['issue_date'])
            amount=money(b['amount'])
            if amount<=0: raise ValueError('银票金额非正')
            totals[party(b['payee'])]+=amount
        for p,a in totals.items():
            if p not in limits or a>limits[p]: raise ValueError(f'{p}合同未付金额不足或缺合同')
        lines.append('本次BI与合同未付款余额核对通过；仍须逐BI核验发票覆盖和贸易真实性。')
    else:
        lines.append('提票前底稿：未取得BI，尚未核对实际银票。')
    return '\n\n'.join(lines),{p:str(v) for p,v in limits.items()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--contracts',required=True);p.add_argument('--bills');p.add_argument('--out',required=True)
    a=p.parse_args(); data=json.loads(Path(a.contracts).read_text(encoding='utf-8-sig'))
    bills=json.loads(Path(a.bills).read_text(encoding='utf-8-sig')) if a.bills else None
    txt,limits=reconcile(data,bills)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'购销合同录入.txt').write_text(txt,encoding='utf-8')
    (out/'合同未付余额.json').write_text(json.dumps(limits,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
