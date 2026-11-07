---
name: technology-credit-research
description: Use when 用户或待办涉及科技企业行业洞察、研发分析、科技客户分析，需要办理科技企业经营与授信分析。
---

# 科技企业经营与授信分析

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

具体客户、行业子类、分析日期及目的，已有财税、订单、上下游、流水、资质与融资材料。

## 执行

1. 读取businessGuideGuideData的INDUSTRIES.tech_enterprise及对应产品资料，以本客户证据重建经营链，不把行业一般特点写成客户事实。
2. 将经营模式连接到资金用途、周转、回款和偿债来源；制造业重点核产能、采购成本、库存和应收，科技企业重点核研发资本化、技术收入、人员、订单及持续融资需求。
3. 把风险与可证实的缓释措施对应，区分缺口与确定问题；最新行业数据、政策或价格只用经核官方来源，附日期。
4. 给产品适配、走访要点和下一步材料建议；没有现行准入依据时只给候选产品，不承诺额度。

## 交付

客户经营及行业分析Word、风险与证据表、拜访问题及客户沟通TXT。

## 实现与依赖

- content/businessGuideGuideData.ts
- content/businessGuideProducts.ts
