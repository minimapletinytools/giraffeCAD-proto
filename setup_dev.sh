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
echo "   4. When done, deactivate:"
echo "      deactivate"
echo ""

