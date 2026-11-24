#!/usr/bin/env python3
"""Offline PDF plan and confirmed split/merge; original files never modified."""
import argparse,json,hashlib,re,tempfile,shutil
from pathlib import Path
import fitz

ORDER=['入库单','承诺函','发票外部核验次数说明函','发票早于银承开立日说明函','电子发票说明函','存单','冻结凭证','存款入账凭证','移交明细表','购销合同','发票']
CORE=['入库单','承诺函','存单','存款入账凭证','移交明细表','购销合同','发票']
ALIASES={
'排除':['银行承兑汇票业务申请书','提票申请书','质押合同','出库单'],
'入库单':['出入库单','出入库登记单','入库单'],
'承诺函':['承诺函'],
'发票外部核验次数说明函':['发票外部核验次数说明函','外部核验次数说明函','说明函（检核次数）','说明函(检核次数)','核验次数说明函','检核次数说明函'],
'发票早于银承开立日说明函':['发票早于银承开立日说明函','发票早于2个月说明函','发票早于银承开立日'],
'电子发票说明函':['电子发票说明函','说明函（电子发票）','说明函(电子发票)'],
'存单':['单位定期存单','存单'],'冻结凭证':['冻结凭证'],'存款入账凭证':['存款入账凭证','存款入账回单'],'移交明细表':['移交明细表'],
'购销合同':['购销合同','采购合同','销售合同'],'发票':['增值税专用发票','增值税普通发票','电子发票'],'其他说明函':['说明函']}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def safe(s):
    s=str(s).strip()
    if not s or re.search(r'[\\/:*?"<>|\x00-\x1f]',s) or s in ('.','..') or s.endswith('.'):raise ValueError('文件名字段不合法')
    return s
def classify(text):
    text=''.join(text.split())[:160]
    hits=[(len(a),k,a) for k,aliases in ALIASES.items() for a in aliases if a in text]
    if not hits:return []
    # Longest specific title beats nested generic aliases (电子发票/说明函等).
    best=max(x[0] for x in hits)
    return sorted({k for n,k,a in hits if n==best})
def inspect(path,preview=None):
    rows=[]
    with fitz.open(path) as doc:
        for i,p in enumerate(doc,1):
            if preview:p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(preview/f'page-{i:04}.png')
            # Prefer top-of-page title over body mentions; candidates remain unconfirmed.
            text=p.get_text(clip=fitz.Rect(0,0,p.rect.width,p.rect.height*.28))
            rows.append({'page':i,'title_candidates':classify(text),'text_excerpt':''.join(text.split())[:100]})
    starts=[];last=None
    for row in rows:
        hits=row['title_candidates']
        if len(hits)==1 and hits[0]!=last:
            starts.append((row['page'],hits[0]));last=hits[0]
    proposed=[{'kind':k,'start':p,'end':starts[i+1][0]-1 if i+1<len(starts) else len(rows)} for i,(p,k) in enumerate(starts)] if starts and starts[0][0]==1 else []
    return {'path':str(path.resolve()),'sha256':sha(path),'pages':len(rows),'page_candidates':rows,'proposed_segments':proposed,'segments':[]}
def plan(scan=None,folder=None,preview=None):
    paths=[]
    if scan:paths.append(Path(scan))
    nonpdf=[]
    if folder:
        for p in sorted(Path(folder).iterdir()):
            if p.is_file():
                if p.suffix.lower()=='.pdf':paths.append(p)
                else:nonpdf.append(p.name)
    paths=list(dict.fromkeys(p.resolve() for p in paths))
    if not paths:raise ValueError('没有PDF')
    sources=[]
    for i,p in enumerate(paths,1):
        sub=Path(preview)/f'{i:03}' if preview else None
        if sub:sub.mkdir(parents=True,exist_ok=True)
        sources.append(inspect(p,sub))
    return {'customer':'','term':'','period':'','confirmed':False,'required':CORE.copy(),'sources':sources,'non_pdf_files':nonpdf,'invoice_final_selection_confirmed':False,'system_import_confirmed':False}
def filename(m,s):
    k=s['kind'];customer=safe(m['customer'])
    if k=='发票':
        payee=safe(s.get('payee',''));month=s.get('month','')
        if month and not re.fullmatch(r'\d{4}(0[1-9]|1[0-2])',month):raise ValueError('发票月份须YYYYMM')
        return '_'.join([customer,'发票',payee]+([month] if month else []))+'.pdf'
    if k=='其他说明函':
        k=safe(s.get('title',''))
        if not k.endswith('说明函') and '说明函' not in k:raise ValueError('其他说明函须真实标题')
        if k in ORDER or k=='说明函':raise ValueError('使用专类或更明确的真实标题')
    return '_'.join([customer,safe(m['term']),safe(m['period']),safe(k)])+'.pdf'
