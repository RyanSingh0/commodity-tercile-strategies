# Commodity Tercile Strategies

Code and results for *Volatility Sorting, an Untradeable Reversal and Rebalance-Date Luck: What Survives a
Declared Search Over Cross-Sectional Commodity Strategies* (Meena and Pinsky, manuscript for MDPI *Commodities*).

Plain-English dashboard of the results: [ryansingh0.github.io/backtest-reality-check](https://ryansingh0.github.io/backtest-reality-check/)

Every month, week or day, I rank the six to nine most liquid commodities by their past return, split them
into a best, middle and worst group and hold each group at equal weight. I ran every combination of

- 7 lookbacks (1, 5, 10, 21, 63, 126 and 252 sessions)
- 7 rebalance frequencies (daily, weekly, biweekly, monthly, quarterly, semiannual, annual)
- 8 universe splits (Top6 2-2-2, Top7 3-2-2 / 2-3-2 / 2-2-3, Top8 3-3-2 / 3-2-3 / 2-3-3, Top9 3-3-3)
- 4 portfolios (Top, Median, Worst, and long Top / short Worst)

That comes to 1,568 configurations (1,372 distinct portfolios), January 2001 to September 2026, on Bloomberg
Commodity Index total-return sub-indices rather than generic futures prices. The question is which of the
good-looking backtests would have survived a noise ceiling, formal multiple-testing corrections, a one-day
execution delay, a change of rebalance date and out-of-sample selection.

## Main results

| | |
|---|---|
| BCOMTR buy and hold, $100 over 2001–2026 | $206 (Sharpe 0.26, max drawdown −73%) |
| Best gross configuration (daily, buy yesterday's 2 worst of 7) | $5,117 before costs, $50 at 5 bp |
| Same reversal on Top 9, Sharpe at the signal close vs one day later | 0.67 vs 0.34 |
| Middle group beats 1/N of the same commodities | 67.9% of cells, mostly by holding natural gas less often |
| Momentum spread above its noise ceiling | 0 of 8 grids |
| Best net configuration (middle 2 of Top6, 21d lookback, annual) | $2,150 rebalanced in December, median $416 over the 12 possible months |
| Top 5 chosen on 2001–2013, run blind on 2014–2026 | best one $97, buy and hold $149 |
| Hansen SPA p / deflated Sharpe / PBO | ≈ 0.02 / 0.63 / 0.35 |

## Layout

```
commodity_research/   backtest engine, grid runner, noise ceiling, charts and Excel output
01_Commodity_Strategies_vs_BuyHold.ipynb   top 5 per frequency vs buy and hold, cost ladder, three checks
paper_analysis/       paper_numbers.py computes every number in the paper, gen_tex.py writes the LaTeX
paper/                manuscript (MDPI template), tables and figures
data_quality/         open-price screen on every OHLC series (exact binomial test)
tests/                engine checks: no look-ahead, slow pandas re-implementation, cost accounting
outputs/              charts, the colour-coded cost ladder and the full configuration summary
cache/null.pkl        noise-ceiling simulations (200 reps per grid, about 50 minutes to rebuild)
```

## Reproducing

```
pip install -r requirements.txt
python -m pytest -q tests
python paper_analysis/paper_numbers.py     # numbers.json, csv files, paper/figs
python paper_analysis/gen_tex.py           # paper/numbers.tex and paper/tab_*.tex
python data_quality/open_price_screen.py
```

Then open the notebook and run all cells. The paper builds with `pdflatex main && bibtex main && pdflatex main && pdflatex main` inside `paper/`.

## Data

The price data came from a Bloomberg terminal at Boston University (September 2026) and is licensed, so it
is not in this repository. The code expects it at `data/Commodities_TR_Futures.xlsx` with three sheets:
*Total Return Indices* (BCOM single-commodity TR sub-indices), *Continuous Futures* (generic first contracts:
PX_OPEN, PX_HIGH, PX_LOW, PX_LAST, FUT_AGGTE_VOL, FUT_AGGTE_OPEN_INT) and *Benchmark & Risk-Free Rates*
(BCOMTR, US0003M, SPX). The tickers are listed in `commodity_research/universe.py`. The risk-free rate is the
FRED 3-month T-bill series (DTB3), included in `data/`.

The open-price screen also reads the dollar index and currency futures from the companion repository
[dxy-fx-strategies](https://github.com/RyanSingh0/dxy-fx-strategies) if it is cloned next to this one.

## Citation

Meena, A. and Pinsky, E. (2026). Volatility Sorting, an Untradeable Reversal and Rebalance-Date Luck: What
Survives a Declared Search Over Cross-Sectional Commodity Strategies. Manuscript.
