#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill a bank-provided legacy .xls using desktop Excel automation only.

Principle: original template read-only; SaveCopyAs, then Value2 cell assignments ONLY;
never create worksheets, set formats, touch validation, insert/delete rows or columns.
Aborts and removes generated file on structural mismatch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OFFICIAL = {
 'registration': ('InvoiceLogInfo.xls','4b439518802b6587f37d9b6efc10b7252f30ff44daf96c513bffe454b0afd766'),
 'association':('InvoiceInfo.xls','c7a599cf8077177ceffdc7bc2140830d176a2cd7189478550c1dc3edc0653c11'),
}

FIELDS = {
 'payee':['收款人','收款人名称','收票人名称','收票人'],
 'buyer':['购方名称','购买方名称','购方'],
 'seller':['销方名称','销售方名称','销方'],
 'invoice_type':['发票类型','票据类型','发票种类'],
 'medium':['发票介质','介质'],
 'invoice_code':['发票代码'],
 'invoice_no':['发票号码','数电发票号码'],
 'invoice_date':['发票开立日期','发票日期','开票日期'],
 'verification6':['校验码后6位','校验码后六位'],
 'product':['货物或应税劳务名称','商品名称','货物名称','商品或服务名称'],
 'total':['发票合计金额','价税合计','价税合计金额','含税金额'],
 'net':['发票不含税金额','不含税金额'],
 'bi':['汇票序号1','银承汇票序号1','汇票序号'],
}

