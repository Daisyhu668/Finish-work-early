---
name: under-invoice-workflow
description: Use when 用户或待办涉及项下开票、银承预约、质押登记、中登登记、银承续开，需要办理银承项下全链路备稿。
---

# 银承项下全链路备稿

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

本期主体、客户号、账号、KP批次、合同、银票/存单日期、实际本金及利率、逐笔收款人和金额；审批与柜面最新进度。

## 执行

1. 读取UnderInvoiceWorkflow中的flowSteps及相应文本生成器，按本期阶段依次准备预约、存单利率申请、柜面提醒及取件、网银提票、合同及中登/押品登记备稿。
2. 测算先调用acceptance-deposit-calculation；需要发票登记或BI关联时调用bankpro-invoice-two-stage，缺BI时不生成第二阶段关联文件。
3. 最终开票与存单金额均以确认值为准，不把初测值写成最终；逐笔收款金额合计须等于本次开票金额。币种、票号、批次号分开核对。
4. 源码中的1.5倍担保、默认费率、发票例外区间是历史或示例，按本笔有效规则核实，不复制成现行制度；合同原文和签批不得代拟覆盖。
5. 生成逐阶段可复制文案及核对表，银行系统动作由用户实际办理后确认；固定Word/Excel另走batch-billing-documents并核模板。

## 交付

分阶段内部OA/预约TXT、客户办理材料TXT、逐笔明细Excel及字段确认单。

## 实现与依赖

- components/tools/UnderInvoiceWorkflow.tsx
- skills/bankpro-invoice-two-stage/SKILL.md

既有网页支持文本及JSON导出，不代表已具备行内Word/Excel全套批量生成或系统提交。

## 2026-11-25：提向下材料归档（本地扫描PDF）

复用本Skill，不新建重复入口。按客户、期限、业务日期/批次独立工作目录。建议固定扫描顺序：提票申请书、质押合同、出库单、入库单、承诺函、说明函、存单、冻结凭证、存款入账凭证、移交明细表；实际上传分类与必需/不适用项由用户按行内要求确认。不要固定页数。提前整理的购销合同和发票直接纳入，不重新打印扫描。

运行 python scripts/material_pack.py inspect --scan 整套.pdf --out 分页计划.json。PyMuPDF仅提取可用文字层前部标题候选，纯扫描件由授权环境Agent视觉识别或人工录入页码；不得根据页数猜边界。补全customer/term/period、required和not_applicable（覆盖全部预置类别）、segments（kind/start/end，一基闭区间）、external（path/kind/sha256/verified，发票另填payee及可选month），人工确认全部页归属后置confirmed:true。运行 python scripts/material_pack.py build --manifest 分页计划.json --out 最终提交包。按实际顺序合并同类购销合同PDF；发票按企业_发票_交易对手[_月份]归档，不跨对手或月份误合并；其他文件按企业_期限_日期或批次_内容命名。每页唯一归属，缺件、重复页、未确认页阻断。原PDF不改、不删、不上传外部。输出上传材料清单（TXT及JSON含来源页码），仅供实际系统提交前核对，不代替提交。安装 pip install pymupdf。扫描标题候选不是自动识别结果，扫描件须确认页界。
