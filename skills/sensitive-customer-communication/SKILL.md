---
name: sensitive-customer-communication
description: Use when 用户或待办涉及收费通知、利率调整、授信暂缓、拒贷沟通、敏感沟通，需要办理敏感客户沟通。
---

# 敏感客户沟通

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

当前业务事实、沟通对象、渠道、已确认决策、可争取空间、用户希望保留的边界。

## 执行

1. 读取SensitiveCommAssistant对应场景，先说明已确认结论及依据，再提供可执行下一步；未获批的事项不许诺金额、利率、时效。
2. 将内部风险和审批意见转为客户可理解的必要说明，不暴露无关内部标签、他人资料或未经核实判断。
3. 按微信/电话/OA选择长度；微信优先给直接可发一版，必要时另给正式版和柔和版，避免堆砌致歉。
4. 涉及催办先核客户是否已交资料、用户是否已处理，不重复首次通知；只起草，未经明确授权不联系客户。

## 交付

可直接复制的微信TXT；需要时附电话提纲或正式函Word。

## 实现与依赖

- components/tools/SensitiveCommAssistant.tsx
- public/guides/customer-communication.html
