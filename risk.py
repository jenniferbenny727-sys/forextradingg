def calculate_position(balance: float, risk_pct: float, stop_pips: float, pair: str) -> dict:
    if balance <= 0 or risk_pct <= 0 or stop_pips <= 0:
        return {"error": "Balance, risk %, and stop distance must be positive."}

    risk_amount = balance * (risk_pct / 100.0)

    if pair.endswith("/USD") or pair in ("USD/CAD", "USD/CHF", "USD/JPY"):
        pip_value = 10.0
        note = "Standard lot pip value assumed 10 USD (USD-quoted or USD-base pair)."
    else:
        return {
            "error": (
                "Automatic pip-value conversion unavailable for this pair on free tier. "
                "Use a broker calculator for accurate sizing."
            )
        }

    lots = risk_amount / (stop_pips * pip_value)
    return {
        "risk_amount": round(risk_amount, 2),
        "lots": round(lots, 3),
        "pip_value": pip_value,
        "note": note,
    }
