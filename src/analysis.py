"""Per-ticker summary: price, sentiment, direction, positions, S/R, prediction, trade idea; ranking."""
import numpy as np
import pandas as pd
from .levels import support_resistance
from .sentiment import direction

def summarise(exchange, cfg, bars, posts, news, res, hours=48):
    rows = []
    now = max(b.index.max() for b in bars.values()) + pd.Timedelta("1h")
    for a in cfg["assets"]:
        tk = a["ticker"]; b = bars[tk]
        p = posts[posts["ticker"] == tk]
        rp = p[p["ts"] > now - pd.Timedelta(hours=hours)]
        rp = rp if len(rp) else p
        soc = float((rp["sentiment"] * rp["weight"]).sum() / rp["weight"].sum()) if len(rp) else 0.0
        n = news[news["ticker"] == tk] if len(news) else news
        nws = float(n["sentiment"].mean()) if len(n) else 0.0
        score = 0.7 * soc + 0.3 * nws if len(n) else soc
        lv = support_resistance(b)
        nx = res["next"].loc[tk]
        price, pred = float(b["close"].iloc[-1]), float(nx["pred_price"])
        d = direction(score)
        longs, shorts = int((rp["position"] > 0).sum()), int((rp["position"] < 0).sum())
        community = "LONG" if longs > shorts else "SHORT" if shorts > longs else "NONE"
        if d == "BULLISH" and pred > price:
            trade = {"side": "LONG", "entry": price, "stop": lv["support"], "target": lv["resistance"]}
        elif d == "BEARISH" and pred < price:
            trade = {"side": "SHORT", "entry": price, "stop": lv["resistance"], "target": lv["support"]}
        else:
            trade = {"side": "FLAT", "entry": None, "stop": None, "target": None}
        if trade["side"] != "FLAT":
            risk = abs(price - trade["stop"]); rew = abs(trade["target"] - price)
            trade["rr"] = round(rew / risk, 2) if risk > 0 else None
        rows.append({"exchange": exchange, "ticker": tk, "asset": a["name"], "price": price,
                     "mentions": int(len(p)), "mentions_by_source": p.groupby("source").size().to_dict(),
                     "social_sent": round(soc, 3), "news_sent": round(nws, 3), "score": round(score, 3),
                     "direction": d, "community_position": community, "longs": longs, "shorts": shorts,
                     **{k: round(v, 4) for k, v in lv.items()},
                     "pred_price_n+1": pred, "pred_ret_%": float(nx["pred_ret"]), **{f"trade_{k}": v for k, v in trade.items()}})
    df = pd.DataFrame(rows)
    return df.sort_values(["mentions", "score"], ascending=False).reset_index(drop=True)
