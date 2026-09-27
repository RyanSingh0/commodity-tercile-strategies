"""Backtest engine for the tercile (best / middle / worst) strategies.

How a configuration works, and nothing here looks ahead:
- At each rebalance close s I rank the commodities by their trailing L-session total return,
  P(s)/P(s-L) - 1, using prices up to and including s.
- The ranking is cut into three groups: Top (best past returns), Median and Worst.
- Each group is bought equal weight at the close of s and then left alone, so the weights drift
  with prices until the next rebalance.
- The first return a new portfolio earns is s to s+1.
- Costs are cost_bp per unit of one-way turnover, taken on the first day of each holding period.
  The first entry counts as turnover of 1.
"""
import numpy as np
import pandas as pd

TD = 252

# label -> pandas period alias I use to find the last session of each period.
# 'BW' and 'S' are my own codes (pandas has no biweekly or half-year period), handled below.
FREQS = {
    'Daily': None, 'Weekly': 'W-FRI', 'Biweekly': 'BW', 'Monthly': 'M',
    'Quarterly': 'Q', 'Semiannual': 'S', 'Annual': 'Y'}
LOOKBACKS = {'Daily (1d)': 1, 'Weekly (5d)': 5, 'Biweekly (10d)': 10, 'Monthly (21d)': 21,
             'Quarterly (63d)': 63, 'Semiannual (126d)': 126, 'Annual (252d)': 252}


def rebalance_positions(dates: pd.DatetimeIndex, freq: str, start_pos: int) -> np.ndarray:
    """Row positions of the rebalance days. The first one is always start_pos, so every
    configuration is evaluated over exactly the same window."""
    n = len(dates)
    if freq == 'Daily':
        pos = np.arange(start_pos, n - 1)
    else:
        if freq == 'Biweekly':
            key = dates.to_period('W-FRI')
        elif freq == 'Semiannual':
            key = pd.Index(dates.year * 10 + (dates.month > 6).astype(int))
        else:
            key = dates.to_period(FREQS[freq])
        key = pd.Series(np.asarray(key), index=np.arange(n))
        last = key.groupby(key).tail(1).index.values          # last trading day of each period
        if freq == 'Biweekly':
            last = last[last > start_pos][1::2]                # every second Friday
        last = last[(last > start_pos) & (last < n - 1)]
        pos = np.concatenate([[start_pos], last])
    return np.unique(pos)


def hold_returns(P: np.ndarray, reb: np.ndarray, W: np.ndarray):
    """Daily returns of a portfolio that is rebalanced at reb and drifts in between.

    P is (T, N) index levels, reb the sorted rebalance rows, W the (K, N) target weights.
    Returns r (T,), NaN before the first holding day, and the one-way turnover at each rebalance.
    """
    T, N = P.shape
    r = np.full(T, np.nan)
    turn = np.zeros(len(reb))
    prev_w_drift = None
    ends = np.append(reb[1:], T - 1)
    for k, (s, e) in enumerate(zip(reb, ends)):
        w = W[k]
        rel = P[s:e + 1] / P[s]                    # growth of each asset since s (first row is 1)
        V = rel @ w                                # value of the portfolio over the holding period
        r[s + 1:e + 1] = V[1:] / V[:-1] - 1.0
        turn[k] = np.abs(w - prev_w_drift).sum() if prev_w_drift is not None else np.abs(w).sum()
        wd = w * rel[-1]                           # weights have drifted by the next rebalance
        prev_w_drift = wd / wd.sum() if wd.sum() != 0 else wd
    return r, turn


def group_weights(signal_rows: np.ndarray, sizes, tiebreak=None):
    """Turn the (K, N) signal into Top / Median / Worst weight matrices.

    Highest signal ranks first. On ties the stable sort keeps column order, so results are repeatable.
    """
    K, N = signal_rows.shape
    order = np.argsort(-signal_rows, axis=1, kind='stable')
    out = []
    lo = 0
    for sz in sizes:
        Wg = np.zeros((K, N))
        idx = order[:, lo:lo + sz]
        np.put_along_axis(Wg, idx, 1.0 / sz, axis=1)
        out.append(Wg)
        lo += sz
    return out, order


