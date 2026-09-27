"""Turns numbers.json into the LaTeX macros (paper/numbers.tex) and tables (paper/tab_*.tex).

I never type a result into the manuscript by hand. Every number in main.tex is one of these macros,
so rerunning paper_numbers.py and then this script updates the whole paper.
"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
PAPER = HERE.parent / 'paper'
N = json.load(open(HERE / 'numbers.json'))
M = []
import re as _re
def neg(v):
    # proper minus signs in LaTeX, and no "-0.0"
    v = str(v)
    if _re.fullmatch(r'-0(\.0+)?(\\%)?', v):
        v = v[1:]
    return _re.sub(r'(?<![\w$])-(?=\d)', '$-$', v)
def mac(name, val): M.append(f'\\newcommand{{\\{name}}}{{{neg(val)}}}')
f0 = lambda x: f'{x:,.0f}'; f2 = lambda x: f'{x:.2f}'; f3 = lambda x: f'{x:.3f}'; pc = lambda x: f'{100*x:.1f}\\%'
mac('nConfigs', f"{N['n_configs']:,}"); mac('evalStart', N['eval_start']); mac('evalEnd', N['eval_end'])
mac('evalSessions', f"{N['eval_sessions']:,}"); mac('evalYears', f"{N['eval_years']:.1f}"); mac('holidays', N['holidays_dropped'])
mac('sessionsClean', f"{N['sessions_clean']:,}"); mac('sessionsRaw', f"{N['sessions_total_raw']:,}")
mac('clGeneric', pc(N['generic_vs_tr_CL1']['generic_price_return'])); mac('clTR', pc(N['generic_vs_tr_CL1']['tr_return']))
mac('ngGeneric', pc(N['generic_vs_tr_NG1']['generic_price_return'])); mac('ngGenericAbs', pc(-N['generic_vs_tr_NG1']['generic_price_return'])); mac('ngTRAbs', f"{-100*N['generic_vs_tr_NG1']['tr_return']:.2f}\\%"); mac('ngTR', f"{100*N['generic_vs_tr_NG1']['tr_return']:.2f}\\%")
mac('clNeg', f"{N['cl1_2020_04_20']:.2f}"); mac('liborLast', N['libor_last_change'])
b = N['bh']; mac('bhFinal', f0(b['final'])); mac('bhCagr', pc(b['cagr'])); mac('bhSharpe', f2(b['sharpe'])); mac('bhMdd', pc(b['mdd'])); mac('bhExSharpe', f2(b['excess_sharpe']))
rc = N['refined_corr_with_crude']; mac('refCorrLo', f2(min(rc))); mac('refCorrHi', f2(max(rc)))
mac('ewSrLo', f2(N['ew_sharpe_range'][0])); mac('ewSrHi', f2(N['ew_sharpe_range'][1]))
for bp in ['0', '1', '2', '5']:
    mac(f'beatTbill{"ABCD"["0125".index(bp)]}', pc(N['share_beat_tbill'][bp])); mac(f'beatBh{"ABCD"["0125".index(bp)]}', pc(N['share_beat_bh_final'][bp]))
mac('bestGrossSr', f2(N['best_gross']['sharpe'])); mac('bestGrossFinal', f0(N['best_gross']['final']))
mac('bestFinalGross', f0(N['best_final_gross']['final'])); mac('bestFinalGrossSr', f2(N['best_final_gross']['sharpe']))
for bp, L in [('1', 'A'), ('2', 'B'), ('5', 'C')]:
    mac(f'bestFinalNet{L}', f0(N[f'best_final_{bp}bp']['final'])); mac(f'bestFinalNetSr{L}', f2(N[f'best_final_{bp}bp']['sharpe']))
mac('rcP', f2(N['white_rc_p'])); mac('spaP', f2(N['spa_p'])); mac('spaT', f2(N['spa_best_t']))
mac('dsr', f2(N['dsr']['dsr'])); mac('dsrExpMax', f2(N['dsr']['expected_max_sr_ann'])); mac('dsrSr', f2(N['dsr']['sharpe_ann']))
mac('pbo', f2(N['pbo']['pbo'])); mac('nDistinct', f"{N['n_distinct']:,}"); mac('dsrDistinct', f2(N['dsr_distinct'])); mac('nDup', f"{N['n_configs'] - N['n_distinct']:,}"); mac('pboComb', f"{N['pbo']['combinations']:,}")
mv = N['mean_vol_by_group']; mac('volMedian', pc(mv['Median'])); mac('volTop', pc(mv['Top'])); mac('volWorst', pc(mv['Worst']))
mac('medBeatsEw', pc(N['median_beats_ew_cells'])); mac('topBeatsEw', pc(N['top_beats_ew_cells'])); mac('worstBeatsEw', pc(N['worst_beats_ew_cells']))
mm = N['median_membership_monthly21']; mac('ngMedSixt', pc(mm['Top6']['Natural Gas'])); mac('ngMedNine', pc(mm['Top9']['Natural Gas']))
mac('goldMedNine', pc(mm['Top9']['Gold']))
ex = N['ew_ex_natgas_sharpe']; mac('exNgLo', f2(min(v[0] for v in ex.values()))); mac('exNgHi', f2(max(v[1] for v in ex.values())))
mac('exNgSix', f"{ex['Top6'][0]:.2f} to {ex['Top6'][1]:.2f}")
ms = N['median_mean_sharpe_by_universe']; mac('medMeanLo', f2(min(ms.values()))); mac('medMeanHi', f2(max(ms.values())))
gsum = N['group_sharpe']
for g, L in [('Top', 'Top'), ('Median', 'Med'), ('Worst', 'Wor'), ('Top-minus-Worst', 'Tmw')]:
    mac(f'sr{L}Mean', f2(gsum[g]['mean'])); mac(f'sr{L}Max', f2(gsum[g]['max']))
na = N['noise_above_summary']; mac('ncTop', na['Top']); mac('ncMed', na['Median']); mac('ncWor', na['Worst']); mac('ncTmw', na['Top-minus-Worst'])
rg = N['reversal_grid']
mac('revSrLo', f2(rg['sr0'][0])); mac('revSrHi', f2(rg['sr0'][1])); mac('revSrFiveLo', f2(rg['sr5'][0])); mac('revSrFiveHi', f2(rg['sr5'][1]))
mac('revSrOneLo', f2(rg['sr1'][0])); mac('revSrOneHi', f2(rg['sr1'][1])); mac('revSrTwoLo', f2(rg['sr2'][0])); mac('revSrTwoHi', f2(rg['sr2'][1]))
mac('revTurnLo', f0(rg['turn'][0])); mac('revTurnHi', f0(rg['turn'][1])); mac('revBeBhLo', f"{rg['be_bh'][0]:.1f}"); mac('revBeBhHi', f"{rg['be_bh'][1]:.1f}")
mac('revBeCashLo', f"{rg['be_cash_bp'][0]:.1f}"); mac('revBeCashHi', f"{rg['be_cash_bp'][1]:.1f}")
rv = N['reversal']
mac('revNineLagZero', f2(rv['Top9_worst3']['lag0']['sharpe'])); mac('revNineLagOne', f2(rv['Top9_worst3']['lag1']['sharpe']))
mac('revSixLagZero', f2(rv['Top6_worst2']['lag0']['sharpe'])); mac('revSixLagOne', f2(rv['Top6_worst2']['lag1']['sharpe']))
mac('revUsLagZero', f2(rv['US7_worst2']['lag0']['sharpe'])); mac('revUsLagOne', f2(rv['US7_worst2']['lag1']['sharpe']))
ls = N['luck_summary']
mac('luckAnnRange', f2(ls['Annual']['median_range'])); mac('luckSemiRange', f2(ls['Semiannual']['median_range'])); mac('luckQRange', f2(ls['Quarterly']['median_range']))
mac('luckAnnCalBest', pc(ls['Annual']['share_calendar_best'])); mac('luckBwRange', f2(ls['Biweekly']['median_range']))
ta = N['top_annual_offsets']; mac('topAnnFirst', sum(x['calendar_rank'] == 1 for x in ta)); mac('topAnnWorstRank', max(x['calendar_rank'] for x in ta))
mac('topAnnN', len(ta))
sb = N['star_by_month']; fins = [m['final'] for m in sb]; srs = [m['sharpe'] for m in sb]
import statistics
mac('starDec', f0(sb[11]['final'])); mac('starMin', f0(min(fins[:11]))); mac('starMaxOther', f0(max(fins[:11]))); mac('starMedian', f0(statistics.median(fins)))
mac('starSrOtherMean', f2(N['star_other11_mean_sr'])); s1 = N['star_1bp']; mac('starDecOne', f0(s1['dec'])); mac('starMinOne', f0(s1['min_other'])); mac('starMaxOne', f0(s1['max_other']))
bwa = N['biweekly_best_anchor']; mac('bwGrid', f0(bwa['final_grid'])); mac('bwAlt', f0(bwa['final_other_anchor'])); mac('bwAltSr', f2(bwa['sr_other_anchor']))
mac('starSrMin', f2(min(srs))); mac('starSrMaxOther', f2(max(srs[:11]))); mac('starSrMean', f2(sum(srs)/12)); mac('starSrDec', f2(srs[11]))
wf = N['wf_split']; mac('wfInLo', f2(min(x['sr_in'] for x in wf))); mac('wfInHi', f2(max(x['sr_in'] for x in wf)))
mac('wfOutLo', f2(min(x['sr_out'] for x in wf))); mac('wfOutHi', f2(max(x['sr_out'] for x in wf)))
mac('wfFinLo', f0(min(x['final_out'] for x in wf))); mac('wfFinHi', f0(max(x['final_out'] for x in wf)))
mac('wfRankLo', f0(min(x['rank_out'] for x in wf))); mac('wfRankHi', f"{max(x['rank_out'] for x in wf):,}")
mac('wfBhFinal', f0(N['wf_split_bh']['final_out'])); mac('wfBhSr', f2(N['wf_split_bh']['sr_out'])); mac('wfMedOos', f2(N['wf_split_median_oos_sr']))
wa = N['wf_annual']; mac('wfaFinG', f0(wa['0']['final'])); mac('wfaSrG', f2(wa['0']['sharpe'])); mac('wfaFinN', f0(wa['2']['final'])); mac('wfaSrN', f2(wa['2']['sharpe']))
mac('wfaBh', f0(wa['0']['bh_final'])); mac('wfaBhSr', f2(wa['0']['bh_sharpe'])); mac('wfaStart', wa['0']['start'])
scr = {r['Series']: r for r in N['screen']}
dx = [r for r in N['screen'] if r['Source'].startswith('Barchart') and '(DX)' in r['Series']][0]
fr = [r for r in N['screen'] if r['Source'].startswith('Free')][0]
mac('scrDxLow', dx['Open = low']); mac('scrDxHigh', dx['Open = high']); mac('scrDxP', f2(dx['Binomial p']))
mac('scrFreeLow', fr['Open = low']); mac('scrFreeHigh', fr['Open = high'])
bl = [r for r in N['screen'] if r['Source'].startswith('Bloomberg')]
mac('scrNBloom', len(bl)); mac('scrNFail', sum(r['Flag'] == 'FAIL' for r in bl))
cf = N['cost_by_freq']; mac('turnDaily', f0(cf['Daily']['turnover_longonly'])); mac('turnAnnual', f"{cf['Annual']['turnover_longonly']:.1f}")
mac('nBeatDaily', cf['Daily']['n_beat_bh_gross']); mac('nBeatAnnual', cf['Annual']['n_beat_bh_gross'])
sub = N['screen_sub']; lme = [sub[t]['pre2012']['Open outside range %'] for t in ['LA1', 'LL1', 'LN1', 'LT1', 'LX1']]
mac('lmePreLo', f'{min(lme):.0f}'); mac('lmePreHi', f'{max(lme):.0f}'); mac('kwPre', f"{sub['KW1']['pre2012']['Open outside range %']:.1f}")
mac('nNoiseClose', len(N['noise_close']))
W = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
mac('ncMedW', W[na['Median']]); mac('ncWorW', W[na['Worst']]); mac('nNoiseCloseW', W[len(N['noise_close'])].capitalize())
mac('beMedDaily', f"{cf['Daily']['median_be_bh']:.1f}"); mac('beMedAnnual', f0(cf['Annual']['median_be_bh']))
open(PAPER / 'numbers.tex', 'w').write('\n'.join(M) + '\n')

# ---------------------------------
# TABLES
# ---------------------------------
T = []
T.append(r"""\begin{table}[H]
\caption{The traded universe. Liquidity ranks are among the 30 generic contracts in the Bloomberg pull, by mean daily notional volume over 2000--2026 (Vol.) and by mean notional open interest over the last twelve months (OI); the universe is ordered by the average of the two ranks. Return statistics use the total-return sub-index over \evalStart{} to \evalEnd{}.\label{tab:assets}}
\small
\begin{tabularx}{\textwidth}{lllrrrrrr}
\toprule
\textbf{Universe} & \textbf{Commodity} & \textbf{Sub-index} & \textbf{Vol.} & \textbf{OI} & \textbf{CAGR} & \textbf{Volatility} & \textbf{Sharpe} & \textbf{Max DD}\\
\midrule""")
liq = {r['name']: (r['rank_dv'], r['rank_oi']) for r in N['liquidity']}
tags = ['Top6'] * 6 + ['+Top7', '+Top8', '+Top9']
for tag, a in zip(tags + [''], N['assets']):
    lr = liq.get(a['Commodity'], ('--', '--'))
    dd = 100 * a['MaxDD']; dds = f'{dd:.2f}' if a['MaxDD'] < -0.999 else f'{dd:.1f}'
    T.append(f"{tag} & {a['Commodity']} & {a['Index']} & {lr[0]} & {lr[1]} & {100*a['CAGR']:.1f}\\% & {100*a['Vol']:.1f}\\% & {a['Sharpe']:.2f} & {dds}\\%\\\\")
T.insert(-1, r'\midrule')
T.append(r"""\bottomrule
\end{tabularx}
\end{table}
""")
# best per frequency
import pandas as pd
cfg = pd.read_csv(HERE / 'all_configs.csv')
def lab(r):
    sz = r.Split.split('-'); n = r.Universe[3:]
    g = {'Top': f'Best {sz[0]}', 'Median': f'Middle {sz[1]}', 'Worst': f'Worst {sz[2]}'}.get(r.Group, f'Best {sz[0]} $-$ Worst {sz[2]}')
    return f"{g} of {n} ({r.Split}), {r.Lookback.split('(')[1].rstrip(')')}"
T.append(r"""\begin{table}[H]
\caption{Best configuration at each rebalance frequency (highest gross terminal value), with the terminal value of USD 100 net of 0, 1, 2 and 5 bp per unit of one-way turnover, and the cost at which it would end level with BCOMTR buy-and-hold (USD \bhFinal).\label{tab:bestfreq}}
\small
\begin{tabularx}{\textwidth}{lXrrrrrrr}
\toprule
\textbf{Rebalance} & \textbf{Configuration} & \textbf{Turn./yr} & \textbf{0 bp} & \textbf{1 bp} & \textbf{2 bp} & \textbf{5 bp} & \textbf{Sharpe} & \textbf{Break-even (bp)}\\
\midrule""")
for f in ['Daily', 'Weekly', 'Biweekly', 'Monthly', 'Quarterly', 'Semiannual', 'Annual']:
    r = cfg[cfg.Frequency == f].sort_values('fv0', ascending=False).iloc[0]
    T.append(f"{f} & {lab(r)} & {r.turn:.1f} & {r.fv0:,.0f} & {r.fv1:,.0f} & {r.fv2:,.0f} & {r.fv5:,.0f} & {r.sr0:.2f} & {r.be_bh:,.1f}\\\\")
T.append(r"""\bottomrule
\end{tabularx}
\end{table}
""")
# noise ceiling
nc = pd.DataFrame(N['noise_ceiling'])
T.append(r"""\begin{table}[H]
\caption{Best gross Sharpe ratio in each 49-configuration grid against its noise ceiling: the 95th percentile of the best Sharpe the identical grid attains when the ranking is a random permutation at every rebalance (200 replications). Entries are best real / ceiling; an asterisk marks a grid in which at least one real configuration exceeds the ceiling, and a dagger a best configuration within 0.01 of the ceiling, where the verdict is within simulation error.\label{tab:noise}}
\small
\begin{tabularx}{\textwidth}{lXXXX}
\toprule
\textbf{Universe, split} & \textbf{Top} & \textbf{Median} & \textbf{Worst} & \textbf{Top$-$Worst}\\
\midrule""")
for (u, sp), z in nc.groupby(['Universe', 'Split'], sort=False):
    cells = []
    for g in ['Top', 'Median', 'Worst', 'Top-minus-Worst']:
        r = z[z.Group == g].iloc[0]
        mark = ('$^{*}$' if r.n_above > 0 else '') + ('$^{\\dagger}$' if abs(r.best_real - r.ceiling) < 0.01 else '')
        cells.append(f"{r.best_real:.2f} / {r.ceiling:.2f}{mark}")
    T.append(f"{u} {sp} & " + ' & '.join(cells) + r'\\')
T.append(r"""\bottomrule
\end{tabularx}
\end{table}
""")
# formal tests
T.append(r"""\begin{table}[H]
\caption{Multiple-testing diagnostics over all \nConfigs{} configurations (gross). Relative performance is measured against 1/N of the same commodities at the same frequency for the long-only groups and against zero for the long--short spread. Stationary bootstrap with mean block length 21 sessions, 5000 replications. The Hansen $p$-value varies between about 0.01 and 0.03 across bootstrap seeds.\label{tab:formal}}
\small
\begin{tabularx}{\textwidth}{Xr}
\toprule
\textbf{Diagnostic} & \textbf{Value}\\
\midrule
White Reality Check $p$-value & \rcP\\
Hansen SPA $p$-value (consistent) & \spaP\\
\quad best studentised statistic (1-day reversal, Worst 3 of 7, daily) & \spaT\\
Deflated Sharpe ratio of the best configuration (must exceed 0.95) & \dsr\\
\quad annualised Sharpe of the best configuration & \dsrSr\\
\quad expected maximum annualised Sharpe of \nConfigs{} trials under the null & \dsrExpMax\\
Probability of backtest overfitting (CSCV, 16 blocks, \pboComb{} splits) & \pbo\\
\bottomrule
\end{tabularx}
\end{table}
""")
# reversal lag
T.append(r"""\begin{table}[H]
\caption{The 1-day reversal (hold the worst performers of the previous session, rebalanced daily), gross of costs, when executed at the signal close, one session later and two sessions later. The US-settled universe keeps only contracts that settle on CME Group exchanges (WTI, natural gas, gold, silver, soybeans, corn, copper).\label{tab:reversal}}
\small
\begin{tabularx}{\textwidth}{Xrrrrrr}
\toprule
& \multicolumn{2}{c}{\textbf{Same close}} & \multicolumn{2}{c}{\textbf{One day later}} & \multicolumn{2}{c}{\textbf{Two days later}}\\
\textbf{Universe, holding} & \textbf{Sharpe} & \textbf{USD 100 $\to$} & \textbf{Sharpe} & \textbf{USD 100 $\to$} & \textbf{Sharpe} & \textbf{USD 100 $\to$}\\
\midrule""")
for k, nm in [('Top6_worst2', 'Top 6, worst 2'), ('Top7_worst2', 'Top 7, worst 2'), ('Top7_worst3', 'Top 7, worst 3'), ('Top9_worst3', 'Top 9, worst 3'), ('US7_worst2', 'US-settled 7, worst 2')]:
    r = rv[k]
    l2 = f"{r['lag2']['sharpe']:.2f} & {r['lag2']['final']:,.0f}" if 'lag2' in r else '-- & --'
    T.append(f"{nm} & {r['lag0']['sharpe']:.2f} & {r['lag0']['final']:,.0f} & {r['lag1']['sharpe']:.2f} & {r['lag1']['final']:,.0f} & {l2}\\\\")
T.append(r"""\bottomrule
\end{tabularx}
\end{table}
""")
# walk-forward
T.append(r"""\begin{table}[H]
\caption{Out-of-sample check. The five configurations with the highest gross Sharpe ratio over 2001--2013, run unchanged over 2014--2026. Rank is out of \nConfigs{} on the out-of-sample period. BCOMTR buy-and-hold over 2014--2026: USD 100 $\to$ \wfBhFinal, Sharpe \wfBhSr.\label{tab:wf}}
\small
\begin{tabularx}{\textwidth}{Xrrrr}
\toprule
\textbf{Configuration (rebalance)} & \textbf{Sharpe 2001--13} & \textbf{Sharpe 2014--26} & \textbf{USD 100 $\to$} & \textbf{Rank 2014--26}\\
\midrule""")
for x in wf:
    u, sp, lb, f, g = x['config']
    r = pd.Series({'Universe': u, 'Split': sp, 'Lookback': lb, 'Group': g})
    T.append(f"{lab(r)} ({f.lower()}) & {x['sr_in']:.2f} & {x['sr_out']:.2f} & {x['final_out']:,.0f} & {x['rank_out']:,}\\\\")
T.append(r"""\bottomrule
\end{tabularx}
\end{table}
""")
# screen
scr_rows = [r for r in N['screen'] if any(s in r['Series'] for s in ['CL1', 'CO1', 'GC1', 'NG1', 'S 1', 'SI1', 'LA1', 'C 1', 'HG1', 'LN1', 'KC1', 'KW1'])] + \
           [r for r in N['screen'] if not r['Source'].startswith('Bloomberg') and ('(DX)' in r['Series'] or 'free' in r['Series'])]
T.append(r"""\begin{table}[H]
\caption{Open-location screen on daily OHLC data. Under an unbiased open, P(open = low) = P(open = high); $p$ is the exact two-sided binomial test. ``Pos.'' is the mean position of the open in the day's range (0.5 expected); ``Outside'' is the share of opens outside the day's own range. Flag = FAIL if $p$ is below 0.01 after Bonferroni correction over all 37 series screened, or more than 1\% of opens lie outside the range. Selected rows; all 30 Bloomberg contracts are in the replication files.\label{tab:screen}}
\small
\begin{tabularx}{\textwidth}{Xlrrrrrl}
\toprule
\textbf{Series} & \textbf{Source} & \textbf{Open=low} & \textbf{Open=high} & \textbf{$p$} & \textbf{Pos.} & \textbf{Outside} & \textbf{Flag}\\
\midrule""")
for r in scr_rows:
    src = {'Bloomberg generic 1st': 'Bloomberg', 'Barchart, exchange sourced': 'Barchart (exch.)', 'Free provider (paper control)': 'Free provider'}[r['Source']]
    p = r['Binomial p']; ps = f'{p:.2g}' if p < 0.001 else f'{p:.3f}'
    T.append(f"{r['Series'].replace('&','and').replace(' Comdty','')} & {src} & {r['Open = low']} & {r['Open = high']} & {ps} & {r['Mean open position (0.5 = unbiased)']:.2f} & {r['Open outside range %']:.1f}\\% & {r['Flag']}\\\\")
T.append(r"""\bottomrule
\end{tabularx}
\end{table}
""")
# split the block into one file per table and widen them to the full MDPI page width
names = ['assets', 'bestfreq', 'noise', 'formal', 'reversal', 'wf', 'screen']
blocks, cur = [], []
for line in T:
    cur.append(line)
    if line.strip().endswith('\\end{table}'):
        blocks.append('\n'.join(cur)); cur = []
assert len(blocks) == len(names), len(blocks)
for nm, b in zip(names, blocks):
    b = b.replace('\\begin{table}[H]\n', '\\begin{table}[H]\n\\begin{adjustwidth}{-\\extralength}{0cm}\n', 1)
    b = b.replace('\\end{table}', '\\end{adjustwidth}\n\\end{table}')
    b = b.replace('{tabularx}{\\textwidth}', '{tabularx}{\\fulllength}')
    lines = []
    for ln in b.split('\n'):
        if '&' in ln and not ln.lstrip().startswith('\\textbf'):
            ln = _re.sub(r'(?<=[&\s])-0\.00(?=\s*(&|\\\\))', '0.00', ln)
            ln = _re.sub(r'(?<=[&\s])-(?=\d)', '$-$', ln)
        lines.append(ln)
    open(PAPER / f'tab_{nm}.tex', 'w').write('\n'.join(lines) + '\n')
print(len(M), 'macros')
