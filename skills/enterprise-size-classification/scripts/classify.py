"""Decimal threshold engine. Bundled public rules never imply bank-policy approval."""
import argparse
from decimal import Decimal, InvalidOperation
import itertools
import json
from pathlib import Path

SIZES = ['微型','小型','中型','大型']

def number(value, field):
    if isinstance(value,bool): raise ValueError(f'{field}: boolean is not a number')
    try: value=Decimal(str(value))
    except InvalidOperation as exc: raise ValueError(f'{field}: invalid number') from exc
    if not value.is_finite() or value < 0: raise ValueError(f'{field}: finite non-negative value required')
    if field=='employees' and value != value.to_integral_value(): raise ValueError('employees: integer required')
    return value

def classify(industry, values, rules):
    metrics=rules['industries'].get(industry)
    if not metrics: raise ValueError(f'unsupported industry: {industry}; do not infer other industries')
    candidates=[]; missing=[]; detail={}
    for key, raw_bounds in metrics.items():
        bounds=[number(v,key) for v in raw_bounds]
        if len(bounds)!=3 or not 0 < bounds[0] < bounds[1] < bounds[2]: raise ValueError(f'invalid thresholds: {key}')
        raw=values.get(key)
        if raw is None or raw=='':
            missing.append(key); candidates.append(range(4)); continue
        value=number(raw,key)
        tier=sum(value>=bound for bound in bounds)
        candidates.append([tier]); detail[key]={'value':str(value),'lower_bounds':[str(v) for v in bounds],'indicator_size':SIZES[tier]}
    possible=sorted({min(combo) for combo in itertools.product(*candidates)})
    size=SIZES[possible[0]] if len(possible)==1 else None
    approved=rules.get('bank_approved') is True and bool(rules.get('policy_document')) and bool(rules.get('approved_version'))
    return {'rule_id':rules['rule_id'],'industry':industry,'size':size,
            'possible_sizes':[SIZES[x] for x in possible],'missing':missing,'indicators':detail,
            'status':('bank_rule_calculated' if approved else 'reference_only') if size else 'need_data',
            'complete_indicators':not missing,
            'meaning':'阈值运算结果；证据、主体、期间与行内适用性须另行验证'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True); parser.add_argument('--rules',required=True); parser.add_argument('--output')
    args=parser.parse_args()
    case=json.loads(Path(args.input).read_text(encoding='utf-8'))
    rules=json.loads(Path(args.rules).read_text(encoding='utf-8'))
    result=classify(case['industry'],case['metrics'],rules)
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output: Path(args.output).write_text(text+'\n',encoding='utf-8')
    else: print(text)

if __name__=='__main__': main()
