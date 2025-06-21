import logging
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from analyzer import CryptoAnalyzer
from config import config
from data_collector import BinanceDataCollector
from database import get_db_session, get_latest_price, get_symbols, init_db

console = Console()

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_symbol_list(symbols: str | None) -> list[str]:
    """Get list of symbols from argument or database."""
    if symbols:
        return [s.strip() for s in symbols.split(",")]

    with get_db_session() as db:
        return get_symbols(db)


def get_date_range(days: int) -> tuple[datetime, datetime]:
    """Get start and end dates for analysis."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    config.create_directories()


@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)")
@click.option("--days", "-d", default=30, help="Number of days of historical data to fetch")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for data (1m, 5m, 15m, 1h, 4h, 1d)")
def collect(symbols: str, days: int, timeframe: str):
    with console.status("[bold green]Initializing database..."):
        init_db()

    symbol_list = get_symbol_list(symbols) if symbols else config.DEFAULT_SYMBOLS

    console.print(f"[bold blue]Collecting data for {len(symbol_list)} symbols...")
    console.print(f"Symbols: {', '.join(symbol_list)}")
    console.print(f"Timeframe: {timeframe}")
    console.print(f"Days: {days}")

    try:
        collector = BinanceDataCollector()
    except Exception as e:
        console.print(f"[bold red]Failed to connect to Binance: {e}")
        return

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Collecting data...", total=len(symbol_list))

        for symbol in symbol_list:
            progress.update(task, description=f"Processing {symbol}...")

            try:
                df = collector.fetch_historical_data(symbol, timeframe, days)
                if df.empty:
                    console.print(f"[yellow]No data found for {symbol}")
                    continue

                collector.save_to_database(symbol, df, timeframe)
                console.print(f"[green]✓ Collected {len(df)} records for {symbol}")

            except Exception as e:
                console.print(f"[red]✗ Error processing {symbol}: {e}")

            progress.advance(task)

    console.print("[bold green]Data collection completed!")


@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols to analyze")
@click.option("--days", "-d", default=30, help="Number of days to analyze")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for analysis")
def analyze(symbols: str, days: int, timeframe: str):
    symbol_list = get_symbol_list(symbols)

    if not symbol_list:
        console.print("[yellow]No symbols found in database. Run 'collect' first.")
        return

    console.print(f"[bold blue]Analyzing data for {len(symbol_list)} symbols...")

    analyzer = CryptoAnalyzer()
    start_date, end_date = get_date_range(days)

    console.print("\n[bold]Summary Statistics:[/bold]")
    stats_table = Table(title="Cryptocurrency Performance Summary")
    stats_table.add_column("Symbol", style="cyan")
    stats_table.add_column("Current Price", style="green")
    stats_table.add_column("Total Change %", style="yellow")
    stats_table.add_column("Volatility %", style="red")
    stats_table.add_column("Volume", style="blue")

    for symbol in symbol_list:
        stats = analyzer.generate_summary_statistics(symbol, start_date, end_date, timeframe)
        if stats:
            stats_table.add_row(
                symbol,
                f"${stats['latest_price']:,.2f}",
                f"{stats['price_change_pct']:+.2f}%",
                f"{stats['volatility']:.2f}%",
                f"{stats['24h_volume']:,.0f}",
            )

    console.print(stats_table)

    console.print("\n[bold]Performance Comparison:[/bold]")
    comparison_df = analyzer.compare_symbols(symbol_list, start_date, end_date, timeframe)

    if not comparison_df.empty:
        comparison_df = comparison_df.sort_values("price_change_pct", ascending=False)
        comp_table = Table(title="Performance Ranking")
        comp_table.add_column("Rank", style="cyan")
        comp_table.add_column("Symbol", style="cyan")
        comp_table.add_column("Total Change %", style="yellow")
        comp_table.add_column("Volatility %", style="red")
        comp_table.add_column("Avg Volume", style="blue")

        for i, (symbol, row) in enumerate(comparison_df.iterrows(), 1):
            comp_table.add_row(
                str(i),
                symbol,
                f"{row['price_change_pct']:+.2f}%",
                f"{row['volatility']:.2f}%",
                f"{row['24h_volume']:,.0f}",
            )

        console.print(comp_table)


@cli.command()
@click.option("--symbol", "-s", required=True, help="Symbol to chart (e.g., BTC/USDT)")
@click.option("--days", "-d", default=30, help="Number of days to chart")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for chart")
@click.option("--save", help="Save chart to file (e.g., chart.html)")
@click.option("--no-indicators", is_flag=True, help="Exclude technical indicators")
def chart(symbol: str, days: int, timeframe: str, save: str, no_indicators: bool):
    console.print(f"[bold blue]Generating chart for {symbol}...")

    analyzer = CryptoAnalyzer()
    start_date, end_date = get_date_range(days)

    try:
        analyzer.plot_price_chart(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            include_indicators=not no_indicators,
            save_path=save,
        )

        if save:
            console.print(f"[green]Chart saved to {save}")
        else:
            console.print("[green]Chart displayed in browser")

    except Exception as e:
        console.print(f"[red]Error generating chart: {e}")


@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols for correlation")
@click.option("--days", "-d", default=30, help="Number of days for correlation analysis")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for analysis")
@click.option("--save", help="Save correlation heatmap to file (e.g., correlation.html)")
def correlation(symbols: str, days: int, timeframe: str, save: str):
    symbol_list = get_symbol_list(symbols)

    if not symbol_list:
        console.print("[yellow]No symbols found in database for correlation. Run 'collect' first.")
        return

    console.print(f"[bold blue]Generating correlation heatmap for {len(symbol_list)} symbols...")

    analyzer = CryptoAnalyzer()
    start_date, end_date = get_date_range(days)

    try:
        analyzer.plot_correlation_heatmap(
            symbols=symbol_list,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            save_path=save,
        )

        if save:
            console.print(f"[green]Correlation heatmap saved to {save}")
        else:
            console.print("[green]Correlation heatmap displayed")

    except Exception as e:
        console.print(f"[red]Error generating correlation heatmap: {e}")


@cli.command()
def status():
    console.print("[bold blue]Application Status[/bold blue]")

    try:
        with get_db_session() as db:
            symbols_in_db = get_symbols(db)

        status_panel = Panel(
            f"Symbols in database: {len(symbols_in_db)}\n"
            f"Default symbols: {', '.join(config.DEFAULT_SYMBOLS)}\n"
            f"Data directory: {config.DATA_DIR}\n"
            f"Cache directory: {config.CACHE_DIR}",
            title="Database and Configuration",
            border_style="green",
        )
        console.print(status_panel)

        if symbols_in_db:
            console.print("\n[bold]Latest Data in DB:[/bold]")
            latest_prices_table = Table(title="Latest Prices")
            latest_prices_table.add_column("Symbol", style="cyan")
            latest_prices_table.add_column("Latest Timestamp", style="green")

            with get_db_session() as db:
                for symbol in symbols_in_db:
                    latest_price = get_latest_price(db, symbol)
                    if latest_price:
                        latest_prices_table.add_row(symbol, str(latest_price.timestamp))

            console.print(latest_prices_table)

    except Exception as e:
        console.print(f"[red]Error checking status: {e}")


@cli.command()
def setup():
    console.print("[bold blue]Setting up Crypto Data Analysis Tool...[/bold blue]")

    config.create_directories()
    console.print("[green]✓ Created data directories")

    try:
        init_db()
        console.print("[green]✓ Database initialized")
    except Exception as e:
        console.print(f"[red]✗ Database initialization failed: {e}")
        return

    try:
        BinanceDataCollector()
        console.print("[green]✓ Binance connection successful")
    except Exception as e:
        console.print(f"[yellow]⚠ Binance connection failed: {e}")
        console.print("[yellow]You can still use the tool with limited functionality")

    console.print("\n[bold green]Setup completed![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Run 'python main.py collect' to download data")
    console.print("2. Run 'python main.py analyze' to analyze trends")
    console.print("3. Run 'python main.py chart --symbol BTC/USDT' to generate charts")


if __name__ == "__main__":
    cli()
