#!/bin/bash
#
# Pre-commit validation script
# Ensures main branch is always buildable
#
# Usage:
#   ./scripts/validate-build.sh
#
# Or install as git hook:
#   ln -s ../../scripts/validate-build.sh .git/hooks/pre-commit
#

set -e  # Exit on first error

echo "============================================================"
echo "Pre-Commit Validation"
echo "============================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILED=0

# 1. Syntax Check
echo "📝 [1/5] Checking Python syntax..."
if python3 -m py_compile duckdice_cli.py duckdice.py duckdice_tui.py 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Syntax check passed"
else
    echo -e "${RED}✗${NC} Syntax check FAILED"
    FAILED=1
fi
echo ""

# 2. Import Check
echo "📦 [2/5] Checking imports..."
if python3 -c "import sys; sys.path.insert(0, 'src'); from betbot_strategies import list_strategies; print(f'✓ Found {len(list_strategies())} strategies')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Import check passed"
else
    echo -e "${RED}✗${NC} Import check FAILED"
    FAILED=1
fi
echo ""

# 3. Test Suite
echo "🧪 [3/5] Running test suite..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if python3 -m pytest tests/ -v --tb=short 2>&1 | tail -1 | grep -q "passed"; then
    echo -e "${GREEN}✓${NC} Tests passed"
else
    echo -e "${RED}✗${NC} Tests FAILED"
    FAILED=1
fi
echo ""

# 4. Package Build
echo "📦 [4/5] Testing package build..."
if python3 -m pip install -e . --quiet 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Package builds successfully"
else
    echo -e "${RED}✗${NC} Package build FAILED"
    FAILED=1
fi
echo ""

# 5. CLI Functionality
echo "🎯 [5/5] Testing CLI functionality..."
if python3 duckdice_cli.py --help >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} CLI works"
else
    echo -e "${RED}✗${NC} CLI FAILED"
    FAILED=1
fi
echo ""

# Summary
echo "============================================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All validation checks passed${NC}"
    echo "Safe to commit to main branch"
    echo "============================================================"
    exit 0
else
    echo -e "${RED}❌ Validation FAILED${NC}"
    echo ""
    echo "Main branch must always be buildable!"
    echo "Fix the errors above before committing."
    echo "============================================================"
    exit 1
fi
