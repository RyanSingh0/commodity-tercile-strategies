"""Top strategies at each rebalance frequency against BCOMTR buy and hold.

Bar charts of the final value of $100 and of max drawdown, and the colour-coded Excel cost ladder.
"""
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from .grid import FREQS, label, config_series, buy_and_hold, equal_weight, final_value, max_drawdown, sharpe, breakeven_bp

COST_COLORS = {0: '#0B3C5D', 1: '#3A6EA5', 2: '#7FA7CF', 5: '#C4D8EC'}   # more cost, paler bar
BH_COLOR = '#D62728'


def top_per_frequency(grid, n=5, by='Final $0bp'):
    """Top n configurations per frequency by gross final value. Identical portfolios reached
    through different splits are listed once, with the duplicates noted."""
    out = []
    for f in FREQS:
        g = grid[grid.Frequency == f].sort_values(by, ascending=False)
        seen, k = set(), 0
        for _, r in g.iterrows():
            if r.fingerprint in seen:
                continue
            seen.add(r.fingerprint)
            dup = grid[(grid.fingerprint == r.fingerprint)]
            rr = r.copy()
            rr['Same portfolio as'] = '; '.join(f"{a} {b}" for a, b in zip(dup.Universe, dup.Split) if (a, b) != (r.Universe, r.Split))
            rr['Rank'] = k + 1
            rr['Strategy'] = label(r)
            out.append(rr)
            k += 1
            if k == n:
                break
    return pd.DataFrame(out).reset_index(drop=True)


def _style(ax):
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', color='#E5E5E5', lw=0.8)
    ax.set_axisbelow(True)


