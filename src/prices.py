"""Hourly price bars (UTC) via yfinance."""
import pandas as pd

def fetch_bars(cfg, days=10):
    import yfinance as yf
    out = {}
    for a in cfg["assets"]:
        df = yf.download(a["ticker"], period="1mo", interval="60m", progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
        df.index = pd.to_datetime(df.index, utc=True).astype("datetime64[ns, UTC]")
        df.index.name = "ts"
        out[a["ticker"]] = df[df.index >= df.index.max() - pd.Timedelta(days=days)]
    return out
