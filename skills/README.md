# 工作技能区

日常银行工作技能的统一维护入口。新增工作技能统一放在本目录；已有脚本、模板及调用路径保留，避免破坏现有任务。开发用的GitNexus/生成技能仍在`.agents/skills`和`.claude/skills`，生活/社区项目保留原位。

**先读 [工作技能统一入口](work-skills-router/SKILL.md)**；按任务关键词查[机器目录](catalog.json)。[逐项来源映射](source-map.json)覆盖网页原27个目录项，并补入项下开票链路与独立授信/开户等来源。

本区包含办理说明、现有离线脚本入口及外部引擎入口；收录不等于已经自动执行，也不等于已经安装进任何客户端。具体环境、模板与局限以目录和各技能为准。

## 日常执行

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [日常主动工作助理](personal-work-assistant/SKILL.md) | 今天待办、工作成果、收件箱 | 连接应用执行规范 |
| [工作技能统一入口](work-skills-router/SKILL.md) | 工作技能、日常工作、待办调用技能、新增工作技能 | 办理说明/备稿 |
| [按客户汇总工作周报](weekly-work-report/SKILL.md) | 周报、晨会汇报、月度工作汇报、领导进度汇报 | 办理说明/备稿 |

## 贷后与期限

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [借据接力贷与额度到期](loan-maturity-relay-and-credit-expiry/SKILL.md) | 借据到期、接力贷、额度到期、续授信 | 办理说明/备稿 |
| [提前还款申请](prepay-corporate-loan/SKILL.md) | 提前还款、提前结清 | 已有离线脚本 |
| [重大预警额度解冻申请](credit-limit-unfreeze/SKILL.md) | 额度解冻、重大预警冻结、接力贷解冻 | 依赖本次原模板/资料 |

## 材料与调查

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [客户专属授信材料清单](customer-credit-material-checklist/SKILL.md) | 材料清单、授信材料、年审、续授信材料 | 办理说明/备稿 |
| [开户销户及柜面材料清单](counter-business-material-checklist/SKILL.md) | 开户材料、销户材料、变更材料、久悬户 | 办理说明/备稿 |
| [开户尽职调查预填](account-opening-due-diligence/SKILL.md) | 开户尽调、开户调查表 | 外部代码/模板依赖 |
| [销户尽职调查预填](account-closing-due-diligence/SKILL.md) | 销户尽调、销户调查表 | 外部代码/模板依赖 |
| [企业划型与ECIF佐证材料](enterprise-size-classification/SKILL.md) | 企业划型、001-划型、划型佐证、ECIF佐证 | 依赖本次原模板/资料 |
| [受益所有人穿透与证据整理](beneficial-owner-evidence/SKILL.md) | 受益所有人、股权穿透、境外股东、查册材料 | 依赖本次原模板/资料 |

## 票据与存单

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [发票登记与银承关联](bankpro-invoice-two-stage/SKILL.md) | 整理发票、发票登记、选票、BI关联 | 已有离线脚本 |
| [存单解冻与手工备款](cd-unfreeze-manual-funding/SKILL.md) | 存单解冻、解除质押、手工备款 | 依赖本次原模板/资料 |
| [银承与存单测算](acceptance-deposit-calculation/SKILL.md) | 银承测算、存单测算、一年期银承、半年期银承 | 办理说明/备稿 |
| [银承项下全链路备稿](under-invoice-workflow/SKILL.md) | 项下开票、银承预约、质押登记、中登登记 | 办理说明/备稿 |
| [批量开票文书与明细](batch-billing-documents/SKILL.md) | 批量开票、项下开票材料、开票工具包、批量生成开票文书 | 依赖本次原模板/资料 |

## OA与文稿

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [账户费用优惠申请](account-fee-discount/SKILL.md) | 账户费用优惠、费用减免、中收优惠 | 办理说明/备稿 |
| [利率优惠签报](rate-discount-report/SKILL.md) | 利率优惠、贷款定价、优惠签报 | 办理说明/备稿 |
| [银行宣传稿与排版](bank-news-typesetting/SKILL.md) | 厦行信息、银行宣传稿、新闻稿排版、投稿 | 办理说明/备稿 |
| [授信合同封包与用印沟通](credit-contract-sealing/SKILL.md) | 授信合同用印、合同封包、信托用印、法审回复 | 办理说明/备稿 |

