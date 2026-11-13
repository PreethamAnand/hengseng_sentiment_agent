"""Pooled (per-exchange) Ridge model predicting next-bar return -> price at n+1.
Validation: expanding-window walk-forward by TIME (train on past timestamps only), compared with
(a) naive 'price[n+1] = price[n]' and (b) a price-only ablation (no sentiment)."""
from math import comb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .features import FEATURES, PRICE_ONLY

def _mk():
    return make_pipeline(StandardScaler(), Ridge(alpha=10.0))

def walk_forward(panel, feats, min_frac=0.6, folds=5):
    lab = panel.dropna(subset=["target"]).copy()
    ts = np.array(sorted(lab["ts"].unique()))
    start = int(len(ts) * min_frac)
    edges = np.linspace(start, len(ts), folds + 1).astype(int)
    preds = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a: continue
        tr = lab[lab["ts"] < ts[a]]
        te = lab[(lab["ts"] >= ts[a]) & (lab["ts"] < (ts[b] if b < len(ts) else ts[-1] + pd.Timedelta("1h")))]
        if len(tr) < 30 or te.empty: continue
        m = _mk().fit(tr[feats], tr["target"])
        t = te.copy(); t["pred_ret"] = m.predict(te[feats]); preds.append(t)
    if not preds: return pd.DataFrame()
    o = pd.concat(preds)
    o["pred_price"] = o["close"] * (1 + o["pred_ret"] / 100)
    return o

def _binom_p(k, n):  # one-sided P(X>=k | p=0.5)
    return float(sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n) if n else 1.0

def metrics(o):
    if o.empty: return {}
    err = o["pred_price"] - o["next_close"]; nerr = o["close"] - o["next_close"]
    hit = int(((o["pred_ret"] > 0) == (o["target"] > 0)).sum()); n = len(o)
    return {"n_oos": n, "MAE": float(err.abs().mean()), "RMSE": float(np.sqrt((err ** 2).mean())),
            "MAPE_%": float((err.abs() / o["next_close"]).mean() * 100),
            "naive_MAE": float(nerr.abs().mean()),
            "MAE_vs_naive_%": float((1 - err.abs().mean() / nerr.abs().mean()) * 100),
            "dir_acc_%": hit / n * 100, "dir_p_value": _binom_p(hit, n)}

def run(panel):
    full = walk_forward(panel, FEATURES)
    ablate = walk_forward(panel, PRICE_ONLY)
    res = {"oos": full, "metrics": metrics(full), "metrics_price_only": metrics(ablate)}
    lab = panel.dropna(subset=["target"])
    m = _mk().fit(lab[FEATURES], lab["target"])
    last = panel.sort_values("ts").groupby("ticker").tail(1).copy()
    last["pred_ret"] = m.predict(last[FEATURES])
    last["pred_price"] = last["close"] * (1 + last["pred_ret"] / 100)
    res["next"] = last.set_index("ticker")
    res["coef"] = dict(zip(FEATURES, m[-1].coef_.round(4)))
    return res
