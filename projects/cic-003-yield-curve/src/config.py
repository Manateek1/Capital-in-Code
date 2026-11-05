"""Fixed research settings and source locations for CIC-003."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"
CHARTS_DIR = PROJECT_ROOT / "charts"
SITE_IMAGE_DIR = (
    PROJECT_ROOT.parents[1] / "site" / "public" / "images" / "cic-003"
)
SITE_SUMMARY_PATH = (
    PROJECT_ROOT.parents[1] / "site" / "src" / "cic003" / "summary.json"
)

FRED_T10Y3M_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y3M"
FRED_USREC_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=USREC"
FRED_T10Y3M_PAGE = "https://fred.stlouisfed.org/series/T10Y3M"
FRED_USREC_PAGE = "https://fred.stlouisfed.org/series/USREC"
NBER_CYCLES_PAGE = (
    "https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions"
)

PRIMARY_THRESHOLD_PERCENT = 0.0
SENSITIVITY_THRESHOLDS_PERCENT = (-0.25, 0.0, 0.25)
CONFIRMATION_MONTHS = 3
POST_EPISODE_MONTHS = 12
