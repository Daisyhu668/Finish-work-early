#!/usr/bin/env python3
"""Offline PDF plan and confirmed split/merge; original files never modified."""
import argparse,json,hashlib,re,tempfile,shutil
from pathlib import Path
import fitz

ORDER=['提票申请书','质押合同','出库单','入库单','承诺函','说明函','存单','冻结凭证','存款入账凭证','移交明细表','购销合同','发票']
ALIASES={'提票申请书':['提票申请书','银行承兑汇票业务申请书'],'质押合同':['质押合同'],'出库单':['出库单'],'入库单':['入库单'],'承诺函':['承诺函'],'说明函':['说明函'],'存单':['单位定期存单','存单'],'冻结凭证':['冻结凭证'],'存款入账凭证':['存款入账凭证','存款入账回单'],'移交明细表':['移交明细表'],'购销合同':['购销合同','采购合同','销售合同'],'发票':['增值税专用发票','增值税普通发票','电子发票']}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def safe(s):
    s=str(s).strip()
    if not s or re.search(r'[\\/:*?"<>|\x00-\x1f]',s) or s in ('.','..'): raise ValueError('文件名字段不合法')
    return s
def filename(customer,term,period,kind,payee='',month=''):
    if kind=='发票':
        if not payee: raise ValueError('发票须有已核实交易对手')
        return '_'.join([safe(customer),'发票',safe(payee)]+([safe(month)] if month else []))+'.pdf'
    return '_'.join(map(safe,[customer,term,period,kind]))+'.pdf'

def inspect(scan,preview_dir=None):
    with fitz.open(scan) as doc:
        result=[]
        if preview_dir: Path(preview_dir).mkdir(parents=True,exist_ok=True)
        for i,page in enumerate(doc,1):
            if preview_dir: page.get_pixmap(matrix=fitz.Matrix(1.0,1.0),alpha=False).save(Path(preview_dir)/f'page-{i:04}.png')
            text=''.join(page.get_text().split())[:120]
            hits=[k for k,vs in ALIASES.items() if any(v in text for v in vs)]
            result.append({'page':i,'title_candidates':hits,'text_excerpt':text[:80]})
        return result

def proposed_segments(candidates):
    # Conservative suggestions only; unknown pages belong to the prior candidate,
    # but every boundary and page must be verified visually before build.
    starts=[]; last=-1
    for row in candidates:
        hits=row['title_candidates']
        if len(hits)!=1: continue
        k=hits[0]; idx=ORDER.index(k)
        if idx>last:
            starts.append((row['page'],k));last=idx
    if not starts or starts[0][0]!=1: return []
    return [{'kind':k,'start':p,'end':(starts[i+1][0]-1 if i+1<len(starts) else len(candidates))}
            for i,(p,k) in enumerate(starts)]

