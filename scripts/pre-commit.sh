#!/bin/bash
# Pre-commit hook for code quality checks

set -e

echo "🔍 Running pre-commit checks..."

# Check for Python syntax errors
echo "  Checking Python syntax..."
python3 -m py_compile src/**/*.py 2>/dev/null || {
    echo "❌ Python syntax errors found"
    exit 1
}

# Check for debugging statements
echo "  Checking for debugging statements..."
if grep -r "import pdb\|breakpoint()" src/ --include="*.py" 2>/dev/null; then
    echo "❌ Debugging statements found (pdb/breakpoint)"
    exit 1
fi

# Check for TODO/FIXME in new code
echo "  Checking for unresolved TODOs..."
if git diff --cached --name-only | grep "\.py$" | xargs grep -n "TODO\|FIXME" 2>/dev/null; then
    echo "⚠️  TODOs found in staged files (warning only)"
fi

# Run quick tests
echo "  Running quick tests..."
pytest tests/ -q --tb=line -m "not slow and not api" || {
    echo "❌ Tests failed"
    exit 1
}

echo "✅ Pre-commit checks passed!"
