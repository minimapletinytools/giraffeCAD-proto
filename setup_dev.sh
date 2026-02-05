#!/bin/bash
# Development environment setup script for GiraffeCAD

set -e  # Exit on error

echo "🦒 GiraffeCAD Development Environment Setup"
echo "==========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.9 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
echo "Found Python: $python_version"
echo ""

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate venv
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📚 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "📝 Setting up ty (type checker) with uv..."
    uv add --dev ty
    echo "✅ ty installed via uv"
    echo ""
else
    echo "📝 Note: uv is not installed (recommended for managing ty)"
    echo ""
    echo "To install uv:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "Then install ty:"
    echo "   uv add --dev ty"
    echo ""
    echo "Or install ty globally:"
    echo "   curl -LsSf https://astral.sh/ty/install.sh | sh"
    echo ""
fi

echo "🎯 Next steps:"
echo "   1. Activate the virtual environment:"
echo "      source venv/bin/activate"
echo ""
echo "   2. Run tests:"
echo "      python3 -m pytest code_goes_here/ -v"
echo ""
echo "   3. Run tests with coverage:"
echo "      python3 -m pytest code_goes_here/ --cov=code_goes_here --cov-report=html"
echo ""
echo "   4. Run type checking:"
if command -v uv &> /dev/null; then
    echo "      uv run ty check"
else
    echo "      ty check  (install ty first - see TYPECHECK_SETUP.md)"
fi
echo ""
echo "   5. When done, deactivate:"
echo "      deactivate"
echo ""

