"""Align social posts / news (UTC) with hourly price bars and build the modelling panel.
Posts are assigned to the FIRST bar whose END is >= post time, i.e. features for bar t only use
information available at the close of bar t (no look-ahead). Target = return of bar t+1."""
import numpy as np
import pandas as pd

FEATURES = ["sent_mean", "sent_w", "n_posts_log", "pos_ratio", "neg_ratio", "src_agree",
            "news_sent", "sent_chg", "ret_1", "ret_2", "vol_z"]
PRICE_ONLY = ["ret_1", "ret_2", "vol_z"]

def _ns(s):
    return pd.to_datetime(s, utc=True).astype("datetime64[ns, UTC]")

def build_panel(bars: dict, posts: pd.DataFrame, news: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for tk, b in bars.items():
        b = b.copy().sort_index()
        b["bar_end"] = _ns(b.index + pd.Timedelta(hours=1))
        b["ret"] = b["close"].pct_change()
        b["ret_1"] = b["ret"] * 100
        b["ret_2"] = b["ret_1"].shift(1)
        b["vol_z"] = (b["volume"] - b["volume"].rolling(20, min_periods=3).mean()) / (
            b["volume"].rolling(20, min_periods=3).std() + 1e-9)
        p = posts[posts["ticker"] == tk].sort_values("ts").copy() if not posts.empty else posts
        agg = pd.DataFrame(index=b["bar_end"])
        if len(p):
            p["ts"] = _ns(p["ts"])
            m = pd.merge_asof(p, b[["bar_end"]].reset_index(drop=True), left_on="ts", right_on="bar_end",
                              direction="forward", tolerance=pd.Timedelta("4D")).dropna(subset=["bar_end"])
            m["ws"] = m["sentiment"] * m["weight"]
            m["pos"] = (m["sentiment"] > 0.08).astype(float)
            m["neg"] = (m["sentiment"] < -0.08).astype(float)
            g = m.groupby("bar_end")
            agg = pd.DataFrame({"sent_mean": g["sentiment"].mean(), "n_posts": g.size(),
                                "sent_w": g["ws"].sum() / g["weight"].sum(),
                                "pos_ratio": g["pos"].mean(), "neg_ratio": g["neg"].mean()})
            ps = m.groupby(["bar_end", "source"])["sentiment"].mean().unstack()
            if ps.shape[1] >= 2:
                agg["src_agree"] = 1 - (ps.iloc[:, 0] - ps.iloc[:, 1]).abs().reindex(agg.index)
        f = b.reset_index().merge(agg.reset_index(), on="bar_end", how="left")
        for c in ["sent_mean", "sent_w", "n_posts", "pos_ratio", "neg_ratio", "src_agree"]:
            if c not in f: f[c] = 0.0
            f[c] = f[c].fillna(0.0)
        f["n_posts_log"] = np.log1p(f["n_posts"])
        f["sent_chg"] = f["sent_w"].diff().fillna(0.0)
        # news sentiment: mean of articles published within the 24h before bar close
        n = news[news["ticker"] == tk] if not news.empty else news
        ns = []
        for e in f["bar_end"]:
            w = n[(n["ts"] <= e) & (n["ts"] > e - pd.Timedelta("24h"))] if len(n) else n
            ns.append(w["sentiment"].mean() if len(w) else 0.0)
        f["news_sent"] = ns
        f["ticker"] = tk
        f["next_close"] = f["close"].shift(-1)
        f["target"] = (f["next_close"] / f["close"] - 1) * 100
        frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    out[FEATURES] = out[FEATURES].fillna(0.0)
    return out
