"""Computes every number, table input and figure in the commodities paper.

Run from the repo root:  python paper_analysis/paper_numbers.py   then   python paper_analysis/gen_tex.py
It uses cache/null.pkl for the noise ceiling and rebuilds it if it's missing (about 50 minutes).
Writes paper_analysis/numbers.json, a few csv files, and the figures into paper/figs/.
"""
import sys, json, itertools, pickle
from math import comb
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as st

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
from commodity_research.loader import Data
from commodity_research import engine as E, grid as G, noise
from commodity_research.config import START_POS, CACHE
from commodity_research.universe import UNIVERSES, TR, NAME, ORDER, MULT, SHORT

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9})
FIG = BASE / 'paper' / 'figs'; FIG.mkdir(exist_ok=True)
N = {}                                    # everything the paper quotes goes in here
TD = 252
FREQS = G.FREQS
LBS = list(E.LOOKBACKS)
GROUPS = G.GROUPS
S0 = START_POS


def sr(x):
    x = np.asarray(x); return float(x.mean() / x.std(ddof=1) * np.sqrt(TD))


def fv(x):
    return float(100 * np.prod(1 + np.asarray(x)))


def cagr(x):
    x = np.asarray(x); return float(np.prod(1 + x) ** (TD / len(x)) - 1)


def mdd(x):
    eq = np.cumprod(1 + np.asarray(x)); return float((eq / np.maximum.accumulate(eq) - 1).min())


d = Data()
dates = d.dates
ev = dates[S0 + 1:]
N['sessions_total_raw'] = int(len(d.raw['tr']))
N['holidays_dropped'] = int(d.joint_holidays.sum())
N['sessions_clean'] = int(len(dates))
N['eval_start'] = str(ev[0].date()); N['eval_end'] = str(ev[-1].date()); N['eval_sessions'] = int(len(ev))
N['eval_years'] = round(len(ev) / TD, 2)

# ---------------------------------
# 1) DATA: generic futures vs TR indices, asset table
# ---------------------------------
fut = d.raw['fut']
t0 = dates[S0]
for k in ['CL1', 'NG1', 'GC1']:
    gp = fut[f'{k} Comdty|PX_LAST']
    trs = d.PX[TR[k]]
    N[f'generic_vs_tr_{k}'] = {'generic_price_return': float(gp.iloc[-1] / gp.loc[t0] - 1),
                               'tr_return': float(trs.iloc[-1] / trs.loc[t0] - 1)}
N['cl1_2020_04_20'] = float(fut['CL1 Comdty|PX_LAST'].loc['2020-04-20'])
lib = d.raw['bench']['US0003M Index|PX_LAST']
N['libor_last_change'] = str(lib[lib.diff().ne(0)].index[-1].date())

R = d.PX.pct_change().iloc[S0 + 1:]
bh = d.BCOM_R.iloc[S0 + 1:].values
rf = d.RF.iloc[S0 + 1:].values
asset_rows = []
for k in ORDER:
    x = R[TR[k]].values
    asset_rows.append({'Commodity': NAME[k], 'Index': TR[k], 'CAGR': cagr(x), 'Vol': float(x.std() * np.sqrt(TD)),
                       'Sharpe': sr(x), 'MaxDD': mdd(x)})
asset_rows.append({'Commodity': 'BCOMTR (benchmark)', 'Index': 'BCOMTR', 'CAGR': cagr(bh), 'Vol': float(bh.std() * np.sqrt(TD)),
                   'Sharpe': sr(bh), 'MaxDD': mdd(bh)})
N['assets'] = asset_rows
N['bh'] = {'final': fv(bh), 'cagr': cagr(bh), 'sharpe': sr(bh), 'mdd': mdd(bh), 'excess_sharpe': sr(bh - rf)}

# liquidity ranking: notional volume over the full sample, notional open interest over the last 12 months
rows = []
for k, m in MULT.items():
    t = k + ' Comdty'
    px, v, oi = fut[t + '|PX_LAST'], fut[t + '|FUT_AGGTE_VOL'], fut[t + '|FUT_AGGTE_OPEN_INT']
    rows.append({'key': k, 'name': NAME[k], 'dv_full': float((px * v * m).mean() / 1e9),
                 'doi_12m': float((px * oi * m).loc['2025-09-18':].mean() / 1e9)})
