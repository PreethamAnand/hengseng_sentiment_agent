import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import sentiment, social
from src.config import EXCHANGES
from src.demo import generate
from src import features, model

def test_sentiment_multilingual():
    assert sentiment.score_text("삼성전자 급등 매수") > 0
    assert sentiment.score_text("騰訊 大跌 下車") < 0
    assert sentiment.score_text("going long, bull run") > 0

def test_naver_tz_to_utc():
    r = social.normalise_naver([{"date": "2026.11.05 09:00", "title": "x"}], "KRX", "naver", "005930.KS", "Asia/Seoul")
    assert str(r[0]["ts"]) == "2026-11-05 00:00:00+00:00"

def test_no_lookahead_and_oos():
    cfg = EXCHANGES["HKEX"]
    bars, p, n = generate("HKEX", cfg, 10)
    p, n = sentiment.annotate_posts(p), sentiment.annotate_news(n)
    panel = features.build_panel(bars, p, n)
    assert panel["target"].isna().sum() == len(cfg["assets"])  # last bar only
    o = model.walk_forward(panel, features.FEATURES)
    assert len(o) > 20 and o["ts"].min() > panel["ts"].min()
