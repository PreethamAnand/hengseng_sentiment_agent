"""CLI: python run_pipeline.py --demo | --live [--days 10] [--exchanges HKEX KRX]"""
import argparse, json, logging
import pandas as pd
from dotenv import load_dotenv
from src.config import EXCHANGES, OUT
from src import sentiment, features, model, analysis, report

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true", help="synthetic offline data")
    g.add_argument("--live", action="store_true", help="Apify + Exa + yfinance")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--exchanges", nargs="+", default=list(EXCHANGES))
    a = ap.parse_args()
    load_dotenv(); OUT.mkdir(exist_ok=True)
    results, all_sum, all_posts, all_news, metrics = {}, [], [], [], {}
    for ex in a.exchanges:
        cfg = EXCHANGES[ex]
        if a.demo:
            from src.demo import generate
            bars, posts, news = generate(ex, cfg, a.days)
        else:
            from src import social, news as nw, prices
            bars = prices.fetch_bars(cfg, a.days)
            posts = social.fetch_exchange(ex, cfg, a.days)
            news = nw.fetch_news(ex, cfg, a.days)
        posts, news = sentiment.annotate_posts(posts), sentiment.annotate_news(news)
        panel = features.build_panel(bars, posts, news)
        res = model.run(panel)
        summ = analysis.summarise(ex, cfg, bars, posts, news, res)
        results[ex] = {"cfg": cfg, "summary": summ, "res": res, "panel": panel, "news": news}
        all_sum.append(summ); all_posts.append(posts); all_news.append(news)
        metrics[ex] = {"sentiment_model": res["metrics"], "price_only": res["metrics_price_only"], "coef": {k: float(v) for k, v in res["coef"].items()}}
        logging.info("%s done: %s", ex, res["metrics"])
    pd.concat(all_sum).to_csv(OUT / "predictions.csv", index=False)
    pd.concat(all_posts).to_csv(OUT / "posts.csv", index=False)
    pd.concat(all_news).to_csv(OUT / "news.csv", index=False)
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    report.render(OUT / "report.html", results, a.demo, a)
    logging.info("Report: %s", OUT / "report.html")

if __name__ == "__main__":
    main()
