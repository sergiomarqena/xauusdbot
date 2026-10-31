# NORDXAU.GPT

**Read-only, research-first market intelligence console.**

NORDXAU.GPT brings together XAU/USD candles (when a Twelve Data key is configured), public macroeconomic series, selected crypto spot snapshots, and official U.S. policy/economic RSS headlines.

## Current capabilities

- XAU/USD OHLC history and EMA 20 / EMA 50 / RSI 14 / ATR 14 measurements through Twelve Data.
- FRED macro observations: broad trade-weighted USD index (DTWEXBGS), 10-year nominal Treasury yield (DGS10), 10-year real Treasury yield (DFII10), and WTI crude (DCOILWTICO).
- Public Binance 24-hour spot ticker snapshots for BTC/USDT and ETH/USDT.
- Official Federal Reserve press-release and BLS latest-number RSS headlines.
- Cached source responses with source labels, timestamps, and visible unavailable states.
- Responsive research terminal with green/red trend-glow chart, news-tone bubbles, and a BTC/XAU/OIL 1H/4H/1D/1W bias matrix.
- A buy-side / sell-side activity monitor: Binance taker quote volume for BTC and explicitly labelled candle-direction volume proxies for XAU and WTI.
- Read-only JSON API.

## Data setup

The dashboard intentionally does not invent a Gold price. To connect the Gold feed:

1. Open the nordxau-gpt service in Railway.
2. Add service variable TWELVE_DATA_API_KEY with your own Twelve Data key.
3. Keep DATA_PROVIDER=twelvedata (the application default), then redeploy/restart the service if Railway does not redeploy automatically.

Local setup: copy .env.example to .env, set the key, then run the backend as described below.

~~~powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
~~~

Dashboard: http://127.0.0.1:8000  
API schema: http://127.0.0.1:8000/docs

To inspect the rest of the terminal without a Gold key, the macro, crypto and official RSS panels can still load independently. To deliberately inspect the deterministic illustrative candle feed locally, set DATA_PROVIDER=demo; it is always labelled DEMO DATA.

## API routes

- GET /health
- GET /api/v1/market/status
- GET /api/v1/market/candles?interval=1h&limit=200
- GET /api/v1/research/overview?interval=1h&limit=200
- GET /api/v1/terminal/snapshot?interval=1h&limit=200

## Data source notes

- Twelve Data time series: https://twelvedata.com/docs
- FRED series pages: https://fred.stlouisfed.org/
- Binance public market-data-only API: https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md
- Federal Reserve RSS: https://www.federalreserve.gov/feeds/feeds.htm
- BLS RSS: https://www.bls.gov/feed/

FRED series are not tick data and update on their own schedules. DTWEXBGS is a broad trade-weighted USD index, not the ICE U.S. Dollar Index (DXY). Binance prices represent the crypto spot market, not XAU/USD or a broker CFD quote.

## Scope and safeguards

This is a read-only educational/research dashboard. It does not make buy/sell calls, provide position sizing or guaranteed probabilities, connect to a broker account, or place orders. Technical measurements and macro observations are context, not trading instructions. No real-money execution feature is included.

Before interpreting any display, check its source, observation timestamp, availability, and market venue. Headline sentiment currently uses a transparent keyword tagger, not an AI analyst. Multi-timeframe bias is a descriptive EMA/RSI alignment, not a probability. BTC flow uses Binance taker-side quote volumes; Gold and WTI flow displays use candle-volume direction proxies only where source volume exists. These values are not net exchange deposits or institutional capital flows. Historical testing, paper-only simulation, and the AI research analyst are future milestones, not current capabilities.

## Development

Run tests:

~~~powershell
cd backend
python -m pip install -r requirements.txt
pytest
~~~

See docs/architecture.md, docs/data-contracts.md, docs/validation-policy.md, and docs/roadmap.md.
