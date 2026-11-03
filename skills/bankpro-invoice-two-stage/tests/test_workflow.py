# -*- coding: utf-8 -*-
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from case_workflow import source_manifest,plan_stage2,check_invoice_policy,selection_from_file,frozen_case
from allocate_bills import allocate
from datetime import date
C='甲采购企业有限公司';S='乙供货公司有限公司'
def rec(i,amount=1000,seller=S):
    return {'invoice_no':f'2610000000000000{i:04d}','total':str(amount),'net':str(amount*0.9),
            'invoice_date':'2026-09-01','buyer':C,'seller':seller,'payee':seller,
            'product':'锌锭','invoice_type':'全面数字化电子发票','medium':'电子发票',
            'selected':True,'external_count':None,'used_amount':None}
class TestSkill(unittest.TestCase):
 def test_multi_bi_one_payee_auto_split(self):
    chosen,report=allocate([rec(1,1200),rec(2,1100),rec(3,1800),rec(4,2100)],
       [{'bi':'BI2026101400000001','payee':S,'amount':'2000'},
        {'bi':'BI2026101400000002','payee':S,'amount':'2200'}])
    self.assertEqual(len(chosen),len(set(chosen)))
    self.assertEqual(set(chosen.values()),{'BI2026101400000001','BI2026101400000002'})
    self.assertTrue(all(float(a['overage'])>=0 for a in report['bills']))
 def test_insufficient_separate_supplier(self):
    with self.assertRaisesRegex(ValueError,'不足'):
      allocate([rec(1,200)], [{'bi':'BI2026101400000001','payee':S,'amount':'1000'}])
 def test_external_two_needs_enhanced_review(self):
    with self.assertRaisesRegex(ValueError,'强化核实'):
      check_invoice_policy(rec(1),date(2026,10,14),{'external_count':2,'used_amount':'0'},False)
    self.assertTrue(check_invoice_policy(rec(1),date(2026,10,14),
      {'external_count':2,'used_amount':'0','external2_enhanced_review_confirmed':True},False))
 def test_cross_customer_manifest_fails(self):
    d={'summary':{'block_count':0},'records':[rec(1),dict(rec(2),buyer='其他企业')]}
    with self.assertRaisesRegex(ValueError,'跨客户'):source_manifest(d,C)
 def test_stage1_complete_pool_stage2_selected_subset(self):
    d={'summary':{'block_count':0},'records':[rec(1,1100),rec(2,1200),rec(3,1500),rec(4,1600)]}
    with tempfile.TemporaryDirectory() as t:
      root=Path(t);(root/'data').mkdir()
      case={'case_id':'DEMO2026','customer':C};(root/'case.json').write_text(json.dumps(case,ensure_ascii=False),encoding='utf8')
      (root/'data'/'normalized.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf8')
      f=source_manifest(d,C)
      (root/'data'/'frozen.json').write_text(json.dumps(f,ensure_ascii=False),encoding='utf8')
      ids=root/'selected.txt';ids.write_text('\n'.join([rec(1)['invoice_no'],rec(2)['invoice_no'],rec(3)['invoice_no']]),encoding='utf8')
      status={r['invoice_no']:{'external_count':0,'used_amount':'0.00'} for r in d['records']}
      (root/'status.json').write_text(json.dumps(status),encoding='utf8')
      bill={'case_id':'DEMO2026','customer':C,'source_hash':f['source_hash'],
        'registration_bank_system_confirmed':True,'over_6_month_exception_confirmed':False,
        'bills':[{'bi':'BI2026101400000001','payee':S,'amount':'1900','issue_date':'2026-10-14'}]}
      (root/'bills.json').write_text(json.dumps(bill,ensure_ascii=False),encoding='utf8')
      args=SimpleNamespace(case=root,bills=root/'bills.json',selected_invoices=ids,status_source='',status_json=root/'status.json')
      plan_stage2(args)
      p=json.loads((root/'stage2'/'association_plan.json').read_text(encoding='utf8'))
      self.assertEqual(f['count'],4)
      self.assertLess(p['selected_count'],4)
      self.assertGreaterEqual(float(p['selected_face_total']),1900)
      self.assertEqual(len(p['assignments']),p['selected_count'])
      self.assertTrue((root/'stage2'/'not_selected.csv').is_file())
 def test_invoice_date_over_one_year_block(self):
    row=rec(1);row['invoice_date']='2025-09-01'
    with self.assertRaisesRegex(ValueError,'1年'):
      check_invoice_policy(row,date(2026,10,14),{'external_count':0},False)
 def test_frozen_product_change_is_blocked(self):
    d={'summary':{'block_count':0},'records':[rec(1,1000)]}
    with tempfile.TemporaryDirectory() as t:
      root=Path(t);(root/'data').mkdir()
      config={'case_id':'DEMO2026','customer':C}
      (root/'case.json').write_text(json.dumps(config,ensure_ascii=False),encoding='utf8')
      (root/'data'/'frozen.json').write_text(json.dumps(source_manifest(d,C),ensure_ascii=False),encoding='utf8')
      d['records'][0]['product']='未经确认的新货物'
      (root/'data'/'normalized.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf8')
      with self.assertRaisesRegex(ValueError,'发生改动'):frozen_case(root,config)
 def test_missing_fresh_used_amount_blocks(self):
    with self.assertRaisesRegex(ValueError,'已占用金额'):
      check_invoice_policy(rec(1),date(2026,10,14),{'external_count':0},False)
 def test_no_stale_external_count_fallback(self):
    r=rec(1);r['external_count']=0
    with self.assertRaisesRegex(ValueError,'外部核验次数'):
      check_invoice_policy(r,date(2026,10,14),{'used_amount':'0'},False)
 def test_noninteger_external_count_rejected(self):
    with self.assertRaisesRegex(ValueError,'有效整数'):
      check_invoice_policy(rec(1),date(2026,10,14),{'used_amount':'0','external_count':1.5},False)
 def test_frozen_cross_customer_immutability(self):
    a=source_manifest({'summary':{'block_count':0},'records':[rec(1)]},C)
    b=source_manifest({'summary':{'block_count':0},'records':[dict(rec(1),product='新货物')]},C)
    self.assertNotEqual(a['source_hash'],b['source_hash'])
 def test_full_plan_multi_company_payees_and_multi_bi(self):
    supplier2='丙另一家供货公司有限公司'
    rows=[rec(1,1200),rec(2,1100),rec(3,1800),rec(4,2100),rec(5,1550,supplier2),rec(6,1700,supplier2)]
    doc={'summary':{'block_count':0},'records':rows}
    with tempfile.TemporaryDirectory() as t:
      case=Path(t);(case/'data').mkdir()
      conf={'case_id':'CASE_MULTI_001','customer':C}
      (case/'case.json').write_text(json.dumps(conf,ensure_ascii=False),encoding='utf8')
      (case/'data'/'normalized.json').write_text(json.dumps(doc,ensure_ascii=False),encoding='utf8')
      frozen=source_manifest(doc,C)
      (case/'data'/'frozen.json').write_text(json.dumps(frozen,ensure_ascii=False),encoding='utf8')
      selected=case/'chosen.txt'
      selected.write_text('\n'.join(r['invoice_no'] for r in rows),encoding='utf8')
      status=case/'latest.json'
      status.write_text(json.dumps({r['invoice_no']:{'external_count':0,'used_amount':'0.00','verification_status':'正常'} for r in rows},ensure_ascii=False),encoding='utf8')
      bi_payload={'customer':C,'case_id':conf['case_id'],'source_hash':frozen['source_hash'],
        'registration_bank_system_confirmed':True,'over_6_month_exception_confirmed':False,
        'bills':[{'bi':'BI2026101400000001','payee':S,'amount':'2000','issue_date':'2026-10-14'},
                 {'bi':'BI2026101400000002','payee':S,'amount':'2200','issue_date':'2026-10-14'},
                 {'bi':'BI2026101400000003','payee':supplier2,'amount':'1500','issue_date':'2026-10-14'}]}
      bills=case/'bills.json';bills.write_text(json.dumps(bi_payload,ensure_ascii=False),encoding='utf8')
      args=SimpleNamespace(case=case,bills=bills,selected_invoices=selected,status_source='',status_json=status)
      plan_stage2(args)
      result=json.loads((case/'stage2'/'association_plan.json').read_text(encoding='utf8'))
      self.assertEqual(len(result['coverage']),3)
      self.assertEqual(len(result['assignments']),len(set(result['assignments'])))
      self.assertTrue(all(float(x['invoice_total'])>=float(x['bill_amount']) for x in result['coverage']))
      self.assertEqual(set(result['assignments'].values()),{x['bi'] for x in bi_payload['bills']})
      self.assertTrue((case/'stage2'/'bill_coverage.csv').exists())
if __name__=='__main__':unittest.main()