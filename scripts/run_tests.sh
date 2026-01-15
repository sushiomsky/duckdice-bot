#!/bin/bash
# Automated test runner script

set -e

echo "🧪 DuckDice Bot - Automated Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
major=$(echo $python_version | cut -d'.' -f1)
minor=$(echo $python_version | cut -d'.' -f2)
echo "   Python version: $python_version"
if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 9 ]); then
    echo -e "${RED}❌ Python 3.9 or higher required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"
echo ""

# Check dependencies
echo "📦 Checking dependencies..."
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest not found${NC}"
    if [ -d "venv" ]; then
        echo "   Using venv for dependencies"
        source venv/bin/activate 2>/dev/null || true
    else
        echo "   Please install pytest: pip install pytest pytest-cov"
        echo "   Or run: python3 -m venv venv && source venv/bin/activate && pip install -e .[test]"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Dependencies OK${NC}"
echo ""

# Run linting (if available)
if command -v pylint &> /dev/null; then
    echo "🔍 Running linting..."
    pylint src/ --exit-zero || true
    echo ""
fi

# Run unit tests
echo "🧪 Running unit tests..."
pytest tests/ -v -m "not slow and not api" --tb=short || TEST_FAILED=1
echo ""

# Run integration tests (if requested)
if [[ "$1" == "--all" ]] || [[ "$1" == "--integration" ]]; then
    echo "🔗 Running integration tests..."
    pytest tests/ -v -m "integration" --tb=short || TEST_FAILED=1
    echo ""
fi

# Run coverage (if requested)
if [[ "$1" == "--coverage" ]] || [[ "$1" == "--all" ]]; then
    echo "📊 Running coverage analysis..."
    pytest tests/ --cov=src --cov-report=html --cov-report=term
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
fi

# Summary
echo "========================================"
if [ -z "$TEST_FAILED" ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
