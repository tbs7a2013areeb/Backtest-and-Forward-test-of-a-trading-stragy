"""Trading strategies for this project."""

from __future__ import annotations

import numpy as np
import pandas as pd
from backtesting import Strategy

from .config import DEFAULT_MA_WINDOW


def simple_moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """Calculate the simple moving average."""
    return (
        pd.Series(values)
        .rolling(window=int(window), min_periods=int(window))
        .mean()
        .to_numpy()
    )


class MovingAverageCrossStrategy(Strategy):
    """Long only moving average strategy."""

    moving_average_window = DEFAULT_MA_WINDOW
    start_trading_at = None

    def init(self) -> None:
        """Set up the moving average."""
        self.moving_average = self.I(
            simple_moving_average,
            self.data.Close,
            self.moving_average_window,
            name=f"SMA({self.moving_average_window})",
            overlay=True,
        )
        self._is_first_tradable_bar = True

    def next(self) -> None:
        """Buy above the SMA and close below it."""
        current_close = float(self.data.Close[-1])
        current_ma = float(self.moving_average[-1])

        if np.isnan(current_ma):
            return

        if self.start_trading_at is not None:
            current_time = pd.Timestamp(self.data.index[-1])
            if current_time < pd.Timestamp(self.start_trading_at):
                return

        previous_close = float(self.data.Close[-2]) if len(self.data.Close) > 1 else np.nan
        previous_ma = float(self.moving_average[-2]) if len(self.moving_average) > 1 else np.nan

        crossed_above = (
            not np.isnan(previous_ma)
            and previous_close <= previous_ma
            and current_close > current_ma
        )
        crossed_below = (
            not np.isnan(previous_ma)
            and previous_close >= previous_ma
            and current_close < current_ma
        )
        starts_above_ma = self._is_first_tradable_bar and current_close > current_ma

        if not self.position and (starts_above_ma or crossed_above):
            self.buy()
        elif self.position and crossed_below:
            # Close the long here. self.sell() would start a short trade.
            self.position.close()

        self._is_first_tradable_bar = False
