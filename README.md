# NORDXAU.GPT

**A research-first XAU/USD market intelligence workspace.**

NORDXAU.GPT is designed to collect market data, calculate transparent indicators, label market regimes, preserve research runs, and evaluate ideas with reproducible historical tests and paper simulation.

> **Current stage:** foundation scaffold. Without a configured data provider the app serves clearly labelled deterministic demo data. Demo data is not a market quote.

## What this project is — and is not

- A modular market-data and research platform, beginning with XAU/USD.
- Built to keep raw data, derived features, research hypotheses, and evaluation results separate.
- Designed for historical replay and paper simulation before any conclusions are drawn.
- Not a broker, exchange, order router, investment adviser, or autonomous trading system.
- No live order-placement code, broker credentials, or real-money execution path is included.

## Repository layout

```text
backend/   FastAPI service, data adapters, indicators, tests
frontend/  Lightweight browser dashboard served by FastAPI
docs/      Architecture, data contracts, validation policy, roadmap
```

## Run locally (Windows PowerShell)

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. API docs: `http://127.0.0.1:8000/docs`.

To enable the Twelve Data adapter, put your own key in the root `.env` file:

```env
DATA_PROVIDER=twelvedata
TWELVE_DATA_API_KEY=your_key_here
DEFAULT_SYMBOL=XAU/USD
DEFAULT_INTERVAL=1h
```

Never commit `.env`, API keys, account credentials, or personal data. Twelve Data endpoint documentation: https://twelvedata.com/docs

## Tests

```powershell
cd backend
python -m pip install -r requirements.txt
pytest
```

## Current API

- `GET /health` — service health
- `GET /api/v1/market/status` — selected provider and whether it is demo/external-provider data
- `GET /api/v1/market/candles` — OHLC candles for the configured symbol
- `GET /api/v1/research/overview` — latest candle and transparent indicator summary

## Build principles

1. Label every datum with provider, symbol, interval, timestamp, and demo/external-provider status.
2. Never silently substitute demo data when a configured provider fails.
3. Version feature definitions and research hypotheses.
4. Test with time-ordered data; avoid look-ahead and survivorship bias.
5. Include spread, fees, slippage, missing data, and session effects in later evaluations.
6. Evaluate on unseen periods; do not tune a system on its final test set.
7. Keep any future simulation separate from broker connectivity.

See `docs/` before extending the system.