def bar_chart(top, bh_value, metric='Final', bps=(0, 1, 2, 5), path=None, ew=None):
    """metric is 'Final' (final value of $100) or 'MaxDD' (max drawdown, plotted as a positive %)."""
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9})
    fig, axes = plt.subplots(len(FREQS), 1, figsize=(11, 3.1 * len(FREQS)))
    w = 0.8 / len(bps)
    for ax, f in zip(axes, FREQS):
        t = top[top.Frequency == f].sort_values('Rank')
        x = np.arange(len(t))
        for i, bp in enumerate(bps):
            col = f'{metric} {bp}bp' if metric == 'MaxDD' else f'Final ${bp}bp'
            v = t[col].values * (-100 if metric == 'MaxDD' else 1)
            ax.bar(x + (i - (len(bps) - 1) / 2) * w, v, w * 0.92, color=COST_COLORS[bp],
                   edgecolor='#0B3C5D', linewidth=0.4, label=f'{bp} bp per unit traded')
        ref = bh_value if metric == 'Final' else -100 * bh_value
        ax.axhline(ref, color=BH_COLOR, ls='--', lw=1.4, label='BCOMTR buy & hold')
        if metric == 'Final':
            ax.axhline(100, color='black', lw=0.8)
            if ew is not None:
                ax.axhline(ew[f], color='#555555', ls=':', lw=1.2, label='1/N equal weight (same commodities, same frequency)')
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace(', ', '\n').replace(' / ', ' /\n') for s in t.Strategy], fontsize=8)
        ax.set_title(f'{f} rebalancing: top 5 strategies by gross return', fontsize=10, loc='left', fontweight='bold')
        ax.set_ylabel('Final value of $100' if metric == 'Final' else 'Maximum drawdown (%)')
        _style(ax)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper center', ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.0))
    ttl = ('Terminal value of $100, Jan 2001 to Sep 2026' if metric == 'Final'
           else 'Maximum drawdown, Jan 2001 to Sep 2026 (lower is better)')
    fig.suptitle(ttl, y=1.015, fontsize=12, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    if path:
        fig.savefig(path, dpi=200, bbox_inches='tight')
    return fig


def cost_ladder(data, top, bh_final):
    """Final value of $100 for each top strategy as the cost goes up, stopping once every strategy
    is at or below buy and hold. Also the exact break-even cost of each one."""
    series = {}
    for i, r in top.iterrows():
        series[i] = config_series(data, r.Universe, r.Split, r.Lookback, r.Frequency, r.Group)
    ladder = [0, 1, 2, 3, 4, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000,
              1500, 2000, 3000, 5000]
    cols = []
    for bp in ladder:
        vals = {i: final_value(g.values, c.values, bp) for i, (g, c) in series.items()}
        cols.append((bp, vals))
        if max(vals.values()) <= bh_final:
            break
    tab = top[['Frequency', 'Rank', 'Strategy', 'Universe', 'Split', 'Lookback', 'Group', 'turnover_per_year']].copy()
    for bp, vals in cols:
        tab[f'{bp:g} bp'] = pd.Series(vals)
    tab['Break-even cost vs buy & hold (bp)'] = [breakeven_bp(series[i][0].values, series[i][1].values, bh_final) for i in tab.index]
    for bp in (0, 1, 2, 5):
        tab[f'Sharpe {bp}bp'] = [sharpe(series[i][0].values, series[i][1].values, bp) for i in tab.index]
        tab[f'MaxDD {bp}bp'] = [max_drawdown(series[i][0].values, series[i][1].values, bp) for i in tab.index]
    return tab, [bp for bp, _ in cols], series


def write_excel(tab, cost_cols, bh_final, bh_dd, bh_sharpe, path, ew_table=None):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    BLUE = PatternFill('solid', fgColor='BDD7EE')
    GREEN = PatternFill('solid', fgColor='C6EFCE')
    RED = PatternFill('solid', fgColor='FFC7CE')
    HDR = PatternFill('solid', fgColor='1F3864')
    F = lambda **k: Font(name='Arial', size=10, **k)
    wb = Workbook()

    def sheet(ws, title, note, value_cols, bh_val, fmt, better_high=True, extra=None):
        ws['A1'] = title; ws['A1'].font = Font(name='Arial', size=13, bold=True, color='1F3864')
        ws['A2'] = note; ws['A2'].font = Font(name='Arial', size=9, italic=True)
        ws['A3'] = 'Legend:'; ws['A3'].font = F(bold=True)
        for c, (txt, fill) in zip('BCD', [('Buy & hold (BCOMTR)', BLUE), ('Better than buy & hold', GREEN), ('Worse than buy & hold', RED)]):
            ws[f'{c}3'] = txt; ws[f'{c}3'].fill = fill; ws[f'{c}3'].font = F()
        head = ['Frequency', 'Rank', 'Strategy', 'Universe', 'Split', 'Lookback', 'Group', 'Turnover (x/yr)'] + value_cols + (extra or [])
        r0 = 5
        for j, h in enumerate(head, 1):
            c = ws.cell(r0, j, h); c.fill = HDR; c.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
            c.alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
        ws.row_dimensions[r0].height = 32
        # buy and hold goes first, in blue
        r = r0 + 1
        ws.cell(r, 1, 'Buy & hold'); ws.cell(r, 3, 'BCOMTR (Bloomberg Commodity Index, total return)')
        for j in range(1, len(head) + 1):
            ws.cell(r, j).fill = BLUE; ws.cell(r, j).font = F(bold=True)
        for j, col in enumerate(value_cols):
            c = ws.cell(r, 9 + j, bh_val); c.number_format = fmt
        for _, row in tab.iterrows():
            r += 1
            vals = [row.Frequency, int(row.Rank), row.Strategy, row.Universe, row.Split, row.Lookback, row.Group, row.turnover_per_year]
            for j, v in enumerate(vals, 1):
                c = ws.cell(r, j, v); c.font = F()
            ws.cell(r, 8).number_format = '0.0'
            for j, col in enumerate(value_cols):
                v = float(row[col if col in row else col])
                c = ws.cell(r, 9 + j, v); c.number_format = fmt; c.font = F()
                better = v > bh_val if better_high else v > bh_val   # drawdowns are negative, so higher is shallower
                c.fill = GREEN if better else RED
            for k, col in enumerate(extra or []):
                v = row[col]
                c = ws.cell(r, 9 + len(value_cols) + k, None if not np.isfinite(v) else float(v))
                c.number_format = '#,##0.0'; c.font = F(bold=True)
                if not np.isfinite(v):
                    c.value = 'never trades'
        widths = [11, 6, 44, 9, 7, 16, 16, 10] + [11] * (len(value_cols) + len(extra or []))
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.freeze_panes = ws.cell(r0 + 2, 4)

    ws = wb.active; ws.title = 'Final value vs cost'
    value_cols = [f'{bp:g} bp' for bp in cost_cols]
    sheet(ws, 'Final value of $100 (Jan 2001 to Sep 2026) as trading cost rises',
          'Columns increase the cost per unit of one-way turnover until every strategy has fallen to or below buy & hold. '
          'Last column: exact cost at which each strategy ends level with buy & hold.',
          value_cols, bh_final, '$#,##0', extra=['Break-even cost vs buy & hold (bp)'])
    ws2 = wb.create_sheet('Max drawdown vs cost')
    sheet(ws2, 'Maximum drawdown at 0, 1, 2 and 5 bp (closer to zero is better)',
          'Green = shallower drawdown than BCOMTR buy & hold, red = deeper.',
          [f'MaxDD {bp}bp' for bp in (0, 1, 2, 5)], bh_dd, '0.0%')
    ws3 = wb.create_sheet('Sharpe vs cost')
    sheet(ws3, 'Sharpe ratio (rf = 0) at 0, 1, 2 and 5 bp',
          'Green = higher Sharpe than BCOMTR buy & hold, red = lower.',
          [f'Sharpe {bp}bp' for bp in (0, 1, 2, 5)], bh_sharpe, '0.00')
    if ew_table is not None:
        w4 = wb.create_sheet('1-N reference')
        w4['A1'] = '1/N equal weight of the same commodities (secondary reference, final value of $100, gross)'
        w4['A1'].font = F(bold=True)
        for j, h in enumerate(ew_table.columns, 1):
            c = w4.cell(3, j, h); c.fill = HDR; c.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
        for i, row in enumerate(ew_table.itertuples(index=False), 4):
            for j, v in enumerate(row, 1):
                c = w4.cell(i, j, v); c.font = F()
                if isinstance(v, float): c.number_format = '$#,##0'
        for j in range(1, len(ew_table.columns) + 1):
            w4.column_dimensions[get_column_letter(j)].width = 14
    wb.save(path)
