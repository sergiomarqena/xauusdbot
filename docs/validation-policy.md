# Research validation and safety policy

NORDXAU.GPT is a research and software project, not a promise of financial returns.

## Evidence standards

- Preserve raw observations separately from indicators and model outputs.
- Record every transformation and strategy/configuration version.
- Use chronological splits and walk-forward evaluation.
- Prevent look-ahead leakage: a decision timestamp may use only information available by that timestamp.
- Include realistic spread, commission, financing/swap, slippage, gaps, and execution delay in simulations.
- Report sample size, drawdown, volatility, exposure, turnover, and uncertainty—not just win rate or headline return.
- Compare results against simple baselines and a no-position baseline.
- Keep a final untouched evaluation window.
- Treat all probabilities as uncalibrated until calibration is independently measured.

## Project boundary

This scaffold includes read-only market data and descriptive analytics. It deliberately excludes broker login, account access, order placement, and real-money execution. Planned strategy experiments are restricted to historical replay and paper simulation.

## AI layer (future)

AI may summarize events, identify conflicting evidence, or explain a research run. It must not invent missing observations, claim certainty, or change numeric calculations. Each generated statement should point to supporting source records and include an uncertainty label.
