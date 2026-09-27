"""Runs the whole grid and summarises every configuration at any cost level.

Costs are linear in bp (cost_bp/1e4 times turnover, on the first day of each holding period),
so I run each configuration once gross, keep a "return lost per 1 bp" series next to it, and get
the net result at any cost exactly without rerunning the backtest.
"""
import hashlib
import itertools
import numpy as np
import pandas as pd
from . import engine as e
from .config import START_POS
from .universe import UNIVERSES

FREQS = list(e.FREQS)
LOOKBACKS = e.LOOKBACKS
GROUPS = ['Top', 'Median', 'Worst', 'Top-minus-Worst']
TD = 252


def config_series(data, universe, split, lookback_label, freq, group):
    """Gross daily returns and the per-bp cost series for one configuration, evaluation window only."""
    keys, _ = UNIVERSES[universe]
    P, names, _ = data.prices(keys)
    sz = tuple(int(s) for s in split.split('-'))
    L = LOOKBACKS[lookback_label]
    res, reb, order, sig = e.run_config(P, data.dates, L, freq, sz, START_POS, 0.0)
    g = res[group][0]
    turn = res[group][1]
    c = np.zeros_like(g)
    c[reb + 1] = turn / 1e4                       # return lost for every 1 bp of cost
    sl = slice(START_POS + 1, None)
    return pd.Series(g[sl], index=data.dates[sl]), pd.Series(c[sl], index=data.dates[sl])


def buy_and_hold(data):
    r = data.BCOM_R.iloc[START_POS + 1:]
    return r


def equal_weight(data, universe, freq):
    keys, _ = UNIVERSES[universe]
    P, _, _ = data.prices(keys)
    r, t, reb = e.equal_weight(P, data.dates, freq, START_POS, 0.0)
    c = np.zeros_like(r); c[reb + 1] = t / 1e4
    sl = slice(START_POS + 1, None)
    return pd.Series(r[sl], index=data.dates[sl]), pd.Series(c[sl], index=data.dates[sl])


def final_value(g, c, bp):
    return 100.0 * np.exp(np.log1p(g - c * bp).sum())


def max_drawdown(g, c, bp):
    eq = np.cumprod(1 + g - c * bp)
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def sharpe(g, c, bp):
    x = g - c * bp
    return float(x.mean() / x.std(ddof=1) * np.sqrt(TD))


def breakeven_bp(g, c, target_final, hi=100000.0):
    """Cost in bp per unit turnover at which the final value of $100 falls to target_final.

    0 if it never beats the target, inf if it never trades. Found by doubling then bisection.
    """
    if final_value(g, c, 0) <= target_final:
        return 0.0
    if c.sum() == 0:
        return np.inf
    lo, h = 0.0, 1.0
    while final_value(g, c, h) > target_final and h < hi:
        h *= 2
    for _ in range(60):
        mid = 0.5 * (lo + h)
        if final_value(g, c, mid) > target_final:
            lo = mid
        else:
            h = mid
    return 0.5 * (lo + h)


def run_grid(data, bps=(0, 1, 2, 5), progress=True):
    """One row per configuration: final value, Sharpe and max drawdown at each bp, turnover,
    break-even cost against BCOMTR buy and hold, and a fingerprint of the return series."""
    bh = buy_and_hold(data).values
    bh_final = 100 * np.prod(1 + bh)
    rows = []
    for uname, (keys, splits) in UNIVERSES.items():
        P, names, _ = data.prices(keys)
        for sz in splits:
            sp = '-'.join(map(str, sz))
            for (lb, L), f in itertools.product(LOOKBACKS.items(), FREQS):
                res, reb, order, sig = e.run_config(P, data.dates, L, f, sz, START_POS, 0.0)
                for grp in GROUPS:
                    g = res[grp][0][START_POS + 1:]
                    c = np.zeros(len(res[grp][0])); c[reb + 1] = res[grp][1] / 1e4
                    c = c[START_POS + 1:]
                    rec = dict(Universe=uname, Split=sp, Lookback=lb, Frequency=f, Group=grp,
                               # some splits give the same portfolio (e.g. Worst 2 of 7 under 3-2-2 and 2-3-2),
                               # the hash of the returns lets me list those once
                               fingerprint=hashlib.md5(np.round(g, 12).tobytes()).hexdigest()[:12],
                               turnover_per_year=c.sum() * 1e4 / (len(g) / TD))
                    for bp in bps:
                        rec[f'Final ${bp}bp'] = final_value(g, c, bp)
                        rec[f'Sharpe {bp}bp'] = sharpe(g, c, bp)
                        rec[f'MaxDD {bp}bp'] = max_drawdown(g, c, bp)
                    rec['Breakeven bp vs B&H'] = breakeven_bp(g, c, bh_final)
                    rows.append(rec)
            if progress:
                print(f'{uname} {sp} done', flush=True)
    df = pd.DataFrame(rows)
    return df, bh_final


def label(row):
    # readable name for charts and tables, e.g. "Middle 2 of top 6 (2-2-2), 21d lookback"
    sz = row['Split'].split('-')
    n = int(row['Universe'][3:])
    if row['Group'] == 'Top':
        g = f"Best {sz[0]}"
    elif row['Group'] == 'Median':
        g = f"Middle {sz[1]}"
    elif row['Group'] == 'Worst':
        g = f"Worst {sz[2]}"
    else:
        g = f"Long best {sz[0]} / short worst {sz[2]}"
    lb = row['Lookback'].split('(')[1].rstrip(')')
    return f"{g} of top {n} ({row['Split']}), {lb} lookback"
