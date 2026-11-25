import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
TRADE_FILE = BASE_DIR / "trades_test.csv"
REFERENCE_FILE = BASE_DIR / "portfolio_reference.json"
OUTPUT_FILE = BASE_DIR / "trade_approval_report.csv"

REQUIRED_TRADE_COLUMNS = [
    "portfolio_id", "security_id", "action", "quantity", "price", "security_type"
]


def to_number(value):
    """Convert a value to float; return None when it is not numeric."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def load_inputs():
    if not TRADE_FILE.exists():
        raise FileNotFoundError("trades_test.csv was not found beside test.py.")
    if not REFERENCE_FILE.exists():
        raise FileNotFoundError("portfolio_reference.json was not found beside test.py.")

    trades = pd.read_csv(TRADE_FILE, dtype=str, keep_default_na=False)
    trades.columns = trades.columns.str.strip().str.lower()

    missing_columns = [column for column in REQUIRED_TRADE_COLUMNS if column not in trades.columns]
    if missing_columns:
        raise ValueError(f"trades_test.csv is missing columns: {missing_columns}")

    with REFERENCE_FILE.open("r", encoding="utf-8") as file:
        reference_data = json.load(file)

    if not isinstance(reference_data, list):
        raise ValueError("portfolio_reference.json must contain a JSON list of portfolios.")

    return trades, reference_data


def build_portfolio_lookup(reference_data):
    portfolios = {}

    for portfolio in reference_data:
        portfolio_id = str(portfolio.get("portfolio_id", "")).strip().upper()
        cash_balance = to_number(portfolio.get("cash_balance"))
        max_position_pct = to_number(portfolio.get("max_position_pct"))
        restricted = portfolio.get("restricted_securities")
        current_holdings = portfolio.get("current_holdings")

        if not portfolio_id or portfolio_id in portfolios:
            raise ValueError("Each portfolio must have a unique, non-empty portfolio_id.")
        if cash_balance is None or cash_balance < 0:
            raise ValueError(f"Invalid cash_balance for portfolio {portfolio_id}.")
        if max_position_pct is None or not 0 <= max_position_pct <= 100:
            raise ValueError(f"max_position_pct for {portfolio_id} must be between 0 and 100.")
        if not isinstance(restricted, list) or not isinstance(current_holdings, list):
            raise ValueError(f"restricted_securities and current_holdings must be lists for {portfolio_id}.")

        holdings = {}
        for holding in current_holdings:
            security_id = str(holding.get("security_id", "")).strip().upper()
            quantity = to_number(holding.get("quantity"))
            market_price = to_number(holding.get("market_price"))
            if not security_id or security_id in holdings:
                raise ValueError(f"Invalid or duplicate holding in portfolio {portfolio_id}.")
            if quantity is None or quantity < 0 or market_price is None or market_price <= 0:
                raise ValueError(f"Invalid quantity or market_price for {security_id} in {portfolio_id}.")
            holdings[security_id] = {
                "quantity": quantity,
                "market_price": market_price
            }

        portfolios[portfolio_id] = {
            "cash_balance": cash_balance,
            "restricted_securities": {
                str(security).strip().upper() for security in restricted
            },
            "max_position_pct": max_position_pct,
            "current_holdings": holdings
        }

    return portfolios


def evaluate_trade(trade, portfolios):
    """Apply the requested rules in order and return decision and reason."""
    portfolio_id = str(trade["portfolio_id"]).strip().upper()
    security_id = str(trade["security_id"]).strip().upper()
    action = str(trade["action"]).strip().lower()
    quantity = to_number(trade["quantity"])
    price = to_number(trade["price"])
    security_type = str(trade["security_type"]).strip()

    # Step 1: Validate trade data.
    if (not portfolio_id or not security_id or not security_type
            or quantity is None or quantity <= 0
            or price is None or price <= 0
            or action not in ("buy", "sell")):
        return "Rejected", "Invalid trade data."

    # Portfolio reference data is required to run Steps 2-5.
    if portfolio_id not in portfolios:
        return "Needs Manual Sign-off", "Portfolio reference data is unavailable."

    portfolio = portfolios[portfolio_id]

    # Step 2: Restricted security check.
    if security_id in portfolio["restricted_securities"]:
        return "Rejected", "Security is restricted for this portfolio."

    holdings = portfolio["current_holdings"]
    existing_quantity = holdings.get(security_id, {}).get("quantity", 0.0)

    # Step 3: Sell check.
    if action == "sell":
        if existing_quantity < quantity:
            return "Rejected", "Insufficient holdings to sell."
        return "Approved", "Trade passed all checks."

    # Step 4: Buy affordability check.
    trade_cost = quantity * price
    cash_balance = portfolio["cash_balance"]
    if trade_cost > cash_balance:
        return "Rejected", "Insufficient cash for this buy order."

    # Step 5: Buy-only position concentration check.
    post_trade_cash = cash_balance - trade_cost
    post_trade_quantity = existing_quantity + quantity
    post_trade_value_of_this_security = post_trade_quantity * price

    value_of_other_holdings = 0.0
    for other_security_id, holding in holdings.items():
        if other_security_id != security_id:
            value_of_other_holdings += holding["quantity"] * holding["market_price"]

    total_portfolio_value_after = (
        post_trade_cash
        + post_trade_value_of_this_security
        + value_of_other_holdings
    )

    if total_portfolio_value_after <= 0:
        return "Rejected", "Invalid total portfolio value after trade."

    position_pct = (
        post_trade_value_of_this_security / total_portfolio_value_after
    ) * 100

    if position_pct > portfolio["max_position_pct"]:
        return (
            "Needs Manual Sign-off",
            "Exceeds maximum position concentration — requires approval."
        )

    # Step 6: All checks passed.
    return "Approved", "Trade passed all checks."


def main():
    print("\n========== PORTFOLIO TRADE ORDER COMPLIANCE & EXECUTION CHECKER ==========")

    try:
        trades, reference_data = load_inputs()
        portfolios = build_portfolio_lookup(reference_data)
    except (FileNotFoundError, ValueError, json.JSONDecodeError, pd.errors.EmptyDataError) as error:
        print(f"INPUT ERROR: {error}")
        return

    if trades.empty:
        print("INPUT ERROR: trades_test.csv contains no proposed trades.")
        return

    decisions = []
    reasons = []

    # Evaluate each trade against the reference snapshot, in input order.
    # The stated rules do not request cash/holding updates between proposed trades.
    for _, trade in trades.iterrows():
        decision, reason = evaluate_trade(trade, portfolios)
        decisions.append(decision)
        reasons.append(reason)

    trades["decision"] = decisions
    trades["reason"] = reasons

    output_columns = REQUIRED_TRADE_COLUMNS + ["decision", "reason"]
    print("\n========== TRADE APPROVAL REPORT ==========")
    print(trades[output_columns].to_string(index=False))

    print("\n========== FINAL SUMMARY ==========")
    print(f"Total trades: {len(trades)}")
    print(f"Approved: {(trades['decision'] == 'Approved').sum()}")
    print(f"Rejected: {(trades['decision'] == 'Rejected').sum()}")
    print(f"Needs Manual Sign-off: {(trades['decision'] == 'Needs Manual Sign-off').sum()}")

    trades[output_columns].to_csv(OUTPUT_FILE, index=False)
    print(f"\nReport saved: {OUTPUT_FILE.name}")
    print("========== VALIDATION COMPLETED ==========")


if __name__ == "__main__":
    main()
