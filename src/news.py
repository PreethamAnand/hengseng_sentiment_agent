"""Exa.ai news ingestion."""
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import requests

COLS = ["ts", "exchange", "ticker", "title", "url", "text"]

def fetch_news(exchange, cfg, days=10, n=10):
    key = os.getenv("EXA_API_KEY")
    if not key: raise RuntimeError("EXA_API_KEY missing")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000Z")
    rows = []
    for a in cfg["assets"]:
        r = requests.post("https://api.exa.ai/search", timeout=60,
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={"query": f"{a['name']} {a['ticker'].split('.')[0]} stock news", "type": "auto",
                  "category": "news", "numResults": n, "startPublishedDate": since,
                  "contents": {"text": {"maxCharacters": 800}}})
        r.raise_for_status()
        for x in r.json().get("results", []):
            rows.append({"ts": pd.to_datetime(x.get("publishedDate"), utc=True, errors="coerce"),
                         "exchange": exchange, "ticker": a["ticker"], "title": x.get("title") or "",
                         "url": x.get("url", ""), "text": x.get("text") or ""})
    df = pd.DataFrame(rows, columns=COLS).dropna(subset=["ts"])
    return df.drop_duplicates(subset=["url"]).reset_index(drop=True)
