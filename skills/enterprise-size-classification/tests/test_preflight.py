import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from preflight import inspect

RULES=json.loads((ROOT/'references/public_rules.json').read_text())

class PreflightTests(unittest.TestCase):
    def test_report_all_missing_and_conflicting_labels_without_inventing_size(self):
        case={'company':'合成示例企业','branch':'annual_update','industry':'软件和信息技术服务业',
              'reporting_year':2025,'decision_date':'2026-11-09','staff_basis':'insured_only',
              'metrics':{'revenue_wan':'50000'},'existing_labels':[{'value':'小型企业','source':'旧表'},{'value':'中型','source':'外部页面'}]}
        r=inspect(case,RULES);codes={i['code'] for i in r['issues']}
        self.assertEqual(r['status'],'blocked');self.assertIsNone(r['calculation']['size'])
        self.assertTrue({'bank_policy_missing','headcount_basis_missing','prior_labels_conflict','evidence_missing','metric_missing'}<=codes)
        self.assertNotIn('employees',case['metrics'])

    def test_no_update_has_no_irrelevant_financial_requests(self):
        r=inspect({'company':'合成示例企业','branch':'annual_no_update'}, {})
        self.assertEqual(r['status'],'checklist_only');self.assertEqual(r['issues'],[])

    def test_invalid_numeric_value_becomes_report_not_exception(self):
        r=inspect({'company':'示例','branch':'new','industry':'工业','metrics':{'employees':-1}},RULES)
        self.assertIn('invalid_value',{i['code'] for i in r['issues']})

    def test_resolved_labels_preserve_trace_without_bypassing_missing_policy(self):
        case={'company':'合成示例','branch':'new','industry':'工业','reporting_year':2025,
              'existing_labels':[{'value':'小型'},{'value':'中型'}],
              'label_conflict_resolution':{'confirmed':True,'basis':'SYNTHETIC source p1, different year','year':2025}}
        r=inspect(case,RULES)
        self.assertEqual(r['status'],'blocked')
        conflict=next(i for i in r['issues'] if i['code']=='prior_labels_conflict')
        self.assertFalse(conflict['blocking'])
        self.assertTrue(next(i for i in r['issues'] if i['code']=='bank_policy_missing')['blocking'])

if __name__=='__main__': unittest.main()
