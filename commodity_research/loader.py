"""Reads my Bloomberg workbook once and caches it as a pickle.

The workbook has three sheets (Total Return Indices, Continuous Futures, Benchmark & Risk-Free Rates).
In each one row 4 has the tickers, row 6 the Bloomberg field names and the data starts on row 7.
"""
import pickle
import numpy as np
import pandas as pd
from .config import RAW_XLSX, DTB3_CSV, CACHE
from .universe import TR, NAME, UNIVERSES

_SHEETS = {'Total Return Indices': 'tr', 'Continuous Futures': 'fut', 'Benchmark & Risk-Free Rates': 'bench'}


def load_raw(force=False):
    CACHE.mkdir(exist_ok=True)
    pk = CACHE / 'raw.pkl'
    # reuse the pickle unless the workbook is newer than it
    if pk.exists() and not force and pk.stat().st_mtime > RAW_XLSX.stat().st_mtime:
        return pickle.load(open(pk, 'rb'))
    import openpyxl
    wb = openpyxl.load_workbook(RAW_XLSX, read_only=True, data_only=True)
    D = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        tick, fld = rows[3], rows[5]
        cols, cur = [], None
        for j, (t, f) in enumerate(zip(tick, fld)):
            if j == 0:
                cols.append('Date'); continue
            if t: cur = t                          # ticker is only written above the first field of each block
            cols.append(f"{cur}|{f}")
        df = pd.DataFrame(rows[6:], columns=cols)
        df = df[df.Date.notna()]
        df['Date'] = pd.to_datetime(df.Date)
        for c in cols[1:]:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        D[_SHEETS[ws.title]] = df.set_index('Date')
    pickle.dump(D, open(pk, 'wb'))
    return D


class Data:
    """TR index levels on one calendar, plus the BCOMTR benchmark and the T-bill rate."""
    def __init__(self, force=False):
        D = load_raw(force)
        self.raw = D
        tr = D['tr']
        px = tr[[c for c in tr if c.endswith('PX_LAST')]].copy()
        px.columns = [c.split('|')[0].replace(' Index', '') for c in px]
        r = px.pct_change()
        # days where every index is flat are exchange holidays that Bloomberg forward-filled, so I drop them
        self.joint_holidays = (r == 0).all(axis=1) & (r.index > px.index[0])
        self.PX = px[~self.joint_holidays]
        self.dates = self.PX.index
        self.BCOM = D['bench']['BCOMTR Index|PX_LAST'].reindex(self.dates)
        self.BCOM_R = self.BCOM.pct_change()
        tb = pd.read_csv(DTB3_CSV, parse_dates=['observation_date'], index_col=0)['DTB3']
        tb = pd.to_numeric(tb, errors='coerce').ffill()
        rf = tb.reindex(self.dates, method='ffill') / 100 / 252   # daily accrual
        self.RF = rf.shift(1).fillna(rf.iloc[0])                  # yesterday's rate is what I earn today

    def prices(self, keys):
        cols = [TR[k] for k in keys]
        return self.PX[cols].values, [NAME[k] for k in keys], cols
