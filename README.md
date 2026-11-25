# Portfolio Trade Order Compliance & Execution Checker

## Overview

The Portfolio Trade Order Compliance & Execution Checker evaluates proposed portfolio trades before execution. It checks each trade against portfolio cash, security restrictions, current holdings, position limits, and manual-review rules. Each trade receives one of three decisions:

- **Approved** - all configured checks passed.
- **Rejected** - a configured trade, compliance, or execution rule failed.
- **Needs Manual Sign-off** - required reference data is unavailable or the trade meets the configured manual-review threshold.

The application records a reason for every decision and exports a transaction-level report.

## Project files

Place the following files in the same directory:

| File | Purpose |
|---|---|
| `test.py` | Main Python application. |
| `trades_test.csv` | Proposed trades to evaluate. |
| `portfolio_balance.json` | Available cash for each portfolio. |
| `security_reference.json` | Security restriction flags. |
| `portfolio_positions.json` | Current holdings and maximum position limits by portfolio and security. |
| `approval_rules.json` | Configurable manual-review threshold. |
| `trade_approval_report.csv` | Generated output report. |

## Requirements

- Python 3.8 or later recommended.
- pandas.

Install pandas:

```bash
python -m pip install pandas
```

## Input formats

### 1. Proposed trades: `trades_test.csv`

The CSV must contain these columns:

```csv
portfolio_id,security_id,action,quantity,price,security_type
POR001,TCS,buy,10,310,Equity
POR001,TCS,sell,5,310,Equity
```

`action` must be `buy` or `sell`. Quantity and price must be positive numeric values.

### 2. Portfolio cash: `portfolio_balance.json`

Stores available cash per portfolio. Each portfolio ID must appear only once.

```json
[
  {"portfolio_id": "POR001", "available_cash": 100000},
  {"portfolio_id": "POR002", "available_cash": 150000}
]
```

### 3. Security restrictions: `security_reference.json`

Stores whether each security is restricted. `restricted` must be a JSON boolean (`true` or `false`). Each security ID must appear only once.

```json
[
  {"security_id": "AAPL", "restricted": true},
  {"security_id": "TCS", "restricted": false}
]
```

### 4. Portfolio positions: `portfolio_positions.json`

Stores current holdings and the maximum permitted holding for each portfolio/security pair. Each pair must appear only once.

```json
[
  {
    "portfolio_id": "POR001",
    "security_id": "TCS",
    "current_holding": 50,
    "max_position": 100
  }
]
```

### 5. Approval rules: `approval_rules.json`

Sets the trade-value threshold at which manual sign-off is required.

```json
{
  "manual_review_trade_value": 50000
}
```

Replace example values with authorized, current reference data before using the application for real decisions.

## Run the application

1. Put all input files in the same folder as `test.py`.
2. Open a terminal in that folder.
3. Install pandas if it is not already installed.
4. Run:

```bash
python test.py
```

The application prints a transaction approval report and saves `trade_approval_report.csv` in the same directory.

## Validation flow

Trades are evaluated in the order they appear in `trades_test.csv`:

1. Required trade details must be present.
2. Action must be `buy` or `sell`.
3. Quantity and price must be positive numeric values.
4. Cash, security, and portfolio-position reference data must be available.
5. Restricted securities are rejected.
6. A buy must fit within available portfolio cash.
7. A sell must not exceed current holdings.
8. A buy must not exceed the configured maximum position.
9. A trade at or above the manual-review threshold requires manual sign-off.

The first applicable failure determines the decision and reason for that trade.

## Balance and holding updates

The application simulates trades sequentially. **Only Approved trades** update the in-memory portfolio state:

- Approved buy: subtracts `quantity * price` from portfolio cash and adds quantity to holdings.
- Approved sell: subtracts quantity from holdings and adds `quantity * price` to portfolio cash.
- Rejected or manually flagged trade: does not update cash or holdings.

These updates are in-memory for the current run. The JSON reference files are not changed.

## Output

`trade_approval_report.csv` contains the original trade fields plus:

- `decision`: `Approved`, `Rejected`, or `Needs Manual Sign-off`.
- `reason`: explanation for the decision.

The terminal also displays totals for approved, rejected, and manually flagged trades.

## Important assumptions and limitations

- Cash is shared across all securities within a portfolio, as represented by `portfolio_balance.json`.
- Holdings and maximum position limits are maintained separately for each portfolio/security pair.
- A missing cash, security, or position reference results in `Needs Manual Sign-off`; it is not automatically approved.
- The application uses the order of rows in the trades CSV as the proposed processing order.
- A manually flagged trade does not reserve cash or holdings. A human approval workflow and a subsequent re-validation step are not implemented.
- The manual-review threshold is a simple trade-value rule. Other business rules may require additional configuration.
- The application assumes sell proceeds are available to fund later buys after an approved sell. Confirm that this matches the organization's settlement and cash-availability policy.
- The sample JSON data is illustrative, not real portfolio or compliance data.
- This is a basic validation example, not a production trading or compliance platform. Production use requires authorized reference data, access controls, audit logging, exception handling, human approval integration, and review by the relevant compliance and operations teams.

## Troubleshooting

**`File not found`**: Check that the CSV and all four JSON files are in the same folder as `test.py`, and that the filenames match exactly.

**Missing-column error**: Check the CSV header spelling. The required trade columns are `portfolio_id`, `security_id`, `action`, `quantity`, `price`, and `security_type`.

**Invalid JSON error**: Check commas, quotation marks, brackets, and boolean values. JSON booleans must be lowercase `true` or `false`.

**Needs Manual Sign-off**: Check that the portfolio exists in `portfolio_balance.json`, the security exists in `security_reference.json`, and the portfolio/security pair exists in `portfolio_positions.json`. Also check whether the trade value reaches the configured threshold.

**Rejected trade**: Read the `reason` column in `trade_approval_report.csv` to identify the first rule that failed.
