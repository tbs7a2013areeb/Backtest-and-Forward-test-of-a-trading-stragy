# Trading Backtester

This Python project evaluates a long only Apple stock trading strategy. It uses
daily AAPL price data, runs a full historical backtest, saves the results, and
then applies a walk forward test

This repository is a **simple, lightweight demo project** for an ultra short presentation about the concept of algorithmic trading. Readers who want to explore advanced algorithmic trading further may want to look into platforms such as MultiCharts or QuantConnect.




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
It runs the full backtest, runs the walk forward test, prints the
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
This rule is based on Saxo’s commission structure, where the commission is the greater of USD 1 or 0.08% of the total trade value. Other trading costs, such as slippage and spread, have been excluded to keep the demo simple and easy to understand.

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


Backtests are useful for evaluating how a strategy would have performed on historical data, but they have important limitations. 
A strong backtest does not guarantee strong future performance because market conditions change over time.
One major issue is overfitting. A strategy can be tuned too closely to past data, making it look profitable historically while failing in live trading.
Because of these limitations, we will use a walk forward test. Walk forward testing evaluates the strategy on unseen data after training or selecting parameters on earlier data. 
This gives a more realistic view of how the strategy may perform in live market conditions and helps reduce the risk of relying on an overfit backtest.



## Walk Forward Test

The walk forward test splits the dataset into rolling in sample and out of sample periods.

In this project, the in sample period is 3 years of previous AAPL price data. This gives the strategy enough historical context to calculate the 200 day SMA before the test period begins. 
The next 1 year is then used as the out of sample test period, where the strategy is evaluated on data it has not been tested on in that window.

The process moves forward one year at a time:

```text
2014 to 2016 is used as the in sample period, then 2017 is tested out of sample.
2015 to 2017 is used as the in sample period, then 2018 is tested out of sample.
2016 to 2018 is used as the in sample period, then 2019 is tested out of sample.
```

As this is a simple demo, I want to keep it easy to understand. That is why I have chosen to conduct only a walk forward test and not a full walk forward analysis, which would also include walk forward optimization.




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
