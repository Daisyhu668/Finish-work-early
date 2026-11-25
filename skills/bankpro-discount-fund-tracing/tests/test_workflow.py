import unittest, sys
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_package import summarize, compose
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.bank={'bank':'测试银行','discounts':[{'id':'a','date':'2026-11-19','amount':'1000.10'},{'id':'b','date':'2026-11-19','amount':'2000.20'}],'interest':[{'id':'c','date':'2026-11-19','amount':'10.30'}],'payments':[{'id':'d','date':'2026-11-19','payee':'甲有限公司','amount':'1500.00','purpose':'货款'},{'id':'e','date':'2026-11-19','payee':'甲有限公司','amount':'1490.00','purpose':'货款'}],'opening':'0.00','closing':'0.00','fees':[]}
    def test_net_and_grouping(self):
        s=summarize(self.bank); self.assertEqual(s['net'],Decimal('2990.00')); self.assertEqual(s['payees']['甲有限公司'][0],Decimal('2990.00')); self.assertEqual(s['count'],2); self.assertEqual(s['difference'],0)
    def test_duplicate(self):
        self.bank['discounts'].append(self.bank['discounts'][0]); self.assertRaises(ValueError,summarize,self.bank)
    def test_unreconciled(self):
        self.bank['closing']='1.00'; self.assertEqual(summarize(self.bank)['difference'],Decimal('-1.00'))
    def test_unverified_source(self):
        d={'company':'示例公司','credit_query_date':'2026-11-25','credit_query_confirmed':True,'source_status':'pending','banks':[self.bank]}
        t=compose(d); self.assertIn('以本次存单入金流水核实为准',t); self.assertIn('客户经理于2026年11月25日查询企业征信',t); self.assertNotIn('已核实本次',t)
    def test_unknown_credit(self):
        d={'company':'示例公司','credit_query_date':'2026-11-25','credit_query_confirmed':False,'source_status':'pending','banks':[self.bank]}
        self.assertNotIn('客户经理于',compose(d))
if __name__=='__main__':unittest.main()
