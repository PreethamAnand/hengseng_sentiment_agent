"""Synthetic data generator so the whole pipeline runs offline (--demo). NOT real market data."""
import zlib
import numpy as np
import pandas as pd

ZH_B = ["睇好", "買入", "反彈", "大升", "上車"]; ZH_S = ["睇淡", "賣出", "大跌", "下車", "見頂"]
KO_B = ["매수", "급등", "호재", "가즈아", "강세"]; KO_S = ["매도", "급락", "악재", "손절", "폭락"]
EN_B = ["bull", "buy", "breakout", "rally"]; EN_S = ["bear", "sell", "dump", "crash"]

def generate(exchange, cfg, days=10, seed=7):
    rng = np.random.default_rng(seed + zlib.crc32(exchange.encode()) % 1000)
    zh = exchange == "HKEX"
    B, S = (ZH_B if zh else KO_B), (ZH_S if zh else KO_S)
    end = pd.Timestamp.now(tz="UTC").normalize()
    bdays = pd.bdate_range((end - pd.Timedelta(days=days + 4)).tz_localize(None),
                           (end - pd.Timedelta(days=1)).tz_localize(None), tz="UTC")[-days:]
    starts = [d + pd.Timedelta(hours=h) for d in bdays for h in cfg["bar_hours_utc"]]
    bars, posts, news = {}, [], []
    for a in cfg["assets"]:
        n = len(starts)
        s = np.zeros(n)
        for i in range(1, n): s[i] = np.clip(0.6 * s[i - 1] + rng.normal(0, 0.55), -1, 1)
        ret = np.r_[0, 0.0025 * s[:-1] + rng.normal(0, 0.004, n - 1)]
        close = rng.uniform(40, 400) * np.exp(np.cumsum(ret))
        opn = np.r_[close[0], close[:-1]]
        hi = np.maximum(opn, close) * (1 + np.abs(rng.normal(0, .002, n)))
        lo = np.minimum(opn, close) * (1 - np.abs(rng.normal(0, .002, n)))
        vol = rng.integers(100_000, 5_000_000, n) * (1 + np.abs(s))
        bars[a["ticker"]] = pd.DataFrame({"open": opn, "high": hi, "low": lo, "close": close, "volume": vol},
                                          index=pd.DatetimeIndex(starts, name="ts").astype("datetime64[ns, UTC]"))
        pop = rng.uniform(0.6, 1.6)
        for i, st in enumerate(starts):
            prev_end = starts[i - 1] + pd.Timedelta(hours=1) if i else st
            end_t = st + pd.Timedelta(hours=1)
            for src, lam in zip(cfg["sources"], [10, 6]):
                for _ in range(rng.poisson(lam * pop)):
                    pb = 0.5 + 0.35 * s[i]
                    w = rng.choice(B if rng.random() < pb else S)
                    ts = prev_end + (end_t - prev_end) * rng.random()
                    posts.append({"ts": ts, "exchange": exchange, "source": src, "ticker": a["ticker"],
                                  "author": f"user{rng.integers(1, 400)}", "text": f"{a['name']} {w} {a['cashtag']}",
                                  "likes": float(rng.lognormal(1, 1.2)), "reposts": float(rng.poisson(1)),
                                  "views": float(rng.lognormal(5, 1)), "followers": float(rng.lognormal(5, 1.5))})
        for j, d in enumerate(bdays):
            i = j * len(cfg["bar_hours_utc"])
            m = s[i:i + len(cfg["bar_hours_utc"])].mean()
            for _ in range(int(rng.integers(1, 3))):
                w = rng.choice(EN_B if m + rng.normal(0, .3) > 0 else EN_S)
                news.append({"ts": d + pd.Timedelta(hours=int(rng.integers(0, 6))), "exchange": exchange,
                             "ticker": a["ticker"], "title": f"[demo] {a['name']} {w} outlook for analysts",
                             "url": "https://example.com/demo", "text": f"{w} sentiment on {a['name']}"})
    p = pd.DataFrame(posts)
    p["ts"] = pd.to_datetime(p["ts"], utc=True)
    nw = pd.DataFrame(news)
    nw["ts"] = pd.to_datetime(nw["ts"], utc=True)
    return bars, p, nw
