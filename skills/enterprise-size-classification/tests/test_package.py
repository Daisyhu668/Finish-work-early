import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_case import build
from template_io import patch, verify, cell_values, manifest

class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.rules=json.loads((ROOT/'references/public_rules.json').read_text())
        # Only a synthetic test policy; never a real approved banking rule.
        self.rules.update(bank_approved=True,policy_document='SYNTHETIC TEST ONLY',approved_version='test')
        image=Image.new('RGB',(900,700),'white')
        ImageDraw.Draw(image).text((30,30),'SYNTHETIC evidence - NOT A CUSTOMER - FY2025',fill='black')
        source=self.base/'source.png';image.save(source)
        self.case={'company':'合成测试企业有限公司','branch':'new','industry':'工业',
          'reporting_year':2025,'decision_date':'2026-11-09','identity_confirmed':True,'industry_confirmed':True,
          'metrics_confirmed':True,'period_confirmed':True,'policy_applicability_confirmed':True,
          'staff_basis':'employees_year_end','metrics':{'employees':20,'revenue_wan':'2000'},
          'metric_sources':{k:{'source':'SYNTHETIC','location':'page 1','unit':'person' if k=='employees' else '万元','year':2025} for k in ['employees','revenue_wan']},
          'methods':{'industry':2,'staff':3,'finance':1},
          'evidence':{k:{'paths':[str(source)],'company':'合成测试企业有限公司','year':2025,'source':'SYNTHETIC TEST','identity_verified':True,'content_verified':True} for k in ['finance','staff','industry']}}
    def tearDown(self): self.temp.cleanup()

    def test_complete_four_file_package_preserves_original_template(self):
        r=build(self.case,self.rules,self.base/'out')
        self.assertEqual(r['status'],'prepared_not_uploaded')
        self.assertEqual(len(r['files']),4)
        with ZipFile(r['zip']) as z:
            self.assertEqual(set(z.namelist()),set(r['files']))
            self.assertIsNone(z.testzip())
        template=ROOT/'assets'/manifest()['file'];output=self.base/'out'/r['files'][0]
        verify(template,output,{'A2','B4','B6','B7','B9','B10','B16','B22'})
        cells=cell_values(output);original=cell_values(template)
        self.assertEqual(cells['B9'],'小型')
        self.assertEqual(cells['B26'],original['B26']);self.assertEqual(cells['B27'],original['B27'])
        self.assertNotIn('2000',cells['B22'])

    def test_no_update_and_not_required_branches(self):
        c={'company':'合成测试企业有限公司','branch':'annual_no_update'}
        r=build(c,{},self.base/'no-update')
        self.assertEqual(len(r['files']),1)
        cells=cell_values(self.base/'no-update'/r['files'][0]);self.assertEqual(cells['B9'],'')
        for branch in ['condition_change','individual_business']:
            c['branch']=branch
            self.assertEqual(build(c,{},self.base/branch)['files'],[])

    def test_bank_rule_missing_and_evidence_mismatch_block(self):
        public=json.loads((ROOT/'references/public_rules.json').read_text())
        with self.assertRaises(ValueError): build(self.case,public,self.base/'blocked')
        c=copy.deepcopy(self.case);c['evidence']['staff']['year']=2024
        with self.assertRaises(ValueError): build(c,self.rules,self.base/'bad-year')
        c=copy.deepcopy(self.case);c['evidence']['industry']['company']='其他合成企业'
        with self.assertRaises(ValueError): build(c,self.rules,self.base/'bad-name')

    def test_insured_population_old_period_and_unverified_data_block(self):
        for change in [{'staff_basis':'insured_only'},{'reporting_year':2024},{'metrics_confirmed':False}]:
            c=copy.deepcopy(self.case);c.update(change)
            with self.assertRaises(ValueError): build(c,self.rules,self.base/'bad')

    def test_template_hash_and_forbidden_cells_block(self):
        template=ROOT/'assets'/manifest()['file']
        with self.assertRaises(ValueError): patch(template,self.base/'out.xlsx',{'B26':'done'},manifest()['sha256'])
        with self.assertRaises(ValueError): patch(template,self.base/'out.xlsx',{'A2':'test'},'bad')
        with self.assertRaises(ValueError): patch(template,template,{'A2':'test'},manifest()['sha256'])

    def test_cli_no_update_default_rules_and_audit_isolation(self):
        source=self.base/'input.json'
        source.write_text(json.dumps({'company':'合成测试企业有限公司','branch':'annual_no_update'}))
        command=[sys.executable,str(ROOT/'scripts/build_case.py'),'--input',str(source),'--out',str(self.base/'cli')]
        audit=self.base/'nested/audit.json'
        ok=subprocess.run(command+['--audit',str(audit)],capture_output=True,text=True)
        self.assertEqual(ok.returncode,0,ok.stderr);self.assertTrue(audit.exists())
        bad=subprocess.run(command+['--audit',str(self.base/'cli/overwrite.json')],capture_output=True,text=True)
        self.assertNotEqual(bad.returncode,0)

    def test_formal_builder_cannot_bypass_unresolved_label_conflict(self):
        c=copy.deepcopy(self.case)
        c['existing_labels']=[{'value':'小型','source':'synthetic old form'},{'value':'中型','source':'synthetic external label'}]
        with self.assertRaisesRegex(ValueError,'prior_labels_conflict'):
            build(c,self.rules,self.base/'blocked-conflict')
        self.assertFalse((self.base/'blocked-conflict').exists())

if __name__=='__main__':unittest.main()
