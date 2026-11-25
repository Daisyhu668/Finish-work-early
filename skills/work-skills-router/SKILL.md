---
name: work-skills-router
description: Use when 用户或待办涉及工作技能、日常工作、待办调用技能、新增工作技能，需要办理工作技能统一入口。
---

# 工作技能统一入口

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

用户当前请求或Todoist任务原文；当前阶段；客户主体及业务期次。

## 执行

1. 读取../catalog.json与../source-map.json，按任务动作和业务对象找技能；只加载命中的SKILL.md及其必要资源，不一次读全库。
2. 先判断材料清单、批量开票文书、发票登记、真实BI关联是否是同一请求；含糊的“开票”不能自动转为第二阶段发票关联。**强制路由**：请求包含“发票、选票、银票关联、BI关联、InvoiceInfo、InvoiceLogInfo、xls导入报错、按月份剔除发票PDF”等任意线索时，先读`../bankpro-invoice-two-stage/SKILL.md`及所需`references/`，不可直接凭文件结构或金额猜配生成成品；BI真实收款人、票面金额、核验数据、客户确认的选票缺任一关键项，必须BLOCK并报告，不得绕过Skill。在发票关联业务中，逐BI核收款人=销方、金额足额，处理失败优先业务和物理格式双重排查。
3. 记忆清理或技能沉淀走personal-work-assistant的references/memory-hygiene.md；客户移交/共同认领核对走loan-maturity-relay-and-credit-expiry的references/handover-review.md；风险客户重组/面访/审查回复走shouxin-report的references/restructuring-review.md。授信报告走shouxin-report；财报转换走normalizing-corporate-financial-statements；日常执行走personal-work-assistant。一年期银承先用acceptance-deposit-calculation核实银票/存单分别期限，再走under-invoice-workflow；不套用写死六个月的旧页面。
4. 查catalog的status、limitation和template_paths，核实文件及运行依赖；说明型技能可直接指导起草，模板或环境缺失则交已确认部分与具体缺口，不声称全自动成功。
5. 一个事项需要多个技能时按当前阶段顺序组合，客户上下文只核一次并保留来源；后续新增工作技能按../AGENTS.md保存并更新目录。

## 交付

给出匹配技能、当前可执行步骤和可用成果；确有阻塞时列出具体缺失字段或依赖。

## 实现与依赖

- skills/catalog.json
- skills/source-map.json
- skills/personal-work-assistant/SKILL.md

## 银承两个用户入口（V3.4优先）
“银承前置准备/发票/购销合同识别/BI出来了”统一走bankpro-invoice-two-stage按阶段推进；“整套扫描PDF/向下交付材料/银承材料整理”优先走under-invoice-workflow，引用发票技能的最终选票，不重新登记、不另做系统操作Skill。测算及文书生成保留内部辅助入口。若两个阶段同时请求，先前置/关联，再交付归档。

## 强制路由：近期贴现及资金来源核查（2026-11-25）
凡用户提出企业近一周/一周之内有贴现、征信发现贴现、贴现说明、贴现流水、贴现资金去向、开票资金来源说明、质押存单资金来源核查等同义业务需求，必须先读 [bankpro-discount-fund-tracing/SKILL.md](../bankpro-discount-fund-tracing/SKILL.md) 及必要的输入规范和脚本。默认按完整工作流办理：逐页核查所有银行流水→按银行日期归集贴现笔数及净额→按收款方归集支出并勾稽余额→形成单段说明及Word→企业全称+贴现流水+银行名称重命名原件副本→合并PDF→验收打包。不能只写一段话，除非用户明确仅要文字。此为银承前置准备资金来源子模块；不另建第三个用户入口，不误路由到贴现专门授信；同一任务有发票时同时按原发票双阶段规范执行。征信查询日期须为真实确认日期，资金来源无存单入金证据不得作已核实结论。真实客户数据严禁进入公开仓库。
