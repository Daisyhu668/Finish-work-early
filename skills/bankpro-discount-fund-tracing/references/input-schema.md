# 输入约定与字段说明

JSON由Agent读完原始流水并复核后生成，金额使用十进制字符串，日期 ISO YYYY-MM-DD。源PDF路径相对JSON文件目录或绝对路径。id须为同银行内唯一的原始流水号或稳定的文件页码+行号；相同交易号的本金和利息可使用方向/类型后缀区分。其他入出账分别录入 other_in/other_out。

```json
{
  "company": "示例科技有限公司",
  "credit_query_date": "2026-11-25",
  "credit_query_confirmed": true,
  "source_status": "pending",
  "operating_use_confirmed": false,
  "banks": [{
    "bank": "示例银行", "pdf": "example.pdf",
    "opening": "10.00", "closing": "10.00",
    "discounts": [{"id":"1","date":"2026-11-19","amount":"1000.00"}],
    "interest": [{"id":"2","date":"2026-11-19","amount":"10.00"}],
    "payments": [{"id":"3","date":"2026-11-19","amount":"990.00","payee":"示例商贸有限公司","purpose":"货款"}],
    "fees": [], "other_in": [], "other_out": []
  }]
}
```

- discounts：实际放款入账额；已是净额时interest留空。单独列支且与该贴现有关的利息才填interest。
- payments：已追踪到的相关收款方交易；摘要未标注货款时填“转款”。其他支出录入other_out。
- opening/closing：完整连续流水可确定则必须填；不连续或筛选流水不得编造。缺失时脚本不做余额勾稽，Agent须提示覆盖缺口。
- source_status：pending / customer_confirmed / verified / exception。verified须提供source_evidence，即实际存单入金证据及核对依据；字符串本身不能替代证据。
- credit_query_confirmed：用户或征信原件确认实际查询日期及近一周贴现时才填true。
- operating_use_confirmed：已核查经营用途且基本已对外支付时填true；仅凭公司名称不能填true。
- 脚本可拒绝重复行、重复文件、余额不平、覆盖已有输出等问题，不能自行验证OCR正确性、交易归属或银行合规性。

## 验收场景
1. 净额贴现不能再扣息；分列利息才扣除。
2. 同一收款方多笔支付按全称归集；不同银行避免重复。
3. 支付大于净额时核期初余额，保留原数。
4. 无存单入金证据时不能声称已核实。
5. 无征信确认不得声称客户经理已查询。
6. 扫描件视觉核对，余额差额或重复标识须处理后再生成。
