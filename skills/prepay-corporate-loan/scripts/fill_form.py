"""Fill the approved two-copy DOCX without rebuilding its layout."""
import argparse
import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
XMLSPACE = '{http://www.w3.org/XML/1998/namespace}space'
TEMPLATE_SHA256 = 'de9208a2897d22bdf4016c9711fe23201f700c49b28313e08993447c876e309e'
VALUE_SLOTS = {1: (5, 1), 87: (6, 0), 5: (0, 5), 91: (0, 5), 6: (0, 5), 92: (0, 5), 8: (4, 2), 94: (5, 0), 9: (0, 5), 95: (1, 0), 10: (0, 5), 96: (0, 5), 13: (0, 5), 99: (0, 5), 31: (0, 7), 117: (0, 7), 32: (0, 5), 118: (1, 0), 34: (0, 7), 120: (0, 7), 35: (0, 5), 121: (1, 0)}
FIELDS = {
    'unit': ('经营单位（支行）：', [1, 87]),
    'borrower': ('借款人：', [5, 91]),
    'identity_number': ('证件号码：', [6, 92]),
    'amount': ('拟提前结清授信币种及金额（详见说明1）：', [8, 94]),
    'amount_upper': ('大写金额：', [9, 95]),
    'loan_account': ('贷款账号：', [10, 96]),
    'repayment_account': ('还款账号：', [13, 99]),
    'credit_contract': ('授信合同编号：', [31, 117]),
    'credit_limit': ('授信额度：', [32, 118]),
    'loan_note': ('借款借据编号：', [34, 120]),
    'approval_authority': ('审批权限：', [35, 121]),
}

def txt(p):
    return ''.join(p.xpath('.//w:t/text()', namespaces=NS))

def replace_span(p, start, stop, replacement):
    nodes = p.xpath('.//w:t', namespaces=NS)
    size = sum(len(n.text or '') for n in nodes)
    if not (0 <= start <= stop <= size): raise ValueError('Invalid span')
    pos, inserted = 0, False
    for n in nodes:
        s = n.text or ''
        end = pos + len(s)
        changed = False
        if start == stop and not inserted and pos <= start <= end:
            n.text = s[:start-pos] + replacement + s[start-pos:]
            inserted, changed = True, True
        elif end > start and pos < stop:
            left = s[:max(0, start-pos)]
            right = s[max(0, stop-pos):] if stop < end else ''
            n.text = left + (replacement if not inserted else '') + right
            inserted, changed = True, True
        if changed: n.set(XMLSPACE, 'preserve')
        pos = end
    if not inserted: raise ValueError('No text node for replacement')

def set_field(p, label, value, slot=None):
    s = txt(p)
    if not s.startswith(label): raise ValueError(f'Unexpected label {label}')
    # Keep label/placeholder whitespace in its own run. Replace the actual old
    # value where it begins, so its font does not migrate to a larger spacer run.
    start = len(label)
    while start < len(s) and s[start].isspace(): start += 1
    if start == len(s) and slot is not None:
        nodes = p.xpath('.//w:t', namespaces=NS)
        node, offset = nodes[slot[0]], slot[1]
        old = node.text or ''
        if offset > len(old): raise ValueError('Template value slot mismatch')
        node.text = old[:offset] + value + old[offset:]
        node.set(XMLSPACE, 'preserve')
    else:
        replace_span(p, start, len(s), value)

def content_free(root):
    r = copy.deepcopy(root)
    for n in r.xpath('//w:t|//w:sym', namespaces=NS): n.getparent().remove(n)
    return E.tostring(r, method='c14n')

