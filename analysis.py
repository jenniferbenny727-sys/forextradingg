import logging
from typing import Optional

logger = logging.getLogger(__name__)

def _ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out

def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    return 100 - (100 / (1 + ag / al))

def _macd(closes: list[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    e12 = _ema(closes, 12)
    e26 = _ema(closes, 26)
    if not e12 or not e26:
        return None, None, None
    n = min(len(e12), len(e26))
    macd_line = [e12[i] - e26[i] for i in range(n)]
    signal = _ema(macd_line, 9)
    if not signal:
        return macd_line[-1], None, None
    hist = macd_line[-1] - signal[-1]
    return macd_line[-1], signal[-1], hist

def _atr(candles: list[dict], period: int = 14) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(len(candles) - 1, 0, -1):
        h = float(candles[i - 1]["high"])
        l = float(candles[i - 1]["low"])
        pc = float(candles[i]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        if len(trs) >= period:
            break
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period

def analyze(pair: str, candles: list[dict]) -> dict:
    closes = [float(c["close"]) for c in reversed(candles)]
    e20 = _ema(closes, 20)
    e50 = _ema(closes, 50)
    rsi = _rsi(closes)
    macd_line, signal_line, hist = _macd(closes)
    atr = _atr(candles)

    result = {
        "pair": pair,
        "decision": "NO TRADE",
        "reason": "",
        "entry": None, "stop": None, "tp1": None, "tp2": None,
        "rr": None, "atr": atr,
        "ema20": e20[-1] if e20 else None,
        "ema50": e50[-1] if e50 else None,
        "rsi": rsi, "macd_hist": hist,
    }

    if not e20 or not e50 or rsi is None or hist is None or atr is None:
        result["reason"] = "Insufficient data for indicators."
        return result

    price = closes[-1]
    trend_up = e20[-1] > e50[-1]
    trend_down = e20[-1] < e50[-1]
    macd_up = hist > 0
    macd_down = hist < 0

    if trend_up and macd_up and 50 <= rsi <= 70:
        result["decision"] = "BUY"
        result["entry"] = round(price, 5)
        result["stop"] = round(price - 1.5 * atr, 5)
        risk = price - result["stop"]
        result["tp1"] = round(price + 1.5 * risk, 5)
        result["tp2"] = round(price + 3.0 * risk, 5)
        result["rr"] = round((result["tp1"] - price) / risk, 2) if risk > 0 else None
        result["reason"] = (
            f"EMA20({e20[-1]:.5f}) > EMA50({e50[-1]:.5f}); "
            f"MACD hist positive ({hist:.5f}); RSI {rsi:.1f} in 50-70."
        )
    elif trend_down and macd_down and 30 <= rsi <= 50:
        result["decision"] = "SELL"
        result["entry"] = round(price, 5)
        result["stop"] = round(price + 1.5 * atr, 5)
        risk = result["stop"] - price
        result["tp1"] = round(price - 1.5 * risk, 5)
        result["tp2"] = round(price - 3.0 * risk, 5)
        result["rr"] = round((price - result["tp1"]) / risk, 2) if risk > 0 else None
        result["reason"] = (
            f"EMA20({e20[-1]:.5f}) < EMA50({e50[-1]:.5f}); "
            f"MACD hist negative ({hist:.5f}); RSI {rsi:.1f} in 30-50."
        )
    else:
        result["reason"] = (
            f"Conditions not aligned. EMA trend={'up' if trend_up else 'down' if trend_down else 'flat'}; "
            f"MACD={'positive' if macd_up else 'negative' if macd_down else 'flat'}; RSI={rsi:.1f}."
        )
    return result
