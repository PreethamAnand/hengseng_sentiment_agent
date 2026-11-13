"""Apify-based social scraping + normalisation to a common schema (UTC timestamps)."""
import logging, os
from datetime import datetime, timedelta, timezone
import pandas as pd
from .config import load_sources

log = logging.getLogger("social")
COLS = ["ts", "exchange", "source", "ticker", "author", "text", "likes", "reposts", "views", "followers"]

# cheerio-scraper pageFunction for Naver Finance discussion room (종목토론실)
NAVER_PAGE_FUNCTION = r"""
async function pageFunction(context) {
  const { $, request } = context;
  const out = [];
  try {
    const bodyText = typeof context.body === 'string' ? context.body : (context.body ? context.body.toString('utf8') : $('body').text());
    const d = JSON.parse(bodyText);
    if (d && Array.isArray(d.posts)) {
      for (const p of d.posts) {
        out.push({
          ticker: request.userData.ticker,
          date: p.writtenAt,
          title: (p.title || '') + ' ' + (p.contentSwReplaced || ''),
          author: (p.writer && p.writer.nickname) || '',
          views: p.commentCount || 0,
          likes: p.recommendCount || 0,
          dislikes: p.notRecommendCount || 0
        });
      }
      return out;
    }
  } catch (e) {}
  $('table.type2 tr').each((i, tr) => {
    const td = $(tr).find('td');
    if (td.length < 6) return;
    const date = $(td[0]).text().trim();
    if (!/\d{4}\.\d{2}\.\d{2}/.test(date)) return;
    const num = (el) => parseInt($(el).text().replace(/[^0-9]/g, '')) || 0;
    out.push({
      ticker: request.userData.ticker, date,
      title: $(td[1]).find('a').attr('title') || $(td[1]).text().trim(),
      author: $(td[2]).text().trim(),
      views: num(td[3]), likes: num(td[4]), dislikes: num(td[5])
    });
  });
  return out;
}
"""

def _fill(obj, ctx):
    if isinstance(obj, dict):
        return {k: _fill(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fill(v, ctx) for v in obj]
    if isinstance(obj, str):
        if obj == "{queries}": return ctx["queries"]
        if obj == "{max_items}": return ctx["max_items"]
        return obj.replace("{since}", ctx["since"]).replace("{ticker}", ctx["ticker"])
    return obj

def _to_utc(v, tz):
    if v is None or v == "": return pd.NaT
    if isinstance(v, (int, float)):
        return pd.to_datetime(v, unit="ms" if v > 1e11 else "s", utc=True)
    t = pd.to_datetime(v, errors="coerce")
    if pd.isna(t): return pd.NaT
    return t.tz_localize(tz).tz_convert("UTC") if t.tzinfo is None else t.tz_convert("UTC")

def _pick(d, keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""): return d[k]
    return default

def _num(x):
    try: return float(str(x).replace(",", ""))
    except Exception: return 0.0

def normalise_generic(items, exchange, source, ticker, tz):
    rows = []
    for d in items:
        a = d.get("author") if isinstance(d.get("author"), dict) else {}
        rows.append({
            "ts": _to_utc(_pick(d, ["createdAt", "created_at", "date", "timestamp", "time", "publishedAt", "postedAt"]), tz),
            "exchange": exchange, "source": source, "ticker": ticker,
            "author": str(_pick(d, ["username", "user", "userName", "author"], a.get("name", ""))),
            "text": str(_pick(d, ["text", "content", "message", "title", "body"], "")),
            "likes": _num(_pick(d, ["likes", "likeCount", "like_count", "favorites", "upvotes"], 0)),
            "reposts": _num(_pick(d, ["reposts", "retweets", "shares", "forwards", "forwardCount"], 0)),
            "views": _num(_pick(d, ["views", "viewCount", "view_count", "impressions"], 0)),
            "followers": _num(_pick(d, ["followers", "followerCount", "authorFollowers"], a.get("followers", 0))),
        })
    return rows

def normalise_naver(items, exchange, source, ticker, tz):
    # Naver boards expose views + 공감(likes); no reposts / follower counts -> 0
    return [{"ts": _to_utc(d["date"], tz), "exchange": exchange, "source": source, "ticker": ticker,
             "author": d.get("author", ""), "text": d.get("title", ""), "likes": float(d.get("likes", 0)),
             "reposts": 0.0, "views": float(d.get("views", 0)), "followers": 0.0} for d in items]

def run_actor(client, actor_id, run_input, timeout=600):
    kwargs = {"run_input": run_input}
    try:
        from datetime import timedelta
        run = client.actor(actor_id).call(**kwargs, run_timeout=timedelta(seconds=timeout))
    except TypeError:
        run = client.actor(actor_id).call(**kwargs)
    if not run:
        return []
    ds_id = getattr(run, "default_dataset_id", None) or (run.get("defaultDatasetId") if isinstance(run, dict) else None)
    if not ds_id:
        return []
    return list(client.dataset(ds_id).iterate_items())

def fetch_exchange(exchange, cfg, days=10, max_items=500):
    from apify_client import ApifyClient
    token = os.getenv("APIFY_TOKEN")
    if not token: raise RuntimeError("APIFY_TOKEN missing")
    client = ApifyClient(token)
    srcs = load_sources()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows, used = [], []
    for s in cfg["sources"]:
        sc = srcs[s]
        if not sc.get("actor_id"):
            log.warning("No actor_id for source '%s' (set APIFY_ACTOR_%s) - skipping", s, s.upper())
            continue
        ok = False
        for a in cfg["assets"]:
            code = a["ticker"].split(".")[0]
            try:
                if sc["kind"] == "naver_board":
                    urls = [{"url": f"https://stock.naver.com/api/community/discussion/posts?itemCode={code}&pageSize=50",
                             "userData": {"ticker": a["ticker"]}}]
                    inp = {"startUrls": urls, "pageFunction": NAVER_PAGE_FUNCTION,
                           "proxyConfiguration": {"useApifyProxy": True}, "maxConcurrency": 5}
                    items = run_actor(client, sc["actor_id"], inp)
                    rows += normalise_naver(items, exchange, s, a["ticker"], sc["tz"])
                else:
                    q = [a["cashtag"], code, a["name"]] + a["keywords"]
                    ctx = {"queries": q, "max_items": max_items, "since": since, "ticker": a["ticker"]}
                    items = run_actor(client, sc["actor_id"], _fill(sc["input_template"], ctx))
                    rows += normalise_generic(items, exchange, s, a["ticker"], sc["tz"])
                ok = True
            except Exception as e:
                log.error("%s/%s failed: %s", s, a["ticker"], e)
        if ok: used.append(s)
    if len(used) < 2:
        raise RuntimeError(f"{exchange}: need >=2 working social sources, got {used}. Configure actor IDs.")
    df = pd.DataFrame(rows, columns=COLS).dropna(subset=["ts"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df[df["ts"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)]
    return df.drop_duplicates(subset=["source", "ticker", "ts", "text"]).reset_index(drop=True)