def norm(v):return re.sub(r'[\s*＊★_：:()（）\-]+','',str(v or '')).lower()
FIELD_LOOKUP = {norm(v):k for k, aliases in FIELDS.items() for v in aliases}
REQUIRED_BY_MODE = {
 'registration':{'payee','buyer','seller','invoice_type','medium','invoice_no','invoice_date','product','total','net'},
 'association':{'payee','invoice_type','medium','invoice_no','invoice_date','product','total','net','bi'},
}

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as fp:
        for block in iter(lambda:fp.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def normalize_party(s):return str(s or '').replace('（','(').replace('）',')').replace(' ','').strip()

def open_excel(engine):
    if sys.platform!='win32':raise RuntimeError('银行原生.xls保真写入必须在Windows安装了Microsoft Excel或支持COM的WPS环境中运行。本环境只能执行预处理与审计。')
    try:import win32com.client
    except ImportError:raise RuntimeError('缺少pywin32：py -m pip install pywin32')
    prog_id='Excel.Application' if engine=='excel' else 'ket.Application'
    try:app=win32com.client.DispatchEx(prog_id)
    except Exception as e:raise RuntimeError(f'无法启动{prog_id} COM组件；请改在已安装Microsoft Excel的Windows电脑运行：{e}')
    app.Visible=False
    app.DisplayAlerts=False
    return app

def template_header(ws):
    """Choose header row by distinct known labels; never assume A1 is header."""
    candidates=[]
    # A single COM call replaces hundreds of per-cell header reads.
    last_col=min(int(ws.UsedRange.Columns.Count)+1,119)
    header_values=ws.Range(ws.Cells(1,1),ws.Cells(15,last_col)).Value2
    for rowid in range(1,16):
        fields={}; required_by_star=set();raw={}
        for colid in range(1,last_col+1):
            val=header_values[rowid-1][colid-1]
            if val is None:continue
            label=str(val)
            key=FIELD_LOOKUP.get(norm(label))
            if key and key not in fields:
                fields[key]=colid;raw[key]=label
                if any(x in label for x in ('*','＊','★')):required_by_star.add(key)
        score=len(fields)+int('invoice_no' in fields)*3+int('total' in fields)*3
        candidates.append((score,-rowid,rowid,fields,required_by_star,raw))
    _,__,r,fieldmap,stars,labels=max(candidates,key=lambda x:(x[0],x[1]))
    if len(fieldmap)<6 or 'invoice_no' not in fieldmap or 'total' not in fieldmap:
        raise ValueError('未识别出银行模板字段；停止写入，严禁按旧列序号猜填')
    return r,fieldmap,stars,labels

def validations(cell):
    try:
        v=cell.Validation
        return {'type':int(v.Type),'formula':str(v.Formula1 or ''),'alert':bool(v.ShowError)}
    except Exception:return None

def workbook_snapshot(wb,ws,headerrow,mapping,rows):
    head=[str(ws.Cells(headerrow,i).Value2 or '') for i in range(1, min(int(ws.UsedRange.Columns.Count)+2,120))]
    sampled=[]
    for i in range(headerrow+1, headerrow+rows+1):
        row={}
        for key,col in mapping.items():
            c=ws.Cells(i,col)
            row[key]={'number_format':str(c.NumberFormat),'style':str(c.Style), 'validation':validations(c)}
        sampled.append(row)
    return {'sheets':[str(x.Name) for x in wb.Worksheets], 'head':head,'rowprops':sampled,
            'headerrow':headerrow,'mappedcols':mapping}

def structural_diff(before,after):
    if before['sheets']!=after['sheets']:return '工作表结构或顺序发生改变'
    if before['head']!=after['head']:return '原有列标题发生改变'
    if before['mappedcols']!=after['mappedcols']:return '字段列位置发生改变'
    if before['rowprops']!=after['rowprops']:return '数据区样式/单元格格式/下拉验证发生改变'
    return ''

def clean_data(rows,mode,fieldmap,bi_map):
    # one invoice => one output row, no silent dedupe or default field inference
    errors=[];seen=set();out=[]
    by_invoice=bi_map.get('by_invoice',{}) if isinstance(bi_map,dict) and 'by_invoice' in bi_map else {}
    by_payee=bi_map.get('by_payee',{}) if isinstance(bi_map,dict) and 'by_payee' in bi_map else bi_map
    for ix,r in enumerate(rows,1):
        if not r.get('selected',True):continue
        no=str(r.get('invoice_no') or '')
        if no in seen:errors.append(f'第{ix}条重复号码{no}');continue
        seen.add(no)
        if not re.fullmatch(r'\d{8,20}',no):errors.append(f'第{ix}条发票号码非法{no}')
        if not r.get('buyer'):errors.append(f'第{ix}条购方名称缺失')
        if not r.get('seller'):errors.append(f'第{ix}条销方名称缺失')
        if not r.get('product'):errors.append(f'第{ix}条商品名称缺失（不能凭同一交易对手推测）')
        if not r.get('invoice_type'):errors.append(f'第{ix}条发票类型缺失')
        if not r.get('medium'):errors.append(f'第{ix}条发票介质缺失')
        if not r.get('invoice_date'):errors.append(f'第{ix}条日期缺失')
        if not r.get('total'):errors.append(f'第{ix}条价税合计缺失')
        if r.get('net') in ('',None):errors.append(f'第{ix}条不含税金额缺失（专票不能留空）')
        if r.get('used_amount') is not None and Decimal(str(r['used_amount']))>0:
            errors.append(f'第{ix}条已占用金额>0，禁止未经审核重复导入')
        r=r.copy()
        if mode=='association':
            key=normalize_party(r.get('payee') or r.get('seller'))
            bi = by_invoice.get(no) or by_payee.get(key)
            if not bi:errors.append(f'第{ix}条发票{no}收款人「{r.get("payee")}」缺少对应BI汇票序号')
            else:
                r['bi']=bi
                if not re.fullmatch(r'BI\d{16}',str(bi)):
                    errors.append(f'第{ix}条BI号码格式异常：{bi}')
        out.append(r)
    if errors:raise ValueError('数据校验未通过：\n'+'\n'.join(errors[:30])+('\n...' if len(errors)>30 else ''))
    return out

def excel_value(rec,key):
    if key in ('payee','buyer','seller','invoice_type','medium','invoice_code','invoice_no','product','bi'):
        val=rec.get(key,'')
        return str(val) if val not in (None,'') else None
    if key=='invoice_date':return str(rec['invoice_date']).replace('-','/')
    if key in ('total','net'):
        val=rec.get(key)
        return float(Decimal(str(val))) if val not in ('',None) else None
    if key=='verification6':return str(rec.get('verification6')) if rec.get('verification6') else None
    return None

def check_official(template,mode,unsafe=False):
    name,digest=OFFICIAL[mode]
    # User-provided templates are valid if explicit opt-in but never silently treat other file as official
    if template.name==name and sha256(template)==digest:return
    if not unsafe:raise RuntimeError(f'模板与内置官方{mode}基准不一致；请使用assets/{name}。如确认新模板版本，人工复核后传--accept-new-template。')

def run(argv=None):
    ap=argparse.ArgumentParser(description='仅向银行原始.xls写入单元格值，不改格式')
    ap.add_argument('--data',required=True,help='normalize_invoices.py产生的normalized.json')
    ap.add_argument('--mode',required=True,choices=['registration','association'])
    ap.add_argument('--template',required=True,help='原始.xls模板，勿使用历史失败生成稿')
    ap.add_argument('--out',required=True,help='必须是.xls，必须不同于原模板')
    ap.add_argument('--bi-mapping',default='',help='关联模式必须提供收款人->BI字典JSON')
    ap.add_argument('--prepared',default='',help='原版关联模板的已填非BI字段副本；仅写空白汇票序号列')
    ap.add_argument('--engine',choices=['excel','wps'],default='excel')
    ap.add_argument('--accept-new-template',action='store_true',help='明确授权新模板，并在复核后使用')
    args=ap.parse_args(argv)
    inp=Path(args.data).resolve();template=Path(args.template).resolve();out=Path(args.out).resolve()
    if template==out:raise ValueError('禁止覆盖原模板！')
    if template.suffix.lower()!='.xls' or out.suffix.lower()!='.xls':raise ValueError('输入/输出必须为.xls，不得更改文件格式')
    check_official(template,args.mode,args.accept_new_template)
    doc=json.loads(inp.read_text(encoding='utf-8'))
    if doc.get('summary',{}).get('block_count',0):raise RuntimeError('normalized.json存在阻断项。请先修复issues.csv，禁止强行导入')
    bi_map={}
    if args.mode=='association':
        if not args.bi_mapping:raise ValueError('关联模式必须提供--bi-mapping，不能编造汇票序号')
        raw=json.loads(Path(args.bi_mapping).read_text(encoding='utf-8'))
        if 'by_invoice' in raw or 'by_payee' in raw:
            by_payee={}
            for k,v in raw.get('by_payee',{}).items():
                nk=normalize_party(k)
                if nk in by_payee:raise ValueError(f'多条收款人映射标准化后冲突：{k}')
                by_payee[nk]=str(v)
            bi_map={'by_invoice':{str(k):str(v) for k,v in raw.get('by_invoice',{}).items()},'by_payee':by_payee}
        else:
            for k,v in raw.items():
                nk=normalize_party(k)
                if nk in bi_map:raise ValueError(f'多条映射标准化后冲突：{k}')
                bi_map[nk]=str(v)
    records=clean_data(doc['records'],args.mode,{},bi_map)
    if not records:raise ValueError('选用发票0张')
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError(f'输出已存在，禁止覆盖：{out}')
    prepared=Path(args.prepared).resolve() if args.prepared else None
    if prepared and (args.mode!='association' or prepared.suffix.lower()!='.xls' or prepared in (out,template)):
        raise ValueError('BI极速填列仅支持独立的已预填关联.xls副本')
    app=open_excel(args.engine)
    wb=None
    try:
        # SaveCopyAs produces an exact copy of bank-provided original BEFORE editing any cells.
        src=app.Workbooks.Open(str(template),UpdateLinks=0,ReadOnly=True)
        reference=None
        try:
            if prepared:
                ref_candidates=[]
                for sheet in src.Worksheets:
                    try:
                        hr,fm,st,lb=template_header(sheet)
                        if REQUIRED_BY_MODE['association']<=set(fm):
                            ref_candidates.append((len(fm),sheet,hr,fm))
                    except ValueError:continue
                if not ref_candidates:raise ValueError('原版关联模板字段不足')
                _,refsheet,refrow,refmap=max(ref_candidates,key=lambda x:x[0])
                reference=workbook_snapshot(src,refsheet,refrow,refmap,len(records))
            else:src.SaveCopyAs(str(out))
        finally:src.Close(False)
        if prepared:
            draft=app.Workbooks.Open(str(prepared),UpdateLinks=0,ReadOnly=True)
            try:draft.SaveCopyAs(str(out))
            finally:draft.Close(False)
        wb=app.Workbooks.Open(str(out),UpdateLinks=0,ReadOnly=False)
        candidates=[]
        for sheet in wb.Worksheets:
            try:
                hrow,fields,star,labels=template_header(sheet)
                score=len(fields)+3*int('bi' in fields and args.mode=='association')
                candidates.append((score,sheet,hrow,fields,star,labels))
            except ValueError:continue
        if not candidates:raise ValueError('原模板数据Sheet及字段未识别')
        _,ws,hrow,fields,stars,labels=max(candidates,key=lambda x:x[0])
        mandatory=REQUIRED_BY_MODE[args.mode].union(stars)
        missing=mandatory-set(fields)
        if missing:raise ValueError(f'模板字段不完整：{sorted(missing)}；不要按列序号猜测')
        # prohibit writing beyond preconfigured styles; avoid row insertion/format copying
        data_start=hrow+1
        before=workbook_snapshot(wb,ws,hrow,fields,len(records))
        # Prevent silently extending below template-prepared data cells. Excel
        # otherwise creates default-format rows that may fail bank import.
        for offset in range(len(records)):
            ri=data_start+offset
            for key,col in fields.items():
                cell=ws.Cells(ri,col)
                if str(cell.Style)=='Normal' and str(cell.NumberFormat)=='General':
                    first=ws.Cells(data_start,col)
                    if (str(first.Style),str(first.NumberFormat)) != ('Normal','General'):
                        raise ValueError(f'模板第{ri}行{key}列未预设格式；禁止插入/复制样式，请向系统导出足量行数的原始模板')
        if prepared:
            if structural_diff(reference,before):
                raise ValueError('预填副本与原版模板结构不同，不能只补BI')
            # All prefilled non-BI cells must agree with the approved frozen rows.
            # Reject additional populated data rows and any pre-existing BI.
            last=data_start+len(records)-1
            for key,col in fields.items():
                last_used=int(ws.Cells(ws.Rows.Count,col).End(-4162).Row)
                if last_used>last:raise ValueError(f'{key}列含额外旧数据')
                rng=ws.Range(ws.Cells(data_start,col),ws.Cells(last,col))
                raw=rng.Value2
                actual=(raw,) if len(records)==1 else tuple(v[0] for v in raw)
                expected=[excel_value(r,key) for r in records]
                if key=='bi':
                    if any(v not in (None,'') for v in actual):raise ValueError('已有BI，禁止覆盖或串单')
                    continue
                for got,want in zip(actual,expected):
                    if want is None:
                        ok=got in (None,'')
                    elif key in ('total','net'):
                        try:ok=Decimal(str(got)).quantize(Decimal('.01'))==Decimal(str(want)).quantize(Decimal('.01'))
                        except Exception:ok=False
                    else:
                        ok=isinstance(got,str) and got==want
                    if not ok:raise ValueError(f'预填表{key}与审核计划不一致；请走原版模板批量生成')
            col=fields['bi']
            rng=ws.Range(ws.Cells(data_start,col),ws.Cells(last,col))
            vals=[r['bi'] for r in records]
            rng.Value2=vals[0] if len(vals)==1 else tuple((v,) for v in vals)
            raw=rng.Value2
            actual=(raw,) if len(vals)==1 else tuple(v[0] for v in raw)
            if any(not isinstance(got,str) or got!=v for got,v in zip(actual,vals)):
                raise ValueError('BI极速填列读回失败')
        else:
            # Bulk-write by recognized field, never hard-code the BI column.
            # Preflight all values/blank cells before editing any data.
            for key,col in fields.items():
                rng=ws.Range(ws.Cells(data_start,col),ws.Cells(data_start+len(records)-1,col))
                old=rng.Value2
                old_rows=(old,) if len(records)==1 else tuple(v[0] for v in old)
                if any(v not in (None,'') for v in old_rows):
                    raise ValueError(f'{ws.Name} {key}列存在旧客户数据，禁止覆盖')
                vals=[excel_value(r,key) for r in records]
                if key in mandatory and any(v is None for v in vals):
                    raise ValueError(f'{key}为必填，来源缺少有效值')
                if any(v is not None for v in vals):
                    rng.Value2=vals[0] if len(vals)==1 else tuple((v,) for v in vals)
                if key in ('invoice_no','bi'):
                    actual=rng.Value2
                    read=(actual,) if len(vals)==1 else tuple(v[0] for v in actual)
                    if any(v is not None and (not isinstance(got,str) or got!=v) for got,v in zip(read,vals)):
                        raise ValueError(f'{key}批量写入读回失真，禁止导入')
        after=workbook_snapshot(wb,ws,hrow,fields,len(records))
        diff=structural_diff(before,after)
        if diff:raise RuntimeError('检测到非数据变化：'+diff)
        sheet_name=str(ws.Name)
        wb.Save()
        wb.Close(False);wb=None
        # reopen check (some office suites rewrite .xls on save)
        checkwb=app.Workbooks.Open(str(out),UpdateLinks=0,ReadOnly=True)
        try:
            checkws=checkwb.Worksheets(sheet_name)
            reopen=workbook_snapshot(checkwb,checkws,hrow,fields,len(records))
            diff=structural_diff(before,reopen)
            if diff:raise RuntimeError('保存后结构不符：'+diff)
            for i,r in enumerate(records, data_start):
                if str(checkws.Cells(i,fields['invoice_no']).Value2)!=r['invoice_no']:
                    raise RuntimeError(f'保存后发票号码核对失败：第{i}行')
                if abs(Decimal(str(checkws.Cells(i,fields['total']).Value2))-Decimal(r['total']))>Decimal('0.01'):
                    raise RuntimeError(f'保存后票面金额核对失败：第{i}行')
                if args.mode=='association' and str(checkws.Cells(i,fields['bi']).Value2)!=r['bi']:
                    raise RuntimeError(f'保存后BI映射不一致：第{i}行')
                if normalize_party(checkws.Cells(i,fields['payee']).Value2)!=normalize_party(r['seller']):
                    raise RuntimeError(f'保存后收款人/销方不一致：第{i}行')
        finally:checkwb.Close(False)
        audit={'template':str(template),'template_sha256':sha256(template),'output':str(out),'mode':args.mode,
               'count':len(records),'sum':str(sum((Decimal(r['total']) for r in records),Decimal('0'))),
               'field_mapping':fields,'write_mode':'bi_only' if prepared else 'bulk_fields','structure_checks':'pass','system_import_tested':False}
        Path(str(out)+'.audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(audit,ensure_ascii=False,indent=2))
    except Exception:
        try:
            if wb:wb.Close(False)
        except Exception:pass
        if out.exists():out.unlink()
        raise
    finally:
        try:app.Quit()
        except Exception:pass

if __name__=='__main__':sys.exit(run())