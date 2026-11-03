#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize heterogenous invoice exports. Stdlib only for CSV/XLSX; XLS requires Windows Excel COM.

This module never edits a source workbook or an official bank template.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import xml.etree.ElementTree as ET

CENT = Decimal('0.01')
NS = {'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
ALIASES = {
    'invoice_no': ['数电发票号码','发票号码','电子发票号码','发票流水号'],
    'invoice_code': ['发票代码'],
    'invoice_date': ['开票日期','发票开立日期','发票日期'],
    'seller': ['销售方纳税人名称','销售方名称','销方名称','销方企业名称'],
    'buyer': ['购买方名称','购方名称','购买方纳税人名称'],
    'total_amount': ['价税合计','发票合计金额','价税合计金额','合计金额（含税）','含税金额'],
    'net_amount': ['不含税金额','发票不含税金额','金额'],
    'tax_amount': ['税额','合计税额'],
    'type': ['发票类型','票种'],
    'medium': ['发票介质'],
    'product': ['货物或应税劳务名称','商品名称','货物名称','商品或服务名称','项目名称'],
    'external_count': ['外部核验次数','外部查询次数'],
    'used_amount': ['发票已占用金额','已占用金额'],
    'status': ['发票状态','核验状态'],
}

def norm_header(s):
    return re.sub(r'[\s*＊★:\-－_（()）\[\]【】]', '', str(s or '')).strip().lower()

ALIASES_N = {k: {norm_header(x) for x in v} for k,v in ALIASES.items()}

def parse_money(s, label):
    if s is None or str(s).strip() == '':
        raise ValueError(f'{label} 缺失')
    raw = str(s).strip().replace(',','').replace('￥','').replace('¥','').replace('元','')
    try:
        d = Decimal(raw)
    except InvalidOperation:
        raise ValueError(f'{label} 非有效金额：{s!r}')
    if not d.is_finite() or d < 0:
        raise ValueError(f'{label} 不允许负数或非有限数：{s!r}')
    return d.quantize(CENT, rounding=ROUND_HALF_UP)

def parse_date(s):
    if isinstance(s, (int,float)):
        return (datetime(1899,12,30)+timedelta(days=float(s))).strftime('%Y-%m-%d')
    txt = str(s or '').strip()
    if not txt: raise ValueError('缺失开票日期')
    if re.fullmatch(r'\d{5}(?:\.0+)?', txt):
        return (datetime(1899,12,30)+timedelta(days=float(txt))).strftime('%Y-%m-%d')
    txt = txt.replace('年','-').replace('月','-').replace('日','').replace('/','-')
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})',txt)
    if not m: raise ValueError(f'日期无法识别 {s!r}')
    return datetime(int(m[1]),int(m[2]),int(m[3])).strftime('%Y-%m-%d')

def invoice_number(s):
    if s is None or s == '': raise ValueError('发票号码为空')
    if isinstance(s, (int,float)) or re.search(r'[Ee][+-]\d+',str(s)):
        if len(str(s)) >= 16 or re.search(r'[Ee][+-]\d+',str(s)):
            raise ValueError('发票号码疑似被Excel数值化，可能丢失16位以上精度；须使用原始文本重新导出')
    s = str(s).strip().replace(' ', '')
    if s.endswith('.0'): s=s[:-2]
    if not re.fullmatch(r'\d{8,20}',s):
        raise ValueError(f'发票号码不合规：{s!r}')
    return s

def read_csv(path):
    for enc in ('utf-8-sig','gb18030'):
        try:
            with open(path,'r',encoding=enc,newline='') as fh: return list(csv.reader(fh))
        except UnicodeError: pass
    raise ValueError(f'CSV编码无法识别：{path}')

def excel_col_idx(ref):
    col = re.match(r'[A-Z]+',ref).group()
    n=0
    for x in col:n=n*26+ord(x)-64
    return n-1

