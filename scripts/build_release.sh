#!/bin/bash
# Build script for DuckDice Bot v3.9.0
# Creates distribution packages for release

set -e  # Exit on error

VERSION="3.9.0"
APP_NAME="DuckDice-Bot"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Building $APP_NAME v$VERSION for Release              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    EXT=""
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    EXT=""
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
    EXT=".exe"
else
    echo -e "${RED}❌ Unsupported platform: $OSTYPE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Detected platform: $PLATFORM${NC}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  PyInstaller not found. Installing...${NC}"
    pip install -r requirements-build.txt
fi

# Create dist directory
mkdir -p dist
mkdir -p releases/v$VERSION

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Building DuckDice CLI/TUI package"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create a simple launcher for Textual TUI
cat > dist/run_bot.py << 'EOF'
#!/usr/bin/env python3
"""
DuckDice Bot v3.9.0 - Textual TUI
Launcher script for standalone distribution
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run
from duckdice_tui import main as run_tui

if __name__ == '__main__':
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║           DuckDice Bot v3.9.0 - Turbo Edition                 ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("")
    print("Starting terminal interface...")
    print("")
    print("Press Ctrl+C to stop")
    print("")
    run_tui()
EOF

chmod +x dist/run_bot.py

echo -e "${GREEN}✅ Created launcher script${NC}"
echo ""

# Create README for distribution
cat > dist/README.txt << 'EOF'
DuckDice Bot v3.9.0 "Turbo Edition"
===================================

🚀 The Fastest DuckDice Betting Bot Available!

QUICK START
-----------

1. Ensure Python 3.9+ is installed
2. Install dependencies:
   pip install -r requirements.txt

3. Run the bot:
   
   Web Interface (Recommended):
   python3 run_bot.py

4. Go to Settings and enter your DuckDice API key
5. Start betting!

FEATURES
--------

⚡ Turbo Mode: 15-25x faster betting
📊 Statistics Dashboard: Multi-period analytics
💾 Persistent History: Auto-saved bet data
🌍 Multi-Currency: All DuckDice currencies
🎯 17 Strategies: Built-in + custom scripts
🔐 Provably Fair: Bet verification

SYSTEM REQUIREMENTS
-------------------

- Python 3.9 or higher
- 512 MB RAM minimum
- Internet connection
- Terminal emulator

SUPPORT
-------

Documentation: README.md
Issues: https://github.com/sushiomsky/duckdice-bot/issues
License: MIT

RESPONSIBLE GAMBLING
--------------------

⚠️ This is a tool for automation and analysis.
⚠️ Only bet what you can afford to lose.
⚠️ Gambling should be for entertainment only.
⚠️ If you have a gambling problem, seek help.

Enjoy! ⚡
EOF

echo -e "${GREEN}✅ Created distribution README${NC}"
echo ""

# Create requirements.txt copy for distribution
cp requirements.txt dist/

# Package source code
echo "Packaging source code..."
echo ""

# Create version-specific archive name
ARCHIVE_NAME="duckdice-bot-v${VERSION}-${PLATFORM}"

if [[ "$PLATFORM" == "windows" ]]; then
    # Create ZIP for Windows
    echo "Creating ZIP archive for Windows..."
    cd dist
    zip -r "../releases/v${VERSION}/${ARCHIVE_NAME}.zip" . -x "*.pyc" -x "__pycache__/*"
    cd ..
    echo -e "${GREEN}✅ Created: releases/v${VERSION}/${ARCHIVE_NAME}.zip${NC}"
else
    # Create tar.gz for Linux/macOS
    echo "Creating tar.gz archive..."
    tar -czf "releases/v${VERSION}/${ARCHIVE_NAME}.tar.gz" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude=".git" \
        --exclude="venv" \
        --exclude="build" \
        --exclude="dist" \
        -C . \
        src/ duckdice_cli.py duckdice_tui.py duckdice.py requirements.txt LICENSE README.md
    
    echo -e "${GREEN}✅ Created: releases/v${VERSION}/${ARCHIVE_NAME}.tar.gz${NC}"
fi

# Create source distribution
echo ""
echo "Creating source distribution..."
python3 -m build 2>/dev/null || {
    echo -e "${YELLOW}⚠️  build module not found, creating manual source dist${NC}"
    tar -czf "releases/v${VERSION}/duckdice-bot-v${VERSION}-source.tar.gz" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude=".git" \
        --exclude="venv" \
        --exclude="build" \
        --exclude="dist" \
        --exclude="*.egg-info" \
        .
}

echo -e "${GREEN}✅ Created source distribution${NC}"
echo ""

# Calculate checksums
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Calculating checksums..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "releases/v${VERSION}"
if command -v sha256sum &> /dev/null; then
    sha256sum * > SHA256SUMS
elif command -v shasum &> /dev/null; then
    shasum -a 256 * > SHA256SUMS
fi

if [ -f SHA256SUMS ]; then
    echo -e "${GREEN}✅ Created SHA256SUMS${NC}"
    echo ""
    cat SHA256SUMS
    echo ""
fi

cd ../..

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    BUILD COMPLETE! ✅                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Release artifacts in: releases/v${VERSION}/"
echo ""
ls -lh "releases/v${VERSION}/"
echo ""
echo "Next steps:"
echo "  1. Test the package"
echo "  2. Upload to GitHub release:"
echo "     gh release upload v${VERSION} releases/v${VERSION}/*"
echo ""
