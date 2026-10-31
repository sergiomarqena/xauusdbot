# Contributing

- Keep provider code in `backend/app/data/` and pure calculations in `backend/app/analytics/`.
- Every provider response must be validated and labelled with source metadata.
- Add tests for every new indicator, transformation, or API response contract.
- Never commit API keys, credentials, `.env` files, or account data.
- Do not add broker authentication, live order placement, or real-money execution functionality.
- Prefer small, reviewable changes with documented assumptions.