liq = pd.DataFrame(rows).sort_values('dv_full', ascending=False).reset_index(drop=True)
liq['rank_dv'] = np.arange(1, len(liq) + 1)
liq['rank_oi'] = liq.doi_12m.rank(ascending=False).astype(int)
N['liquidity'] = liq.to_dict('records')
# weekly correlation of the refined products with crude, the reason I leave them out
wk = (1 + d.PX[['BCOMCLTR', 'BCOMCOT', 'BCOMHOTR', 'BCOMRBTR', 'BCOMGOT']].pct_change()).resample('W-FRI').prod() - 1
c = wk.corr()
N['refined_corr_with_crude'] = [float(c.loc['BCOMCLTR', x]) for x in ['BCOMHOTR', 'BCOMRBTR', 'BCOMGOT']] + \
                               [float(c.loc['BCOMCOT', x]) for x in ['BCOMHOTR', 'BCOMRBTR', 'BCOMGOT']]

# ---------------------------------
# 2) FULL GRID, all daily series kept in memory
# ---------------------------------
keys, Gm, Cm = [], [], []
for u, (ks, splits) in UNIVERSES.items():
    P, _, _ = d.prices(ks)
    for sz in splits:
        sp = '-'.join(map(str, sz))
        for lb, f in itertools.product(LBS, FREQS):
            res, reb, order, sig = E.run_config(P, dates, E.LOOKBACKS[lb], f, sz, S0, 0.0)
            for g in GROUPS:
                cc = np.zeros(len(dates)); cc[reb + 1] = res[g][1] / 1e4
                keys.append((u, sp, lb, f, g)); Gm.append(res[g][0][S0 + 1:]); Cm.append(cc[S0 + 1:])
Gm = np.array(Gm); Cm = np.array(Cm)
K, T = Gm.shape
idx = pd.MultiIndex.from_tuples(keys, names=['Universe', 'Split', 'Lookback', 'Frequency', 'Group'])
N['n_configs'] = int(K)
import hashlib
# identical portfolios from different splits, counted once for the distinct-trials numbers
fp = [hashlib.md5(np.round(Gm[i], 12).tobytes()).hexdigest() for i in range(K)]
N['n_distinct'] = int(len(set(fp)))
EW = {}
for u in UNIVERSES:
    P, _, _ = d.prices(UNIVERSES[u][0])
    for f in FREQS:
        r, t, reb = E.equal_weight(P, dates, f, S0, 0.0)
        cc = np.zeros(len(dates)); cc[reb + 1] = t / 1e4
        EW[(u, f)] = (r[S0 + 1:], cc[S0 + 1:])


def net(i, bp):
    return Gm[i] - Cm[i] * bp


tab = pd.DataFrame(index=idx)
for bp in [0, 1, 2, 5]:
    X = Gm - Cm * bp
    tab[f'sr{bp}'] = X.mean(1) / X.std(1, ddof=1) * np.sqrt(TD)
    tab[f'fv{bp}'] = 100 * np.exp(np.log1p(X).sum(1))
    tab[f'exsr{bp}'] = [sr(X[i] - (0 if keys[i][4] == 'Top-minus-Worst' else rf)) for i in range(K)]
tab['vol'] = Gm.std(1, ddof=1) * np.sqrt(TD)
tab['turn'] = Cm.sum(1) * 1e4 / (T / TD)
tab['mdd0'] = [mdd(Gm[i]) for i in range(K)]
tab['be_bh'] = [G.breakeven_bp(Gm[i], Cm[i], fv(bh)) for i in range(K)]
tab['ew_sr0'] = [sr(EW[(k[0], k[3])][0]) for k in keys]
tab.to_csv(HERE / 'all_configs.csv')

gs = tab.reset_index()
N['group_sharpe'] = {g: {'mean': float(gs[gs.Group == g].sr0.mean()), 'median': float(gs[gs.Group == g].sr0.median()),
                         'max': float(gs[gs.Group == g].sr0.max()), 'min': float(gs[gs.Group == g].sr0.min())} for g in GROUPS}
N['ew_sharpe_range'] = [float(min(sr(v[0]) for v in EW.values())), float(max(sr(v[0]) for v in EW.values()))]
N['share_beat_tbill'] = {bp: float((tab[f'exsr{bp}'] > 0).mean()) for bp in [0, 1, 2, 5]}
N['share_beat_bh_final'] = {bp: float((tab[f'fv{bp}'] > fv(bh)).mean()) for bp in [0, 1, 2, 5]}
best0 = tab.sr0.idxmax(); N['best_gross'] = {'config': list(best0), 'sharpe': float(tab.sr0.max()), 'final': float(tab.loc[best0, 'fv0'])}
bestf = tab.fv0.idxmax(); N['best_final_gross'] = {'config': list(bestf), 'final': float(tab.fv0.max()), 'sharpe': float(tab.loc[bestf, 'sr0'])}
for bp in [1, 2, 5]:
    b = tab[f'fv{bp}'].idxmax(); N[f'best_final_{bp}bp'] = {'config': list(b), 'final': float(tab.loc[b, f'fv{bp}']), 'sharpe': float(tab.loc[b, f'sr{bp}'])}
