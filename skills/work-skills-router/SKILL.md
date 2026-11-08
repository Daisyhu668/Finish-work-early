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
2. 先判断材料清单、批量开票文书、发票登记、真实BI关联是否是同一请求；含糊的“开票”不能自动转为第二阶段发票关联。
3. 记忆清理或技能沉淀走personal-work-assistant的references/memory-hygiene.md；客户移交/共同认领核对走loan-maturity-relay-and-credit-expiry的references/handover-review.md；风险客户重组/面访/审查回复走shouxin-report的references/restructuring-review.md。授信报告走shouxin-report；财报转换走normalizing-corporate-financial-statements；日常执行走personal-work-assistant。一年期银承先用acceptance-deposit-calculation核实银票/存单分别期限，再走under-invoice-workflow；不套用写死六个月的旧页面。
4. 查catalog的status、limitation和template_paths，核实文件及运行依赖；说明型技能可直接指导起草，模板或环境缺失则交已确认部分与具体缺口，不声称全自动成功。
5. 一个事项需要多个技能时按当前阶段顺序组合，客户上下文只核一次并保留来源；后续新增工作技能按../AGENTS.md保存并更新目录。

## 交付

给出匹配技能、当前可执行步骤和可用成果；确有阻塞时列出具体缺失字段或依赖。

## 实现与依赖

- skills/catalog.json
- skills/source-map.json
- skills/personal-work-assistant/SKILL.md
