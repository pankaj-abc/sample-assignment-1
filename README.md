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
