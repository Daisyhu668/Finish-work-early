# 私有输入约定

参考计算最小输入：

```json
{"industry":"工业","metrics":{"employees":20,"revenue_wan":"2000"}}
```

人数为非负整数，金额为人民币万元无千分位十进制数；null/缺字段表示未知，有来源的0才是零。原始提取、单位换算、行业确定及来源核验由代理先完成，脚本不提供OCR。

完整制作在私有JSON中提供：

- company：正式全称；branch：见业务分支。
- industry、reporting_year（整数）、decision_date（YYYY-MM-DD）；非上一年度另提供period_exception_basis及真实依据。
- identity_confirmed、industry_confirmed、metrics_confirmed、period_confirmed、policy_applicability_confirmed：逐一读取原件后才能设true，不能默认全勾。
- staff_basis：employees_year_end/annual_average；仅insured_only不能用于需要人数的正式结论。
- metrics：按行业提供employees、revenue_wan、assets_wan。
- metric_sources：每个所用指标对应source、location、unit、year，必须可追溯原页。
- methods：industry（1至5）、staff（1至5）、finance（1至3），按真实证据选原表方法。
- evidence：finance、staff、industry三个对象；分别有paths（文件绝对路径数组）、company、source、identity_verified=true、content_verified=true；finance和staff另有year并与reporting_year一致。字段由代理真实核对，不因脚本需要编造。

evidence结构示例（全为合成）：

```json
{"finance":{"paths":["/private/审计报告.pdf"],"company":"示例企业有限公司","year":2025,"source":"用户原件","identity_verified":true,"content_verified":true}}
```

年审不更新仅需company、branch=annual_no_update，不要求无关财报；代理执行前先核业务分支。条件变更/个体户返回不需全套状态，不生成空包。

--out必须为空目录防串单；--audit指向材料包外部。脚本校验方法号范围但不代替真实性判断；来源类型、方法号相符由代理复核。所有客户JSON、审计、原件和成果不进技能或公开仓库。

--rules可省略，默认使用随包公开参考规则；这仅供参考计算或年审不更新分支使用。完整正式包必须显式指定经核行内配置。审计必须为独立JSON，禁止指向输入、规则、证据原件或输出目录；脚本会建立审计父目录。

出件前使用scripts/preflight.py集中列缺口。可选existing_labels为历史/外部标签数组，例如[{"value":"小型","source":"历史表"},{"value":"中型","source":"外部页面"}]。保留来源并核其年度与口径，不因有历史标签而省略实际证据。预检仅写独立JSON报告，不填表、不改源文件或任务。

标签冲突已实际核清时，提供label_conflict_resolution={"confirmed":true,"basis":"本期已读取的具体文件、页行及解释","year":指标年度}，保留原标签作为非阻断提示，不删除历史证据。该项仅解释历史标签差异，不能替代行内规则、核心指标或证据，不得为消除告警而捏造解释。