def read_xlsx(path):
    """Read cell values from XLSX without touching formatting. Formula cells require cached values."""
    sheets=[]
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        if '[Content_Types].xml' not in names:raise ValueError(f'非有效xlsx：{path}')
        shared=[]
        if 'xl/sharedStrings.xml' in names:
            sst=ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in sst.findall('x:si',NS):
                shared.append(''.join(t.text or '' for t in si.findall('.//x:t',NS)))
        sheet_files=sorted((x for x in names if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',x)),key=lambda s:int(re.search(r'(\d+)\.xml',s)[1]))
        for sheet_file in sheet_files:
            root=ET.fromstring(z.read(sheet_file))
            sparse={};max_col=0
            for row in root.findall('.//x:sheetData/x:row',NS):
                ridx=int(row.get('r'))-1
                for c in row.findall('x:c',NS):
                    cidx=excel_col_idx(c.get('r'));max_col=max(max_col,cidx)
                    kind=c.get('t')
                    v=c.find('x:v',NS); inline=c.find('x:is',NS)
                    if kind=='s' and v is not None:
                        value=shared[int(v.text)]
                    elif kind=='inlineStr' and inline is not None:
                        value=''.join(t.text or '' for t in inline.findall('.//x:t',NS))
                    elif v is not None:
                        value=v.text or ''
                        # Invoice number precision can already be lost when XLSX stored it as numeric.
                        # Preserve an explicit failure marker instead of trusting a 16-20 digit numeric ID.
                        if kind not in ('s','str','inlineStr') and re.fullmatch(r'\d{16,}(?:\.0+)?',value):
                            value='__NUMERIC_INVOICE_ID_UNSAFE__'+value
                    else: continue
                    sparse[(ridx,cidx)]=value
            if sparse:
                max_row=max(i for i,j in sparse)
                grid=[[None]*(max_col+1) for _ in range(max_row+1)]
                for (r,c),v in sparse.items():grid[r][c]=v
                sheets.append(grid)
    return sheets

def read_xls_windows(path):
    if sys.platform!='win32':
        raise RuntimeError('.xls来源文件需在安装Microsoft Excel的Windows上运行；不要转换银行原始模板。客户来源表可另行导出.xlsx或.csv。')
    try:import win32com.client
    except ImportError:raise RuntimeError('请先在Windows安装 pywin32：py -m pip install pywin32')
    app=None
    for prog_id in ('Excel.Application','ket.Application'):
        try:
            app=win32com.client.DispatchEx(prog_id)
            break
        except Exception:pass
    if app is None:raise RuntimeError('未找到Microsoft Excel或支持COM的WPS，无法保真读取旧.xls来源文件')
    app.Visible=False;app.DisplayAlerts=False
    try:
        wb=app.Workbooks.Open(str(path.resolve()),UpdateLinks=0,ReadOnly=True)
        try:
            result=[]
            for sheet in wb.Worksheets:
                raw=sheet.UsedRange.Value2
                if isinstance(raw,tuple):
                    rows=[list(r) if isinstance(r,tuple) else [r] for r in raw]
                else:rows=[[raw]]
                result.append(rows)
            return result
        finally:wb.Close(False)
    finally:app.Quit()

def load_files(paths):
    for filename in paths:
        path=Path(filename).resolve()
        if not path.is_file():raise FileNotFoundError(path)
        if path.suffix.lower()=='.xlsx': grids=read_xlsx(path)
        elif path.suffix.lower()=='.xls': grids=read_xls_windows(path)
        elif path.suffix.lower()=='.csv': grids=[read_csv(path)]
        else:raise ValueError(f'不支持的来源：{path}；请用 xls/xlsx/csv')
        for idx,grid in enumerate(grids,1):yield str(path),idx,grid

def detect_header(grid):
    """Detect column names in complex tax portal exports; favor populated invoice-no column."""
    candidates=[]
    for i,row in enumerate(grid[:25]):
        grouped={}
        for j,value in enumerate(row):
            label=norm_header(value)
            for key,aliases in ALIASES_N.items():
                if label in aliases:grouped.setdefault(key,[]).append(j)
        cols={}
        for key,idxs in grouped.items():
            # e.g. 2026.10 export has blank 发票号码 (C), populated 数电发票号码 (D)
            def density(j):
                nonblank=sum(j<len(r) and r[j] not in (None,'') for r in grid[i+1:i+12])
                label=str(row[j] or '')
                return (nonblank, int('数电发票号码' in label),-j)
            cols[key]=max(idxs,key=density)
        score=sum(k in cols for k in ('invoice_no','invoice_date','seller','total_amount','net_amount','tax_amount'))
        candidates.append((score,len(cols),-i,i,cols))
    chosen=max(candidates) if candidates else (0,0,0,0,{})
    if chosen[0]<3 or 'invoice_no' not in chosen[-1]:
        raise ValueError('找不到有效发票表头。需要至少识别发票号码、日期、销方或金额等字段。')
    return chosen[-2],chosen[-1]

def first_nonblank(row, col):
    if col is None or col>=len(row):return ''
    v=row[col]
    return '' if v is None else str(v).strip()

def detect_buyer_metadata(grid, header_idx):
    for row in grid[:header_idx]:
        for i,v in enumerate(row):
            if norm_header(v) in ('纳税人名称','购方名称','购买方名称') and i+1<len(row):
                if row[i+1]:return str(row[i+1]).strip()
    return ''

def parse_grid(grid, source, sheetno, buyer_override='', product_override=''):
    head,cols=detect_header(grid)
    metadata_buyer=detect_buyer_metadata(grid,head)
    out=[];issues=[]
    for idx,row in enumerate(grid[head+1:],head+2):
        raw_no=first_nonblank(row,cols.get('invoice_no'))
        if not raw_no:continue
        where=f'{Path(source).name} Sheet{sheetno} R{idx}'
        try:
            no=invoice_number(raw_no)
            total_raw=first_nonblank(row,cols.get('total_amount'))
            net_raw=first_nonblank(row,cols.get('net_amount'))
            tax_raw=first_nonblank(row,cols.get('tax_amount'))
            net=parse_money(net_raw,'不含税金额') if net_raw else None
            tax=parse_money(tax_raw,'税额') if tax_raw else None
            if total_raw:total=parse_money(total_raw,'价税合计')
            elif net is not None and tax is not None:total=net+tax
            else:raise ValueError('缺少价税合计，且无法用不含税金额+税额计算')
            if net is not None and tax is not None and abs(total-(net+tax))>CENT:
                raise ValueError(f'价税合计{total}与金额{net}+税额{tax}不符')
            inv_type=first_nonblank(row,cols.get('type'))
            if not inv_type and '数电发票号码' in [str(x or '') for x in grid[head]]:
                inv_type='全面数字化电子发票'
            if '数电' in inv_type or '全电' in inv_type:inv_type='全面数字化电子发票'
            medium=first_nonblank(row,cols.get('medium'))
            if not medium and ('数电' in first_nonblank(row,cols.get('type')) or '全面数字' in inv_type):medium='电子发票'
            buyer=first_nonblank(row,cols.get('buyer')) or metadata_buyer or buyer_override
            seller=first_nonblank(row,cols.get('seller'))
            product=first_nonblank(row,cols.get('product')) or product_override
            external=first_nonblank(row,cols.get('external_count'))
            used=first_nonblank(row,cols.get('used_amount'))
            r={
              'invoice_no':no,
              'invoice_code':first_nonblank(row,cols.get('invoice_code')),
              'invoice_date':parse_date(first_nonblank(row,cols.get('invoice_date'))),
              'buyer':buyer,'seller':seller,'payee':seller,
              'invoice_type':inv_type,'medium':medium,'product':product,
              'total':str(total),'net':str(net) if net is not None else '',
              'tax':str(tax) if tax is not None else '',
              'external_count':int(Decimal(external)) if external else None,
              'used_amount':str(parse_money(used,'已占用金额')) if used else None,
              'status':first_nonblank(row,cols.get('status')),
              'source_file':Path(source).name,'source_sheet':sheetno,'source_row':idx,
              'selected':True,'reason':'',
            }
            if not r['seller']:issues.append({'severity':'BLOCK','invoice_no':no,'where':where,'issue':'销方名称缺失'})
            if not r['buyer']:issues.append({'severity':'BLOCK','invoice_no':no,'where':where,'issue':'购方名称缺失'})
            if not r['product']:issues.append({'severity':'BLOCK','invoice_no':no,'where':where,'issue':'商品名称缺失：禁止由其他月份同销方推断'})
            if not r['invoice_type']:issues.append({'severity':'BLOCK','invoice_no':no,'where':where,'issue':'发票类型无法证实'})
            if not r['medium']:issues.append({'severity':'BLOCK','invoice_no':no,'where':where,'issue':'发票介质缺失'})
            out.append(r)
        except (ValueError,InvalidOperation) as e:
            issues.append({'severity':'BLOCK','invoice_no':raw_no,'where':where,'issue':str(e)})
    return out,issues

def load_status_lookup(path):
    if not path:return {}
    merged={}
    for filename,idx,grid in load_files([path]):
        header,cols=detect_header(grid)
        for row in grid[header+1:]:
            raw=first_nonblank(row,cols.get('invoice_no'))
            if not raw:continue
            no=invoice_number(raw)
            if no in merged:raise ValueError(f'核验来源重复发票号码：{no}')
            external=first_nonblank(row,cols.get('external_count'))
            used=first_nonblank(row,cols.get('used_amount'))
            merged[no]={
             'external_count':int(Decimal(external)) if external else None,
             'used_amount':str(parse_money(used,'已占用金额')) if used else None,
             'verification_status':first_nonblank(row,cols.get('status')),
            }
    return merged

def export_csv(path, records, fields):
    with open(path,'w',encoding='utf-8-sig',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(records)

def run(argv=None):
    p=argparse.ArgumentParser(description='不同格式发票规范化与审计；不触碰银行模板')
    p.add_argument('--sources',nargs='+',required=True,help='原始发票xls/xlsx/csv文件列表')
    p.add_argument('--status-source',help='另提供系统发票录入列表以合并外部核验次数')
    p.add_argument('--buyer',default='',help='当来源未提供购方时，由用户确认后明确传入')
    p.add_argument('--product-override',default='',help='仅由用户核实商品名称后明确传入，勿根据同公司其它月份推定')
    p.add_argument('--exclude-external',type=int,default=None,help='剔除特定外部核验次数，如2')
    p.add_argument('--max-total',type=str,default='',help='可选：限制选中总票面金额（元），采用确定性贪心并标注非全局最优')
    p.add_argument('--all-invoice-sheets',action='store_true',help='默认每个文件只处理第一个有发票数据的工作表，避免把附件/说明工作表重复计入；需要全表时显式启用')
    p.add_argument('--output-dir',required=True)
    args=p.parse_args(argv)
    outdir=Path(args.output_dir);outdir.mkdir(parents=True,exist_ok=True)
    records=[];issues=[]
    per_source=Counter()
    for filename in args.sources:
        picked=0
        for absolute,idx,grid in load_files([filename]):
            try:
                rows,warnings=parse_grid(grid,absolute,idx,args.buyer,args.product_override)
                if not rows:continue
                if picked and not args.all_invoice_sheets:
                    issues.append({'severity':'WARN','invoice_no':'','where':f'{Path(filename).name} Sheet{idx}',
                                   'issue':f'本表另有{len(rows)}条数据，但默认仅取首张发票明细工作表；如确为有效分表请带--all-invoice-sheets重新提取'})
                    continue
                records.extend(rows);issues.extend(warnings)
                per_source[absolute]+=len(rows);picked+=1
            except ValueError as exc:
                if '找不到有效发票表头' not in str(exc):
                    issues.append({'severity':'BLOCK','invoice_no':'','where':f'{filename} Sheet{idx}','issue':str(exc)})
        if per_source[str(Path(filename).resolve())]==0:
            issues.append({'severity':'BLOCK','invoice_no':'','where':Path(filename).name,'issue':'该来源文件未提取到任何发票；禁止静默跳过'})
    dup=Counter(x['invoice_no'] for x in records)
    for no,cnt in dup.items():
        if cnt>1:issues.append({'severity':'BLOCK','invoice_no':no,'where':'多来源','issue':f'重复出现{cnt}次；不得自动去重后悄悄跳过'})
    status=load_status_lookup(args.status_source) if args.status_source else {}
    for r in records:
        if r['invoice_no'] in status:
            st=status[r['invoice_no']]
            r['external_count']=st['external_count']
            r['used_amount']=st['used_amount']
            r['status']=st['verification_status'] or r['status']
        if r['used_amount'] is not None and Decimal(r['used_amount'])>0:
            issues.append({'severity':'BLOCK','invoice_no':r['invoice_no'],'where':r['source_file'],'issue':'已占用金额>0，必须核实剩余额度及重复融资'})
        if r['status'] and r['status'] not in ('正常','Y','已核验','有效'):
            issues.append({'severity':'BLOCK','invoice_no':r['invoice_no'],'where':r['source_file'],'issue':f'异常发票状态：{r["status"]}'})
        if args.exclude_external is not None and r['external_count']==args.exclude_external:
            r['selected']=False;r['reason']=f'按要求剔除外部核验{args.exclude_external}次'
    if args.max_total:
        cap=parse_money(args.max_total,'金额上限')
        remaining=[r for r in records if r['selected']]
        # deterministic; zero first, missing count last; recent invoices first, amount small first for fit
        remaining.sort(key=lambda x:(x['external_count'] is None,x['external_count'] or 0,-int(x['invoice_date'].replace('-','')),Decimal(x['total']),x['invoice_no']))
        s=Decimal('0')
        for r in remaining:
            v=Decimal(r['total'])
            if s+v<=cap:s+=v
            else:r['selected']=False;r['reason']='金额上限贪心筛选剔除（非最优组合保证）'
    total=sum((Decimal(r['total']) for r in records),Decimal('0'))
    selected=[r for r in records if r['selected']]
    excluded=[r for r in records if not r['selected']]
    groups=defaultdict(lambda:{'count':0,'amount':Decimal('0')})
    for r in selected:
        item=groups[r['seller']];item['count']+=1;item['amount']+=Decimal(r['total'])
    if any(r['external_count'] is None for r in records):
        issues.append({'severity':'WARN','invoice_no':'','where':'全部来源','issue':'部分或全部发票未提供外部核验次数；不能推定为0次'})
    summary={
      'input_count':len(records),'input_amount':str(total),
      'selected_count':len(selected),'selected_amount':str(sum((Decimal(r['total']) for r in selected),Decimal('0'))),
      'excluded_count':len(excluded),'excluded_amount':str(sum((Decimal(r['total']) for r in excluded),Decimal('0'))),
      'by_seller':{k:{'count':v['count'],'amount':str(v['amount'])} for k,v in groups.items()},
      'block_count':sum(x['severity']=='BLOCK' for x in issues),
      'warning_count':sum(x['severity']=='WARN' for x in issues),
      'selection_method':'deterministic_greedy_not_optimal' if args.max_total else 'keep_all_except_user_exclusions',
      'source_files':[Path(x).name for x in args.sources],
    }
    (outdir/'normalized.json').write_text(json.dumps({'summary':summary,'records':records,'issues':issues},ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['invoice_no','invoice_date','buyer','seller','product','total','net','tax','external_count','used_amount','invoice_type','medium','selected','reason','source_file','source_row']
    export_csv(outdir/'selected.csv',selected,fields)
    export_csv(outdir/'excluded.csv',excluded,fields)
    export_csv(outdir/'issues.csv',issues,['severity','invoice_no','where','issue'])
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary['block_count']:
        print('⚠ 存在阻断项。已保存审计清单，但正式写入前必须修复。',file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':sys.exit(run())