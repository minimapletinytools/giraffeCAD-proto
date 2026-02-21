.PHONY: help setup test test-verbose test-cov typecheck typecheck-watch clean

help:
	@echo "🦒 GiraffeCAD Development Commands"
	@echo "=================================="
	@echo ""
	@echo "  make setup           - Setup development environment (create venv and install deps)"
	@echo "  make test            - Run all tests"
	@echo "  make test-verbose    - Run tests with verbose output"
	@echo "  make test-cov        - Run tests with coverage report"
	@echo "  make typecheck       - Run type checking with ty"
	@echo "  make typecheck-watch - Run type checking in watch mode"
	@echo "  make clean           - Remove build artifacts and cache files"
	@echo ""

setup:
	@./setup_dev.sh

test:
	@echo "Running tests..."
	@uv run python -m pytest tests/

test-verbose:
	@echo "Running tests (verbose)..."
	@uv run python -m pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	@uv run python -m pytest tests/ --cov=code_goes_here --cov-report=html
	@echo ""
	@echo "✅ Coverage report generated in htmlcov/index.html"

typecheck:
	@echo "Running type checks..."
	@if command -v uv >/dev/null 2>&1; then \
		uv run ty check; \
	elif command -v ty >/dev/null 2>&1; then \
		ty check; \
	else \
		echo "❌ Error: ty is not installed."; \
		echo ""; \
		echo "To install with uv (recommended):"; \
		echo "  uv add --dev ty"; \
		echo ""; \
		echo "Or install globally:"; \
		echo "  curl -LsSf https://astral.sh/ty/install.sh | sh"; \
		exit 1; \
	fi
	@echo ""
	@echo "✅ Type checking complete"

typecheck-watch:
	@echo "Running type checks in watch mode..."
	@echo "Press Ctrl+C to stop"
	@if command -v uv >/dev/null 2>&1; then \
		uv run ty check --watch; \
	elif command -v ty >/dev/null 2>&1; then \
		ty check --watch; \
	else \
		echo "❌ Error: ty is not installed."; \
		echo ""; \
		echo "To install with uv (recommended):"; \
		echo "  uv add --dev ty"; \
		exit 1; \
	fi

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage
	@echo "✅ Clean complete"

