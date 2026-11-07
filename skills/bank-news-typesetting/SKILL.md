---
name: bank-news-typesetting
description: Use when 用户或待办涉及厦行信息、银行宣传稿、新闻稿排版、投稿，需要办理银行宣传稿与排版。
---

# 银行宣传稿与排版

先读取[共用工作规则](../_shared/WORKFLOW.md)，再执行本技能。

## 输入

原始事实材料、确切标题/时间/名称/活动内容、配图及授权、落款单位和投稿要求。

## 执行

1. 读取NewsTypesettingAssistant的栏目、样式、图片与Word导出结构，采用本次明确要求的版式。
2. 逐条核事实，区分已发生和计划；不编造金额、荣誉、领导讲话或客户评价。需要新事实时回查原文和官方来源。
3. 先写清事件及工作成果，再以必要背景支撑；新闻摘要任务按用户要求控制200—250字，内部宣传稿按投稿规范，不混用公众号心理战文风。
4. 图注、署名、落款和日期按已提供内容；导出可编辑Word并检查图片、分页和文字溢出。

## 交付

成稿Word、纯文本及必要排版核对项。

## 实现与依赖

- components/tools/NewsTypesettingAssistant.tsx
- public/guides/document-typesetting.html
