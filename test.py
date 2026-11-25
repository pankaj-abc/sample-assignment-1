import json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent


def load_json(name):
    path = BASE / name
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {name}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def number(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def main():
    print("\n========== PRE-TRADE COMPLIANCE CHECK ==========")

    try:
        trades_path = BASE / "trades_test.csv"
        if not trades_path.exists():
            raise FileNotFoundError("Required file not found: trades_test.csv")
        trades = pd.read_csv(trades_path, dtype=str, keep_default_na=False)
        trades.columns = trades.columns.str.strip().str.lower()

        balances = load_json("portfolio_balance.json")
        securities = load_json("security_reference.json")
        positions = load_json("portfolio_positions.json")
        rules = load_json("approval_rules.json")
    except (FileNotFoundError, json.JSONDecodeError, pd.errors.EmptyDataError) as error:
        print(f"INPUT ERROR: {error}")
        return

    trade_columns = ["portfolio_id", "security_id", "action", "quantity", "price", "security_type"]
    missing = [column for column in trade_columns if column not in trades.columns]
    if missing:
        print(f"INPUT ERROR: trades_test.csv is missing columns: {missing}")
        return
    if trades.empty:
        print("INPUT ERROR: trades_test.csv contains no trades.")
        return

    # Validate and index portfolio cash.
    cash = {}
    for item in balances:
        portfolio = str(item.get("portfolio_id", "")).strip().upper()
        amount = number(item.get("available_cash"))
        if not portfolio or amount is None or amount < 0 or portfolio in cash:
            print("INPUT ERROR: Invalid or duplicate portfolio balance entry.")
            return
        cash[portfolio] = amount

    # Validate and index security restriction status.
    security_ref = {}
    for item in securities:
        security = str(item.get("security_id", "")).strip().upper()
        restricted = item.get("restricted")
        if not security or not isinstance(restricted, bool) or security in security_ref:
            print("INPUT ERROR: Security entries need unique security_id and true/false restricted values.")
            return
        security_ref[security] = restricted

    # Validate and index holdings and position limits.
    holdings = {}
    limits = {}
    for item in positions:
        portfolio = str(item.get("portfolio_id", "")).strip().upper()
        security = str(item.get("security_id", "")).strip().upper()
        current = number(item.get("current_holding"))
        maximum = number(item.get("max_position"))
        key = (portfolio, security)
        if not portfolio or not security or current is None or maximum is None or current < 0 or maximum < 0 or key in holdings:
            print("INPUT ERROR: Invalid or duplicate portfolio position entry.")
            return
        holdings[key] = current
        limits[key] = maximum

    manual_threshold = number(rules.get("manual_review_trade_value"))
    if manual_threshold is None or manual_threshold < 0:
        print("INPUT ERROR: approval_rules.json needs a non-negative manual_review_trade_value.")
        return

    # Normalize proposed trade fields.
    trades["portfolio_id"] = trades["portfolio_id"].str.strip().str.upper()
    trades["security_id"] = trades["security_id"].str.strip().str.upper()
    trades["action"] = trades["action"].str.strip().str.lower()

    decisions, reasons = [], []

    # Process in file order; only approved trades change simulated balances/holdings.
    for _, trade in trades.iterrows():
        portfolio = trade["portfolio_id"]
        security = trade["security_id"]
        action = trade["action"]
        quantity = number(trade["quantity"])
        price = number(trade["price"])
        key = (portfolio, security)
        decision = "Approved"
        reason = "All checks passed."

        if not portfolio or not security or not trade["security_type"].strip():
            decision, reason = "Rejected", "Required trade details are missing."
        elif action not in ("buy", "sell"):
            decision, reason = "Rejected", "Action must be buy or sell."
        elif quantity is None or quantity <= 0:
            decision, reason = "Rejected", "Quantity must be a positive number."
        elif price is None or price <= 0:
            decision, reason = "Rejected", "Price must be a positive number."
        elif portfolio not in cash or security not in security_ref or key not in holdings:
            decision, reason = "Needs Manual Sign-off", "Required portfolio, security, cash, or holdings reference data is missing."
        elif security_ref[security]:
            decision, reason = "Rejected", "Security is restricted."
        else:
            value = quantity * price
            if action == "buy" and value > cash[portfolio]:
                decision, reason = "Rejected", "Insufficient available cash."
            elif action == "sell" and quantity > holdings[key]:
                decision, reason = "Rejected", "Insufficient security holdings."
            elif action == "buy" and holdings[key] + quantity > limits[key]:
                decision, reason = "Rejected", "Maximum position limit would be exceeded."
            elif value >= manual_threshold:
                decision, reason = "Needs Manual Sign-off", "Trade value meets or exceeds the manual review threshold."

        if decision == "Approved":
            value = quantity * price
            if action == "buy":
                cash[portfolio] -= value
                holdings[key] += quantity
            else:
                holdings[key] -= quantity
                cash[portfolio] += value

        decisions.append(decision)
        reasons.append(reason)

    trades["decision"] = decisions
    trades["reason"] = reasons

    output_columns = trade_columns + ["decision", "reason"]
    print("\n========== TRADE APPROVAL REPORT ==========")
    print(trades[output_columns].to_string(index=False))

    print("\n========== FINAL SUMMARY ==========")
    print(f"Total trades: {len(trades)}")
    print(f"Approved: {(trades['decision'] == 'Approved').sum()}")
    print(f"Rejected: {(trades['decision'] == 'Rejected').sum()}")
    print(f"Needs Manual Sign-off: {(trades['decision'] == 'Needs Manual Sign-off').sum()}")

    output_path = BASE / "trade_approval_report.csv"
    trades[output_columns].to_csv(output_path, index=False)
    print(f"\nReport saved: {output_path.name}")
    print("========== VALIDATION COMPLETED ==========")


if __name__ == "__main__":
    main()
