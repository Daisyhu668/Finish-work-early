---
name: business-guide
description: Use when 用户或待办涉及业务通、贸易业分析、台企分析、客户主动问融资、产品打法，需要办理业务通与综合产品打法。
---

# 业务通与综合产品打法

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

客户行业、当前场景、真实融资/结算需求、已有资料和当前有效产品口径。

## 执行

1. 读取BusinessGuide及businessGuideGuideData的行业、场景和PERSONAS，仅取匹配项；产品字段读businessGuideProducts及productConfig。
2. 制造业/科技深分析分别路由专门技能，长融保/长易担走bank-guarantee-product-matching，首次拜访和他行客户转化走对应技能。
3. 贸易业核真实货物流、票据与回款，台企核集团支持、跨境交易、汇率与资金合规；以客户原始材料验证，不能从行业标签推定企业情况。
4. 筛除旧场景中“融资肯定没问题”等承诺，输出适配建议和可推进动作；产品及跨境规则以本次有效来源为准。

## 交付

场景打法、需求问题清单、产品候选及下一步资料/沟通TXT。

## 实现与依赖

- components/tools/BusinessGuide.tsx
- content/businessGuideGuideData.ts
- content/businessGuideProducts.ts
- content/productConfig.ts
