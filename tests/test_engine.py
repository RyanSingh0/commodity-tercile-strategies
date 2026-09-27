"""Checks on the backtest engine. Run from the repo root:  python -m pytest -q tests

They need the Bloomberg workbook in data/, same as everything else.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commodity_research import engine as e
from commodity_research.config import START_POS, RAW_XLSX
from commodity_research.universe import UNIVERSES

pytestmark = pytest.mark.skipif(not RAW_XLSX.exists(), reason='Bloomberg workbook not in data/')


@pytest.fixture(scope='module')
def top6():
    from commodity_research.loader import Data
    d = Data()
    P, names, _ = d.prices(UNIVERSES['Top6'][0])
    return P, names, d.dates


def test_daily_equal_weight_is_cross_sectional_mean(top6):
    # rebalanced every day, 1/N is just the average of the daily returns
    P, _, dates = top6
    R = P[1:] / P[:-1] - 1
    r, _, _ = e.equal_weight(P, dates, 'Daily', START_POS)
    assert np.allclose(r[START_POS + 1:], R[START_POS:].mean(1))


def test_ranking_order_and_signal(top6):
    # every Top member's trailing return >= every Median member's >= every Worst member's
    P, _, dates = top6
    for L in [1, 21, 252]:
        _, reb, order, sig = e.run_config(P, dates, L, 'Monthly', (2, 2, 2), START_POS)
        s = np.take_along_axis(sig, order, 1)
        assert (s[:, 1] >= s[:, 2]).all() and (s[:, 3] >= s[:, 4]).all()
        assert np.allclose(sig, P[reb] / P[reb - L] - 1)


def test_no_look_ahead(top6):
    # I shock all prices after a cut date. Nothing before the cut is allowed to move.
    P, _, dates = top6
    cut = 4000
    P2 = P.copy()
    P2[cut:] *= np.linspace(1, 3, len(P) - cut)[:, None] * np.array([1, .5, 2, 1, .7, 1.3])
    for f in e.FREQS:
        a, *_ = e.run_config(P, dates, 21, f, (2, 2, 2), START_POS)
        b, *_ = e.run_config(P2, dates, 21, f, (2, 2, 2), START_POS)
        for g in a:
            x, y = a[g][0][:cut], b[g][0][:cut]
            assert np.allclose(x[~np.isnan(x)], y[~np.isnan(y)]), (f, g)


def test_matches_slow_pandas_version(top6):
    # the same Top / monthly / 21d strategy written the slow, obvious way with pandas
    P, names, dates = top6
    px = pd.DataFrame(P, index=dates, columns=names)
    start = dates[START_POS]
    month_ends = [g.index[-1] for _, g in px.loc[start:].groupby(px.loc[start:].index.to_period('M'))]
    reb_dates = sorted({x for x in month_ends if start < x < dates[-1]} | {start})
    out = pd.Series(np.nan, index=dates)
    for i, s in enumerate(reb_dates):
        past = px.loc[s] / px.shift(21).loc[s] - 1
        top = past.sort_values(ascending=False, kind='stable').index[:2]
        end = reb_dates[i + 1] if i + 1 < len(reb_dates) else dates[-1]
        seg = px.loc[s:end, top]
        val = (seg / seg.iloc[0]).mean(axis=1)
        out.loc[val.index[1:]] = (val / val.shift(1) - 1).iloc[1:].values
    res, *_ = e.run_config(P, dates, 21, 'Monthly', (2, 2, 2), START_POS)
    mine = pd.Series(res['Top'][0], index=dates)
    assert (mine - out).abs().max() < 1e-12


def test_costs_charged_on_turnover(top6):
    # net = gross minus bp x turnover on the first day of each holding period
    P, _, dates = top6
    g, *_ = e.run_config(P, dates, 21, 'Monthly', (2, 2, 2), START_POS, cost_bp=0)
    n, *_ = e.run_config(P, dates, 21, 'Monthly', (2, 2, 2), START_POS, cost_bp=5)
    assert np.isclose(np.nansum(g['Top'][0] - n['Top'][0]), g['Top'][1].sum() * 5e-4)


def test_long_short_pays_both_legs(top6):
    # this one caught a real bug: the short leg's costs were being added back
    P, _, dates = top6
    g, *_ = e.run_config(P, dates, 21, 'Monthly', (2, 2, 2), START_POS, cost_bp=0)
    n, *_ = e.run_config(P, dates, 21, 'Monthly', (2, 2, 2), START_POS, cost_bp=5)
    lost = np.nansum(g['Top-minus-Worst'][0] - n['Top-minus-Worst'][0])
    assert np.isclose(lost, (g['Top'][1].sum() + g['Worst'][1].sum()) * 5e-4)


def test_rebalance_counts(top6):
    # rough number of rebalances per year for each frequency
    _, _, dates = top6
    years = (len(dates) - START_POS) / 252
    expected = {'Daily': 252, 'Weekly': 52, 'Biweekly': 26, 'Monthly': 12, 'Quarterly': 4, 'Semiannual': 2, 'Annual': 1}
    for f, per_year in expected.items():
        rb = e.rebalance_positions(dates, f, START_POS)
        assert abs(len(rb) / years - per_year) / per_year < 0.05, f
