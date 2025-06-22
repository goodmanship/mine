#!/usr/bin/env python3

import logging
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.analyze.analyzer import CryptoAnalyzer
from src.core.app_config import config
from src.core.database import get_db_session, get_latest_price, get_symbols, init_db
from src.data.data_collector import BinanceDataCollector

console = Console()

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_symbol_list(symbols):
    """Get list of symbols from argument or database."""
    if symbols:
        return [s.strip() for s in symbols.split(",")]

    with get_db_session() as db:
        return get_symbols(db)


def get_date_range(days):
    """Get start and end dates for analysis."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option("--symbols", "-s", help="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)")
@click.option("--days", "-d", default=30, help="Number of days of historical data to fetch")
@click.option("--timeframe", "-t", default="1h", help="Timeframe for data (1m, 5m, 15m, 1h, 4h, 1d)")
def collect(symbols, days, timeframe):
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
def analyze(symbols, days, timeframe):
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
def chart(symbol, days, timeframe, save, no_indicators):
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
def correlation(symbols, days, timeframe, save):
    symbol_list = get_symbol_list(symbols)

    if not symbol_list:
        console.print("[yellow]No symbols found in database for correlation. Run 'collect' first.")
        return

    console.print(f"[bold blue]Generating correlation heatmap for {len(symbol_list)} symbols...")

    analyzer = CryptoAnalyzer()
    start_date, end_date = get_date_range(days)

    try:
        analyzer.plot_correlation_heatmap(
            symbols=symbol_list, start_date=start_date, end_date=end_date, timeframe=timeframe, save_path=save
        )

        if save:
            console.print(f"[green]Correlation heatmap saved to {save}")
        else:
            console.print("[green]Correlation heatmap displayed in browser")

    except Exception as e:
        console.print(f"[red]Error generating correlation heatmap: {e}")


@cli.command()
def status():
    console.print("[bold blue]Application Status[/bold blue]")

    with get_db_session() as db:
        symbols = get_symbols(db)

        if not symbols:
            console.print("[yellow]No data found in database. Run 'collect' first.")
            return

        console.print("[green]✓ Database connected")
        console.print(f"[green]✓ Found {len(symbols)} symbols in database")

        status_table = Table(title="Symbol Status")
        status_table.add_column("Symbol", style="cyan")
        status_table.add_column("Latest Price", style="green")
        status_table.add_column("Last Updated", style="yellow")

        for symbol in symbols[:10]:  # Show first 10 symbols
            latest = get_latest_price(db, symbol)
            if latest:
                status_table.add_row(symbol, f"${latest.close_price:,.2f}", latest.timestamp.strftime("%Y-%m-%d %H:%M"))

        console.print(status_table)

        if len(symbols) > 10:
            console.print(f"[dim]... and {len(symbols) - 10} more symbols")


@cli.command()
def setup():
    """Set up the application."""
    console.print("[bold blue]Setting up Crypto Data Analysis Tool[/bold blue]")

    with console.status("[bold green]Creating directories..."):
        try:
            config.create_directories()
            console.print("[green]✓ Directories created successfully")
        except Exception as e:
            console.print(f"[red]✗ Directory creation failed: {e}")

    with console.status("[bold green]Initializing database..."):
        try:
            init_db()
            console.print("[green]✓ Database initialized successfully")
        except Exception as e:
            console.print(f"[red]✗ Database initialization failed: {e}")

    console.print("\n[bold green]Setup completed successfully![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Run 'make collect' to gather crypto data")
    console.print("2. Run 'make chart SYMBOL=BTC/USDT' to generate charts")
    console.print("3. Run 'make analyze' to analyze the data")


if __name__ == "__main__":
    cli()
