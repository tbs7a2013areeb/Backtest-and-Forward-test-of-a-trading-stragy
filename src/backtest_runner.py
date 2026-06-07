"""Run backtesting.py from one place."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Type

import pandas as pd
from backtesting import Backtest, Strategy

from .config import (
    COMMISSION_RATE,
    DEFAULT_MA_WINDOW,
    EXCLUSIVE_ORDERS,
    FINALIZE_TRADES,
    INITIAL_CASH,
    MIN_COMMISSION,
    TRADE_ON_CLOSE,
)
from .strategies import MovingAverageCrossStrategy


class BacktestRunError(RuntimeError):
    """Used when the backtest fails."""


@dataclass
class BacktestRunner:
    """Runs the chosen strategy."""

    data: pd.DataFrame
    strategy: Type[Strategy] = MovingAverageCrossStrategy
    initial_cash: float = INITIAL_CASH
    commission_rate: float = COMMISSION_RATE
    min_commission: float = MIN_COMMISSION
    trade_on_close: bool = TRADE_ON_CLOSE
    exclusive_orders: bool = EXCLUSIVE_ORDERS
    finalize_trades: bool = FINALIZE_TRADES

    def __post_init__(self) -> None:
        self.backtest: Optional[Backtest] = None
        self.results: Optional[pd.Series] = None

    def commission_model(self) -> Callable[[int, float], float]:
        """Build the commission rule."""

        def commission(order_size: int, price: float) -> float:
            return max(
                float(self.min_commission),
                abs(int(order_size)) * float(price) * float(self.commission_rate),
            )

        return commission

    def run(
        self,
        moving_average_window: int = DEFAULT_MA_WINDOW,
        start_trading_at: object = None,
    ) -> pd.Series:
        """Run the backtest."""
        try:
            self.backtest = Backtest(
                self.data,
                self.strategy,
                cash=float(self.initial_cash),
                commission=self.commission_model(),
                trade_on_close=bool(self.trade_on_close),
                exclusive_orders=bool(self.exclusive_orders),
                finalize_trades=bool(self.finalize_trades),
            )
            self.results = self.backtest.run(
                moving_average_window=int(moving_average_window),
                start_trading_at=start_trading_at,
            )
        except Exception as exc:
            raise BacktestRunError(f"Backtest failed: {exc}") from exc

        return self.results

    def save_builtin_plot(
        self,
        filename: Path,
        results: Optional[pd.Series] = None,
        open_browser: bool = False,
    ) -> Optional[Path]:
        """Save the built in backtesting.py plot."""
        if self.backtest is None:
            raise BacktestRunError("Run the backtest before calling Backtest.plot().")

        filename.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.backtest.plot(
                results=results if results is not None else self.results,
                filename=str(filename),
                open_browser=open_browser,
            )
        except Exception as exc:
            print(f"Warning: could not save built-in backtesting.py plot: {exc}")
            return None

        return filename
