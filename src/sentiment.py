"""Multilingual (EN / 繁中-粵語 / 한국어) finance lexicon sentiment + stated-position detection.
Swap `score_text` for a transformer model if you want; the rest of the pipeline only needs a float in [-1, 1]."""
import re
import numpy as np
import pandas as pd

BULL = ["bull", "buy", "long", "moon", "breakout", "rally", "upgrade", "beat", "surge", "strong", "undervalued",
        "睇好", "看好", "買入", "上車", "大升", "起飛", "反彈", "牛", "升", "抽水", "利好",
        "매수", "상승", "급등", "호재", "가즈아", "강세", "존버", "대박", "불타기", "반등"]
BEAR = ["bear", "sell", "crash", "dump", "downgrade", "miss", "plunge", "weak", "overvalued",
        "睇淡", "看淡", "賣出", "下車", "大跌", "暴跌", "見頂", "熊", "跌", "沽", "利淡",
        "매도", "하락", "급락", "악재", "손절", "폭락", "약세", "물림", "공매도"]
LONG = ["long", "買入", "买入", "上車", "全倉", "매수", "물타기", "불타기"]
SHORT = ["short", "沽空", "做空", "下車", "매도", "공매도", "손절"]

def _count(text, terms):
    n = 0
    for t in terms:
        n += len(re.findall(rf"\b{re.escape(t)}\b", text)) if t.isascii() else text.count(t)
    return n

def score_text(text: str) -> float:
    t = str(text).lower()
    p, n = _count(t, BULL), _count(t, BEAR)
    return (p - n) / (p + n + 1)

def stated_position(text: str) -> int:
    t = str(text).lower()
    l, s = _count(t, LONG), _count(t, SHORT)
    return 1 if l > s else -1 if s > l else 0

def annotate_posts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["sentiment"] = df["text"].map(score_text)
    df["position"] = df["text"].map(stated_position)
    df["weight"] = (1 + np.log1p(df["likes"]) + np.log1p(df["reposts"])
                    + 0.5 * np.log1p(df["views"]) + 0.5 * np.log1p(df["followers"]))
    return df

def annotate_news(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["sentiment"] = (df["title"].fillna("") + " " + df["text"].fillna("")).map(score_text)
    return df

def direction(score: float, thr: float = 0.08) -> str:
    return "BULLISH" if score > thr else "BEARISH" if score < -thr else "NEUTRAL"
