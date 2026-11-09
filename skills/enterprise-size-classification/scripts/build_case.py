"""Prepare one private case from confirmed data and genuine PDF/image evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile
from classify import classify
from preflight import inspect as preflight_inspect
from template_io import patch, manifest, digest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE={'finance':'资产营收佐证材料.pdf','staff':'从业人数佐证材料.pdf','industry':'行业类别佐证材料.pdf'}

def pdf_from_sources(paths, output):
    from pypdf import PdfReader, PdfWriter
    from PIL import Image, ImageOps
    writer=PdfWriter()
    if not paths: raise ValueError('missing evidence source')
    with tempfile.TemporaryDirectory() as tmp:
        for index,source in enumerate(paths):
            p=Path(source)
            if p.suffix.lower() in {'.png','.jpg','.jpeg','.tif','.tiff','.webp'}:
                with Image.open(p) as image:
                    rgb=ImageOps.exif_transpose(image).convert('RGB')
                    p=Path(tmp)/f'{index}.pdf'; rgb.save(p,'PDF',resolution=150)
            reader=PdfReader(str(p))
            if reader.is_encrypted or not reader.pages: raise ValueError('unreadable PDF')
            for page in reader.pages:
                if not page.extract_text().strip() and not page.get('/Resources',{}).get('/XObject'):
                    raise ValueError('blank evidence page')
                writer.add_page(page)
        if len(paths)==1 and Path(paths[0]).suffix.lower()=='.pdf': shutil.copyfile(paths[0],output)
        else:
            with open(output,'wb') as f: writer.write(f)

def build(case, rules, outdir):
    company=case['company'].strip()
    if not company or any(c in company for c in '/\\:*?"<>|') or company in {'.','..'}: raise ValueError('unsafe or empty company name')
    branch=case['branch']
    if branch in {'individual_business','condition_change'}:
        return {'status':'not_required_under_template','files':[],'note':'按本模板不需全套划型，先核本次有效行内要求'}
    if branch not in {'new','annual_update','annual_no_update'}: raise ValueError('unknown branch')
    values={'A2':'企业名称：'+company,'B4':'/','B6':'/','B7':'/','B9':'','B10':'','B16':'','B22':''}
    result=None
    if branch=='annual_no_update': values['B7']='存量授信客户年审，本次未涉及划型更新。'
    else:
        readiness=preflight_inspect(case,rules)
        if readiness['status']!='ready_for_formal_preparation':
            gaps=[x['code']+':'+x['field'] for x in readiness['issues'] if x['blocking']]
            raise ValueError('preflight blocked: '+', '.join(gaps))
        required=['identity_confirmed','industry_confirmed','metrics_confirmed','period_confirmed','policy_applicability_confirmed']
        if any(case.get(k) is not True for k in required): raise ValueError('identity, industry, metrics, period and policy confirmations required')
        if 'employees' in rules['industries'].get(case['industry'],{}) and case.get('staff_basis') not in {'employees_year_end','annual_average'}:
            raise ValueError('confirmed year-end or annual-average employee headcount required; insured count is not interchangeable')
        if not case.get('reporting_year') or not case.get('decision_date'): raise ValueError('reporting year and decision date required')
        from datetime import date
        decision=date.fromisoformat(case['decision_date'])
        year=int(case['reporting_year'])
        if year!=decision.year-1 and not case.get('period_exception_basis'): raise ValueError('non-prior-year data needs explicit policy basis')
        if not rules.get('effective_from') or decision<date.fromisoformat(rules['effective_from']): raise ValueError('rules not effective on decision date')
        if rules.get('effective_to') and decision>date.fromisoformat(rules['effective_to']): raise ValueError('rules expired')
        result=classify(case['industry'],case['metrics'],rules)
        if result['status']!='bank_rule_calculated' or not result['complete_indicators']: raise ValueError('approved bank rules and complete core indicators required for formal template')
        for metric in rules['industries'][case['industry']]:
            provenance=case.get('metric_sources',{}).get(metric,{})
            if not provenance.get('source') or not provenance.get('location') or not provenance.get('unit') or provenance.get('year')!=year:
                raise ValueError(f'{metric}: source, location, unit and reporting year required')
        for key in EVIDENCE:
            ev=case['evidence'][key]
            if ev.get('company')!=company or ev.get('identity_verified') is not True: raise ValueError(f'{key}: identity not verified')
            if key in {'finance','staff'} and ev.get('year')!=year: raise ValueError(f'{key}: wrong evidence year')
            if not ev.get('source') or not ev.get('paths'): raise ValueError(f'{key}: evidence provenance missing')
            if ev.get('content_verified') is not True: raise ValueError(f'{key}: source contents must be read and verified')
        methods=case['methods']
        if methods['industry'] not in range(1,6) or methods['staff'] not in range(1,6) or methods['finance'] not in range(1,4): raise ValueError('method number inconsistent with original template')
        values['B4' if branch=='new' else 'B6']='为新客户，需按照检核表提供所有划型材料并填写检核表。' if branch=='new' else '存量授信客户年审，涉及划型更新，重新提供全套划型材料并填写检核表。'
        values['B9']=result['size']
        for key,cell in [('industry','B10'),('staff','B16'),('finance','B22')]:
            values[cell]=f'采用方法（{methods[key]}），\n命名规则：“{Path(EVIDENCE[key]).stem}”'
    out=Path(outdir)
    if out.exists() and any(out.iterdir()): raise ValueError('output directory must be empty; do not mix cases')
    out.mkdir(parents=True,exist_ok=True)
    files=[]
    try:
        if result:
            for key,name in EVIDENCE.items():
                pdf_from_sources(case['evidence'][key]['paths'],out/name); files.append(out/name)
        mf=manifest(); template=ROOT/'assets'/mf['file']
        xlsx=out/(company+'授信企业划型检核表.xlsx')
        patch(template,xlsx,values,mf['sha256']);files.insert(0,xlsx)
        archive=out/(company+'企业划型材料.zip')
        with ZipFile(archive,'w') as z:
            for p in files: z.write(p,p.name)
        with ZipFile(archive) as z:
            if z.testzip() is not None or len(z.namelist())!=(4 if result else 1): raise ValueError('package validation failed')
        return {'status':'prepared_not_uploaded','files':[p.name for p in files],'zip':str(archive),
                'hashes':{p.name:digest(p) for p in files},'calculation':result,
                'state_notice':'原模板B26/B27既有文字保留，不证明本次已检视或已上挂；须经办人实际核对。'}
    except Exception:
        for p in files:
            if p.exists(): p.unlink()
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--rules',default=str(ROOT/'references/public_rules.json'));p.add_argument('--out',required=True);p.add_argument('--audit',required=True)
    a=p.parse_args()
    case=json.loads(Path(a.input).read_text(encoding='utf-8'));rules=json.loads(Path(a.rules).read_text(encoding='utf-8'))
    audit=Path(a.audit).resolve();out=Path(a.out).resolve()
    sources={Path(a.input).resolve(),Path(a.rules).resolve()}
    sources.update(Path(v).resolve() for ev in case.get('evidence',{}).values() for v in ev.get('paths',[]))
    if audit.is_relative_to(out) or audit in sources or audit.suffix.lower()!='.json':
        raise ValueError('audit must be a separate JSON outside output and source files')
    audit.parent.mkdir(parents=True,exist_ok=True)
    result=build(case,rules,a.out)
    audit.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'files':result['files']},ensure_ascii=False))

if __name__=='__main__': main()
