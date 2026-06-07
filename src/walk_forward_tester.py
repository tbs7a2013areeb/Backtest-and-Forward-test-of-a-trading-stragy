"""Walk forward testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from backtesting import Strategy

from .backtest_runner import BacktestRunner
from .config import (
    DEFAULT_MA_WINDOW,
    INITIAL_CASH,
    OUTPUT_DIR,
    TESTING_WINDOW_YEARS,
    TRAINING_WINDOW_YEARS,
    WALK_FORWARD_OPTIMIZATION_WINDOWS,
)
from .strategies import MovingAverageCrossStrategy


@dataclass
class WalkForwardResult:
    """Holds the walk forward results."""

    summary: pd.DataFrame
    combined_equity_curve: pd.DataFrame


@dataclass
class WalkForwardTester:
    """Runs the rolling test periods."""

    data: pd.DataFrame
    strategy: Type[Strategy] = MovingAverageCrossStrategy
    moving_average_window: int = DEFAULT_MA_WINDOW
    optimization_windows: tuple[int, ...] = WALK_FORWARD_OPTIMIZATION_WINDOWS
    training_window_years: int = TRAINING_WINDOW_YEARS
    testing_window_years: int = TESTING_WINDOW_YEARS
    initial_cash: float = INITIAL_CASH
    output_dir: Path = OUTPUT_DIR

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.optimization_windows = tuple(
            sorted(
                {
                    int(window)
                    for window in self.optimization_windows
                    if 1 < int(window) < int(self.moving_average_window)
                }
            )
        )
        if not self.optimization_windows:
            raise ValueError("Add at least one optimization window below the default MA.")

    def run(self) -> WalkForwardResult:
        """Run all walk forward periods."""
        rows: list[dict[str, object]] = []
        combined_segments: list[pd.Series] = []
        combined_start_equity = float(self.initial_cash)

        for reference_start, reference_end, testing_start, testing_end in self._periods():
            reference_data = self.data.loc[
                (self.data.index >= reference_start) & (self.data.index < reference_end)
            ]
            testing_data = self.data.loc[
                (self.data.index >= testing_start) & (self.data.index < testing_end)
            ]
            period_data = self.data.loc[
                (self.data.index >= reference_start) & (self.data.index < testing_end)
            ]

            if self._should_skip(reference_data, testing_data, period_data):
                continue

            best_window, training_return_pct = self._best_window(reference_data)
            if best_window is None:
                continue

            runner = BacktestRunner(
                data=period_data,
                strategy=self.strategy,
                initial_cash=self.initial_cash,
            )
            stats = runner.run(
                moving_average_window=best_window,
                start_trading_at=testing_data.index.min(),
            )
            equity_curve = stats.get("_equity_curve")
            trades = stats.get("_trades")

            if not isinstance(equity_curve, pd.DataFrame) or "Equity" not in equity_curve:
                continue

            test_equity = equity_curve.loc[
                (equity_curve.index >= testing_data.index.min())
                & (equity_curve.index <= testing_data.index.max()),
                "Equity",
            ].dropna()
            if len(test_equity) < 2:
                continue

            normalized_equity = test_equity / float(test_equity.iloc[0])
            scaled_equity = normalized_equity * combined_start_equity
            combined_start_equity = float(scaled_equity.iloc[-1])
            combined_segments.append(scaled_equity)

            test_trades = self._test_period_trades(
                trades,
                testing_start=testing_data.index.min(),
                testing_end=testing_data.index.max(),
            )

            test_return_pct = (float(test_equity.iloc[-1]) / float(test_equity.iloc[0]) - 1.0) * 100
            rows.append(
                {
                    "reference_start": reference_data.index.min().date().isoformat(),
                    "reference_end": reference_data.index.max().date().isoformat(),
                    "testing_start": testing_data.index.min().date().isoformat(),
                    "testing_end": testing_data.index.max().date().isoformat(),
                    "moving_average_window": int(best_window),
                    "training_return_pct": training_return_pct,
                    "test_return_pct": test_return_pct,
                    "win_rate_pct": self._win_rate(test_trades),
                    "max_drawdown_pct": self._max_drawdown_pct(test_equity),
                    "num_trades": int(len(test_trades)),
                    "final_equity": float(self.initial_cash) * (1.0 + test_return_pct / 100.0),
                }
            )

        summary = pd.DataFrame(rows)
        combined_equity_curve = self._combine_equity_segments(combined_segments)
        self._save_outputs(summary, combined_equity_curve)
        return WalkForwardResult(summary=summary, combined_equity_curve=combined_equity_curve)

    def _periods(self) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
        """Make the rolling date windows."""
        periods: list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]] = []
        current_start = pd.Timestamp(self.data.index.min()).normalize()
        final_date = pd.Timestamp(self.data.index.max()).normalize()

        while True:
            reference_start = current_start
            reference_end = reference_start + pd.DateOffset(years=int(self.training_window_years))
            testing_start = reference_end
            testing_end = testing_start + pd.DateOffset(years=int(self.testing_window_years))

            if testing_start >= final_date:
                break

            periods.append((reference_start, reference_end, testing_start, testing_end))
            current_start = current_start + pd.DateOffset(years=int(self.testing_window_years))

        return periods

    def _should_skip(
        self,
        reference_data: pd.DataFrame,
        testing_data: pd.DataFrame,
        period_data: pd.DataFrame,
    ) -> bool:
        """Skip periods that do not have enough data."""
        if reference_data.empty or testing_data.empty or period_data.empty:
            return True
        if len(reference_data) < max(self.optimization_windows):
            return True
        if len(testing_data) < min(self.optimization_windows):
            return True
        if len(period_data) < max(self.optimization_windows) + 2:
            return True
        return False

    def _best_window(self, reference_data: pd.DataFrame) -> tuple[Optional[int], float]:
        """Choose the best MA from the reference period."""
        best_window: Optional[int] = None
        best_return = -np.inf

        for window in self.optimization_windows:
            if len(reference_data) < int(window) + 2:
                continue

            runner = BacktestRunner(
                data=reference_data,
                strategy=self.strategy,
                initial_cash=self.initial_cash,
            )
            try:
                stats = runner.run(moving_average_window=int(window))
            except Exception:
                continue

            training_return = self._to_float(stats.get("Return [%]"))
            if np.isnan(training_return):
                continue

            is_better = training_return > best_return
            is_tie_with_higher_window = (
                np.isclose(training_return, best_return)
                and best_window is not None
                and int(window) > int(best_window)
            )
            if is_better or is_tie_with_higher_window:
                best_window = int(window)
                best_return = float(training_return)

        return best_window, best_return

    def _test_period_trades(
        self,
        trades: object,
        testing_start: pd.Timestamp,
        testing_end: pd.Timestamp,
    ) -> pd.DataFrame:
        """Get trades that closed in the test period."""
        if not isinstance(trades, pd.DataFrame) or trades.empty or "ExitTime" not in trades:
            return pd.DataFrame()

        filtered = trades.copy()
        filtered["ExitTime"] = pd.to_datetime(filtered["ExitTime"], errors="coerce")
        return filtered.loc[
            (filtered["ExitTime"] >= testing_start) & (filtered["ExitTime"] <= testing_end)
        ]

    def _win_rate(self, trades: pd.DataFrame) -> float:
        if trades.empty:
            return np.nan
        if "PnL" in trades.columns:
            return float((pd.to_numeric(trades["PnL"], errors="coerce") > 0).mean() * 100)
        if "ReturnPct" in trades.columns:
            return float((pd.to_numeric(trades["ReturnPct"], errors="coerce") > 0).mean() * 100)
        return np.nan

    def _max_drawdown_pct(self, equity: pd.Series) -> float:
        if equity.empty:
            return np.nan
        drawdown = equity / equity.cummax() - 1.0
        return float(drawdown.min() * 100)

    def _to_float(self, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return np.nan

    def _combine_equity_segments(self, segments: list[pd.Series]) -> pd.DataFrame:
        if not segments:
            return pd.DataFrame(columns=["Equity"])

        cleaned_segments: list[pd.Series] = []
        last_index: Optional[pd.Timestamp] = None
        for segment in segments:
            cleaned = segment.copy()
            if last_index is not None:
                cleaned = cleaned.loc[cleaned.index > last_index]
            if cleaned.empty:
                continue
            last_index = cleaned.index.max()
            cleaned_segments.append(cleaned)

        if not cleaned_segments:
            return pd.DataFrame(columns=["Equity"])

        combined = pd.concat(cleaned_segments).sort_index()
        return combined.to_frame(name="Equity")

    def _save_outputs(self, summary: pd.DataFrame, combined_equity_curve: pd.DataFrame) -> None:
        summary_path = self.output_dir / "walk_forward_summary.csv"
        summary.to_csv(summary_path, index=False)

        equity_path = self.output_dir / "walk_forward_combined_equity_curve.csv"
        combined_equity_curve.to_csv(equity_path)

        if combined_equity_curve.empty or "Equity" not in combined_equity_curve:
            return

        chart_path = self.output_dir / "walk_forward_combined_equity_curve.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            combined_equity_curve.index,
            combined_equity_curve["Equity"],
            color="#9467bd",
            linewidth=1.8,
        )
        ax.set_title("Walk forward optimization")
        ax.set_xlabel("Date")
        ax.set_ylabel("Scaled Equity [$]")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(chart_path, dpi=150)
        plt.close(fig)
