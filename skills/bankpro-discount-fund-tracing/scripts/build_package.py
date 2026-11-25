"""Build a local evidence package from agent-reviewed transaction rows, never infer OCR facts."""
import argparse, json, shutil, hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pypdf import PdfReader, PdfWriter

D=Decimal
KINDS=('discounts','interest','payments','fees','other_in','other_out')
def money(v):
    n=D(str(v))
    if not n.is_finite() or n<0 or n!=n.quantize(D('0.01')): raise ValueError(f'Invalid amount: {v}')
    return n

def sum_rows(rows): return sum((money(r['amount']) for r in rows),D('0'))
def fmt(n): return f'{n:,.2f}'
def cn_date(s):
    d=date.fromisoformat(s); return f'{d.year}年{d.month}月{d.day}日'
def safe(s):
    if not s or any(c in s for c in '/\\:*?"<>|') or s in ('.','..'): raise ValueError(f'Invalid filename component: {s}')
    return s

def summarize(bank):
    seen=set()
    for kind in KINDS:
        for r in bank.get(kind,[]):
            if not r.get('id') or r['id'] in seen: raise ValueError('Missing or duplicate transaction ID; review source rows')
            seen.add(r['id']); money(r['amount']); date.fromisoformat(r['date'])
    gross=sum_rows(bank['discounts']); interest=sum_rows(bank.get('interest',[])); net=gross-interest
    if not bank['discounts'] or net<0: raise ValueError('Missing discounts or invalid interest')
    payees={}
    for r in bank['payments']:
        key=r['payee']; prior,purposes=payees.get(key,(D('0'),set())); payees[key]=(prior+money(r['amount']),purposes|{r.get('purpose','转款')})
    paid=sum_rows(bank['payments']); fees=sum_rows(bank.get('fees',[]))
    diff=None
    if 'opening' in bank and 'closing' in bank:
        diff=money(bank['opening'])+net+sum_rows(bank.get('other_in',[]))-paid-fees-sum_rows(bank.get('other_out',[]))-money(bank['closing'])
    return {'gross':gross,'interest':interest,'net':net,'count':len(bank['discounts']),'paid':paid,'fees':fees,'payees':payees,'difference':diff,'dates':sorted({r['date'] for r in bank['discounts']})}

def compose(data):
    company=data['company']; head=(f"客户经理于{cn_date(data['credit_query_date'])}查询企业征信，发现{company}近一周内有贴现业务。" if data.get('credit_query_confirmed') else f'根据客户提供的流水，{company}近期存在贴现业务。')
    paragraphs=[]; total=D('0'); count=0
    for bank in data['banks']:
        s=summarize(bank); total+=s['net']; count+=s['count']
        if s['difference'] not in (None,D('0')): raise ValueError(f"{bank['bank']}余额勾稽不符：{s['difference']}")
        dates='、'.join(cn_date(x) for x in s['dates']); payees='、'.join(f"向{k}{'支付货款' if p=={'货款'} else '支付'}{fmt(v)}元" for k,(v,p) in s['payees'].items())
        amounts=(f"贴现金额{fmt(s['gross'])}元，扣除单列贴现利息后实际取得资金{fmt(s['net'])}元" if s['interest'] else f"贴现资金实际到账{fmt(s['net'])}元")
        paragraphs.append(f"于{dates}在{bank['bank']}办理贴现业务{s['count']}笔，{amounts}"+(f'，流水显示后续{payees}' if payees else '，后续资金去向待补充核实'))
    status=data.get('source_status','pending')
    suffix={'pending':'本次银行承兑汇票开立拟使用企业自有资金作为质押存单资金，非上述贴现资金，具体资金来源以本次存单入金流水核实为准。','customer_confirmed':'据客户说明，本次银行承兑汇票开立所涉及的质押存单资金来源为企业自有资金，非上述贴现资金，具体以本次存单入金流水核实为准。','verified':'经核对本次质押存单入金及资金来源流水，本次开票质押存单资金来源为企业自有资金，非上述贴现资金。','exception':'本次开票资金来源尚存在待核实事项，暂不能确认其与上述贴现资金无关联。'}[status]
    if status=='verified' and not data.get('source_evidence'): raise ValueError('Verified source requires specific evidence reference')
    purpose='上述贴现资金基本已用于企业对外经营结算。' if data.get('operating_use_confirmed') else '上述资金去向以所列账户流水为依据。'
    return head+'经核查客户提供的银行账户流水，具体情况如下：'+'；'.join(paragraphs)+f'。上述贴现业务合计{count}笔，实际取得资金{fmt(total)}元。'+purpose+suffix+'特此说明。'

def make_docx(path,company,body):
    doc=Document(); sec=doc.sections[0]; sec.page_width=Cm(21); sec.page_height=Cm(29.7); sec.top_margin=Cm(2.7); sec.bottom_margin=Cm(2.7); sec.left_margin=Cm(2.8); sec.right_margin=Cm(2.8)
    style=doc.styles['Normal']; style.font.name='Noto Serif CJK SC'; style.font.size=Pt(12); style._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Noto Serif CJK SC')
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(f'关于{company}\n近期贴现及开票资金来源的情况说明'); r.bold=True; r.font.size=Pt(16); p.paragraph_format.space_after=Pt(18)
    p=doc.add_paragraph(body); f=p.paragraph_format; f.first_line_indent=Pt(24); f.line_spacing=1.6; f.space_after=Pt(0)
    doc.save(path)

def build(data,base,out):
    company=safe(data['company']); body=compose(data); out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()): raise ValueError('Output directory must be empty to prevent overwriting')
    paths=[]; hashes=set(); names=set(); writer=PdfWriter(); audit=[]
    for bank in data['banks']:
        bank_name=safe(bank['bank']); s=summarize(bank); src=base/bank['pdf']; dst=out/f'{company}贴现流水-{bank_name}.pdf'
        if dst.name in names: raise ValueError('Duplicate bank filename; use unique account labels')
        names.add(dst.name); h=hashlib.sha256(src.read_bytes()).hexdigest()
        if h in hashes: raise ValueError('Duplicate source PDF')
        hashes.add(h); reader=PdfReader(src); shutil.copy2(src,dst); writer.append(str(src)); paths.append(dst); audit.append({'bank':bank_name,'pages':len(reader.pages),'sha256':h,**{k:str(s[k]) for k in ('count','gross','interest','net','paid','fees','difference')}})
    merged=out/f'{company}贴现流水-合并.pdf'; writer.write(str(merged)); writer.close(); paths.append(merged)
    doc=out/f'{company}贴现情况说明.docx'; make_docx(doc,company,body); paths.append(doc)
    return {'files':[str(p) for p in paths],'audit':audit,'body':body}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input',type=Path); p.add_argument('output',type=Path); a=p.parse_args(); data=json.loads(a.input.read_text(encoding='utf-8')); print(json.dumps(build(data,a.input.parent,a.output),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
