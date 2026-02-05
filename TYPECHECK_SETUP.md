# Type Checking Setup Guide

This guide will help you set up `ty` type checking for the GiraffeCAD project using `uv`.

## Quick Start (Recommended)

### 1. Install uv (if not already installed)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS with Homebrew:**
```bash
brew install uv
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install ty as a dev dependency

```bash
uv add --dev ty
```

This will:
- Add `ty` to your `pyproject.toml` as a development dependency
- Install `ty` for use with this project
- Create/update a `uv.lock` file to lock the version

### 3. Run type checking

```bash
# Run type checks
uv run ty check

# Run with watch mode (auto-checks on file changes)
uv run ty check --watch

# Or use make commands
make typecheck
make typecheck-watch
```

## Why Use uv?

- **Project-specific versions**: Each project can use a different version of `ty`
- **Reproducible builds**: Lock file ensures consistent versions across machines
- **No global installation**: Avoids conflicts with other projects
- **Fast**: uv is extremely fast at resolving and installing packages
- **Automatic management**: uv handles installation and updates seamlessly

## Alternative: Global Installation

If you prefer a global installation (not recommended):

```bash
# Standalone installer
curl -LsSf https://astral.sh/ty/install.sh | sh

# Then run directly
ty check
```

## Integration with Development Workflow

The `Makefile` automatically detects whether you're using `uv` or a global installation:

```bash
make typecheck        # Runs: uv run ty check (if uv is available)
make typecheck-watch  # Runs: uv run ty check --watch
```

## Configuration

Type checking is configured in `pyproject.toml`:

```toml
[tool.ty]
include = ["code_goes_here"]
exclude = ["venv", "fusion360/libs", "__pycache__", ...]
```

See the [ty documentation](https://docs.astral.sh/ty/) for more configuration options.

## Troubleshooting

### "ty is not installed"

Run: `uv add --dev ty`

### "uv: command not found"

Install uv first (see step 1 above)

### Type checking is slow

Use watch mode for incremental checking: `uv run ty check --watch`

### Need to update ty

```bash
uv add --dev ty --upgrade
```
