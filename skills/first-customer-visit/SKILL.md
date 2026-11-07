---
name: first-customer-visit
description: Use when 用户或待办涉及首次拜访、客户走访、初访准备、走访纪要，需要办理首次客户拜访与走访记录。
---

# 首次客户拜访与走访记录

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

企业正式名称、当前沟通记录、拜访目标、行业、已知产品和实际预约安排。

## 执行

1. 读businessGuideGuideData的first_visit及对应行业要点，结合原客户档案形成拜访前背景卡；无依据不写“关注多年/口碑很好”。
2. 围绕主营业务、订单、上下游账期、资金缺口、他行服务与担保安排列必要问题，按对方回答再展开。
3. 走访后仅把实际观察和客户陈述分开记录；未走访不虚构厂房、人员、生产及拍照情况。
4. 形成需求、产品候选、材料、责任人及下一检查点；晨会提炼客户、进展、预计落地及待做系统动作。

## 交付

拜访提纲TXT、实际走访记录Word、简短晨会汇报TXT。

## 实现与依赖

- content/businessGuideGuideData.ts
- components/tools/BusinessGuide.tsx
