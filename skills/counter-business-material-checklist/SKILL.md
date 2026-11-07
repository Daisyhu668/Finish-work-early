---
name: counter-business-material-checklist
description: Use when 用户或待办涉及开户材料、销户材料、变更材料、久悬户、柜面清单，需要办理开户销户及柜面材料清单。
---

# 开户销户及柜面材料清单

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

正式主体、账户类型、具体柜面动作、经办方式、已有有效材料及柜面本次确认口径。

## 执行

1. 读取data/checklistData.ts的COUNTER_BUSINESS，精确选择基本/一般/专户及开户、销户、变更或特殊业务分支，不套用授信材料。
2. 逐项保留原件/复印件、签章、交回、授权及特殊说明；旧受益所有人表述须与本次现行规则核对，不能仅凭源码阈值下结论。
3. 仅核实已在档、仍有效且没变更的资料才建议沿用；不能凭存量客户身份全部免交。
4. 输出客户需带清单与银行内部核对项，疑义先向柜面核对；未实际办理不写已开户或已销户。

## 交付

逐客户清单Word、客户微信TXT及内部核验TXT。

## 实现与依赖

- data/checklistData.ts
- components/MaterialChecklistCenter.tsx