def build(m,out):
    if m.get('confirmed') is not True:raise ValueError('须确认客户、批次和各页归属')
    if m['term'] not in ('半年期','一年期'):raise ValueError('期限须明确')
    safe(m['customer']);safe(m['period'])
    out=Path(out)
    if out.exists():raise FileExistsError('输出目录已存在')
    required=set(m['required'])
    if not required or not required<=set(ORDER):raise ValueError('请核实本笔必需材料')
    groups={};present=set();excluded=[];hashes=set();months={}
    for src in m['sources']:
        p=Path(src['path']);h=sha(p)
        if h!=src['sha256'] or h in hashes:raise ValueError('原件变化或重复PDF')
        hashes.add(h)
        with fitz.open(p) as d:n=len(d)
        used=set()
        for seg in src['segments']:
            k=seg['kind'];a,b=seg['start'],seg['end']
            if type(a) is not int or type(b) is not int or not 1<=a<=b<=n:raise ValueError('页码越界')
            pages=set(range(a,b+1))
            if pages&used:raise ValueError('重复页')
            used|=pages
            if k=='排除':
                reason=seg.get('reason','').strip()
                if not reason:raise ValueError('排除页须明确原因')
                excluded.append({'source':str(p),'start':a,'end':b,'reason':reason});continue
            if k not in ORDER and k!='其他说明函':raise ValueError('未知或待确认材料：'+k)
            name=filename(m,seg)
            if k=='发票':
                payee=seg['payee'];mode=bool(seg.get('month'))
                if payee in months and months[payee]!=mode:raise ValueError('同一对手分月与不分月混用')
                months[payee]=mode
            present.add(k);groups.setdefault(name,[]).append((p,a,b))
        if used!=set(range(1,n+1)):raise ValueError('存在未分类页：'+p.name)
    missing=required-present
    if missing:raise ValueError('缺少必需材料：'+','.join(sorted(missing)))
    if '发票' in present and not (m.get('invoice_final_selection_confirmed') is True and m.get('system_import_confirmed') is True):raise ValueError('发票最终选票与实际系统导入须确认')
    if not groups:raise ValueError('没有上传文件')
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(tempfile.mkdtemp(prefix='.pack-',dir=out.parent))
    try:
        report=[]
        for name,items in groups.items():
            expected=sum(b-a+1 for _,a,b in items)
            with fitz.open() as dst:
                for p,a,b in items:
                    with fitz.open(p) as doc:dst.insert_pdf(doc,from_page=a-1,to_page=b-1)
                dst.save(tmp/name)
            with fitz.open(tmp/name) as check:
                if len(check)!=expected:raise ValueError('页数核对失败')
            report.append({'file':name,'pages':expected,'sources':[{'path':str(p),'start':a,'end':b} for p,a,b in items]})
        info={'file_count':len(report),'files':report,'excluded':excluded,'non_pdf_files':m.get('non_pdf_files',[]),'missing':[]}
        (tmp/'上传材料清单.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        (tmp/'上传材料清单.txt').write_text('\n'.join([f"有效PDF：{len(report)}份",*[f"{r['file']} | {r['pages']}页" for r in report],*[f"排除：{r['source']} 第{r['start']}-{r['end']}页 {r['reason']}" for r in excluded],*[f"非PDF未纳入：{x}" for x in m.get('non_pdf_files',[])]]),encoding='utf-8')
        if out.exists():raise FileExistsError('输出目录已存在')
        tmp.rename(out)
    finally:
        if tmp.exists():shutil.rmtree(tmp)
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('inspect');q.add_argument('--scan');q.add_argument('--folder');q.add_argument('--out',required=True);q.add_argument('--preview-dir')
    q=sub.add_parser('build');q.add_argument('--manifest',required=True);q.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='inspect':Path(a.out).write_text(json.dumps(plan(a.scan,a.folder,a.preview_dir),ensure_ascii=False,indent=2),encoding='utf-8')
    else:build(json.loads(Path(a.manifest).read_text(encoding='utf-8-sig')),a.out)
if __name__=='__main__':main()
