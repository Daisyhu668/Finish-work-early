"""Read-only readiness check: report all material gaps before formal preparation."""
import argparse
from datetime import date
import json
from pathlib import Path
from classify import classify

ROOT=Path(__file__).resolve().parents[1]

def inspect(case,rules):
    issues=[]
    def add(code,message,field,blocking=True):
        issues.append({'code':code,'field':field,'message':message,'blocking':blocking})
    if not isinstance(case,dict) or not isinstance(rules,dict): raise ValueError('case and rules must be JSON objects')
    company=case.get('company')
    if not isinstance(company,str) or not company.strip(): add('identity_missing','缺企业正式名称','company')
    branch=case.get('branch')
    if branch not in {'new','annual_update','annual_no_update','condition_change','individual_business'}:
        add('branch_missing','请确认本期新客/年审更新/不更新/条件变更/个体户分支','branch')
    if branch in {'annual_no_update','condition_change','individual_business'}:
        return {'status':'blocked' if issues else 'checklist_only' if branch=='annual_no_update' else 'not_required_under_template','issues':issues,'calculation':None}
    for key,label in [('identity_confirmed','主体'),('industry_confirmed','主营行业'),('metrics_confirmed','取数及口径'),('period_confirmed','期间'),('policy_applicability_confirmed','行内制度适用性')]:
        if case.get(key) is not True: add('confirmation_missing',f'{label}尚未根据原件确认',key)
    if not (rules.get('bank_approved') is True and rules.get('policy_document') and rules.get('approved_version')):
        add('bank_policy_missing','缺经核有效行内规则；公开参考不能直接用于正式出件','rules')
    year=case.get('reporting_year')
    if type(year) is not int: add('year_missing','缺整型指标所属年度','reporting_year')
    try: decision=date.fromisoformat(case.get('decision_date',''))
    except (TypeError,ValueError):
        decision=None;add('decision_date_missing','缺有效判断日期YYYY-MM-DD','decision_date')
    if decision and type(year) is int and year!=decision.year-1 and not case.get('period_exception_basis'):
        add('period_mismatch','非上一年度数据缺实际制度例外依据','reporting_year')
    for key in ['effective_from','effective_to']:
        raw=rules.get(key)
        if not raw and key=='effective_from': add('rule_date_missing','缺规则生效日期','rules.effective_from')
        if raw:
            try:
                boundary=date.fromisoformat(raw)
                if decision and ((key=='effective_from' and decision<boundary) or (key=='effective_to' and decision>boundary)):
                    add('rule_out_of_date','规则在判断日尚未生效或已经失效','rules.'+key)
            except (ValueError,TypeError): add('invalid_rule_date','规则日期格式错误','rules.'+key)
    industry=case.get('industry');metric_rules=rules.get('industries',{}).get(industry,{})
    if not metric_rules: add('industry_unsupported','缺适用的行业规则，不能任意套其他未列明','industry')
    metrics=case.get('metrics',{})
    if not isinstance(metrics,dict): metrics={};add('invalid_metrics','指标必须为JSON对象','metrics')
    calculation=None
    if metric_rules:
        try: calculation=classify(industry,metrics,rules)
        except (ValueError,KeyError,TypeError) as exc: add('invalid_value',str(exc),'metrics')
        if calculation:
            for key in calculation['missing']: add('metric_missing','缺有依据的指标值，不能用0代替未知','metrics.'+key)
        if 'employees' in metric_rules and case.get('staff_basis') not in {'employees_year_end','annual_average'}:
            add('headcount_basis_missing','参保人数不能直接替代从业人数；需核期末从业或适用全年平均','staff_basis')
        provenance=case.get('metric_sources',{})
        for key in metric_rules:
            source=provenance.get(key,{}) if isinstance(provenance,dict) else {}
            if not isinstance(source,dict): source={}
            if not all(source.get(k) for k in ['source','location','unit']) or source.get('year')!=year:
                add('metric_source_missing','指标来源、页行、单位或年度未完整核对','metric_sources.'+key)
    evidence=case.get('evidence',{})
    for key in ['finance','staff','industry']:
        ev=evidence.get(key,{}) if isinstance(evidence,dict) else {}
        if not isinstance(ev,dict): ev={}
        if ev.get('company')!=company or ev.get('identity_verified') is not True:
            add('evidence_identity','证据主体尚未逐项核对','evidence.'+key)
        if ev.get('content_verified') is not True or not ev.get('source'):
            add('evidence_provenance','证据内容/来源尚未确认','evidence.'+key)
        if key in {'finance','staff'} and ev.get('year')!=year:
            add('evidence_year','财务/人数证据年度不一致','evidence.'+key+'.year')
        paths=ev.get('paths',[])
        if not isinstance(paths,list) or not paths: add('evidence_missing','缺真实原始证据文件','evidence.'+key+'.paths')
        else:
            for item in paths:
                if not isinstance(item,str) or not Path(item).is_file(): add('evidence_file_missing','证据路径不存在或不是文件','evidence.'+key+'.paths')
    methods=case.get('methods',{})
    for key,upper in [('industry',5),('staff',5),('finance',3)]:
        value=methods.get(key) if isinstance(methods,dict) else None
        if type(value) is not int or value not in range(1,upper+1): add('method_missing','缺原表允许且与真实证据相符的方法号','methods.'+key)
    labels=case.get('existing_labels',[])
    if not isinstance(labels,list):
        add('invalid_labels','历史标签必须为带来源的数组','existing_labels');labels=[]
    normalized={str(x.get('value','')).replace('企业','').strip() for x in labels if isinstance(x,dict) and x.get('value')}
    resolution=case.get('label_conflict_resolution',{})
    resolved=isinstance(resolution,dict) and resolution.get('confirmed') is True and bool(resolution.get('basis')) and resolution.get('year')==year
    if len(normalized)>1:
        add('prior_labels_conflict','历史表/外部页面规模标签不一致，需核年度与依据；不能择一覆盖','existing_labels',not resolved)
    elif normalized and calculation and calculation['size'] and calculation['size'] not in normalized:
        add('calculation_label_conflict','本次参考运算与既有标签不同，需核口径和证据','existing_labels',not resolved)
    return {'status':'blocked' if any(x['blocking'] for x in issues) else 'ready_for_formal_preparation',
            'issues':issues,'calculation':calculation,'read_only':True,
            'note':'此为证据及参数预检，不证明银行审批、经理检视或系统上挂完成。'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True);p.add_argument('--rules',default=str(ROOT/'references/public_rules.json'));p.add_argument('--output')
    a=p.parse_args();case=json.loads(Path(a.input).read_text(encoding='utf-8'));rules=json.loads(Path(a.rules).read_text(encoding='utf-8'))
    result=inspect(case,rules);text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        dest=Path(a.output).resolve()
        originals={Path(a.input).resolve(),Path(a.rules).resolve()}
        originals.update(Path(v).resolve() for ev in case.get('evidence',{}).values() if isinstance(ev,dict) for v in ev.get('paths',[]) if isinstance(v,str))
        if dest in originals or dest.suffix.lower()!='.json': raise ValueError('report must be a separate JSON, not an original input')
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text+'\n',encoding='utf-8')
    else: print(text)

if __name__=='__main__': main()
