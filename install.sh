#!/bin/bash
# Installation script for Muninn MCP Server

set -e

echo "🧠 Installing Muninn MCP Server"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3.13 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3.10 or higher."
        exit 1
    fi
    PYTHON=python3
else
    PYTHON=python3.13
fi

PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠ Virtual environment already exists. Skipping creation."
else
    $PYTHON -m venv .venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate and install
echo "Installing dependencies..."
source .venv/bin/activate

pip install --upgrade pip > /dev/null 2>&1
pip install -e .

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Test: source .venv/bin/activate && python test_muninn.py"
echo "  2. Add to Hugin config (see QUICK_START.md)"
echo "  3. Run: muninn"
echo ""
echo "Documentation:"
echo "  - README.md - Overview and features"
echo "  - QUICK_START.md - Getting started guide"
echo "  - EXAMPLES.md - Detailed usage examples"
echo ""
