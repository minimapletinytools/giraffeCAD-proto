## Quick Start

To setup your environment, run `make setup` and run `make test` to run tests. 

## Development Setup

`make setup` or run `/.setup_dev.sh`

### Note on CAD Integrations

CAD applications ship with their own Python environments use their own Python environments. This is why dependencies are also vendored in `fusion360/libs/` for CAD environments. The venv setup does not affect CAD integrations. FreeCAD does not seem to require this.

## Running Tests

### Manual Testing

To run the test suite manually:

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run all tests
python3 -m pytest tests/ -v

# Or use the test runner script
python3 run_tests.py

# Or run specific test files
python3 -m pytest tests/test_rule.py -v

# Run with coverage
python3 -m pytest tests/ --cov=code_goes_here --cov-report=html
```

Tests flagged with # 🐪 have been hand reviewed, the rest are AI slop

## Type Checking

This project uses [ty](https://docs.astral.sh/ty/), an extremely fast Python type checker written in Rust by Astral (the creators of Ruff). ty is 10x-100x faster than traditional type checkers like mypy and Pyright.

📖 **See [TYPECHECK_SETUP.md](TYPECHECK_SETUP.md) for detailed setup instructions.**

### Installing ty

#### Recommended: Using uv (Easiest, Project-Managed)

If you don't have `uv` yet, install it first:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using Homebrew on macOS
brew install uv
```

Then add `ty` as a development dependency:

```bash
# Add ty to your project
uv add --dev ty

# Run ty (uv will manage the installation)
uv run ty check
```

This is the recommended approach because:
- `uv` manages ty versions per-project
- No global installation needed
- Works consistently across all team members
- Automatically handles updates

### Running Type Checking

Use these `make` commands:

```bash
make typecheck        # Run type checking on all files
make typecheck-watch  # Run type checking in watch mode (auto-checks on file changes)
```

or manually:

```bash
# If using uv (recommended)
uv run ty check

# If installed globally
ty check

# Check specific files or directories
uv run ty check code_goes_here/timber.py
uv run ty check code_goes_here/

# Watch mode - automatically re-checks when files change
uv run ty check --watch
```



### Cleaning Build Artifacts

To clean up Python cache files and test artifacts:

```bash
make clean

# Or manually:
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf htmlcov/ .coverage .pytest_cache/
```
