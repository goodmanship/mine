from datetime import datetime
from typing import Any

import pandas as pd

class CryptoAnalyzer:
    def get_data_as_dataframe(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        limit: int | None = None,
    ) -> pd.DataFrame: ...
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def calculate_correlation_matrix(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> pd.DataFrame: ...
    def plot_price_chart(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        include_indicators: bool = True,
        save_path: str | None = None,
    ) -> None: ...
    def plot_correlation_heatmap(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
        save_path: str | None = None,
    ) -> None: ...
    def generate_summary_statistics(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> dict[str, Any]: ...
    def compare_symbols(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timeframe: str = "1h",
    ) -> pd.DataFrame: ...

def main() -> None: ...
