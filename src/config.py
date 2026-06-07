"""Settings used by the project."""

from pathlib import Path


TICKER = "AAPL"
INITIAL_CASH = 10_000
COMMISSION_RATE = 0.0008
MIN_COMMISSION = 1.00
TRADE_ON_CLOSE = True
EXCLUSIVE_ORDERS = True
FINALIZE_TRADES = True
DEFAULT_MA_WINDOW = 200
TRAINING_WINDOW_YEARS = 3
TESTING_WINDOW_YEARS = 1
TIMEFRAME = "1d"

# Start here so we get 10+ years of daily AAPL data.
START_DATE = "2014-01-01"
END_DATE = None

OUTPUT_DIR = Path("output")
