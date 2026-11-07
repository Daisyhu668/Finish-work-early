---
name: discount-credit-workflow
description: Use when 用户或待办涉及贴现授信、专门授信、贴现调查报告，需要办理贴现专门授信办理。
---

# 贴现专门授信办理

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

正式主体、统一代码、注册信息、申请日期、上一年度营业收入、净资产、上下游及当前原模板、有效准入文件。

## 执行

1. 读取外部专仓SKILL.md、references/required-checklist.md和scripts/run_discount_pipeline.py等实际实现；取得同版完整源码及templates，不只下载单个SKILL.md。
2. 核原始资料并输出字段确认单；公开查询只补可核工商字段，收入和净资产必须来自本户原材料；原脚本收入×80%、净资产×12等公式须核本次有效制度，不自动沿用。
3. 本户确认后在授权私有环境运行不带--send-email的生成路径，先看--help并核实际参数。不要使用--yes跳过尚未核实的客户字段或审批。
4. 生成调查报告、附件4、客户盖章材料清单等适用文件，保持同版原模板及企业名称-文件名命名。缺材料只出可用草稿，不以--allow-missing当正式完整件。
5. 两封邮件默认仅草稿；对客户或他人发送必须有本次明确授权。给用户的成果合入已有综合邮件，不按旧专仓脚本自动另发两封。

## 交付

字段确认单、调查报告、附件4、适用操作材料及客户材料TXT、邮件草稿。

## 实现与依赖

- https://github.com/Daisyhu668/discount-credit-workflow-skill
- https://github.com/Daisyhu668/discount-credit-workflow-skill/blob/main/references/required-checklist.md

统一入口在主工作区，实际Python引擎与历史模板仍由专仓维护；本区不重复复制未经检查的历史模板。
