---
name: rate-discount-report
description: Use when 用户或待办涉及利率优惠、贷款定价、优惠签报，需要办理利率优惠签报。
---

# 利率优惠签报

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

客户、金额、产品、期限、担保、用途、当前与拟执行利率、经核实LPR/FTP、EVA、当前权限及价格文件。

## 执行

1. 读取RateOfferTool结构与附件目录；CONFIG.THRESH、peerRange及默认LPR/FTP不是当前价格，先核本次有效来源和单位。
2. 计算拟利率与LPR/FTP差异：百分数口径相减乘100为BP；复核负号、利差和审批层级，不凭缺失参数判断权限。
3. 按客户事实写申请事项、经营及合作依据、定价对比、风险控制、综合收益和审批诉求；剔除无证据的“营收稳定/现金流覆盖”等套话。
4. 附件按真实已有文件列示，未获批前使用“拟申请”；不将贷款、存款、贴现与结汇点差混为同一价格。

## 交付

签报Word、短摘要TXT、价格及附件核对表。

## 实现与依赖

- components/tools/RateOfferTool.tsx
- lib/exportDocx.ts

网页为历史规则文案辅助；报价、LPR、FTP和权限须逐笔核实。
