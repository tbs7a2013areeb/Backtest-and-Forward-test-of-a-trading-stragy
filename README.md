# Trading Backtester

This Python project evaluates a long only Apple stock trading strategy. It uses
daily AAPL price data, runs a full historical backtest, saves the results, and
then applies a walk forward out of sample test.

This repository is a demo project.

The project uses `backtesting.py`, `yfinance`, `pandas`, `numpy`, and
`matplotlib`.

## Files

```text
.
├── main.py
├── requirements.txt
├── README.md
├── output/
└── src/
    ├── __init__.py
    ├── backtest_runner.py
    ├── config.py
    ├── data_loader.py
    ├── results_analyzer.py
    ├── strategies.py
    └── walk_forward_tester.py
```

## Install

Run this from the project folder:

```bash
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 main.py
```

The script downloads AAPL daily data from 2014 until the latest available date.
It runs the full backtest, runs the walk forward out of sample test, prints the
results, and saves charts and tables in `output/`.

## Settings

Most settings are in `src/config.py`.

1. Ticker symbol is `TICKER = "AAPL"`.
2. Initial capital is `INITIAL_CASH = 10_000`.
3. Commission rate is `COMMISSION_RATE = 0.0008`.
4. Minimum commission per order is `MIN_COMMISSION = 1.00`.
5. Default SMA window is `DEFAULT_MA_WINDOW = 200`.
6. In sample reference window is `TRAINING_WINDOW_YEARS = 3`.
7. Out of sample test window is `TESTING_WINDOW_YEARS = 1`.
8. Data timeframe is `TIMEFRAME = "1d"`.

The commission rule is:

```python
commission = max(1.00, abs(order_size) * price * 0.0008)
```

This means each entry and exit pays the larger value between 0.08 percent of
the trade value and 1 USD.

## Strategy

The default strategy is in `src/strategies.py`.

The strategy is a long only SMA crossover system using a fixed 200 day simple
moving average. The 200 day SMA is the average closing price over the last 200
trading days and is used as a trend filter. When AAPL trades above this
average, the trend is treated as stronger. When it trades below this average,
the trend is treated as weaker. The strategy does not use short selling.

1. Enter a long position when there is no open trade and price crosses above the SMA.
2. If the first valid bar is already above the SMA, the strategy can enter once.
3. Exit the position when price crosses below the SMA.
4. Avoid duplicate entries while an active position is already open.

## Backtest

The full backtest evaluates the strategy on the complete AAPL history in the
dataset. This provides the total return, trade count, drawdown, transaction
cost impact, and equity curve.

A single full historical backtest can be influenced by specific market regimes.
The walk forward test below checks whether performance is more consistent
across separate out of sample periods.

## Walk Forward Test

The walk forward test splits the dataset into rolling in sample reference
periods and out of sample test periods. In this project, the in sample period is
used as prior price history for the 200 day SMA, not for parameter selection.

The rolling split is:

1. Use 3 years as the in sample reference period.
2. Use the next 1 year as the out of sample test period.
3. Move the window forward by 1 year and repeat.

Example:

```text
2014 to 2016 is the in sample period, then 2017 is tested out of sample.
2015 to 2017 is the in sample period, then 2018 is tested out of sample.
2016 to 2018 is the in sample period, then 2019 is tested out of sample.
```

The same fixed 200 day SMA is used in every out of sample period. This checks
whether the original strategy rule is stable across time without selecting
parameters again from each reference period.

Walk forward optimization is different. It would test several possible SMA
windows inside each in sample period, choose the best performing window, and
then test that selected parameter on the next out of sample year.

The difference is:

```text
Walk forward test:
Uses the same fixed parameter in every test period.

Walk forward optimization:
Selects the best parameter from the in sample period, then tests that selected
parameter out of sample.
```

## Main Metrics

The project prints and saves these results:

1. Final equity
2. Total return
3. Buy and hold return
4. Win rate
5. Number of trades
6. Max drawdown
7. Sharpe ratio
8. Sortino ratio
9. Profit factor
10. Average trade
11. Best trade
12. Worst trade
13. Exposure time

The detailed equity curve and trade list are also saved in `output/`.

## Output

The `output/` folder contains the result CSV files, charts, and the built in
HTML plot from `backtesting.py`.

This project is for research and demonstration only. It is not investment
advice.
