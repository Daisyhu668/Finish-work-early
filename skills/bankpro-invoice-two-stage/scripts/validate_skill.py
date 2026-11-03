#!/usr/bin/env python3
from pathlib import Path
import hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'InvoiceLogInfo.xls':'4b439518802b6587f37d9b6efc10b7252f30ff44daf96c513bffe454b0afd766',
          'InvoiceInfo.xls':'c7a599cf8077177ceffdc7bc2140830d176a2cd7189478550c1dc3edc0653c11'}
for name,want in EXPECTED.items():
 p=ROOT/'assets'/name
 assert p.is_file(),p
 assert hashlib.sha256(p.read_bytes()).hexdigest()==want,f'模板被改动：{name}'
text=(ROOT/'SKILL.md').read_text(encoding='utf8')
assert text.startswith('---\nname: bankpro-invoice-two-stage\n')
assert '\n---\n' in text[4:]
for required in ['InvoiceLogInfo.xls','InvoiceInfo.xls','case_id','--selected-invoices','汇票','外部核验']:
 assert required in text,required
files=list((ROOT/'scripts').glob('*.py'))
assert len(files)>=4
for p in files:
 x=subprocess.run([sys.executable,'-m','py_compile',str(p)],capture_output=True,text=True)
 assert x.returncode==0,(p,x.stderr)
print('PASS: YAML-frontmatter, scripts, both official template SHA256')