"""Noise ceiling for the grid search.

I rerun each 7 x 7 (lookback x frequency) grid with the ranking replaced by a random shuffle at
every rebalance. Returns, calendars, group sizes and holding rules stay the same, so the only thing
removed is the information in past returns. The ceiling is the 95th percentile of the best gross
Sharpe the whole grid reaches. 200 reps took me about 50 minutes on 2 cores.
"""
import numpy as np
from . import engine as e
from .config import START_POS
from .universe import UNIVERSES

GROUPS = ['Top', 'Median', 'Worst', 'Top-minus-Worst']


def null_best(data, reps=200, seed=20260926, progress=True):
    out = {}
    for uname, (keys, splits) in UNIVERSES.items():
        P, _, _ = data.prices(keys)
        for sz in splits:
            sp = '-'.join(map(str, sz))
            rng = np.random.default_rng(seed)      # same seed per grid so any run can be repeated
            best = {g: [] for g in GROUPS}
            for _ in range(reps):
                sh = {g: [] for g in GROUPS}
                for L in e.LOOKBACKS.values():
                    for f in e.FREQS:
                        res, *_ = e.run_config(P, data.dates, L, f, sz, START_POS, 0.0, rng=rng)
                        for g in GROUPS:
                            x = res[g][0][START_POS + 1:]
                            sh[g].append(x.mean() / x.std(ddof=1) * np.sqrt(252))
                for g in GROUPS:
                    best[g].append(max(sh[g]))
            out[(uname, sp)] = {g: np.array(v) for g, v in best.items()}
            if progress:
                print(uname, sp, 'done', flush=True)
    return out
