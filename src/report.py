"""Visual HTML report (self-contained, charts embedded as base64 PNG)."""
import base64, html, io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COL = {"BULLISH": "#16a34a", "BEARISH": "#dc2626", "NEUTRAL": "#6b7280"}

def _img(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110, bbox_inches="tight"); plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}"/>'

def overview_chart(df):
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
    ax[0].barh(df["asset"], df["mentions"], color="#3b82f6"); ax[0].set_title("Social mentions"); ax[0].invert_yaxis()
    ax[1].barh(df["asset"], df["score"], color=[COL[d] for d in df["direction"]]); ax[1].axvline(0, color="k", lw=.6)
    ax[1].set_title("Sentiment score (70% social / 30% news)"); ax[1].invert_yaxis()
    return _img(fig)

def ticker_chart(r, bars, oos):
    fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=False, gridspec_kw={"height_ratios": [3, 1.3]})
    ax[0].plot(range(len(bars)), bars["close"].values, color="#111", lw=1.2, label="close")
    ax[0].axhline(r["support"], color="#16a34a", ls="--", lw=1, label=f"support {r['support']:.2f}")
    ax[0].axhline(r["resistance"], color="#dc2626", ls="--", lw=1, label=f"resistance {r['resistance']:.2f}")
    ax[0].scatter([len(bars)], [r["pred_price_n+1"]], color="#f59e0b", s=60, zorder=5, label=f"pred n+1 {r['pred_price_n+1']:.2f}")
    if len(oos):
        idx = [bars.index.get_loc(t) + 1 for t in oos["ts"] if t in bars.index]
        ax[0].scatter(idx, oos["pred_price"].values[:len(idx)], s=9, color="#8b5cf6", alpha=.7, label="OOS pred (next bar)")
    ax[0].set_title(f"{r['asset']} ({r['ticker']})  {r['direction']}"); ax[0].legend(fontsize=7, ncol=3)
    ax[1].bar(range(len(bars)), bars["sent_w"].values, color=["#16a34a" if v > 0 else "#dc2626" for v in bars["sent_w"]])
    ax[1].set_ylabel("sentiment"); ax[1].set_xlabel("hourly bar")
    return _img(fig)

def render(path, results, demo, args):
    css = """body{font-family:system-ui;margin:24px;max-width:1100px}table{border-collapse:collapse;width:100%;font-size:13px}
    td,th{border:1px solid #ddd;padding:5px 7px;text-align:right}th{background:#f3f4f6}td:nth-child(-n+3){text-align:left}
    .b{padding:2px 8px;border-radius:9px;color:#fff;font-weight:600}.warn{background:#fef3c7;border:1px solid #f59e0b;padding:10px;border-radius:6px}
    .card{border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin:14px 0}img{max-width:100%}h2{margin-top:40px}"""
    h = [f"<html><head><meta charset='utf-8'><title>Sentiment Report</title><style>{css}</style></head><body>",
         "<h1>Social + News Sentiment → n+1 Price Report</h1>"]
    if demo:
        h.append("<p class='warn'><b>DEMO MODE:</b> prices, posts and news are SYNTHETIC (offline run). Run with <code>--live</code> and API keys for real data.</p>")
    for ex, r in results.items():
        df, m, m0 = r["summary"], r["res"]["metrics"], r["res"]["metrics_price_only"]
        h.append(f"<h2>{ex}</h2><p>Sources: {', '.join(r['cfg']['sources'])} + Exa news. Ranked by mentions, then score.</p>")
        h.append(overview_chart(df))
        h.append("<table><tr><th>#</th><th>Ticker</th><th>Asset</th><th>Price</th><th>Mentions</th><th>Score</th><th>Direction</th>"
                 "<th>Crowd pos.</th><th>Support</th><th>Resist.</th><th>Pred n+1</th><th>Trade idea</th></tr>")
        for i, x in df.iterrows():
            t = x["trade_side"] if x["trade_side"] == "FLAT" else f"{x['trade_side']} @{x['trade_entry']:.2f} SL {x['trade_stop']:.2f} TP {x['trade_target']:.2f} (R:R {x.get('trade_rr')})"
            h.append(f"<tr><td>{i+1}</td><td>{x['ticker']}</td><td>{html.escape(x['asset'])}</td><td>{x['price']:.2f}</td><td>{x['mentions']}</td>"
                     f"<td>{x['score']:+.3f}</td><td><span class='b' style='background:{COL[x['direction']]}'>{x['direction']}</span></td>"
                     f"<td>{x['community_position']} ({x['longs']}L/{x['shorts']}S)</td><td>{x['support']:.2f}</td><td>{x['resistance']:.2f}</td>"
                     f"<td>{x['pred_price_n+1']:.2f} ({x['pred_ret_%']:+.2f}%)</td><td style='text-align:left'>{t}</td></tr>")
        h.append("</table>")
        if m:
            h.append(f"<div class='card'><b>Out-of-sample check (expanding walk-forward, {m['n_oos']} predictions)</b><table>"
                     "<tr><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE %</th><th>Dir. acc %</th><th>p-value (dir)</th><th>MAE vs naive</th></tr>"
                     f"<tr><td>Sentiment + price</td><td>{m['MAE']:.3f}</td><td>{m['RMSE']:.3f}</td><td>{m['MAPE_%']:.3f}</td><td>{m['dir_acc_%']:.1f}</td><td>{m['dir_p_value']:.3f}</td><td>{m['MAE_vs_naive_%']:+.2f}%</td></tr>"
                     f"<tr><td>Price only (ablation)</td><td>{m0.get('MAE',float('nan')):.3f}</td><td>{m0.get('RMSE',float('nan')):.3f}</td><td>{m0.get('MAPE_%',float('nan')):.3f}</td><td>{m0.get('dir_acc_%',float('nan')):.1f}</td><td>{m0.get('dir_p_value',float('nan')):.3f}</td><td>{m0.get('MAE_vs_naive_%',float('nan')):+.2f}%</td></tr>"
                     f"<tr><td>Naive (price[n])</td><td>{m['naive_MAE']:.3f}</td><td colspan=5></td></tr></table>"
                     "<small>Only ~10 days of social data: treat significance cautiously. Positive 'MAE vs naive' = beats random-walk baseline.</small></div>")
        for _, x in df.iterrows():
            tk = x["ticker"]
            o = r["res"]["oos"]; o = o[o["ticker"] == tk] if len(o) else o
            h.append(f"<div class='card'><h3>{html.escape(x['asset'])} ({tk})</h3>{ticker_chart(x, r['panel'][r['panel']['ticker']==tk].set_index('ts'), o)}")
            n = r["news"][r["news"]["ticker"] == tk].sort_values("ts", ascending=False).head(3) if len(r["news"]) else []
            if len(n):
                h.append("<b>Latest news (Exa)</b><ul>" + "".join(
                    f"<li><a href='{html.escape(a.url)}'>{html.escape(a.title[:110])}</a> <small>({a.sentiment:+.2f})</small></li>" for a in n.itertuples()) + "</ul>")
            h.append("</div>")
    h.append("</body></html>")
    open(path, "w", encoding="utf-8").write("\n".join(h))
