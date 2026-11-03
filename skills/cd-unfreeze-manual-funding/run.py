# -*- coding: utf-8 -*-
"""存单解冻两阶段批量生成。依赖 python-docx、openpyxl。
python run.py --input batches.json --word templates/unfreeze.docx --excel templates/funding.xlsx --oa templates/oa.md --out output
客户信息仅本地运行，禁止上传公开仓库。
"""
import argparse,json,re,zipfile
from pathlib import Path
from decimal import Decimal
from docx import Document
from openpyxl import load_workbook
DIGITS="零壹贰叁肆伍陆柒捌玖"
def upper_int(n):
    if n==0:return "零"
    small=["","拾","佰","仟"];big=["","万","亿","兆"];groups=[]
    while n:
        x=n%10000;n//=10000
        s="";zero=False
        for i,c in enumerate(str(x)):
            d=int(c);pos=len(str(x))-i-1
            if d:s+=("零" if zero and s else "")+DIGITS[d]+small[pos];zero=False
            else:zero=True
        groups.append(s); 
    return "".join((("零" if i<len(groups)-1 and groups[i] and groups[i+1] and int(str(groups[i]).isdigit()) else "")+groups[i]+big[i]) for i in range(len(groups)-1,-1,-1) if groups[i])
def upper_wan(yuan):
    a=Decimal(str(yuan).replace(",",""))
    if a<=0 or a%10000:raise ValueError("存单金额必须为正且整万元")
    return upper_int(int(a/10000))
def replace_doc(doc,m):
    def sub(p):
        for run in p.runs:
            for k,v in m.items():run.text=run.text.replace("{{"+k+"}}",str(v))
        full="".join(r.text for r in p.runs)
        if "{{" in full:
            for k,v in m.items():full=re.sub(r"{{\\s*"+re.escape(k)+r"\\s*}}",str(v),full)
            if p.runs:p.runs[0].text=full;[setattr(r,"text","") for r in p.runs[1:]]
    for p in doc.paragraphs:sub(p)
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:sub(p)
def run(args):
    rows=json.loads(Path(args.input).read_text(encoding="utf-8"))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for x in rows:
        bills=x["bills"]; total=sum(Decimal(str(b["amount"])) for b in bills)
        if total!=Decimal(str(x["contract_amount"])):raise ValueError(x["contract"]+"票据金额不符")
        if len(bills)!=int(x["bill_count"]):raise ValueError("票据张数不符")
        d=out/(x["contract"]+"_"+x["bill_due"]);d.mkdir(exist_ok=True)
        maturity=x.get("cd_due") or "【待核：存单实际到期日】"
        m={"客户名称":x["customer"],"存单账号":x["cd_account"],"存单金额":upper_wan(x["cd_amount"]),"存单到期日":maturity,"授信到期日":x["bill_due"]}
        md="## 客户资料\\n"+"\\n".join("- {{"+k+"}}: "+str(x["cd_amount"] if k=="存单金额" else v) for k,v in m.items())+"\\n"
        (d/"客户资料_填写模板.md").write_text(md,encoding="utf-8")
        doc=Document(args.word);replace_doc(doc,m);doc.save(d/"存单解冻通知书.docx")
        oa=Path(args.oa).read_text(encoding="utf-8")
        for k,v in m.items():oa=re.sub(r"{{\\s*"+re.escape(k)+r"\\s*}}",str(v),oa)
        (d/"OA给柜台_复制文本.txt").write_text(oa,encoding="utf-8")
        wb=load_workbook(args.excel);ws=wb.active
        for row in ws.iter_rows(min_row=3,max_row=max(ws.max_row,3+len(bills)),min_col=1,max_col=5):
            for c in row:c.value=None
        for i,b in enumerate(bills,3):
            for j,v in enumerate([i-2,str(b["number"]),b["due"],float(b["amount"]),x["customer"]],1):
                ws.cell(i,j).value=v
            ws.cell(i,2).number_format="@"
        wb.save(d/"支行需手工备款票据清单.xlsx")
        (d/"核验说明.txt").write_text("合同："+x["contract"]+"；票面合计："+str(total)+"元。存单本金差额非最终补款。存单实际到期日："+maturity+"；到期本息、柜面及集中作业中心办理须核实。",encoding="utf-8")
    with zipfile.ZipFile(str(out)+".zip","w",zipfile.ZIP_DEFLATED) as z:
        for f in out.rglob("*"):
            if f.is_file():z.write(f,f.relative_to(out.parent))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("input","word","excel","oa","out"):p.add_argument("--"+n,required=True)
    run(p.parse_args())