def run_config(P, dates, lookback, freq, sizes, start_pos, cost_bp=0.0, rng=None):
    """Run one configuration. Passing rng swaps the ranking for a random shuffle at every
    rebalance, which is the no-information null I use for the noise ceiling."""
    reb = rebalance_positions(dates, freq, start_pos)
    if rng is None:
        sig = P[reb] / P[reb - lookback] - 1.0
    else:
        sig = rng.random((len(reb), P.shape[1]))
    Ws, order = group_weights(sig, sizes)
    res, gross, costs = {}, {}, {}
    for name, Wg in zip(['Top', 'Median', 'Worst'], Ws):
        r, t = hold_returns(P, reb, Wg)
        cost = np.zeros_like(r)
        cost[reb + 1] = t * cost_bp / 1e4
        res[name] = (r - cost, t)
        gross[name], costs[name] = r, cost
    # Long Top, short Worst. Both legs pay costs. I had this as net Top minus net Worst at first,
    # which quietly gives the short leg's costs back, so I build it from the gross legs.
    rl = gross['Top'] - gross['Worst'] - costs['Top'] - costs['Worst']
    res['Top-minus-Worst'] = (rl, res['Top'][1] + res['Worst'][1])
    return res, reb, order, sig


def equal_weight(P, dates, freq, start_pos, cost_bp=0.0):
    reb = rebalance_positions(dates, freq, start_pos)
    N = P.shape[1]
    r, t = hold_returns(P, reb, np.full((len(reb), N), 1.0 / N))
    cost = np.zeros_like(r)
    cost[reb + 1] = t * cost_bp / 1e4
    return r - cost, t, reb


# ---------------------------------
# METRICS
# ---------------------------------
def newey_west_t(x, lags=10):
    # returns the Newey-West standard error of the mean (Bartlett weights), not the t itself
    x = x - x.mean()
    n = len(x)
    g0 = (x @ x) / n
    s = g0
    for l in range(1, lags + 1):
        g = (x[l:] @ x[:-l]) / n
        s += 2 * (1 - l / (lags + 1)) * g
    se = np.sqrt(s / n)
    return se


def metrics(r: pd.Series, rf: pd.Series, bench: pd.Series, turnover_per_year=np.nan,
            self_financing=False, split='2013-12-31'):
    from scipy import stats
    r = r.dropna()
    rf = rf.reindex(r.index).fillna(0.0)
    b = bench.reindex(r.index)
    ex = r if self_financing else r - rf
    n = len(r)
    yrs = n / TD
    eq = (1 + r).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1
    mdd = dd.min()
    trough = dd.idxmin()
    # longest stretch of sessions spent below an earlier peak
    under = (dd < 0).astype(int).values
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std(ddof=1) * np.sqrt(TD)
    sh0 = r.mean() / r.std(ddof=1) * np.sqrt(TD)
    shx = ex.mean() / ex.std(ddof=1) * np.sqrt(TD)
    dn = np.sqrt((np.minimum(ex, 0) ** 2).mean()) * np.sqrt(TD)
    sortino = ex.mean() * TD / dn if dn > 0 else np.nan
    se = newey_west_t(ex.values)
    t_nw = ex.mean() / se
    p_nw = 2 * (1 - stats.norm.cdf(abs(t_nw)))
    m = (1 + r).resample('ME').prod() - 1
    bx = b - rf
    beta = np.cov(ex, bx)[0, 1] / bx.var(ddof=1)
    alpha = (ex.mean() - beta * bx.mean()) * TD
    h1 = ex.loc[:split]; h2 = ex.loc[pd.Timestamp(split) + pd.Timedelta(days=1):]
    q = np.quantile(r, 0.05)
    return {
        'Start': r.index[0].date(), 'End': r.index[-1].date(), 'Sessions': n,
        'Final value of $100': 100 * eq.iloc[-1],
        'Total return': eq.iloc[-1] - 1,
        'CAGR': cagr,
        'Ann. mean return': r.mean() * TD,
        'Ann. volatility': vol,
        'Sharpe (rf=0)': sh0,
        'Sharpe (excess of T-bill)': shx,
        'Sortino (excess)': sortino,
        'Max drawdown': mdd,
        'Max DD trough date': trough.date(),
        'Longest drawdown (sessions)': longest,
        'Calmar (CAGR/|MaxDD|)': cagr / abs(mdd) if mdd < 0 else np.nan,
        'Newey-West t (excess mean)': t_nw,
        'p-value (NW, two-sided)': p_nw,
        'Skewness (daily)': stats.skew(r),
        'Excess kurtosis (daily)': stats.kurtosis(r),
        'Daily VaR 95%': q,
        'Daily CVaR 95%': r[r <= q].mean(),
        'Daily hit rate': (r > 0).mean(),
        '% positive months': (m > 0).mean(),
        'Best month': m.max(), 'Worst month': m.min(),
        'Beta vs BCOMTR': beta,
        'Correlation vs BCOMTR': np.corrcoef(ex, bx)[0, 1],
        'Ann. alpha vs BCOMTR': alpha,
        'Annual turnover (x)': turnover_per_year,
        'Sharpe 2001-2013': h1.mean() / h1.std(ddof=1) * np.sqrt(TD),
        'Sharpe 2014-2026': h2.mean() / h2.std(ddof=1) * np.sqrt(TD),
    }
