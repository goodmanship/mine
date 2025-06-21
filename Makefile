.PHONY: help install install-dev clean lint format check test test-cov setup collect analyze chart correlation status example

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development setup
install: ## Install production dependencies
	uv sync --no-dev

install-dev: ## Install all dependencies (including dev)
	uv sync --extra dev

clean: ## Clean up cache and temporary files
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .ty_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Code quality
lint: ## Run ruff linter
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

check: ## Run all code quality checks
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check .

fix: ## Fix code with ruff
	uv run ruff check --fix .
	uv run ruff format .

# Testing
test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=. --cov-report=html --cov-report=term-missing

# Application commands
setup: ## Initial setup for the application
	uv run python main.py setup

collect: ## Collect crypto data from Binance
	uv run python main.py collect

analyze: ## Analyze collected data
	uv run python main.py analyze

chart: ## Generate price charts (use SYMBOL=BTC/USDT to specify symbol)
	uv run python main.py chart --symbol $(or $(SYMBOL),BTC/USDT)

correlation: ## Generate correlation heatmap
	uv run python main.py correlation

status: ## Show application status
	uv run python main.py status

example: ## Run the example script
	uv run python example.py

# Data collection with options
collect-symbols: ## Collect data for specific symbols (use SYMBOLS="BTC/USDT,ETH/USDT")
	uv run python main.py collect --symbols $(SYMBOLS)

collect-days: ## Collect data for specific number of days (use DAYS=30)
	uv run python main.py collect --days $(DAYS)

collect-timeframe: ## Collect data with specific timeframe (use TIMEFRAME=1h)
	uv run python main.py collect --timeframe $(TIMEFRAME)

# Analysis with options
analyze-symbols: ## Analyze specific symbols (use SYMBOLS="BTC/USDT,ETH/USDT")
	uv run python main.py analyze --symbols $(SYMBOLS)

analyze-days: ## Analyze data for specific number of days (use DAYS=30)
	uv run python main.py analyze --days $(DAYS)

# Chart generation with options
chart-save: ## Generate and save chart (use SYMBOL=BTC/USDT SAVE=chart.html)
	uv run python main.py chart --symbol $(SYMBOL) --save $(SAVE)

chart-no-indicators: ## Generate chart without technical indicators (use SYMBOL=BTC/USDT)
	uv run python main.py chart --symbol $(SYMBOL) --no-indicators

# Database operations
db-init: ## Initialize database tables
	uv run python -c "from database import init_db; init_db()"

db-status: ## Check database connection and status
	uv run python -c "from database import get_db, get_symbols; db = next(get_db()); print(f'Symbols in DB: {get_symbols(db)}'); db.close()"

# Development workflow
dev-setup: install-dev ## Complete development setup
	@echo "Development environment setup complete!"

dev-check: lint format check test ## Run all development checks

dev-clean: clean ## Clean development artifacts

# Quick start workflow
quick-start: setup collect analyze ## Quick start: setup, collect data, and analyze

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not yet implemented"

# Release
release: ## Prepare for release
	uv run python -m build

# Environment
env-info: ## Show environment information
	@echo "Python version:"
	uv run python --version
	@echo "\nInstalled packages:"
	uv pip list

# Database setup helper
db-create: ## Create PostgreSQL database (requires createdb command)
	@echo "Creating database 'crypto_data'..."
	createdb crypto_data || echo "Database 'crypto_data' already exists or createdb not available"

# Example usage
usage: ## Show example usage commands
	@echo "Example usage:"
	@echo "  make setup                    # Initial setup"
	@echo "  make collect                  # Collect default symbols"
	@echo "  make collect-symbols SYMBOLS=\"BTC/USDT,ETH/USDT\"  # Collect specific symbols"
	@echo "  make collect-days DAYS=7      # Collect 7 days of data"
	@echo "  make analyze                  # Analyze all data"
	@echo "  make chart SYMBOL=\"BTC/USDT\"  # Generate BTC chart"
	@echo "  make chart-save SYMBOL=\"BTC/USDT\" SAVE=\"btc.html\"  # Save chart to file"
	@echo "  make correlation              # Generate correlation heatmap"
	@echo "  make status                   # Check application status" 