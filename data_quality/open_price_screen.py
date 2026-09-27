"""Open-price screen from our Risks paper, run on every OHLC series I have.

If the recorded open is an honest print from the session, it should sit on the day's low about as
often as on the day's high. Counting the two gives an exact binomial test that needs no second data
source. I also report where the open sits in the day's range on average (0.5 if unbiased), how often
it falls outside [low, high] (impossible for a real print) and how often it equals yesterday's close.

Run from the repo root:  python data_quality/open_price_screen.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import math


def binom_two_sided(k, n):
    """Exact two-sided binomial p-value at p = 0.5, same as scipy.stats.binomtest.
    Written out with lgamma so this script runs without scipy."""
    lp = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2) for i in range(n + 1)]
    pk = lp[k]
    return min(1.0, sum(math.exp(v) for v in lp if v <= pk + 1e-7))

HERE = Path(__file__).resolve().parent
BASE = HERE.parent                                   # repo root
DXY_PROJECT = BASE.parent                            # folder that also holds the dxy-fx-strategies repo
sys.path.insert(0, str(BASE))
from commodity_research.loader import load_raw
from commodity_research.universe import NAME, SECTOR


def screen(O, H, L, C, name, source):
    d = pd.DataFrame({'O': O, 'H': H, 'L': L, 'C': C}).dropna()
    prevC = d.C.shift(1)
    ok = d.H > d.L                                    # drops holidays and forward-filled rows
    x = d[ok]
    lo = int(np.isclose(x.O, x.L, rtol=0, atol=1e-9).sum())
    hi = int(np.isclose(x.O, x.H, rtol=0, atol=1e-9).sum())
    n = lo + hi
    p = binom_two_sided(lo, n) if n else np.nan
    return {'Series': name, 'Source': source, 'Sessions (H>L)': int(ok.sum()),
            'Open = low': lo, 'Open = high': hi, 'Low/high ratio': lo / hi if hi else np.nan,
            'Binomial p': p, 'Mean open position (0.5 = unbiased)': float(((x.O - x.L) / (x.H - x.L)).mean()),
            'Open outside range %': 100 * float(((x.O < x.L - 1e-9) | (x.O > x.H + 1e-9)).mean()),
            'Open = previous close %': 100 * float(np.isclose(x.O, prevC[ok], rtol=0, atol=1e-9).mean())}


def run():
    rows = []
    fut = load_raw()['fut']
    tick = sorted({c.split('|')[0] for c in fut})
    for t in tick:
        k = t.replace(' Comdty', '')
        g = lambda f: fut[f'{t}|{f}']
        r = screen(g('PX_OPEN'), g('PX_HIGH'), g('PX_LOW'), g('PX_LAST'), f'{NAME.get(k, k)} ({t})', 'Bloomberg generic 1st')
        r['Sector'] = SECTOR.get(k, '')
        rows.append(r)
    # dollar index and currency futures from the Risks paper, if that repo sits next to this one
    bc = DXY_PROJECT / 'dxy-fx-strategies' / 'data' / 'futures'
    for f, nm in [('DX', 'U.S. Dollar Index futures'), ('E6', 'Euro futures'), ('B6', 'Sterling futures'),
                  ('D6', 'Canadian dollar futures'), ('J6', 'Yen futures'), ('S6', 'Swiss franc futures')]:
        p = bc / f'{f}.csv'
        if p.exists():
            d = pd.read_csv(p, skipfooter=1, engine='python')
            rows.append(screen(pd.to_numeric(d.Open, errors='coerce'), pd.to_numeric(d.High, errors='coerce'),
                               pd.to_numeric(d.Low, errors='coerce'), pd.to_numeric(d.Latest, errors='coerce'),
                               nm + f' ({f})', 'Barchart, exchange sourced') | {'Sector': 'FX'})
    v = DXY_PROJECT / 'dxy-fx-strategies' / 'data' / 'vendor' / 'fx_ohlc_2010_2025.csv'
    if v.exists():
        d = pd.read_csv(v)
        rows.append(screen(d.DXY_Open, d.DXY_High, d.DXY_Low, d.DXY_Close, 'U.S. Dollar Index (free provider)', 'Free provider (paper control)') | {'Sector': 'FX'})
    out = pd.DataFrame(rows)
    # fail on a Bonferroni-significant low/high imbalance, or opens outside the range on more than 1% of days
    out['Flag'] = np.where((out['Binomial p'] < 0.01 / len(out)) | (out['Open outside range %'] > 1), 'FAIL', 'pass')
    return out


if __name__ == '__main__':
    res = run()
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 100)
    print(res.round(4).to_string(index=False))
    (BASE / 'outputs').mkdir(exist_ok=True)
    res.to_csv(BASE / 'outputs' / 'open_price_screen.csv', index=False)
