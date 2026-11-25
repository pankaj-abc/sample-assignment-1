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

# Portfolio Trade Order Compliance & Execution Checker

## Purpose

This application evaluates proposed portfolio trades before execution. It checks trade data, portfolio-specific restricted securities, sell holdings, buy affordability, and buy-only position concentration. Each trade receives one decision and a reason:

- **Approved**
- **Rejected**
- **Needs Manual Sign-off**

## Project files

Keep these files in one directory:

| File | Purpose |
|---|---|
| `test.py` | Main Python application |
| `trades_test.csv` | Proposed trade input |
| `portfolio_reference.json` | Portfolio cash, restricted securities, concentration cap, and current holdings |
| `trade_approval_report.csv` | Generated output |

## Requirements

- Python 3.8 or later
- pandas

Install pandas:

```bash
python -m pip install pandas
```

## Trade input: `trades_test.csv`

Required columns:

```csv
portfolio_id,security_id,action,quantity,price,security_type
POR001,TCS,Buy,10,310,Equity
POR001,INFY,Sell,5,1500,Equity
```

`action` must be `Buy` or `Sell` (case-insensitive). Quantity and price must be positive numbers. `security_type` is required as an input field.

## Portfolio reference: `portfolio_reference.json`

The JSON file contains one record per portfolio. Each record includes:

- `portfolio_id`
- `cash_balance`
- `restricted_securities`: list of security IDs restricted for that portfolio
- `max_position_pct`: maximum position concentration as a percentage from 0 to 100
- `current_holdings`: list of holdings, each with `security_id`, `quantity`, and its own `market_price`

Example:

```json
[
  {
    "portfolio_id": "POR001",
    "cash_balance": 100000,
    "restricted_securities": ["AAPL", "GOOGL", "TSLA"],
    "max_position_pct": 20,
    "current_holdings": [
      {"security_id": "TCS", "quantity": 50, "market_price": 310},
      {"security_id": "INFY", "quantity": 20, "market_price": 1500}
    ]
  }
]
```

Every holding must have a non-negative quantity and a positive market price. A security not present in `current_holdings` is treated as having an existing quantity of zero for that portfolio.

## Validation order

The application applies these rules in order. The first applicable failure determines the decision and reason.

1. **Validate:** quantity and price must be positive numbers; action must be Buy or Sell. Otherwise: `Rejected` - `Invalid trade data.`
2. **Restricted security:** if the security is in that portfolio's restricted list: `Rejected` - `Security is restricted for this portfolio.`
3. **Sell check:** for a Sell, current holdings must be at least the requested quantity. Equality passes. Otherwise: `Rejected` - `Insufficient holdings to sell.`
4. **Buy affordability:** for a Buy, `quantity * price` must not exceed cash balance. Equality passes. Otherwise: `Rejected` - `Insufficient cash for this buy order.`
5. **Buy-only concentration:** calculate the post-trade cash, post-trade quantity and value of the bought security, and the value of every other current holding using that holding's own market price. Divide the bought security's post-trade value by total portfolio value after the trade and multiply by 100. If the result strictly exceeds `max_position_pct`, return `Needs Manual Sign-off` with reason `Exceeds maximum position concentration — requires approval.` Equality with the cap passes. Sells do not run this check.
6. **Otherwise:** `Approved`.

## Run

Place `test.py`, `trades_test.csv`, and `portfolio_reference.json` in the same directory, then run:

```bash
python test.py
```

The application prints the decision and reason for every trade and writes `trade_approval_report.csv` to the same directory.

## Implementation notes

- Portfolio reference data is looked up by `portfolio_id`.
- Restricted securities are portfolio-specific.
- Current holdings are read as a reference snapshot. A missing security holding is treated as quantity zero.
- Each other holding is valued using its own stored `market_price`.
- The proposed trade's `price` is used to value the target security after a Buy, as specified.
- The application evaluates each proposed trade independently against the supplied reference snapshot. It does not update cash or holdings between rows because the stated rules do not specify sequential reservation or execution of proposed trades.
- Missing portfolio reference data results in `Needs Manual Sign-off`, because the required checks cannot be completed.
- This is a basic rule-based example. Use authorized, current reference data and obtain compliance approval before production use.
