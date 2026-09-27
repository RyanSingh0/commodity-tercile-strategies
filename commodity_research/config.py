from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # repo root
RAW_XLSX = BASE / 'data' / 'Commodities_TR_Futures.xlsx'
DTB3_CSV = BASE / 'data' / 'DTB3.csv'
CACHE = BASE / 'cache'
OUT = BASE / 'outputs'
START_POS = 252                                         # first date where a 252-session lookback exists
