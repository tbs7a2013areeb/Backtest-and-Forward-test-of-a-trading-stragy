# Trading Backtester

This is my Python project for testing a simple Apple stock trading strategy.
It downloads AAPL price data, runs a normal backtest, saves the results, and
then checks the same strategy with a walk forward test.

This is just a demo project.

The normal backtest uses the 200 day moving average. The walk forward test
chooses the best moving average under 200 days for each test period. The rule
buys AAPL when the price moves above the moving average and closes the position
when the price moves below it.

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
It runs the backtest, runs the walk forward test, prints the results, and saves
charts and tables in `output/`.

## Settings

Most settings are in `src/config.py`.

1. Ticker is `TICKER = "AAPL"`.
2. Starting cash is `INITIAL_CASH = 10_000`.
3. Commission rate is `COMMISSION_RATE = 0.0008`.
4. Minimum commission is `MIN_COMMISSION = 1.00`.
5. Moving average window is `DEFAULT_MA_WINDOW = 200`.
6. Walk forward optimization windows are `120, 140, 160, 180, 190`.
7. Reference window is `TRAINING_WINDOW_YEARS = 3`.
8. Test window is `TESTING_WINDOW_YEARS = 1`.
9. Timeframe is `TIMEFRAME = "1d"`.

The commission rule is:

```python
commission = max(1.00, abs(order_size) * price * 0.0008)
```

So every buy and every close pays the larger value between 0.08 percent of the
trade value and 1 USD.

## Strategy

The default strategy is in `src/strategies.py`.

It only trades long positions. It does not short sell.

1. Buy when there is no open position and price crosses above the 200 day moving average.
2. If the first usable bar is already above the moving average, it can buy once.
3. Close the position when price crosses below the moving average.
4. Do not buy again while a position is already open.

## Backtest

The normal backtest runs the strategy on the full AAPL history in the dataset.
This is useful because it shows the full result, the trade count, drawdown,
commission, and equity curve.

However, a backtest alone is not enough because results can be influenced by a
few strong years or overfitting to past data. To reduce this risk, the project
also uses a walk forward test to check performance across different time
periods.

## Walk Forward Test

The walk forward test is used because one normal backtest can look strong
because of a few good years. It can also fit too closely to old data. The walk
forward test gives a more realistic check by testing the strategy on the next
period after only using data from the past.

The dataset is split into rolling parts:

1. Use 3 years as the reference period.
2. Use the next 1 year as the test period.
3. Move the window forward by 1 year and repeat.

Example:

```text
2014 to 2016 is used as the reference period, then 2017 is tested.
2015 to 2017 is used as the reference period, then 2018 is tested.
2016 to 2018 is used as the reference period, then 2019 is tested.
```

In each reference period, the code optimizes the moving average window. It tests
these moving averages, all under 200 days:

```text
120, 140, 160, 180, 190
```

The moving average with the best return in the reference period is selected.
That selected moving average is then used on the next test year. This checks if
the optimized setting still works on new unseen data.

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

This project is for learning and testing. It is not investment advice.