N['cost_by_freq'] = {f: {'turnover': float(gs[gs.Frequency == f].turn.mean()), 'turnover_longonly': float(gs[(gs.Frequency == f) & (gs.Group != 'Top-minus-Worst')].turn.mean()),
                         'n_beat_bh_gross': int(((gs.Frequency == f) & (gs.be_bh > 0)).sum()), 'n_freq': int((gs.Frequency == f).sum()),
                         'sr_lost_5bp': float((gs[gs.Frequency == f].sr0 - gs[gs.Frequency == f].sr5).mean()),
                         'median_be_bh': float(gs[(gs.Frequency == f) & (gs.be_bh > 0)].be_bh.median()) if ((gs.Frequency == f) & (gs.be_bh > 0)).any() else 0.0}
                     for f in FREQS}

# ---------------------------------
# 3) NOISE CEILING
# ---------------------------------
nulp = CACHE / 'null.pkl'
if not nulp.exists():
    pickle.dump(noise.null_best(d), open(nulp, 'wb'))
NULL = pickle.load(open(nulp, 'rb'))
nc = []
for (u, sp), nm in NULL.items():
    for g in GROUPS:
        real = gs[(gs.Universe == u) & (gs.Split == sp) & (gs.Group == g)]
        c95 = float(np.quantile(nm[g], 0.95))
        b = real.sort_values('sr0', ascending=False).iloc[0]
        nc.append({'Universe': u, 'Split': sp, 'Group': g, 'best_real': float(b.sr0), 'best_cfg': f"{b.Lookback}/{b.Frequency}",
                   'null_median': float(np.median(nm[g])), 'ceiling': c95, 'share_null_ge': float((nm[g] >= b.sr0).mean()),
                   'n_above': int((real.sr0 > c95).sum()), 'reps': int(len(nm[g]))})
nc = pd.DataFrame(nc); N['noise_ceiling'] = nc.to_dict('records')
N['noise_close'] = nc[(nc.best_real - nc.ceiling).abs() < 0.01][['Universe', 'Split', 'Group', 'best_real', 'ceiling']].to_dict('records')
N['noise_above_summary'] = {g: int((nc[nc.Group == g].n_above > 0).sum()) for g in GROUPS}

# ---------------------------------
# 4) FORMAL MULTIPLE TESTING (gross)
# ---------------------------------
# I test long-only groups against 1/N of the same universe at the same frequency, and long-short against zero
D = np.array([Gm[i] - (0 if keys[i][4] == 'Top-minus-Worst' else EW[(keys[i][0], keys[i][3])][0]) for i in range(K)]).T  # T x K
dbar = D.mean(0)
rng = np.random.default_rng(7)
B, blk = 5000, 21


def sb_counts(T, B, blk, rng):
    """Stationary bootstrap (Politis and Romano) as a B x T matrix of counts.
    Multiplying counts by the data is much faster than building B resampled series."""
    W = np.zeros((B, T))
    p = 1.0 / blk
    for b in range(B):
        t = rng.integers(T); n = 0
        while n < T:
            W[b, t] += 1; n += 1
            t = rng.integers(T) if rng.random() < p else (t + 1) % T
    return W


