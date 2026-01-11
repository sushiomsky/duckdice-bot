#!/bin/bash
#
# Clean Build Environment
# Removes all temporary files, caches, and build artifacts
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo "🧹 Cleaning DuckDice Bot Build Environment"
echo "========================================"

# Clean Python cache files
echo ""
echo "Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.py~" -delete 2>/dev/null || true

# Clean old spec files
echo "Cleaning old PyInstaller spec files..."
rm -f duckdice.spec duckdice_gui.spec 2>/dev/null || true

# Clean build directories
echo "Cleaning build directories..."
rm -rf build/ dist/ *.egg-info/ .eggs/ 2>/dev/null || true

# Clean test caches
echo "Cleaning test caches..."
rm -rf .pytest_cache/ .tox/ .coverage htmlcov/ 2>/dev/null || true

# Clean editor files
echo "Cleaning editor files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
find . -type f -name "*.swp" -delete 2>/dev/null || true
find . -type f -name "*.swo" -delete 2>/dev/null || true
find . -type f -name "*~" -delete 2>/dev/null || true
find . -type f -name ".*.swp" -delete 2>/dev/null || true

# Clean release artifacts
echo "Cleaning old build artifacts in releases..."
find releases -type f -name "*.zip" -delete 2>/dev/null || true
find releases -type f -name "*.tar.gz" -delete 2>/dev/null || true
find releases -type f -name "SHA256SUMS" -delete 2>/dev/null || true

# Clean temporary files
echo "Cleaning temporary files..."
find . -type f -name "*.tmp" -delete 2>/dev/null || true
rm -f .continue 2>/dev/null || true

echo ""
echo "✅ Clean complete!"
echo ""
