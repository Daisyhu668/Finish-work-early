---
name: normalizing-corporate-financial-statements
description: Use when corporate financial statements from PDFs, scans, images, audit reports, or nonstandard Excel files must be converted into a bank's fixed financial-statement template for credit-system import.
---

# Corporate Financial Statement Normalizer

先读取[共用工作规则](../_shared/WORKFLOW.md)。

## Overview

Convert enterprise-provided financial statements into the bank's standard template without changing the template structure. The mandatory sequence is: extract, normalize, validate, populate, validate again, and export a system-readable PDF.

Accuracy takes precedence over speed. Never fabricate, backsolve, or silently alter figures merely to force a balance.

## When to Use

Use this skill when:
- A customer provides an audit report, scanned PDF, image, Word, native Excel, or self-designed financial statement.
- OCR output is incomplete, misaligned, or unreliable.
- Enterprise account names differ from the bank template.
- A relationship manager must enter annual, interim, monthly, standalone, or consolidated statements into the credit system.
- Beginning and ending balances, current and prior periods, or standalone and consolidated scopes may be confused.
- A clean PDF matching the bank template is required for secondary OCR import.

Do not use this skill to estimate missing statements without authorization or modify the bank template structure.

## Required Inputs

1. Enterprise financial-statement source.
2. Original bank financial-statement template.
3. Reporting instructions:
   - Enterprise name;
   - Reporting date;
   - Annual, interim, or monthly;
   - Standalone or consolidated;
   - Currency and monetary unit;
   - Audited or unaudited.

## Mandatory Workflow

### 1. Identify scope and time columns

Confirm:
- Enterprise legal name;
- Standalone or consolidated;
- Reporting period;
- Balance-sheet date;
- Profit and cash-flow period;
- Currency and unit;
- Audit opinion and report number;
- Exact meaning of every source column.

For annual statements:
- Balance-sheet beginning balance = prior year-end;
- Balance-sheet ending balance = current year-end;
- Income-statement prior amount = prior comparable period;
- Income-statement current amount = current reporting period;
- Cash-flow statement follows the same prior/current logic.

Never assume column meaning based on position or amount size. Read the source header.

### 2. Extract to a structured intermediate table

Before editing the template, create a Markdown or structured table containing:

| Field | Meaning |
|---|---|
| statement | Balance sheet, income statement, or cash-flow statement |
| source_account | Original account name |
| source_column | Exact source header |
| source_value | Original value |
| normalized_account | Bank-template account |
| mapping_basis | Direct match, accounting interpretation, or note breakdown |
| source_location | Page, row, table, or worksheet |
| confidence | High, medium, or low |
| remarks | OCR uncertainty, stamp obstruction, rounding, etc. |

Preserve negative signs, parentheses, decimals, units, and zero/blank distinctions.

### 3. Normalize account mapping

Apply this hierarchy:
1. Exact name match;
2. Equivalent account under accounting standards;
3. Breakdown from notes;
4. Aggregate to the closest defensible existing template account;
5. Leave blank and flag if no defensible mapping exists.

Rules:
- Never add rows or accounts to the bank template.
- Never rename template accounts.
- Never place a net figure into an original-cost field.
- If fixed-asset notes provide original cost, accumulated depreciation, and net value, populate all three.
- If only fixed-asset net value is disclosed, populate only the net-value row.
- Map right-of-use assets, contract assets, contract liabilities, lease liabilities, deferred income, other current assets/liabilities, and impairment losses by economic substance.
- Blank is not automatically zero.
- Process consolidated and standalone statements separately.

### 4. Validate source data

#### Balance sheet
- Total assets = total liabilities + total equity;
- Current and non-current subtotals agree with components;
- Fixed-asset original cost minus accumulated depreciation/impairment equals net carrying amount, where available;
- Current-year beginning balance agrees with prior-year ending balance unless an audit restatement is disclosed.

#### Income statement
- Revenue minus costs, taxes, expenses, and impairment plus/minus other operating items equals operating profit;
- Operating profit plus/minus non-operating items equals profit before tax;
- Profit before tax minus income-tax expense equals net profit;
- Consolidated net profit reconciles to parent-attributable profit and non-controlling interests, where disclosed.

