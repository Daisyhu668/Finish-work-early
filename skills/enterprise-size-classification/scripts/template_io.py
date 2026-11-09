"""Patch only whitelisted cell values and preserve all other ZIP parts byte-for-byte."""
import copy
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZipFile

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ALLOWED={'A2','B4','B6','B7','B9','B10','B16','B22'}
SHEET='xl/worksheets/sheet1.xml'

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def cell_values(path):
    with ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        result={}
        for c in ET.fromstring(z.read(SHEET)).iter(f'{{{NS}}}c'):
            v=c.find(f'{{{NS}}}v')
            result[c.get('r')]=(strings[int(v.text)] if c.get('t')=='s' and v is not None
                                else ''.join(c.find(f'{{{NS}}}is').itertext()) if c.get('t')=='inlineStr'
                                else v.text if v is not None else '')
        return result

def patch(template, output, values, expected_sha):
    if Path(template).resolve()==Path(output).resolve(): raise ValueError('never overwrite template')
    if digest(template)!=expected_sha: raise ValueError('template fingerprint mismatch; inspect new version')
    if set(values)-ALLOWED: raise ValueError('cell outside whitelist')
    with ZipFile(template) as source:
        xml=source.read(SHEET).decode('utf-8')
        for ref,text in values.items():
            if not isinstance(text,str) or len(text)>200: raise ValueError(f'{ref}: short text required')
            pattern=rf'<c\b([^>]*\br="{ref}"[^>]*)(?:/>|>.*?</c>)'
            matches=list(re.finditer(pattern,xml,re.S))
            if len(matches)!=1: raise ValueError(f'expected exactly one existing cell: {ref}')
            if re.search(r'<f\b',matches[0].group()): raise ValueError('cannot overwrite formula')
            attrs=re.sub(r'\s+t="[^"]*"','',matches[0].group(1)).rstrip('/ ')
            replacement=f'<c{attrs} t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
            xml=xml[:matches[0].start()]+replacement+xml[matches[0].end():]
        Path(output).parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(output,'w') as target:
            for info in source.infolist(): target.writestr(info,xml.encode('utf-8') if info.filename==SHEET else source.read(info.filename))
    verify(template,output,set(values))

def verify(template, output, changed):
    with ZipFile(template) as a, ZipFile(output) as b:
        if a.namelist()!=b.namelist(): raise ValueError('ZIP part set/order changed')
        for name in a.namelist():
            if name!=SHEET and a.read(name)!=b.read(name): raise ValueError(f'non-sheet part changed: {name}')
        roots=[ET.fromstring(z.read(SHEET)) for z in [a,b]]
        for root in roots:
            for c in root.iter(f'{{{NS}}}c'):
                if c.get('r') in changed:
                    c.attrib.pop('t',None)
                    for child in list(c):
                        if child.tag in {f'{{{NS}}}v',f'{{{NS}}}is'}: c.remove(child)
        if ET.tostring(roots[0])!=ET.tostring(roots[1]): raise ValueError('non-value worksheet structure changed')
    return True

def manifest():
    return json.loads((Path(__file__).resolve().parents[1]/'assets/template_manifest.json').read_text())
