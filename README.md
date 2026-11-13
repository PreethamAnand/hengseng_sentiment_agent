# HengSeng & KRX Sentiment → $n+1$ Price Prediction Agent

An institutional-grade quantitative sentiment pipeline that fuses **multilingual social media intelligence** (Apify) and **authoritative financial news** (Exa.ai) with **market microstructure price bars** (yfinance) to forecast next-bar ($n+1$) asset returns across the **Hong Kong Stock Exchange (HKEX)** and **Korea Exchange (KRX)**.

---

## 🚀 Quick Start (One-Click for Reviewers)

### Windows (Recommended)
Simply **double-click** the file:
```cmd
run_project.bat
```
**What this does automatically:**
1. Detects Python 3.10+ installation.
2. Automatically verifies and installs dependencies from `requirements.txt`.
3. Runs the test suite (`pytest -q tests`).
4. Executes the pipeline (defaults to **Demo Mode** with synthetic data in 10s if no key is pressed, requiring **zero API keys**).
5. Automatically opens the interactive visual dashboard ([`outputs/report.html`](file:///outputs/report.html)) in your default browser.

---

## 💻 Manual Execution (CLI)

If you prefer executing from the command line:

### 1. Environment Setup
```bash
# Clone or navigate to the directory
cd sentiment_agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Offline Demo Mode (Instant Evaluation — No API Keys Needed)
Demo mode generates synthetic multi-asset data with realistic market regimes, runs the feature pipeline, trains the pooled Ridge model with walk-forward validation, and produces the complete visual dashboard:
```bash
python run_pipeline.py --demo
```
*Outputs are saved to `outputs/` and can be viewed by opening `outputs/report.html`.*

### 3. Run Live Mode (Real-Time Ingestion)
To run against live APIs (requires `.env` configured with Apify & Exa keys):
```bash
# Run KRX live (South Korea - Naver + Telegram + Exa News)
python run_pipeline.py --live --exchanges KRX --days 5

# Run Full live pipeline (HKEX + KRX)
python run_pipeline.py --live --days 10
```

### 4. Run Unit Test Suite
```bash
pytest -v tests
```

---

## 📊 Assets & Target Exchanges

| Exchange | Tickers Tracked | Assets | Primary Social Sources | News Source |
|---|---|---|---|---|
| **HKEX** (Hong Kong) | `0700.HK`, `9988.HK`, `3690.HK`, `1810.HK`, `0005.HK` | Tencent, Alibaba, Meituan, Xiaomi, HSBC | LIHKG Forum + Futu / Moomoo Community | Exa.ai News API |
| **KRX** (South Korea) | `005930.KS`, `000660.KS`, `035420.KS`, `035720.KS`, `005380.KS` | Samsung Electronics, SK Hynix, Naver, Kakao, Hyundai Motor | Naver Finance Discussion + Telegram Keyword Search | Exa.ai News API |

---

## 🧠 Methodology & Architecture

### 1. Multi-Source Ingestion & Strict UTC Alignment
* **Social Media (Apify)**: Ingests investor sentiment from regional discussion hubs (Naver Finance board, Telegram public keyword feeds, LIHKG, and Futu).
* **News Intelligence (Exa.ai)**: Ingests 10-day lookback financial news articles and extracts neural semantic snippets.
* **Hourly OHLCV Bars (yfinance)**: Hourly price bars fetched for each constituent asset.
* **Temporal Alignment (No Lookahead Bias)**:
  * All localized timestamps (Asia/Seoul KST `UTC+9`, Asia/Hong_Kong HKT `UTC+8`) are converted to strict UTC.
  * A post or news item timestamped at $t$ is mapped to the *first hourly bar whose close $\ge t$*.
  * Off-market and overnight posts roll forward into the opening market bar.

### 2. Multilingual Sentiment & Crowdsourced Stance
* **Lexicon Support**: Built-in specialized finance lexicons covering English, Traditional Chinese (繁體中文), and Korean (한국어).
* **Engagement Weighting**: Sentiment scores are scaled by post authority:
  $$\text{Weight} = 1.0 + \ln(1 + \text{views}) + 0.5 \cdot \text{likes} + 1.0 \cdot \text{reposts} + 0.001 \cdot \text{followers}$$
* **Crowd Positioning**: Analyzes stated bullish vs. bearish crowd intentions (e.g., long, short, call, put mentions) to gauge crowd consensus.

### 3. Quantitative Model & Walk-Forward Backtesting
* **Model**: Pooled Ridge Regression ($L_2$ regularization) predicting next-bar asset returns:
  $$r_{i, t+1} = \frac{P_{i, t+1} - P_{i, t}}{P_{i, t}}$$
* **Engineered Features**:
  * Social sentiment mean, engagement-weighted score, and post count.
  * Sentiment delta (acceleration/deceleration) and source agreement ratio.
  * Exa news sentiment score.
  * Historical lagged price returns ($t-1$, $t-2$) and volume $z$-scores.
* **Validation**: Expanding-window **walk-forward out-of-sample (OOS) validation** across time. No future data is ever leaked into training windows.
* **Benchmark Baselines**: Evaluated against:
  1. *Naive Random Walk* ($P_{t+1} = P_t$)
  2. *Price-Only Model* (Ridge regression trained strictly on lagged price/volume features without sentiment).
* **Metrics**: MAE, RMSE, MAPE, Directional Accuracy (%), and binomial test $p$-values.

### 4. Actionable Trade Intelligence
For each ticker, the pipeline computes:
* **Support / Resistance**: Classical Daily Pivot Points (PP, R1, S1, R2, S2) combined with rolling 20-period swing highs/lows.
* **Trade Signal**: Directional stance (Long/Short/Neutral), suggested entry price, target exit, protective stop-loss, and Risk/Reward (R:R) ratio.

---

## 📁 Output Artifacts (`outputs/`)

After every execution, the agent outputs complete artifacts to the `outputs/` directory:

| File | Description |
|---|---|
| [`outputs/report.html`](file:///outputs/report.html) | **Self-contained interactive visual report** featuring dark-themed modern UI, summary metric scorecards, walk-forward OOS backtest comparison charts, and per-ticker trade cards with pivot levels and signals. |
| [`outputs/predictions.csv`](file:///outputs/predictions.csv) | Full tabular dump of all ticker predictions: current price, predicted $n+1$ price, expected return, sentiment score, crowd position, and suggested stop/target trades. |
| [`outputs/metrics.json`](file:///outputs/metrics.json) | Comprehensive performance JSON containing out-of-sample MAE, RMSE, MAPE, directional accuracy, naive comparison, and learned Ridge coefficients. |
| [`outputs/posts.csv`](file:///outputs/posts.csv) | Normalized tabular export of all scraped social posts with raw text, engagement metrics, and assigned sentiment scores. |
| [`outputs/news.csv`](file:///outputs/news.csv) | Tabular export of all analyzed Exa news headlines and text snippets. |

---

## ⚙️ Environment Configuration (`.env`)

For **Demo Mode**, no configuration is needed.

For **Live Mode**, copy `.env.example` to `.env` and configure your credentials:

```env
# Apify API Token (from https://console.apify.com/account/integrations)
APIFY_TOKEN=your_apify_token

# Exa.ai API Key (from https://dashboard.exa.ai/api-keys)
EXA_API_KEY=your_exa_key

# Apify Actor Slugs
APIFY_ACTOR_NAVER=apify/cheerio-scraper
APIFY_ACTOR_TELEGRAM=lofomachines/telegram-keyword-search-scraper
APIFY_ACTOR_LIHKG=claude_code_reviewer/lihkg-scraper
APIFY_ACTOR_FUTU=apify/cheerio-scraper
```

---

## 📂 Project Structure

```text
sentiment_agent/
│
├── run_project.bat         # One-click Windows runner for evaluation
├── run_pipeline.py         # Main CLI pipeline entry point (--demo | --live)
├── requirements.txt        # Production dependencies
├── README.md               # Complete project documentation & guide
├── .env.example            # Environment variables template
│
├── config/
│   └── sources.json        # Apify scrapers configuration & input templates
│
├── src/
│   ├── config.py           # Exchange metadata, asset dictionaries, trading hours
│   ├── prices.py           # yfinance hourly OHLCV bar fetcher & timezone converter
│   ├── social.py           # Apify social scrapers & universal normalizer
│   ├── news.py             # Exa.ai financial news client & text extractor
│   ├── sentiment.py        # Multilingual lexicon annotator & engagement scaler
│   ├── features.py         # Feature engineering & strict UTC temporal alignment
│   ├── model.py            # Pooled Ridge regression & walk-forward validator
│   ├── analysis.py         # Pivot points, support/resistance, & trade setups
│   ├── report.py           # HTML report generation with embedded visualizations
│   └── demo.py             # Synthetic offline data generator for demo mode
│
├── tests/
│   └── test_pipeline.py    # Unit tests for alignment, sentiment, and modeling
│
└── outputs/                # Generated artifacts (HTML report, CSVs, JSON metrics)
    ├── report.html
    ├── predictions.csv
    ├── metrics.json
    ├── posts.csv
    └── news.csv
```

---

## 🧪 Testing

The codebase includes automated unit tests covering lexicon matching, UTC temporal alignment (ensuring zero lookahead bias), and model validation:

```bash
pytest -v tests
```
*All tests pass with 100% success.*
