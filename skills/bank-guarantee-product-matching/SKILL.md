---
name: bank-guarantee-product-matching
description: Use when 用户或待办涉及长融保、长易担、银担产品、产品匹配、检核表，需要办理银担产品匹配与方案检核。
---

# 银担产品匹配与方案检核

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

当前产品文件及版本、客户注册与经营情况、税收/财报、担保现状、用途、期限、额度需求及可接受还本方式。

## 执行

1. 读取businessGuideProducts、productMessagingPacks和checklist-generator/logic的适用产品分支。旧product_rm_expert只作历史资料，不将固化阈值当最新政策。
2. 建立准入字段表，区分已证据确认、缺失和不适用；逐项核用途、负面情形、在保额度及关联方、期限、非循环等关键条件。
3. 按客户实际比较长融保与长易担的办理路径、所需材料、担保安排及不适用点；补贴、贴息和担保费分别核实，不承诺自动叠加。
4. 原表有额度公式时保留并追溯输入；未知项不能默认通过，需突破的明确列审批诉求，不把建议写成批准。

## 交付

产品匹配说明、原模板检核表/授信方案候选稿、真实缺件清单和客户话术。

## 实现与依赖

- content/businessGuideProducts.ts
- content/productMessagingPacks.ts
- components/tools/checklist-generator/logic.ts

源码产品参数为历史口径，使用前必须核本次有效制度；正式表依赖原模板。
