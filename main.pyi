from datetime import datetime

import click

def get_symbol_list(symbols: str | None) -> list[str]: ...
def get_date_range(days: int) -> tuple[datetime, datetime]: ...
@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool) -> None: ...
@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)")
@click.option("--days", "-d", default=30, help="Number of days of historical data to fetch")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for data (1m, 5m, 15m, 1h, 4h, 1d)")
def collect(symbols: str, days: int, timeframe: str) -> None: ...
@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols to analyze")
@click.option("--days", "-d", default=30, help="Number of days to analyze")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for analysis")
def analyze(symbols: str, days: int, timeframe: str) -> None: ...
@cli.command()
@click.option("--symbol", "-s", required=True, help="Symbol to chart (e.g., BTC/USDT)")
@click.option("--days", "-d", default=30, help="Number of days to chart")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for chart")
@click.option("--save", help="Save chart to file (e.g., chart.html)")
@click.option("--no-indicators", is_flag=True, help="Exclude technical indicators")
def chart(symbol: str, days: int, timeframe: str, save: str, no_indicators: bool) -> None: ...
@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols for correlation")
@click.option("--days", "-d", default=30, help="Number of days for correlation analysis")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for analysis")
@click.option("--save", help="Save correlation heatmap to file (e.g., correlation.html)")
def correlation(symbols: str, days: int, timeframe: str, save: str) -> None: ...
@cli.command()
def status() -> None: ...
@cli.command()
def setup() -> None: ...
