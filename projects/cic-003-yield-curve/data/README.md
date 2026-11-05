# CIC-003 Data Cache

The analysis downloads two public FRED CSV series into `raw/`:

- `t10y3m.csv` — daily 10-year minus 3-month Treasury constant-maturity spread.
- `usrec.csv` — monthly NBER-based recession indicator.

The raw files are ignored by Git. FRED marks these series as requiring
attribution; see the cited series pages in the [research report](../research-report.md).
Run `python -m src.main --refresh` from the project directory to replace the
local cache and rebuild the analysis outputs.