def build(manifest,out):
    if manifest.get('confirmed') is not True: raise ValueError('先人工确认全部页码、分类和客户归属')
    customer=manifest['customer'];term=manifest['term'];period=manifest['period']
    if term not in ('半年期','一年期'): raise ValueError('期限须明确')
    scan=Path(manifest['scan']);out=Path(out)
    if sha(scan)!=manifest['scan_sha256']: raise ValueError('扫描源已变化')
    if out.exists(): raise FileExistsError('输出目录已存在，禁止覆盖')
    groups={}; used=set(); required=set(manifest['required']); optional=set(manifest.get('not_applicable',[]))
    if not required or required&optional or not (required|optional)<=set(ORDER): raise ValueError('请明确本笔必需材料及不适用项')
    if set(ORDER)-required-optional: raise ValueError('每个预置材料须明确必需或不适用')
    present=set(); source_hashes={sha(scan)}
    with fitz.open(scan) as src:
        for item in manifest['segments']:
            kind=item['kind'];start=int(item['start']);end=int(item['end'])
            if kind not in ORDER and kind!='待确认': raise ValueError('未知分类')
            if not 1<=start<=end<=len(src): raise ValueError('页码越界')
            pages=set(range(start,end+1))
            if used&pages: raise ValueError('扫描页重复分配')
            used|=pages; present.add(kind)
            name=filename(customer,term,period,kind,item.get('payee',''),item.get('month',''))
            groups.setdefault(name,[]).append((scan,start,end))
        if used!=set(range(1,len(src)+1)): raise ValueError('扫描页存在遗漏')
    for item in manifest.get('external',[]):
        if item.get('verified') is not True: raise ValueError('外部PDF须确认属于本客户本批次')
        path=Path(item['path']);kind=item['kind']
        if kind not in ('购销合同','发票'): raise ValueError('外部分类须为合同或发票')
        source_hash=sha(path)
        if source_hash!=item['sha256']: raise ValueError('外部源文件已变化')
        if source_hash in source_hashes: raise ValueError('发现内容相同的重复PDF')
        source_hashes.add(source_hash)
        if path.resolve()==scan.resolve(): raise ValueError('扫描文件不得重复加入')
        with fitz.open(path) as doc: n=len(doc)
        name=filename(customer,term,period,kind,item.get('payee',''),item.get('month',''))
        if any(p.resolve()==path.resolve() for items in groups.values() for p,_,_ in items): raise ValueError('外部PDF重复')
        groups.setdefault(name,[]).append((path,1,n));present.add(kind)
    if '待确认' in present: raise ValueError('存在待确认页，禁止输出正式上传包')
    if '发票' in present and manifest.get('invoice_final_selection_confirmed') is not True:
        raise ValueError('最终发票PDF须经选票与BI映射核对确认；不擅自剔除原件')
    if '发票' in present and manifest.get('system_import_confirmed') is not True:
        raise ValueError('实际系统发票关联成功后才出最终提交包')
    if present&optional: raise ValueError('标为不适用的材料却出现在提交包，请修正清单')
    missing=sorted(required-present)
    if missing: raise ValueError('缺少必需材料：'+','.join(missing))
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(tempfile.mkdtemp(prefix='.material-pack-',dir=out.parent))
    try:
        report=[]
        for name,items in groups.items():
            expected=sum(end-start+1 for _,start,end in items)
            with fitz.open() as dst:
                for path,start,end in items:
                    with fitz.open(path) as doc: dst.insert_pdf(doc,from_page=start-1,to_page=end-1)
                dst.save(tmp/name)
            with fitz.open(tmp/name) as check:
                if len(check)!=expected: raise ValueError('输出页数不符：'+name)
            report.append({'file':name,'pages':expected,'sources':[{'path':str(p),'start':a,'end':b} for p,a,b in items]})
        (tmp/'上传材料清单.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (tmp/'上传材料清单.txt').write_text('\n'.join(f"{r['file']} | {r['pages']}页" for r in report),encoding='utf-8')
        if out.exists(): raise FileExistsError('输出目录已存在')
        tmp.rename(out)
    finally:
        if tmp.exists(): shutil.rmtree(tmp)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    s=sub.add_parser('inspect');s.add_argument('--scan',required=True);s.add_argument('--out',required=True);s.add_argument('--preview-dir',default='')
    s=sub.add_parser('build');s.add_argument('--manifest',required=True);s.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='inspect':
        candidates=inspect(a.scan,a.preview_dir)
        result={'scan':a.scan,'scan_sha256':sha(a.scan),'confirmed':False,'customer':'','term':'','period':'','required':[],'not_applicable':[],'segments':[],'external':[],'invoice_final_selection_confirmed':False,'system_import_confirmed':False,'page_candidates':candidates,'proposed_segments':proposed_segments(candidates)}
        Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    else: build(json.loads(Path(a.manifest).read_text(encoding='utf-8-sig')),a.out)
if __name__=='__main__': main()
