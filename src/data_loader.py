"""Get the stock data ready."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf

from .config import END_DATE, START_DATE, TICKER, TIMEFRAME


class DataLoadError(RuntimeError):
    """Used when the stock data cannot be loaded."""


@dataclass
class DataLoader:
    """Download and clean the price data."""

    ticker: str = TICKER
    start_date: Optional[str] = START_DATE
    end_date: Optional[str] = END_DATE
    timeframe: str = TIMEFRAME

    REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

    def load(self) -> pd.DataFrame:
        """Return clean OHLCV data."""
        if not self.ticker or not self.ticker.strip():
            raise DataLoadError("Ticker cannot be empty.")

        try:
            raw_data = yf.download(
                tickers=self.ticker,
                start=self.start_date,
                end=self.end_date,
                interval=self.timeframe,
                auto_adjust=False,
                actions=False,
                progress=False,
                group_by="column",
                threads=False,
            )
        except Exception as exc:  # yfinance can fail in a few different ways.
            raise DataLoadError(f"Failed to download data for {self.ticker}: {exc}") from exc

        if raw_data.empty:
            raise DataLoadError(
                f"No data returned for {self.ticker}. Check the ticker, dates, and timeframe."
            )

        clean_data = self._clean(raw_data)
        if clean_data.empty:
            raise DataLoadError(f"Downloaded data for {self.ticker} contained no valid OHLCV rows.")

        return clean_data

    def _clean(self, data: pd.DataFrame) -> pd.DataFrame:
        """Make the yfinance data match what backtesting.py needs."""
        frame = data.copy()
        frame = self._flatten_columns(frame)

        missing = [column for column in self.REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise DataLoadError(
                f"Downloaded data is missing required columns for backtesting.py: {missing}"
            )

        frame = frame.loc[:, self.REQUIRED_COLUMNS].copy()
        frame.index = pd.to_datetime(frame.index)
        if getattr(frame.index, "tz", None) is not None:
            frame.index = frame.index.tz_localize(None)

        frame = frame.sort_index()
        frame = frame[~frame.index.duplicated(keep="last")]

        for column in self.REQUIRED_COLUMNS:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame = frame.dropna(subset=self.REQUIRED_COLUMNS)

        valid_prices = (frame[["Open", "High", "Low", "Close"]] > 0).all(axis=1)
        valid_volume = frame["Volume"] >= 0
        valid_ranges = (
            (frame["High"] >= frame["Low"])
            & (frame["High"] >= frame[["Open", "Close"]].max(axis=1))
            & (frame["Low"] <= frame[["Open", "Close"]].min(axis=1))
        )
        frame = frame.loc[valid_prices & valid_volume & valid_ranges]

        if not isinstance(frame.index, pd.DatetimeIndex):
            raise DataLoadError("Cleaned data index must be a pandas DateTimeIndex.")

        return frame

    def _flatten_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Handle yfinance columns when they come back nested."""
        frame = data.copy()
        if not isinstance(frame.columns, pd.MultiIndex):
            return frame

        ticker_upper = self.ticker.upper()
        for level in range(frame.columns.nlevels):
            values = [str(value).upper() for value in frame.columns.get_level_values(level)]
            if ticker_upper in values:
                try:
                    flattened = frame.xs(self.ticker, axis=1, level=level, drop_level=True)
                except KeyError:
                    flattened = frame.xs(ticker_upper, axis=1, level=level, drop_level=True)
                flattened.columns = [str(column) for column in flattened.columns]
                return flattened

        # If yfinance gives extra column levels, keep the OHLCV part.
        frame.columns = [
            next(
                (
                    str(part)
                    for part in column
                    if str(part) in self.REQUIRED_COLUMNS or str(part) == "Adj Close"
                ),
                "_".join(str(part) for part in column if str(part)),
            )
            for column in frame.columns
        ]
        return frame
