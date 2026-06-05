"""Run the AAPL strategy test."""

from __future__ import annotations

from src.backtest_runner import BacktestRunner
from src.config import DEFAULT_MA_WINDOW, OUTPUT_DIR
from src.data_loader import DataLoader
from src.results_analyzer import ResultsAnalyzer
from src.walk_forward_tester import WalkForwardTester


def main() -> None:
    """Run everything in order."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loader = DataLoader()
    data = loader.load()
    print(
        f"Loaded {len(data):,} daily rows for {loader.ticker} "
        f"from {data.index.min().date()} to {data.index.max().date()}."
    )

    analyzer = ResultsAnalyzer(output_dir=OUTPUT_DIR)

    runner = BacktestRunner(data=data)
    normal_stats = runner.run(moving_average_window=DEFAULT_MA_WINDOW)
    analyzer.print_metrics(normal_stats, "Normal Backtest Results")
    analyzer.save_backtest_outputs(
        stats=normal_stats,
        data=data,
        prefix="normal_backtest",
        moving_average_window=DEFAULT_MA_WINDOW,
    )
    runner.save_builtin_plot(
        filename=OUTPUT_DIR / "normal_backtest_backtesting_plot.html",
        results=normal_stats,
        open_browser=False,
    )

    walk_forward = WalkForwardTester(data=data, moving_average_window=DEFAULT_MA_WINDOW)
    walk_forward_result = walk_forward.run()
    analyzer.print_walk_forward_summary(walk_forward_result.summary)

    analyzer.print_comparison(normal_stats, walk_forward_result.summary)
    analyzer.save_comparison(normal_stats, walk_forward_result.summary)

    print(f"\nSaved output files to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
