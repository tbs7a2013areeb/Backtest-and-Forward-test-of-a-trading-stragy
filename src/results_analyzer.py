"""Work with the result tables and charts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import DEFAULT_MA_WINDOW, INITIAL_CASH, OUTPUT_DIR


@dataclass
class ResultsAnalyzer:
    """Print and save the results."""

    output_dir: Path = OUTPUT_DIR
    initial_cash: float = INITIAL_CASH

    METRIC_KEYS = [
        "Equity Final [$]",
        "Return [%]",
        "Buy & Hold Return [%]",
        "Win Rate [%]",
        "# Trades",
        "Max. Drawdown [%]",
        "Sharpe Ratio",
        "Sortino Ratio",
        "Profit Factor",
        "Avg. Trade [%]",
        "Best Trade [%]",
        "Worst Trade [%]",
        "Exposure Time [%]",
    ]

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def print_metrics(self, stats: pd.Series, title: str = "Backtest Results") -> None:
        """Print the main metrics."""
        print(f"\n{title}")
        print("=" * len(title))
        for key in self.METRIC_KEYS:
            value = stats.get(key, "N/A")
            print(f"{key:24} {self._format_value(value)}")

    def save_backtest_outputs(
        self,
        stats: pd.Series,
        data: pd.DataFrame,
        prefix: str = "normal_backtest",
        moving_average_window: int = DEFAULT_MA_WINDOW,
    ) -> dict[str, Path]:
        """Save the tables and charts."""
        saved_paths: dict[str, Path] = {}

        metrics_path = self.output_dir / f"{prefix}_metrics.csv"
        self._metrics_table(stats).to_csv(metrics_path)
        saved_paths["metrics"] = metrics_path

        equity_curve = self._get_frame(stats, "_equity_curve")
        if equity_curve is not None:
            equity_path = self.output_dir / f"{prefix}_equity_curve.csv"
            equity_curve.to_csv(equity_path)
            saved_paths["equity_curve"] = equity_path

            equity_chart = self.plot_equity_curve(equity_curve, prefix)
            if equity_chart:
                saved_paths["equity_chart"] = equity_chart

            drawdown_chart = self.plot_drawdown_curve(equity_curve, prefix)
            if drawdown_chart:
                saved_paths["drawdown_chart"] = drawdown_chart

        trades = self._get_frame(stats, "_trades")
        if trades is not None:
            trades_path = self.output_dir / f"{prefix}_trades.csv"
            trades.to_csv(trades_path, index=False)
            saved_paths["trades"] = trades_path

            signal_chart = self.plot_price_with_signals(
                data=data,
                trades=trades,
                prefix=prefix,
                moving_average_window=moving_average_window,
            )
            if signal_chart:
                saved_paths["signals_chart"] = signal_chart

        return saved_paths

    def plot_equity_curve(self, equity_curve: pd.DataFrame, prefix: str) -> Optional[Path]:
        """Save the equity curve chart."""
        if "Equity" not in equity_curve.columns:
            return None

        path = self.output_dir / f"{prefix}_equity_curve.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(equity_curve.index, equity_curve["Equity"], color="#1f77b4", linewidth=1.8)
        ax.set_title("Equity Curve")
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity [$]")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def plot_drawdown_curve(self, equity_curve: pd.DataFrame, prefix: str) -> Optional[Path]:
        """Save the drawdown chart."""
        drawdown = self._drawdown_series(equity_curve)
        if drawdown is None:
            return None

        path = self.output_dir / f"{prefix}_drawdown_curve.png"
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.fill_between(drawdown.index, drawdown, 0, color="#d62728", alpha=0.35)
        ax.plot(drawdown.index, drawdown, color="#d62728", linewidth=1.2)
        ax.set_title("Drawdown Curve")
        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown [%]")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def plot_price_with_signals(
        self,
        data: pd.DataFrame,
        trades: pd.DataFrame,
        prefix: str,
        moving_average_window: int,
    ) -> Optional[Path]:
        """Save the price chart with buy and sell marks."""
        if data.empty or "Close" not in data.columns:
            return None

        path = self.output_dir / f"{prefix}_price_signals.png"
        close = data["Close"]
        moving_average = close.rolling(
            window=int(moving_average_window),
            min_periods=int(moving_average_window),
        ).mean()

        fig, ax = plt.subplots(figsize=(14, 7))
        ax.plot(data.index, close, color="#1f77b4", label="Close", linewidth=1.2)
        ax.plot(
            data.index,
            moving_average,
            color="#ff7f0e",
            label=f"SMA {moving_average_window}",
            linewidth=1.2,
        )

        if not trades.empty:
            entry_times = pd.to_datetime(trades.get("EntryTime", pd.Series(dtype="datetime64[ns]")))
            exit_times = pd.to_datetime(trades.get("ExitTime", pd.Series(dtype="datetime64[ns]")))
            entry_prices = pd.to_numeric(trades.get("EntryPrice", pd.Series(dtype=float)), errors="coerce")
            exit_prices = pd.to_numeric(trades.get("ExitPrice", pd.Series(dtype=float)), errors="coerce")

            ax.scatter(
                entry_times,
                entry_prices,
                marker="^",
                color="#2ca02c",
                s=70,
                label="Buy",
                zorder=5,
            )
            ax.scatter(
                exit_times,
                exit_prices,
                marker="v",
                color="#d62728",
                s=70,
                label="Sell",
                zorder=5,
            )

        ax.set_title("Price With Buy/Sell Signals")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price [$]")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path

    def print_walk_forward_summary(self, summary: pd.DataFrame) -> None:
        """Print the walk forward table."""
        print("\nWalk-Forward Results")
        print("====================")
        if summary.empty:
            print("No valid walk-forward periods were produced.")
            return
        display_columns = [
            "reference_start",
            "reference_end",
            "testing_start",
            "testing_end",
            "moving_average_window",
            "test_return_pct",
            "win_rate_pct",
            "max_drawdown_pct",
            "num_trades",
            "final_equity",
        ]
        available_columns = [column for column in display_columns if column in summary.columns]
        print(summary.loc[:, available_columns].to_string(index=False))

    def print_comparison(self, normal_stats: pd.Series, walk_forward_summary: pd.DataFrame) -> None:
        """Print the backtest vs walk forward comparison."""
        print("\nNormal Backtest vs Walk-Forward")
        print("===============================")

        normal_return = self._to_float(normal_stats.get("Return [%]"))
        normal_final_equity = self._to_float(normal_stats.get("Equity Final [$]"))

        if walk_forward_summary.empty:
            print("Walk-forward results were empty, so no comparison is available.")
            return

        compounded_return = self._compound_period_returns(
            walk_forward_summary["test_return_pct"].dropna()
        )
        average_period_return = walk_forward_summary["test_return_pct"].mean()
        positive_period_rate = (
            (walk_forward_summary["test_return_pct"] > 0).mean() * 100
            if "test_return_pct" in walk_forward_summary
            else np.nan
        )

        print(f"Normal backtest return:       {normal_return:.2f}%")
        print(f"Normal final equity:          ${normal_final_equity:,.2f}")
        print(f"Walk-forward compounded OOS:  {compounded_return:.2f}%")
        print(f"Average OOS period return:    {average_period_return:.2f}%")
        print(f"Positive OOS periods:         {positive_period_rate:.2f}%")

    def save_comparison(self, normal_stats: pd.Series, walk_forward_summary: pd.DataFrame) -> Path:
        """Save the comparison values."""
        path = self.output_dir / "comparison_summary.csv"
        normal_return = self._to_float(normal_stats.get("Return [%]"))
        compounded_return = (
            self._compound_period_returns(walk_forward_summary["test_return_pct"].dropna())
            if not walk_forward_summary.empty
            else np.nan
        )
        comparison = pd.DataFrame(
            [
                {"metric": "normal_backtest_return_pct", "value": normal_return},
                {"metric": "walk_forward_compounded_oos_return_pct", "value": compounded_return},
                {
                    "metric": "walk_forward_average_period_return_pct",
                    "value": walk_forward_summary["test_return_pct"].mean()
                    if not walk_forward_summary.empty
                    else np.nan,
                },
            ]
        )
        comparison.to_csv(path, index=False)
        return path

    def _metrics_table(self, stats: pd.Series) -> pd.DataFrame:
        """Turn the metrics into a CSV table."""
        rows = []
        for key in stats.index:
            if str(key).startswith("_"):
                continue
            rows.append({"metric": key, "value": self._format_value(stats[key])})
        return pd.DataFrame(rows).set_index("metric")

    def _get_frame(self, stats: pd.Series, key: str) -> Optional[pd.DataFrame]:
        value = stats.get(key)
        return value.copy() if isinstance(value, pd.DataFrame) else None

    def _drawdown_series(self, equity_curve: pd.DataFrame) -> Optional[pd.Series]:
        if "DrawdownPct" in equity_curve.columns:
            drawdown = pd.to_numeric(equity_curve["DrawdownPct"], errors="coerce").fillna(0)
            if drawdown.abs().max() <= 1.5:
                drawdown = drawdown * 100
            return -drawdown.abs()
        if "Equity" in equity_curve.columns:
            equity = pd.to_numeric(equity_curve["Equity"], errors="coerce").dropna()
            return (equity / equity.cummax() - 1.0) * 100
        return None

    def _format_value(self, value: object) -> str:
        if isinstance(value, float):
            return f"{value:,.4f}"
        if isinstance(value, (int, np.integer)):
            return f"{int(value):,}"
        return str(value)

    def _to_float(self, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return np.nan

    def _compound_period_returns(self, returns_pct: Iterable[float]) -> float:
        returns = pd.Series(list(returns_pct), dtype=float).dropna()
        if returns.empty:
            return np.nan
        return (float((1 + returns / 100).prod()) - 1.0) * 100