def money_upper(amount):
    n = Decimal(str(amount))
    if n <= 0 or n != n.quantize(Decimal('.01')) or n >= Decimal('1000000000000'):
        raise ValueError('Amount must be positive, < 1 trillion, with <= 2 decimals')
    digits = '零壹贰叁肆伍陆柒捌玖'
    def group(v):
        out, zero = '', False
        for d, unit in zip(f'{v:04d}', ['仟','佰','拾','']):
            if d == '0':
                if out: zero = True
            else:
                if zero: out += '零'
                out += digits[int(d)] + unit
                zero = False
        return out
    whole = int(n)
    groups = [(whole // 100000000, '亿'), ((whole // 10000) % 10000, '万'), (whole % 10000, '')]
    out, gap = '', False
    for v, unit in groups:
        if v:
            if out and (gap or v < 1000): out += '零'
            out += group(v) + unit
            gap = False
        elif out: gap = True
    out = '人民币' + (out or '零') + '元'
    cents = int((n - int(n)) * 100)
    jiao, fen = divmod(cents, 10)
    if cents == 0: return out + '整'
    if jiao: out += digits[jiao] + '角'
    elif whole and fen: out += '零'
    if fen: out += digits[fen] + '分'
    return out

def fill(template, payload, output, audit):
    raw = Path(template).read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError('Unapproved template version; inspect and register before use')
    fields = payload.get('fields', {})
    if set(fields) - set(FIELDS) - {'principal_yuan'}: raise ValueError('Unknown fields')
    for key, item in fields.items():
        if not isinstance(item, dict) or not item.get('source') or not isinstance(item.get('value'), str):
            raise ValueError(f'Each filled value needs a source and string value: {key}')
    fields = copy.deepcopy(fields)
    if 'principal_yuan' in fields:
        if 'amount' in fields or 'amount_upper' in fields: raise ValueError('Use principal_yuan exclusively')
        n, source = Decimal(fields['principal_yuan']['value']), fields['principal_yuan']['source']
        fields['amount'] = {'value': f'人民币{n:.2f}', 'source': source}
        fields['amount_upper'] = {'value': money_upper(n), 'source': source}
        del fields['principal_yuan']
    if bool(fields.get('amount')) != bool(fields.get('amount_upper')):
        raise ValueError('Numeric and uppercase amounts must be supplied together')
    with ZipFile(template) as zin:
        before = E.fromstring(zin.read('word/document.xml'))
        root = copy.deepcopy(before)
        ps = root.xpath('//w:p', namespaces=NS)
        if len(ps) != 168 or len(root.xpath('//w:tbl', namespaces=NS)) != 2:
            raise ValueError('Template structure mismatch')
        for key, (label, indices) in FIELDS.items():
            val = fields.get(key, {}).get('value', '')
            for idx in indices: set_field(ps[idx], label, val, VALUE_SLOTS[idx])
        for p in ps:
            for sym in p.xpath('.//w:sym', namespaces=NS):
                if sym.get(f'{{{W}}}font') != 'Wingdings 2' or sym.get(f'{{{W}}}char') != '0052':
                    raise ValueError('Unknown checkbox representation')
                sym.tag = f'{{{W}}}t'
                sym.attrib.clear()
                sym.text = '□'
        replace_span(ps[148], 0, len(txt(ps[148])), txt(ps[62]))
        if content_free(before) != content_free(root): raise AssertionError('Formatting XML changed')
        allowed = {i for _, ids in FIELDS.values() for i in ids} | {102,107,111,115,148}
        for i, (b, p) in enumerate(zip(before.xpath('//w:p', namespaces=NS), ps)):
            if i not in allowed and E.tostring(b) != E.tostring(p): raise AssertionError(f'Fixed paragraph {i} changed')
        data = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, 'w') as zout:
            for item in zin.infolist():
                zout.writestr(item, data if item.filename == 'word/document.xml' else zin.read(item.filename))
    with ZipFile(template) as a, ZipFile(output) as b:
        assert a.namelist() == b.namelist()
        for name in a.namelist():
            if name != 'word/document.xml': assert a.read(name) == b.read(name)
    for key, (label, indices) in FIELDS.items():
        assert txt(ps[indices[0]])[len(label):].strip() == txt(ps[indices[1]])[len(label):].strip()
    report = {'template_sha256': TEMPLATE_SHA256, 'filled': fields,
              'blank': [k for k in FIELDS if k not in fields],
              'selections': 'Unselected; explicit instructions require manual text-only patch',
              'formatting_xml_unchanged': True, 'other_zip_members_identical': True,
              'two_copies_consistent': True}
    Path(audit).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', default=str(Path(__file__).resolve().parents[1] / 'assets' / 'prepayment_application_blank.docx'))
    ap.add_argument('--data', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--audit', required=True)
    args = ap.parse_args()
    fill(args.template, json.loads(Path(args.data).read_text(encoding='utf-8')), args.output, args.audit)