#### Cash-flow statement
- Inflow subtotal minus outflow subtotal equals net cash flow for each activity;
- Operating + investing + financing + exchange-rate effect = net increase in cash;
- Beginning cash and cash equivalents + net increase = ending cash and cash equivalents;
- Reconcile ending cash with cash-note disclosures rather than automatically equating it to total monetary funds.

#### Cross-statement
- Net profit is consistent with equity movement after dividends, capital changes, reserves, and other comprehensive income;
- Borrowing changes are directionally consistent with financing cash flow;
- Ending monetary funds are reasonably consistent with cash-flow disclosures after restricted funds.

### 5. Handle discrepancies

Classify discrepancies as:
- OCR error;
- Unit error;
- Sign error;
- Column reversal;
- Rounding difference;
- Restatement;
- Note/main-statement inconsistency;
- Template mapping limitation;
- Source statement error.

Treatment:
- Correct only demonstrable OCR, unit, sign, or column errors.
- Preserve audit-report inconsistencies and record them.
- Never force-balance using an unexplained balancing figure.
- Treat differences within 0.01 monetary unit as rounding only when mathematically justified.
- Infer an obscured figure only when one unique value can be derived from an explicitly disclosed subtotal; record the derivation.

### 6. Populate the bank template

- Duplicate the original template.
- Clear only prior-customer input cells.
- Preserve sheet names, row order, formulas, formatting, merged cells, hidden sheets, metadata, and print settings.
- Populate reporting information and financial data.
- Do not add worksheets, rows, columns, comments, or explanatory text unless the template contains a designated field.
- Use the template's required unit.

### 7. Validate the completed template

Repeat all major validations inside the completed template:
- Beginning and ending columns are correct;
- Prior and current periods are correct;
- Assets equal liabilities plus equity;
- Profit calculations reconcile;
- Cash-flow calculations reconcile;
- Standalone and consolidated data are not mixed;
- Previous-customer figures are fully cleared;
- Template formulas and structure are intact.

Any failed validation blocks final delivery.

### 8. Export deliverables

Required outputs:
1. Completed bank-template Excel;
2. PDF exported from the completed template;
3. Structured Markdown extraction and mapping record;
4. Validation report with unresolved discrepancies.

PDF requirements:
- Each statement is legible;
- Headers and period labels are visible;
- No clipped rows or columns;
- No blank extra pages;
- One PDF per reporting scope;
- PDF content exactly matches the final Excel.

## Quick Reference

| Issue | Required action |
|---|---|
| Custom enterprise account | Map by economic substance |
| No equivalent template row | Use closest defensible row or leave blank and flag |
| Only fixed-asset net value available | Populate net value only |
| Beginning/ending appear reversed | Re-read source headers |
| Prior-year ending differs from current-year beginning | Check restatement notes |
| OCR sign or decimal uncertain | Verify against source image and subtotals |
| Balance sheet does not balance | Stop delivery and investigate |
| Cash-flow ending differs from monetary funds | Reconcile restricted funds and cash equivalents |
| Source statement contains inconsistency | Preserve, disclose, and do not force-correct |
| Template contains previous-customer data | Clear designated input cells before filling |

## Mandatory Guardrails

- No fabricated data.
- No undocumented balancing figures.
- No template structure changes.
- No mixing of standalone and consolidated data.
- No mixing of beginning/ending or prior/current columns.
- No conversion of blanks into zero without basis.
- No reliance on OCR alone for material figures.
- Every material figure must be traceable to a source page, note, or worksheet.
- Financial-logic validation is mandatory before and after template population.

## Delivery Checklist

- [ ] Enterprise, period, scope, currency, and unit confirmed
- [ ] Source extracted into Markdown
- [ ] Account mapping recorded
- [ ] Beginning/ending columns verified
- [ ] Prior/current columns verified
- [ ] Balance sheet balanced
- [ ] Income statement reconciled
- [ ] Cash-flow statement reconciled
- [ ] Cross-statement checks completed
- [ ] Standalone/consolidated separated
- [ ] Template structure unchanged
- [ ] Final Excel visually reviewed
- [ ] Final PDF visually reviewed
- [ ] Exceptions disclosed


## 模板依赖

沿用用户已有财报转换技能，原银行模板由用户在授权业务环境提供。本目录仅含通用转换规范；不重建模板，不假称已含原Excel。
