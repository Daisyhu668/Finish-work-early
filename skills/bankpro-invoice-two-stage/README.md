# BankPro · 发票登记与银承发票关联 Skill v3.2

这是一个面向**多个企业、多个批次**的双阶段 Agent Skill，不附带任何客户发票数据。整套流程：

- **Stage 1 / InvoiceLogInfo.xls：** 企业多个来源的发票数据→规范校验→全部有效发票填银行登记模板→入系统提前核验。
- **Stage 2 / InvoiceInfo.xls：** 银行核验后明确选定发票→用户提供真实BI号/对手/票面→自动匹配并可按同一对手多张BI分票→核查逐BI发票金额是否足够→人工审核后填银行关联模板。

## 安装

把本目录作为一个完整技能文件夹安装到支持 Agent Skills 的运行环境，入口为 `SKILL.md`。推荐Windows + Microsoft Excel（WPS COM仅可作为需进一步验证的备选）。

```powershell
py -m pip install -r requirements-windows.txt
py -m unittest discover -v -s tests
```

`pywin32`负责对银行原版二进制`.xls`执行**只写单元格值**；`ortools`用于大量发票下同一收款人多张BI的组合分配。安装依赖并不等于已完成银行导入联调。

## 快速开始

```powershell
# 每个企业/批次建立不同case-id
py scripts/case_workflow.py init --workspace "案件" --customer "企业全称" --case-id CASE20261029A

# 第一次：登记全部源发票（可传多份 xlsx/csv/xls）
py scripts/case_workflow.py prepare --case "案件/CASE20261029A" --sources "202607.xlsx" "202608.xlsx" "202609.xlsx"
py scripts/case_workflow.py registration --case "案件/CASE20261029A" --out "输出/登记.xls"

# 银票生成后：填写 stage2/bills_to_fill.json；再用选定发票号码（每行一张）生成计划
py scripts/case_workflow.py bi-template --case "案件/CASE20261029A"
py scripts/case_workflow.py plan --case "案件/CASE20261029A" --bills "案件/CASE20261029A/stage2/bills_to_fill.json" --selected-invoices "选中发票号码.txt" --status-source "最新核验列表.xlsx"

# 复核计划中的每张BI收款人、金额、选票后执行；SHA来自plan输出
py scripts/case_workflow.py association --case "案件/CASE20261029A" --confirm-plan "计划中的SHA256" --out "输出/关联.xls"
```

### 对于一家公司多张银票

在`bills`数组中填写两行相同`payee`但不同`bi`和`amount`。优化器给同一收款人的已选发票分组；**每张发票只关联一个BI**。若实际发票分组无法分别覆盖两张银票，直接报错，不串票、不重复占用。

### 重要业务限制

- `InvoiceLogInfo.xls`和`InvoiceInfo.xls`由由授权用户在本地将**未修改的银行原始xls模板**放入`assets/`，仓库不包含这两份内部模板；校验规则见`references/templates.md`。
- 如果源资料缺商品名称、发票介质、购销双方、不含税金额等必填字段，不能凭惯例猜填。
- 银票尚未出具时只生成可填写BI清单，**不能**生成虚假银行关联Excel。
- 关联阶段必须有最新系统核验次数/占用状态（系统表或人工核对JSON），不默认0次。
- 脚本不直接连接银行系统、不执行实际开户、开票或发票查验；所有xls是**导入候选件**，须行内实际验证。

## 本版变更（3.1）

- 冻结底稿指纹覆盖商品名称、发票类型、介质及来源位置；后期无声修改会被阻断。
- 银承关联时必须有最新外查次数和已占用金额；缺失不能继承登记阶段旧值。
- 拒绝非整数外查次数及非法已占用金额。
- 对超出原版模板预置格式的数据行提前检查并报错，不擅自复制格式或添加行。
## 公共GitHub安全发布说明

本仓库为公开仓库。只允许上传脱敏代码、流程和虚构示例，**不得提交真实企业发票、合同、账户、银行内部模板、生产核验结果**。请在授权本地环境下载/放置 `InvoiceLogInfo.xls` 和 `InvoiceInfo.xls`，并运行完整的本地Skill包。若无Windows Excel COM环境，输出仅限预处理与审核计划，不生成声称可导入的xls。

### 自然语言触发

- `整理发票`：无BI则执行阶段一完整发票登记及核验前准备；已有BI和已选票名单则进入阶段二。
- `这批发票外部查询2次的剔掉`：生成风险筛选和选票/剔票清单，不修改第一阶段登记底稿。
- `汇票序号出来了`：读取最新核验及实际BI、按销方匹配收款人、支持同一收款人多BI自动测算，先审核方案再填InvoiceInfo.xls。

## 2026-11-25：BI极速关联 + 购销合同联合处理（v3.3）

提票前从客户原始合同（本地授权环境）识别购方、销方、合同编号、签订日、合同金额、已核实未付款余额。单份可人工填写，多份由Agent提取后逐项核实，不猜未付金额。将结构化合同保存为 JSON（customer、case_id、contracts，每项 buyer/seller/number/date/amount/unpaid/verified），运行 scripts/contract_reconcile.py --contracts 合同.json --out 输出，生成购销合同录入.txt及合同未付余额.json；提票后加 --bills 真实BI.json，复核同户同批各对手银票总额不得超过已核实未付余额。将余额JSON录入BI payload的 contract_unpaid_by_payee 后再执行plan。合同与发票共同核验，不替代合同真实性调查。

极速：已冻结底稿、最终选票、最新核验、真实BI主表齐备且单BI时，在BI payload明确 fast_confirmed_selection:true，plan直接全量映射已确认发票至该BI，不进入组合求解；原有人工映射、覆盖、占用、核验、日期及计划指纹确认全部保留。多个BI且不同收款人、每个对手仅一BI时也可用该模式；同一对手多BI仍走原分票优化器。无需重复OCR或重新整理第一阶段。手动Excel仅允许在已审核计划对应的原模板副本按实际表头“汇票序号1”填值；禁止猜列号、覆盖其他数据、将编号当数字。建议优先使用原writer保真写出；没有Windows Excel COM不能宣称已生成可导入xls。系统成功后才调整最终发票PDF副本。

### 极速版实际命令

- 提票前：Agent在授权本地环境识别合同，核实后保存合同JSON；单份合同手工填也可以。运行 contract_reconcile.py 产生次日复制用TXT。
- 提票后：原 plan 命令增加 --contracts 合同.json --fast-confirmed-selection，直接联合合同余额/交易对手检查，并在 stage2 生成购销合同录入.txt。仅已确认全部发票且每对手一BI时跳过组合求解；复杂分票仍使用原算法。
- 已有原版关联模板的预填副本（所有非BI字段已填、BI列空白）：association 命令增加 --prepared 预填副本.xls。脚本按真实表头定位汇票序号列、逐行对照冻结底稿和审核计划、比较原版结构、检查旧数据及空BI，只写这一列并保存新副本；不符合即BLOCK，改走原版模板批量生成。无预填副本时默认按列批量写Value2，减少Excel COM调用。
- 不改变原先 --confirm-plan 门禁；没有真实BI主表及最新查验数据不能只凭编码猜收款人/金额/日期。Windows Excel COM及行内导入仍须实机联调。
