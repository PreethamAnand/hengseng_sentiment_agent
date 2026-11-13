"""Support / resistance: classic daily pivots + nearest swing high/low on hourly bars."""
import numpy as np
import pandas as pd

def _swings(x, k=3):
    hi, lo = [], []
    for i in range(k, len(x) - k):
        w = x[i - k:i + k + 1]
        if x[i] == w.max(): hi.append(x[i])
        if x[i] == w.min(): lo.append(x[i])
    return hi, lo

def support_resistance(bars: pd.DataFrame) -> dict:
    price = float(bars["close"].iloc[-1])
    d = bars.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    last = d.iloc[-2] if len(d) > 1 else d.iloc[-1]
    P = (last.high + last.low + last.close) / 3
    R1, S1 = 2 * P - last.low, 2 * P - last.high
    R2, S2 = P + (last.high - last.low), P - (last.high - last.low)
    sh, _ = _swings(bars["high"].to_numpy())
    _, sl = _swings(bars["low"].to_numpy())
    sup_c = [v for v in sl + [S1, S2] if v < price]
    res_c = [v for v in sh + [R1, R2] if v > price]
    support = max(sup_c) if sup_c else float(bars["low"].min())
    resistance = min(res_c) if res_c else float(bars["high"].max())
    return {"pivot": float(P), "S1": float(S1), "S2": float(S2), "R1": float(R1), "R2": float(R2),
            "support": float(support), "resistance": float(resistance)}