## 客户经营

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [敏感客户沟通](sensitive-customer-communication/SKILL.md) | 收费通知、利率调整、授信暂缓、拒贷沟通 | 办理说明/备稿 |
| [业务通与综合产品打法](business-guide/SKILL.md) | 业务通、贸易业分析、台企分析、客户主动问融资 | 办理说明/备稿 |
| [首次客户拜访与走访记录](first-customer-visit/SKILL.md) | 首次拜访、客户走访、初访准备、走访纪要 | 办理说明/备稿 |
| [他行客户转化策略](competitor-customer-conversion/SKILL.md) | 竞争客户、他行客户、挖角策略、客户转化 | 办理说明/备稿 |

## 授信与分析

| 技能 | 常用触发词 | 当前能力/依赖 |
| --- | --- | --- |
| [银担产品匹配与方案检核](bank-guarantee-product-matching/SKILL.md) | 长融保、长易担、银担产品、产品匹配 | 办理说明/备稿 |
| [制造业客户经营与授信分析](manufacturing-credit-research/SKILL.md) | 制造业行业洞察、制造业客户分析 | 办理说明/备稿 |
| [科技企业经营与授信分析](technology-credit-research/SKILL.md) | 科技企业行业洞察、研发分析、科技客户分析 | 办理说明/备稿 |
| [流动资金贷款需求测算](working-capital-calculation/SKILL.md) | 流贷测算、营运资金、流动资金需求、周转天数 | 依赖本次原模板/资料 |
| [客户经理KPI自评与冲刺分析](kpi-self-review/SKILL.md) | KPI分析、排名下降、考核自评、认领攻略 | 办理说明/备稿 |
| [固定模板授信调查报告](shouxin-report/SKILL.md) | 授信报告、调查报告、审查意见回复、报告优化 | 依赖本次原模板/资料 |
| [财报转换与勾稽核验](normalizing-corporate-financial-statements/SKILL.md) | 财报转换、财报标准化、财务报表整理 | 依赖本次原模板/资料 |
| [贴现专门授信办理](discount-credit-workflow/SKILL.md) | 贴现授信、专门授信、贴现调查报告 | 外部代码/模板依赖 |

## 使用示例

| 待办/请求 | 调用顺序 |
| --- | --- |
| 某企业续授信 | 到期核验→客户材料清单→当前阶段→授信报告→复核上报备稿 |
| 某客户提前还款 | 提前还款申请→读取原客户及本笔借据→填两联原模板，未知留空 |
| 一年期银承方案 | 银承存单测算→先核银票/存单分别期限及准入→按真实日期复算 |
| 某企业批量开票材料 | 项下全链路备稿→批量文书；原模板缺失时交已确认明细及缺口 |
| 整理发票/关联BI | 发票双阶段：登记与关联分开；关联须有真实选票及BI |
| 重大预警额度冻结 | 额度解冻申请；不套用存单解冻通知书 |

## 已核实现限制

- `BatchBillingTool.tsx`下载/生成按钮为toast占位；本次补齐办理技能入口，没有把占位网页改成可运行的一键工具。
- `AcceptanceCalculator.tsx`固定六个月；`UnderInvoiceWorkflow.tsx`可改期限，但银票/存单日期不同须单独复算，示例担保倍数不能当批复。
- 产品、定价及收费参数属于历史源码内容，使用时核当前有效制度；支持输入期限不证明业务准入。
- 发票原版xls按专项要求本地提供；提前还款两联模板及存单解冻两份模板已有仓库路径，仍须核版本。其他原模板未取得时明确依赖，不以自建模板替代。

## 新增与维护

新增一个可复用业务动作时：先查是否已有技能→完善原技能或建`skills/<英文动作名>/SKILL.md`→写明输入、步骤、产物和真实依赖→随包放获授权公开的空白模板/脚本→更新`catalog.json`、本目录和`source-map.json`→校验后保存。客户资料不进入公开仓库。

日常自动任务先读取本目录和目录文件，再按当前待办加载命中技能；任务完成与外发仍遵循现有授权。收件箱保持用户自主处置，不能因技能整理修改原待办。

规则：[工作区维护约定](AGENTS.md) · [共用办理规则](_shared/WORKFLOW.md) · [仓库归类与来源](REPOSITORIES.md)
