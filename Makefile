.PHONY: help setup test test-verbose test-cov clean

help:
	@echo "🦒 GiraffeCAD Development Commands"
	@echo "=================================="
	@echo ""
	@echo "  make setup        - Setup development environment (create venv and install deps)"
	@echo "  make test         - Run all tests"
	@echo "  make test-verbose - Run tests with verbose output"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make clean        - Remove build artifacts and cache files"
	@echo ""

setup:
	@./setup_dev.sh

test:
	@echo "Running tests..."
	@python3 -m pytest code_goes_here/

test-verbose:
	@echo "Running tests (verbose)..."
	@python3 -m pytest code_goes_here/ -v

test-cov:
	@echo "Running tests with coverage..."
	@python3 -m pytest code_goes_here/ --cov=code_goes_here --cov-report=html
	@echo ""
	@echo "✅ Coverage report generated in htmlcov/index.html"

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage
	@echo "✅ Clean complete"

