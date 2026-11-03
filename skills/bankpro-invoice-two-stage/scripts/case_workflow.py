#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BankPro generic enterprise-isolated two-stage invoice Skill.
Stage 1 registers ALL valid source invoices into InvoiceLogInfo.xls.
Stage 2 independently selects only user-approved candidates, optimizes whole
invoice -> BI links, then writes InvoiceInfo.xls after explicit review.
"""
from __future__ import annotations
import argparse,calendar,csv,hashlib,json,re,sys
from collections import defaultdict
from datetime import date,datetime
from decimal import Decimal
from pathlib import Path
import normalize_invoices as norm
import allocate_bills as alloc
import write_bank_template as writer
ROOT=Path(__file__).resolve().parents[1]


def save(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stable_party(s):return writer.normalize_party(s)
def digest(data):return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def loadcase(p):
    p=Path(p).resolve();f=p/'case.json'
    if not f.is_file():raise ValueError('项目目录缺少case.json；请先init')
    config=load(f)
    if not config.get('customer') or not config.get('case_id'):raise ValueError('case配置不完整')
    return p,config

def source_manifest(doc,customer):
    if doc['summary'].get('block_count',0):raise ValueError('源清单包含BLOCK项，禁止登记')
    rows=doc['records'];seen=set();items=[]
    for r in rows:
        num=r['invoice_no']
        if num in seen:raise ValueError(f'重复发票号码：{num}')
        seen.add(num)
        if stable_party(r.get('buyer'))!=stable_party(customer):raise ValueError(f'跨客户发票：{num},购方{r.get("buyer")}')
        if not r.get('seller') or stable_party(r.get('seller'))!=stable_party(r.get('payee')):
            raise ValueError(f'销方/收款人不符，需核实：{num}')
        # Bind every business-critical column and origin to the frozen case.
        # Older versions omitted product/type/medium and could silently accept
        # a subsequently altered normalized.json.
        frozen_keys=('invoice_no','invoice_code','buyer','seller','payee',
                     'invoice_date','product','invoice_type','medium','total',
                     'net','tax','external_count','used_amount','status',
                     'source_file','source_sheet','source_row')
        items.append({k:r.get(k) for k in frozen_keys})
    if not items:raise ValueError('源发票池为空')
    items.sort(key=lambda a:a['invoice_no'])
    return {'customer':customer,'count':len(items),'amount':str(sum((Decimal(r['total']) for r in items),Decimal('0'))),
            'source_hash':digest(items)}

def frozen_case(case,conf):
    source=case/'data'/'normalized.json';frozen=case/'data'/'frozen.json'
    if not source.is_file() or not frozen.is_file():raise ValueError('缺少prepare后的底稿，请先prepare')
    doc=load(source);saved=load(frozen)
    if source_manifest(doc,conf['customer'])!=saved:
        raise ValueError('首次登记底稿发生改动：禁止覆盖旧数据，请新建case-id')
    return source,doc,saved

def init(args):
    root=Path(args.workspace).resolve();root.mkdir(parents=True,exist_ok=True)
    cid=args.case_id or datetime.now().strftime('%Y%m%d%H%M%S')
    if not re.fullmatch(r'[A-Za-z0-9_-]{4,64}',cid):raise ValueError('case-id格式无效')
    if not args.customer.strip():raise ValueError('客户名称为空')
    folder=root/cid
    if folder.exists():raise FileExistsError(f'客户/批次目录已存在：{folder}')
    folder.mkdir()
    save(folder/'case.json',{'customer':args.customer.strip(),'case_id':cid,'created':datetime.now().isoformat(timespec='seconds'),
                             'workflow':'BankPro Invoice Stage1+Stage2','version':'3.1.0'})
    print('已创建客户独立目录：'+str(folder))

def prepare(args):
    case,conf=loadcase(args.case)
    if (case/'data'/'frozen.json').exists():raise ValueError('已冻结初次发票池，不允许覆盖；新的一批发票请建立新case')
    stage=case/'data';stage.mkdir(exist_ok=True)
    cmd=['--sources']+args.sources+['--buyer',conf['customer'],'--output-dir',str(stage)]
    if args.product_confirmed:cmd+=['--product-override',args.product_confirmed]
    if args.all_invoice_sheets:cmd+=['--all-invoice-sheets']
    # Stage1 must NOT select by max-amount or exclude 2x - register complete pool for later bank verification.
    rc=norm.run(cmd)
    if rc:raise ValueError('第一次整理存在BLOCK，详见data/issues.csv，未冻结数据')
    doc=load(stage/'normalized.json');f=source_manifest(doc,conf['customer'])
    save(stage/'frozen.json',f)
    print(json.dumps({'stage':'STAGE1_READY','case_id':conf['case_id'],'customer':conf['customer'],**f},ensure_ascii=False,indent=2))

def reg(args):
    case,conf=loadcase(args.case)
    source,doc,frozen=frozen_case(case,conf)
    output=Path(args.out)
    opts=['--data',str(source),'--mode','registration','--template',str(args.template or ROOT/'assets'/'InvoiceLogInfo.xls'),
          '--out',str(output),'--engine',args.engine]
    if args.accept_new_template:opts+=['--accept-new-template']
    writer.run(opts)
    save(str(output)+'.case.json',{'stage':1,'customer':conf['customer'],'case_id':conf['case_id'],
                                   'source_hash':frozen['source_hash'],'system_import_confirmed':False})

def selection_from_file(path,doc):
    if not path:raise ValueError('第二阶段必须明确提供选中的发票号码清单 --selected-invoices；不自动使用全部发票')
    selected=set()
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        val=line.strip()
        if not val or val.startswith('#'):continue
        if not re.fullmatch(r'\d{8,20}',val):raise ValueError(f'选票清单有非纯发票号码：{val}')
        if val in selected:raise ValueError(f'选票清单存在重复号码：{val}')
        selected.add(val)
    source={r['invoice_no']:r for r in doc['records']}
    missing=selected-source.keys()
    if missing:raise ValueError('有未在本批首次登记底稿出现的发票：'+str(sorted(missing)[:12]))
    if not selected:raise ValueError('选票名单为空')
    return [source[n] for n in sorted(selected)]

def sub_months(d,months):
    year=d.year+(d.month-1-months)//12
    month=(d.month-1-months)%12+1
    return date(year,month,min(d.day,calendar.monthrange(year,month)[1]))

def check_invoice_policy(row,bill_date,status,override_6m):
    no=row['invoice_no'];issue=date.fromisoformat(row['invoice_date'])
    if issue>bill_date:raise ValueError(f'{no} 发票开立日在银承签发日之后，禁止默认使用')
    if issue<sub_months(bill_date,12):raise ValueError(f'{no} 发票早于银承开立日超过1年，禁止使用')
    # Stage2 always uses fresh status; Stage1 metadata must never substitute
    # for missing values in the latest bank-system verification record.
    ex=status.get('external_count')
    used=status.get('used_amount')
    if used in (None,''):
        raise ValueError(f'{no} 最新核验记录缺少已占用金额，不能当作0元')
    try:
        used_value=Decimal(str(used))
        if not used_value.is_finite() or used_value<0:raise ValueError()
    except Exception:raise ValueError(f'{no} 已占用金额非法：{used}')
    if used_value>0:raise ValueError(f'{no} 已占用金额{used}，不能未经确认重复关联')
    if ex in (None,''):raise ValueError(f'{no} 最新核验记录缺少外部核验次数，禁止用旧数据代替')
    try:
        dec=Decimal(str(ex))
        if not dec.is_finite() or dec!=dec.to_integral_value():raise ValueError()
        ex=int(dec)
    except Exception:raise ValueError(f'{no} 外部核验次数不是有效整数：{ex}')
    state=status.get('verification_status')
    if state not in (None,'','正常','Y','有效','已核验'):
        raise ValueError(f'{no} 最新核验状态异常：{state}')
    if ex<0:raise ValueError(f'{no} 外部核验次数不允许负数')
    if ex>2:raise ValueError(f'{no} 外部核验{ex}次，超过现行次数口径')
    if ex==2 and not status.get('external2_enhanced_review_confirmed',False):
        raise ValueError(f'{no} 外部核验2次，必须先完成强化核实并在本票核验记录中明确确认')
    if issue<sub_months(bill_date,6):
        if ex>1:raise ValueError(f'{no} 超6个月发票外部核验{ex}次，不符合次数限制')
        if not override_6m:raise ValueError(f'{no} 超6个月，须确认例外准入及强化核实后才可关联')
    return '超6个月例外已声明需人工审查' if issue<sub_months(bill_date,6) else ('外查2次需强化核实' if ex==2 else '次数满足口径')

def bills_from_payload(payload,conf,frozen):
    if stable_party(payload.get('customer'))!=stable_party(conf['customer']):raise ValueError('银票清单客户名称与项目不一致')
    if payload.get('case_id')!=conf['case_id'] or payload.get('source_hash')!=frozen['source_hash']:
        raise ValueError('BI清单项目/底稿指纹不匹配，禁止跨企业或跨批次引用')
    if payload.get('registration_bank_system_confirmed') is not True:
        raise ValueError('必须明确确认首次发票登记已在银行系统完成')
    bills=payload.get('bills')
    if not isinstance(bills,list) or not bills:raise ValueError('bills必须为非空列表，每张银票单独提供真实BI、收款人、票面、签发日')
    seen=set()
    for b in bills:
        bi=str(b.get('bi') or '')
        if not re.fullmatch(r'BI\d{16}',bi):raise ValueError(f'BI缺失或格式异常：{bi}，禁止编造')
        if bi in seen:raise ValueError(f'重复BI号：{bi}')
        seen.add(bi)
        if not b.get('payee') or not b.get('issue_date'):raise ValueError(f'{bi}缺交易对手或签发日')
        try:date.fromisoformat(b['issue_date'])
        except Exception:raise ValueError(f'{bi}签发日格式应为YYYY-MM-DD')
        alloc.cents(b['amount'])
    approved=payload.get('approved_bill_limit')
    if approved not in (None,'') and sum(alloc.cents(b['amount']) for b in bills)>alloc.cents(approved):
        raise ValueError(f'银票合计超过本次拟开票金额/审批上限{approved}')
    unpaid=payload.get('contract_unpaid_by_payee') or {}
    if unpaid:
        by=defaultdict(int)
        for b in bills:by[stable_party(b['payee'])]+=alloc.cents(b['amount'])
        for party,limit in unpaid.items():
            if by[stable_party(party)]>alloc.cents(limit):
                raise ValueError(f'交易对手{party}拟开银承超过已核实合同未付款金额{limit}')
    return bills

def csvwrite(path,rows,fields):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def plan_stage2(args):
    case,conf=loadcase(args.case)
    _,doc,frozen=frozen_case(case,conf)
    payload=load(args.bills)
    bills=bills_from_payload(payload,conf,frozen)
    candidates=selection_from_file(args.selected_invoices,doc)
    # External verification data is read again AFTER bank registration; never trust stale Stage1 snapshot as current status.
    if not args.status_source and not args.status_json:
        raise ValueError('第二阶段必须提供最新系统发票核验表 --status-source，或经人工逐票核实的 --status-json')
    latest=norm.load_status_lookup(args.status_source) if args.status_source else {}
    if args.status_json:
        manual=load(args.status_json)
        if not isinstance(manual,dict):raise ValueError('--status-json应为发票号码到核验明细的字典')
        latest.update(manual)
    bypay=defaultdict(list)
    for b in bills:bypay[stable_party(b['payee'])].append(b)
    buckets=defaultdict(list);problems=[]
    for r in candidates:
        key=stable_party(r['seller'])
        if key not in bypay:
            problems.append(f'{r["invoice_no"]}销方{r["seller"]}未在本次银票收款人清单中；需剔除选票或补充BI')
            continue
        if r['invoice_no'] not in latest:
            problems.append(f'{r["invoice_no"]}未出现在最新核验记录中，不能默认外部查询0次')
            continue
        st=latest.get(r['invoice_no'],{})
        # If multiple bills have different dates, check against EARLIEST date to keep safe.
        issue_date=min(date.fromisoformat(b['issue_date']) for b in bypay[key])
        try:check_invoice_policy(r,issue_date,st,payload.get('over_6_month_exception_confirmed') is True)
        except ValueError as exc:problems.append(str(exc));continue
        buckets[key].append(r)
    if problems:raise ValueError('发票准入/映射核对失败：\n'+'\n'.join(problems[:40]))
    if any(not buckets[k] for k in bypay):raise ValueError('部分BI收款人没有候选发票')
    automatic={};coverage=[];methods=[];excess=[]
    manual=payload.get('by_invoice') or {}
    if manual:
        if not isinstance(manual,dict):raise ValueError('by_invoice必须为发票号码->BI字典')
        # Treat explicit links as authoritative ONLY if full invoice list is covered and amounts reconcile.
        valid_bis={b['bi']:b for b in bills}
        if set(manual)!=set(r['invoice_no'] for r in candidates):raise ValueError('人工逐票映射必须覆盖选票名单所有号码，不得遗漏或多填')
        totals=defaultdict(int)
        for r in candidates:
            bi=manual[r['invoice_no']]
            if bi not in valid_bis:raise ValueError(f'{r["invoice_no"]}关联不存在的BI{bi}')
            if stable_party(valid_bis[bi]['payee'])!=stable_party(r['seller']):raise ValueError(f'{r["invoice_no"]}收款人和BI不一致')
            totals[bi]+=alloc.cents(r['total']);automatic[r['invoice_no']]=bi
        for b in bills:
            t=alloc.cents(b['amount']);got=totals[b['bi']]
            if got<t:raise ValueError(f'{b["bi"]}发票金额{got/100}不足{t/100}')
            coverage.append({'bi':b['bi'],'payee':b['payee'],'bill_amount':b['amount'],'invoice_total':str(Decimal(got)/100),
                             'overage':str(Decimal(got-t)/100),'invoice_count':sum(v==b['bi'] for v in automatic.values())})
        methods.append('verified_manual_mapping')
    else:
        for key,note_list in sorted(bypay.items()):
            mapping,stats=alloc.allocate(buckets[key],note_list)
            automatic.update(mapping);coverage.extend(stats['bills']);methods.append(stats['method'])
            excess.extend(stats['unassigned_invoice_nos'])
    chosen={r['invoice_no'] for r in candidates if r['invoice_no'] in automatic}
    rows=[r for r in doc['records'] if r['invoice_no'] in chosen]
    selection=set(r['invoice_no'] for r in candidates)
    exclusions=[]
    for r in doc['records']:
        if r['invoice_no'] in chosen:continue
        exclusions.append({'invoice_no':r['invoice_no'],'seller':r['seller'],'invoice_date':r['invoice_date'],
                           'total':r['total'],'reason':'候选发票未被自动分配（避免超额或重复使用）' if r['invoice_no'] in selection else '第二阶段未选用'})
    chosen_rows=[{'invoice_no':r['invoice_no'],'seller':r['seller'],'invoice_date':r['invoice_date'],
                  'total':r['total'],'bi':automatic[r['invoice_no']]} for r in rows]
    total_bill=sum((alloc.cents(x['amount']) for x in bills))
    total_face=sum((alloc.cents(r['total']) for r in rows))
    output={'stage':'association_plan','customer':conf['customer'],'case_id':conf['case_id'],
            'source_hash':frozen['source_hash'],'bills':bills,'assignments':automatic,'coverage':coverage,
            'method':methods,'selected_count':len(rows),'selected_face_total':str(Decimal(total_face)/100),
            'bill_total':str(Decimal(total_bill)/100),'surplus':str(Decimal(total_face-total_bill)/100),
            'original_candidate_count':len(candidates),'unused_candidate_count':len(excess),
            'status_source':Path(args.status_source).name if args.status_source else Path(args.status_json).name,
            'system_import_confirmed':False,'note':'每张发票仅分配给一笔银承；结果待客户经理核对，非银行系统接受证明'}
    output['plan_sha256']=digest(output)
    stage=case/'stage2';stage.mkdir(exist_ok=True)
    planfile=stage/'association_plan.json'
    if planfile.exists() and load(planfile)['plan_sha256']!=output['plan_sha256']:
        raise ValueError('已有不同方案，禁止覆盖；请归档/新建批次或明确撤销旧方案')
    save(planfile,output)
    csvwrite(stage/'selected_for_bi.csv',chosen_rows,['seller','bi','invoice_no','invoice_date','total'])
    csvwrite(stage/'not_selected.csv',exclusions,['seller','invoice_no','invoice_date','total','reason'])
    csvwrite(stage/'bill_coverage.csv',coverage,['bi','payee','bill_amount','invoice_total','overage','invoice_count'])
    print(json.dumps({'plan':str(planfile),'plan_sha256':output['plan_sha256'],'count':len(rows),
                      'invoice_total':output['selected_face_total'],'bill_total':output['bill_total'],
                      'surplus':output['surplus'],'method':methods},ensure_ascii=False,indent=2))

def association(args):
    case,conf=loadcase(args.case)
    _,doc,frozen=frozen_case(case,conf)
    plan=load(args.plan or case/'stage2'/'association_plan.json')
    expected=plan.pop('plan_sha256',None)
    if not expected or expected!=digest(plan):raise ValueError('关联方案已被修改，指纹校验不通过')
    if args.confirm_plan!=expected:raise ValueError('请人工复核各笔银票金额/对手后，用 --confirm-plan 填写方案SHA256')
    if plan['case_id']!=conf['case_id'] or plan['source_hash']!=frozen['source_hash'] or stable_party(plan['customer'])!=stable_party(conf['customer']):
        raise ValueError('关联计划客户/批次/底稿不一致')
    assign=plan['assignments'];selected=set(assign)
    subset=dict(doc)
    subset['records']=[dict(r,selected=(r['invoice_no'] in selected)) for r in doc['records']]
    subset['summary']=dict(doc['summary'])
    # keep original block_count=0; never rewrite bank template if blocks exist.
    outdata=case/'stage2'/'normalized_for_association.json';save(outdata,subset)
    mapfile=case/'stage2'/'verified_bi_mapping.json';save(mapfile,{'by_invoice':assign})
    opts=['--mode','association','--data',str(outdata),'--template',str(args.template or ROOT/'assets'/'InvoiceInfo.xls'),
          '--bi-mapping',str(mapfile),'--out',args.out,'--engine',args.engine]
    if args.accept_new_template:opts+=['--accept-new-template']
    writer.run(opts)
    save(str(args.out)+'.case.json',{'customer':conf['customer'],'case_id':conf['case_id'],'plan_sha256':expected,
                                     'system_import_confirmed':False,'output':'InvoiceInfo.xls候选版'})

def bi_template(args):
    case,conf=loadcase(args.case)
    _,doc,frozen=frozen_case(case,conf)
    payees=sorted(set(r['seller'] for r in doc['records']))
    sample={'customer':conf['customer'],'case_id':conf['case_id'],'source_hash':frozen['source_hash'],
            'registration_bank_system_confirmed':False,'over_6_month_exception_confirmed':False,
            'approved_bill_limit':'','contract_unpaid_by_payee':{},
            'bills':[{'bi':'','payee':p,'amount':'','issue_date':''} for p in payees],
            'by_invoice':{}}
    output=case/'stage2'/'bills_to_fill.json';save(output,sample)
    print(str(output))

def main(argv=None):
    p=argparse.ArgumentParser(description='BankPro企业发票两阶段Skill，行内模板原样保存')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('init');s.add_argument('--workspace',required=True);s.add_argument('--customer',required=True);s.add_argument('--case-id',default='')
    s=sub.add_parser('prepare');s.add_argument('--case',required=True);s.add_argument('--sources',nargs='+',required=True);s.add_argument('--product-confirmed',default='');s.add_argument('--all-invoice-sheets',action='store_true')
    s=sub.add_parser('registration');s.add_argument('--case',required=True);s.add_argument('--out',required=True);s.add_argument('--template',default='');s.add_argument('--engine',choices=['excel','wps'],default='excel');s.add_argument('--accept-new-template',action='store_true')
    s=sub.add_parser('bi-template');s.add_argument('--case',required=True)
    s=sub.add_parser('plan');s.add_argument('--case',required=True);s.add_argument('--bills',required=True);s.add_argument('--selected-invoices',required=True);
    s.add_argument('--status-source',default='');s.add_argument('--status-json',default='')
    s=sub.add_parser('association');s.add_argument('--case',required=True);s.add_argument('--plan',default='');s.add_argument('--confirm-plan',required=True);s.add_argument('--out',required=True);s.add_argument('--template',default='');s.add_argument('--engine',choices=['excel','wps'],default='excel');s.add_argument('--accept-new-template',action='store_true')
    a=p.parse_args(argv)
    return {'init':init,'prepare':prepare,'registration':reg,'bi-template':bi_template,
            'plan':plan_stage2,'association':association}[a.command](a)
if __name__=='__main__':
    try:main()
    except Exception as ex:print('BLOCK：'+str(ex),file=sys.stderr);sys.exit(2)