Wc = sb_counts(T, B, blk, rng)
boot = Wc @ D / T                                                   # B x K bootstrap means
# White's Reality Check
omega = np.sqrt(T) * boot.std(0, ddof=1)
V = np.sqrt(T) * dbar.max()
Vb = np.sqrt(T) * (boot - dbar).max(1)
N['white_rc_p'] = float((Vb >= V).mean())
# Hansen's SPA, consistent version (recentre only the models that are not clearly bad)
tk = np.sqrt(T) * dbar / omega
Tspa = max(tk.max(), 0)
thr = -np.sqrt(2 * np.log(np.log(T)))
mu_c = np.where(tk <= thr, dbar, 0.0)
Zb = np.maximum((np.sqrt(T) * (boot - dbar + mu_c) / omega).max(1), 0)
N['spa_p'] = float((Zb >= Tspa).mean())
N['spa_best_t'] = float(tk.max()); N['spa_best_cfg'] = list(keys[int(tk.argmax())])
# deflated Sharpe of the best gross configuration (Bailey and Lopez de Prado 2014), on daily Sharpe
srp = Gm.mean(1) / Gm.std(1, ddof=1)
ib = int(srp.argmax()); x = Gm[ib]
g3, g4 = st.skew(x), st.kurtosis(x, fisher=False)
emc = 0.5772156649
sr0_star = np.sqrt(srp.var(ddof=1)) * ((1 - emc) * st.norm.ppf(1 - 1 / K) + emc * st.norm.ppf(1 - 1 / (K * np.e)))
dsr = st.norm.cdf((srp[ib] - sr0_star) * np.sqrt(T - 1) / np.sqrt(1 - g3 * srp[ib] + (g4 - 1) / 4 * srp[ib] ** 2))
N['dsr'] = {'config': list(keys[ib]), 'sharpe_ann': float(srp[ib] * np.sqrt(TD)), 'expected_max_sr_ann': float(sr0_star * np.sqrt(TD)), 'dsr': float(dsr), 'n_trials': int(K)}
Kd = N['n_distinct']
sr0d = np.sqrt(srp.var(ddof=1)) * ((1 - emc) * st.norm.ppf(1 - 1 / Kd) + emc * st.norm.ppf(1 - 1 / (Kd * np.e)))
N['dsr_distinct'] = float(st.norm.cdf((srp[ib] - sr0d) * np.sqrt(T - 1) / np.sqrt(1 - g3 * srp[ib] + (g4 - 1) / 4 * srp[ib] ** 2)))
# probability of backtest overfitting, CSCV with S = 16 blocks (12,870 splits)
S = 16
edges = np.linspace(0, T, S + 1).astype(int)
s1 = np.array([Gm[:, a:b].sum(1) for a, b in zip(edges[:-1], edges[1:])])        # S x K
s2 = np.array([(Gm[:, a:b] ** 2).sum(1) for a, b in zip(edges[:-1], edges[1:])])
nb = np.diff(edges)
lam = []
for comb_ in itertools.combinations(range(S), S // 2):
    ins = np.zeros(S, bool); ins[list(comb_)] = True
    def _sr(mask):
        n_ = nb[mask].sum(); m = s1[mask].sum(0) / n_; v = s2[mask].sum(0) / n_ - m ** 2
        return m / np.sqrt(v)
    a, b_ = _sr(ins), _sr(~ins)
    k = int(a.argmax())
    w = (st.rankdata(b_)[k]) / (K + 1)
    lam.append(np.log(w / (1 - w)))
lam = np.array(lam)
N['pbo'] = {'S': S, 'combinations': int(comb(S, S // 2)), 'pbo': float((lam <= 0).mean()), 'median_logit': float(np.median(lam))}

# ---------------------------------
# 5) WHY THE MEDIAN GROUP WINS: volatility sorting
# ---------------------------------
# how often each commodity sits in the middle group vs what a random ranking would give
memb = {}
for u in ['Top6', 'Top9']:
    ks = UNIVERSES[u][0]; P, names, _ = d.prices(ks); sz = UNIVERSES[u][1][0]
    res, reb, order, sig = E.run_config(P, dates, 21, 'Monthly', sz, S0)
    lo = sz[0]; mid = order[:, lo:lo + sz[1]]
    memb[u] = {NAME[k]: float((mid == j).any(1).mean()) for j, k in enumerate(ks)}
N['median_membership_monthly21'] = memb
N['median_membership_expected'] = {u: UNIVERSES[u][1][0][1] / len(UNIVERSES[u][0]) for u in ['Top6', 'Top9']}
mv = gs[gs.Group.isin(['Top', 'Median', 'Worst'])].groupby('Group').vol.mean()
N['mean_vol_by_group'] = {k: float(v) for k, v in mv.items()}
med = gs[gs.Group == 'Median']
N['median_beats_ew_cells'] = float((med.sr0 > med.ew_sr0).mean())
N['top_beats_ew_cells'] = float((gs[gs.Group == 'Top'].sr0 > gs[gs.Group == 'Top'].ew_sr0).mean())
N['worst_beats_ew_cells'] = float((gs[gs.Group == 'Worst'].sr0 > gs[gs.Group == 'Worst'].ew_sr0).mean())
# 1/N without natural gas, to see how much of the median 'edge' is just avoiding it
exng = {}
for u in UNIVERSES:
    ks = [k for k in UNIVERSES[u][0] if k != 'NG1']
    P = d.PX[[TR[k] for k in ks]].values
    exng[u] = {f: sr(E.equal_weight(P, dates, f, S0)[0][S0 + 1:]) for f in FREQS}
N['ew_ex_natgas_sharpe'] = {u: [min(v.values()), max(v.values())] for u, v in exng.items()}
N['median_mean_sharpe_by_universe'] = {u: float(med[med.Universe == u].sr0.mean()) for u in UNIVERSES}

# ---------------------------------
# 6) DAILY REVERSAL: execution lag and a US-settled-only universe
# ---------------------------------
# lag 0 trades at the same close the ranking uses, lag 1 waits a day
def daily_rev(ks, k, lag):
    P = d.PX[[TR[x] for x in ks]].values; Rr = P[1:] / P[:-1] - 1; out = []
    for s in range(S0, len(P) - 1):
        w = np.zeros(len(ks)); w[np.argsort(-Rr[s - 1 - lag], kind='stable')[-k:]] = 1 / k; out.append(Rr[s] @ w)
    return np.array(out)
rev = {}
for u, k in [('Top6', 2), ('Top7', 2), ('Top7', 3), ('Top9', 3)]:
    rev[f'{u}_worst{k}'] = {f'lag{l}': {'sharpe': sr(daily_rev(UNIVERSES[u][0], k, l)), 'final': fv(daily_rev(UNIVERSES[u][0], k, l))} for l in (0, 1, 2)}
US = ['CL1', 'NG1', 'GC1', 'SI1', 'S 1', 'C 1', 'HG1']
rev['US7_worst2'] = {f'lag{l}': {'sharpe': sr(daily_rev(US, 2, l)), 'final': fv(daily_rev(US, 2, l))} for l in (0, 1)}
N['reversal'] = rev
dr = gs[(gs.Lookback == 'Daily (1d)') & (gs.Frequency == 'Daily') & (gs.Group == 'Worst')]
N['reversal_grid'] = {'sr0': [float(dr.sr0.min()), float(dr.sr0.max())], 'sr1': [float(dr.sr1.min()), float(dr.sr1.max())],
                      'sr2': [float(dr.sr2.min()), float(dr.sr2.max())], 'sr5': [float(dr.sr5.min()), float(dr.sr5.max())],
                      'turn': [float(dr.turn.min()), float(dr.turn.max())], 'be_bh': [float(dr.be_bh.min()), float(dr.be_bh.max())],
                      'be_cash_bp': [float(min((Gm[i] - rf).mean() / Cm[i].mean() for i in range(K) if keys[i] in dr.set_index(['Universe', 'Split', 'Lookback', 'Frequency', 'Group']).index)),
                                     float(max((Gm[i] - rf).mean() / Cm[i].mean() for i in range(K) if keys[i] in dr.set_index(['Universe', 'Split', 'Lookback', 'Frequency', 'Group']).index))]}

# ---------------------------------
# 7) REBALANCE-DATE LUCK
# ---------------------------------
# same rule, every possible start month (or the other biweekly Friday)
n = len(dates)
mkey = pd.Series(np.asarray(dates.to_period('M')), index=np.arange(n))
me = mkey.groupby(mkey).tail(1).index.values


def offset_runs(P, L, sz, step, offset):
    """Rebalance every `step` months on the month-ends where (month - 1) % step == offset % step."""
    pos = me[((dates[me].month - 1) % step == offset % step) & (me > S0) & (me < n - 1)]
    reb = np.unique(np.concatenate([[S0], pos]))
    Ws, _ = E.group_weights(P[reb] / P[reb - L] - 1, sz)
    out = {}
    for g, W in zip(['Top', 'Median', 'Worst'], Ws):
        out[g] = E.hold_returns(P, reb, W)[0][S0 + 1:]
    out['Top-minus-Worst'] = out['Top'] - out['Worst']
    return out


luck_rows = []
wkey = pd.Series(np.asarray(dates.to_period('W-FRI')), index=np.arange(n))
wend = wkey.groupby(wkey).tail(1).index.values
wend = wend[(wend > S0) & (wend < n - 1)]


def biweekly_runs(P, L, sz, anchor):
    reb = np.unique(np.concatenate([[S0], wend[anchor::2]]))
    Ws, _ = E.group_weights(P[reb] / P[reb - L] - 1, sz)
    out = {}
    for g, W in zip(['Top', 'Median', 'Worst'], Ws):
        out[g] = E.hold_returns(P, reb, W)[0][S0 + 1:]
    out['Top-minus-Worst'] = out['Top'] - out['Worst']
    return out
for u, (ks, splits) in UNIVERSES.items():
    P, _, _ = d.prices(ks)
    for sz in splits:
        for lb in LBS:
            for step, fname in [(12, 'Annual'), (6, 'Semiannual'), (3, 'Quarterly'), (2, 'Biweekly')]:
                if fname == 'Biweekly':
                    runs = [biweekly_runs(P, E.LOOKBACKS[lb], sz, a) for a in (1, 0)]   # anchor 1 is what the grid uses
                else:
                    runs = [offset_runs(P, E.LOOKBACKS[lb], sz, step, o) for o in range(step)]
                for g in GROUPS:
                    s = np.array([sr(r_[g]) for r_ in runs])
                    cal = s[0] if fname == 'Biweekly' else s[(12 - 1) % step]   # the grid's own date: December, or anchor 1
                    luck_rows.append({'Universe': u, 'Split': '-'.join(map(str, sz)), 'Lookback': lb, 'Frequency': fname, 'Group': g,
                                      'sr_calendar': cal, 'sr_min': s.min(), 'sr_max': s.max(), 'sr_mean': s.mean(), 'range': s.max() - s.min(),
                                      'calendar_rank': int((s > cal).sum() + 1), 'n_offsets': step})
luck = pd.DataFrame(luck_rows); luck.to_csv(HERE / 'rebalance_offsets.csv', index=False)
N['luck_summary'] = {f: {'median_range': float(luck[luck.Frequency == f]['range'].median()),
                         'share_calendar_best': float((luck[luck.Frequency == f].calendar_rank == 1).mean())} for f in ['Annual', 'Semiannual', 'Quarterly', 'Biweekly']}
P6, _, _ = d.prices(UNIVERSES['Top6'][0])
star = [offset_runs(P6, 21, (2, 2, 2), 12, o)['Median'] for o in range(12)]
N['star_other11_mean_sr'] = float(np.mean([sr(x) for x in star[:11]]))
N['star_1bp'] = {'dec': None}
N['star_by_month'] = [{'month': pd.Timestamp(2000, (o % 12) + 1, 1).strftime('%B'), 'sharpe': sr(x), 'final': fv(x)} for o, x in enumerate(star)]
# top 10 annual configs by calendar-date Sharpe, and how they rank against their other start months
top_ann = luck[luck.Frequency == 'Annual'].sort_values('sr_calendar', ascending=False).head(10)
N['top_annual_offsets'] = top_ann[['Universe', 'Split', 'Lookback', 'Group', 'sr_calendar', 'sr_min', 'sr_mean', 'sr_max', 'calendar_rank']].to_dict('records')

# ---------------------------------
# 8) WALK-FORWARD
# ---------------------------------
# (a) choose the top 5 on 2001-2013 only and run them blind on 2014-2026
cut = pd.Timestamp('2013-12-31')
ins = ev <= cut
srin = Gm[:, ins].mean(1) / Gm[:, ins].std(1, ddof=1) * np.sqrt(TD)
top5 = np.argsort(-srin)[:5]
oos_all = Gm[:, ~ins].mean(1) / Gm[:, ~ins].std(1, ddof=1) * np.sqrt(TD)
N['wf_split'] = [{'config': list(keys[i]), 'sr_in': float(srin[i]), 'sr_out': float(oos_all[i]), 'final_out': fv(Gm[i, ~ins]),
                  'rank_out': int((oos_all > oos_all[i]).sum() + 1)} for i in top5]
N['wf_split_bh'] = {'final_out': fv(bh[~ins]), 'sr_out': sr(bh[~ins])}
N['wf_split_median_oos_sr'] = float(np.median(oos_all))
# (b) each January pick the best config so far (expanding window), hold it for the year, gross and 2 bp
years = sorted(set(ev.year))
wf = {}
for bp in [0, 2]:
    X = Gm - Cm * bp
    path, picks = [], []
    for y in years[5:]:                              # first selection uses 2001-2005
        tr_m = ev.year < y; te = ev.year == y
        s = X[:, tr_m].mean(1) / X[:, tr_m].std(1, ddof=1)
        k = int(s.argmax()); picks.append(keys[k]); path.append(X[k, te])
    x = np.concatenate(path)
    wf[bp] = {'final': fv(x), 'sharpe': sr(x), 'start': int(years[5]), 'n_distinct': int(len(set(picks))),
              'bh_final': fv(bh[ev.year >= years[5]]), 'bh_sharpe': sr(bh[ev.year >= years[5]])}
N['wf_annual'] = wf

# ---------------------------------
# 9) OPEN-PRICE SCREEN
# ---------------------------------
sys.path.insert(0, str(BASE / 'data_quality'))
from open_price_screen import run as screen_run
scr = screen_run(); scr.to_csv(HERE / 'open_price_screen.csv', index=False)
N['screen'] = scr.to_dict('records')
from open_price_screen import screen as _scr
# failing series split before and after 2012, to see if the problem is historical
sub = {}
for t in ['LA1', 'LL1', 'LN1', 'LT1', 'LX1', 'KW1', 'C 1', 'S 1', 'KC1']:
    gg = lambda f_: fut[f'{t} Comdty|{f_}']
    sub[t] = {per: _scr(gg('PX_OPEN').loc[a:b], gg('PX_HIGH').loc[a:b], gg('PX_LOW').loc[a:b], gg('PX_LAST').loc[a:b], t, '')
              for per, (a, b) in {'pre2012': ('2000', '2011'), 'post2012': ('2012', '2026')}.items()}
N['screen_sub'] = sub

# the rebalance-month result again at 1 bp, each start month paying its own turnover
def offset_net(P, L, sz, step, o, bp, grp='Median'):
    pos = me[((dates[me].month - 1) % step == o % step) & (me > S0) & (me < n - 1)]
    reb = np.unique(np.concatenate([[S0], pos]))
    Ws, _ = E.group_weights(P[reb] / P[reb - L] - 1, sz)
    W = Ws[['Top', 'Median', 'Worst'].index(grp)]
    r, t = E.hold_returns(P, reb, W); c = np.zeros_like(r); c[reb + 1] = t * bp / 1e4
    return (r - c)[S0 + 1:]
v1 = [fv(offset_net(P6, 21, (2, 2, 2), 12, o, 1)) for o in range(12)]
N['star_1bp'] = {'dec': v1[11], 'min_other': min(v1[:11]), 'max_other': max(v1[:11])}
# the biweekly winner in Table 2, rerun on the other set of Fridays
bw = gs[gs.Frequency == 'Biweekly'].sort_values('fv0', ascending=False).iloc[0]
Pb, _, _ = d.prices(UNIVERSES[bw.Universe][0]); szb = tuple(int(x) for x in bw.Split.split('-'))
alt = biweekly_runs(Pb, E.LOOKBACKS[bw.Lookback], szb, 0)[bw.Group]
same = biweekly_runs(Pb, E.LOOKBACKS[bw.Lookback], szb, 1)[bw.Group]
N['biweekly_best_anchor'] = {'config': [bw.Universe, bw.Split, bw.Lookback, bw.Group], 'final_grid': float(bw.fv0), 'final_same_anchor_check': fv(same),
                             'final_other_anchor': fv(alt), 'sr_other_anchor': sr(alt)}
json.dump(N, open(HERE / 'numbers.json', 'w'), indent=1, default=str)

# ---------------------------------
# FIGURES
# ---------------------------------
NAVY, RED, GREY = '#0B3C5D', '#D62728', '#7F7F7F'
# Figure 1, generic front-month price vs the TR index
fig, axs = plt.subplots(1, 2, figsize=(9, 3.2))
for ax, k in zip(axs, ['CL1', 'NG1']):
    gp = fut[f'{k} Comdty|PX_LAST'].loc[t0:]; trs = d.PX[TR[k]].loc[t0:]
    if k == 'CL1':
        gp = gp.where(gp > 0)
    ax.plot(gp.index, 100 * gp / gp.iloc[0], color=GREY, lw=1, label='Generic 1st-month price (CL1/NG1)')
    ax.plot(trs.index, 100 * trs / trs.iloc[0], color=NAVY, lw=1.3, label='Total-return sub-index (investable)')
    ax.set_yscale('log'); ax.set_title(NAME[k], loc='left', fontweight='bold'); ax.set_ylabel('Growth of 100 (log)')
    ax.spines[['top', 'right']].set_visible(False); ax.grid(color='#EEEEEE')
axs[0].legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(FIG / 'fig1_generic_vs_tr.pdf'); fig.savefig(FIG / 'fig1_generic_vs_tr.png', dpi=200)

# Figure 2, best real Sharpe vs the noise ceiling
fig, axs = plt.subplots(1, 4, figsize=(11, 3.4), sharey=True)
for ax, g in zip(axs, GROUPS):
    z = nc[nc.Group == g].reset_index(drop=True)
    y = np.arange(len(z))
    ax.barh(y, z.best_real, color=NAVY, height=0.55, label='Best real configuration')
    ax.scatter(z.ceiling, y, marker='|', s=260, color=RED, lw=2, label='Noise ceiling (95th pct, random ranking)', zorder=3)
    ax.scatter(z.null_median, y, marker='|', s=160, color=GREY, lw=1.5, label='Random ranking: median best', zorder=3)
    ax.set_yticks(y); ax.set_yticklabels([f'{a} {b}' for a, b in zip(z.Universe, z.Split)])
    ax.set_title(g, loc='left', fontweight='bold'); ax.set_xlabel('Best Sharpe of 49 (gross)')
    ax.spines[['top', 'right']].set_visible(False)
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc='upper center', ncol=3, frameon=False)
fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(FIG / 'fig2_noise_ceiling.pdf'); fig.savefig(FIG / 'fig2_noise_ceiling.png', dpi=200)

# Figure 3, best config per frequency vs buy and hold at 0/1/2/5 bp
cols = {0: '#0B3C5D', 1: '#3A6EA5', 2: '#7FA7CF', 5: '#C4D8EC'}
bestper = gs.loc[gs.groupby('Frequency').fv0.idxmax()].set_index('Frequency').reindex(FREQS)
fig, ax = plt.subplots(figsize=(9, 3.6)); w = 0.2; xx = np.arange(len(FREQS))
for i, bp in enumerate([0, 1, 2, 5]):
    ax.bar(xx + (i - 1.5) * w, bestper[f'fv{bp}'], w * 0.92, color=cols[bp], edgecolor=NAVY, lw=0.4, label=f'{bp} bp')
ax.axhline(fv(bh), color=RED, ls='--', lw=1.4, label='BCOMTR buy & hold'); ax.axhline(100, color='black', lw=0.8)
ax.set_xticks(xx); ax.set_xticklabels([f"{f}\n{G.label(r).replace(', ', chr(10))}" for f, r in bestper.iterrows()], fontsize=7)
ax.set_ylabel('Final value of USD 100'); ax.spines[['top', 'right']].set_visible(False); ax.legend(frameon=False, ncol=5, fontsize=8)
fig.tight_layout(); fig.savefig(FIG / 'fig3_best_per_frequency.pdf'); fig.savefig(FIG / 'fig3_best_per_frequency.png', dpi=200)

# Figure 4, the same annual rule started in each month
fig, ax = plt.subplots(figsize=(8, 3))
v = [m['final'] for m in N['star_by_month']]
ax.bar(range(12), v, color=[('#E69F00' if i == 11 else NAVY) for i in range(12)])
ax.axhline(fv(bh), color=RED, ls='--', lw=1.2, label='BCOMTR buy & hold'); ax.axhline(100, color='black', lw=0.8)
ax.set_xticks(range(12)); ax.set_xticklabels([m['month'][:3] for m in N['star_by_month']])
ax.set_ylabel('Final value of USD 100'); ax.set_xlabel('Month-end used for the annual rebalance')
ax.spines[['top', 'right']].set_visible(False); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / 'fig4_rebalance_month.pdf'); fig.savefig(FIG / 'fig4_rebalance_month.png', dpi=200)

# Figure 5, walk-forward
fig, ax = plt.subplots(figsize=(8, 3.3))
evo = ev[~ins]
for j, i in enumerate(top5):
    ax.plot(evo, 100 * np.cumprod(1 + Gm[i, ~ins]), lw=1, color=plt.cm.Blues(0.45 + 0.1 * j), label='Top 5 chosen on 2001–2013' if j == 0 else None)
ax.plot(evo, 100 * np.cumprod(1 + bh[~ins]), color=RED, lw=1.6, label='BCOMTR buy & hold')
ax.axhline(100, color='black', lw=0.6); ax.set_ylabel('Growth of USD 100 from Jan 2014')
ax.spines[['top', 'right']].set_visible(False); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / 'fig5_walk_forward.pdf'); fig.savefig(FIG / 'fig5_walk_forward.png', dpi=200)
print('done', json.dumps({k: N[k] for k in ['white_rc_p', 'spa_p', 'dsr', 'pbo', 'wf_annual']}, default=str, indent=1))
