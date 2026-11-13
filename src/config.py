import json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"

def A(ticker, name, cashtag, kw):
    return {"ticker": ticker, "name": name, "cashtag": cashtag, "keywords": kw}

EXCHANGES = {
    "HKEX": {
        "tz": "Asia/Hong_Kong", "currency": "HKD",
        "sources": ["lihkg", "futu"],
        "bar_hours_utc": [1, 2, 3, 4, 5, 6, 7],
        "assets": [
            A("0700.HK", "Tencent", "$0700", ["騰訊", "Tencent", "00700"]),
            A("9988.HK", "Alibaba", "$9988", ["阿里", "Alibaba", "09988"]),
            A("3690.HK", "Meituan", "$3690", ["美團", "Meituan", "03690"]),
            A("1810.HK", "Xiaomi", "$1810", ["小米", "Xiaomi", "01810"]),
            A("0005.HK", "HSBC", "$0005", ["滙豐", "HSBC", "00005"]),
        ],
    },
    "KRX": {
        "tz": "Asia/Seoul", "currency": "KRW",
        "sources": ["naver", "telegram"],
        "bar_hours_utc": [0, 1, 2, 3, 4, 5, 6],
        "assets": [
            A("005930.KS", "Samsung Electronics", "$005930", ["삼성전자", "Samsung"]),
            A("000660.KS", "SK Hynix", "$000660", ["SK하이닉스", "하이닉스", "Hynix"]),
            A("035420.KS", "Naver", "$035420", ["네이버", "NAVER"]),
            A("035720.KS", "Kakao", "$035720", ["카카오", "Kakao"]),
            A("005380.KS", "Hyundai Motor", "$005380", ["현대차", "Hyundai Motor"]),
        ],
    },
}

def load_sources():
    cfg = json.loads((ROOT / "config" / "sources.json").read_text())
    for k, v in cfg.items():
        env = os.getenv(f"APIFY_ACTOR_{k.upper()}")
        if env:
            v["actor_id"] = env
    return cfg
