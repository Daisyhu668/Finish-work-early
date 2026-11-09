import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from classify import classify

RULES = json.loads((ROOT / 'references/public_rules.json').read_text())

class EngineTests(unittest.TestCase):
    def test_all_industry_thresholds_and_mixed_indicators(self):
        for industry, metrics in RULES['industries'].items():
            for tier, expected in enumerate(['小型','中型','大型']):
                values = {k:str(v[tier]) for k,v in metrics.items()}
                with self.subTest(industry=industry,tier=tier):
                    self.assertEqual(classify(industry,values,RULES)['size'],expected)
            for key, bounds in metrics.items():
                values={k:str(v[2]) for k,v in metrics.items()}
                values[key]=str(bounds[0]-1)
                self.assertEqual(classify(industry,values,RULES)['size'],'微型')

    def test_missing_not_zero(self):
        result=classify('工业',{'employees':100},RULES)
        self.assertIsNone(result['size'])
        self.assertIn('revenue_wan',result['missing'])
        self.assertEqual(classify('工业',{'employees':5},RULES)['size'],'微型')

    def test_zero_and_invalid_numbers(self):
        self.assertEqual(classify('工业',{'employees':0,'revenue_wan':0},RULES)['size'],'微型')
        for bad in [-1,True,'NaN','Infinity','1,000']:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                classify('工业',{'employees':bad,'revenue_wan':300},RULES)
        with self.assertRaises(ValueError):
            classify('工业',{'employees':1.5,'revenue_wan':300},RULES)

    def test_unknown_sector_and_bad_rule_order(self):
        with self.assertRaises(ValueError): classify('金融业',{},RULES)
        rules=copy.deepcopy(RULES)
        rules['industries']['工业']['employees']=[300,20,1000]
        with self.assertRaises(ValueError): classify('工业',{},rules)

    def test_public_rule_cannot_create_bank_conclusion(self):
        result=classify('工业',{'employees':100,'revenue_wan':5000},RULES)
        self.assertEqual(result['status'],'reference_only')
        self.assertEqual(result['size'],'小型')

if __name__=='__main__': unittest.main()
