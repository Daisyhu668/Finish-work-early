---
name: competitor-customer-conversion
description: Use when 用户或待办涉及竞争客户、他行客户、挖角策略、客户转化，需要办理他行客户转化策略。
---

# 他行客户转化策略

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

当前他行合作事实、客户痛点、我行当前可执行产品和价格、成本收益与业务时点。

## 执行

1. 读取businessGuideGuideData的竞争场景及产品内容，先核客户已知事实，缺失的他行额度或利率不得推测。
2. 找能验证的服务切口，如周转、结算、票据、跨境及效率；避免贬低他行或以未批价格承诺吸引客户。
3. 按客户愿意试用的最小业务安排触达、材料和下一动作；用当前KPI口径区分存量承接与新增贡献。
4. 输出首次接触、深入询问和跟进话术，明确用户掌握的可谈空间及不能承诺事项。

## 交付

客户切入方案Word、可复制微信及后续动作TXT。

## 实现与依赖

- content/businessGuideGuideData.ts
- content/businessGuideProducts.ts
