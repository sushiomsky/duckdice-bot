#!/bin/bash
#
# Build DuckDice Bot for All Platforms
# Creates standalone executables for macOS, Linux, and Windows
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Version
VERSION=${VERSION:-"2.0.0"}
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
RELEASE_DIR="$PROJECT_DIR/releases/v$VERSION"

echo "🚀 Building DuckDice Bot v$VERSION"
echo "=========================================="
echo ""

# Clean first
echo "Step 1: Cleaning build environment..."
bash scripts/clean.sh

# Create directories
echo ""
echo "Step 2: Creating build directories..."
mkdir -p "$RELEASE_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Detect platform
PLATFORM=$(uname -s)
echo ""
echo "Detected platform: $PLATFORM"

# Install dependencies
echo ""
echo "Step 3: Installing dependencies..."
pip3 install --upgrade pip setuptools wheel --break-system-packages 2>&1 | tail -3
pip3 install -r requirements.txt --break-system-packages 2>&1 | tail -3
pip3 install pyinstaller --break-system-packages 2>&1 | tail -3

# Build CLI
echo ""
echo "Step 4: Building CLI application..."
pyinstaller --clean --onefile \
    --name "duckdice-cli" \
    --add-data "src:src" \
    --hidden-import betbot_strategies.target_aware \
    --hidden-import betbot_strategies.classic_martingale \
    --hidden-import betbot_strategies.fibonacci \
    --hidden-import betbot_strategies.dalembert \
    --hidden-import betbot_strategies.labouchere \
    --hidden-import betbot_strategies.paroli \
    --hidden-import betbot_strategies.oscars_grind \
    --hidden-import betbot_strategies.one_three_two_six \
    --hidden-import betbot_strategies.kelly_capped \
    --hidden-import betbot_strategies.anti_martingale_streak \
    --hidden-import betbot_strategies.fib_loss_cluster \
    --hidden-import betbot_strategies.max_wager_flow \
    --hidden-import betbot_strategies.faucet_cashout \
    --hidden-import betbot_strategies.rng_analysis_strategy \
    --hidden-import betbot_strategies.range50_random \
    --hidden-import betbot_strategies.custom_script \
    duckdice.py 2>&1 | grep -E "(Building|Analyzing|completed successfully)"

# Build Modern GUI
echo ""
echo "Step 5: Building Modern GUI..."
pyinstaller --clean --onefile --windowed \
    --name "duckdice-gui" \
    --add-data "src:src" \
    --add-data "TARGET_AWARE_STRATEGY.md:." \
    --add-data "GUI_MODERN_README.md:." \
    --hidden-import betbot_strategies.target_aware \
    --hidden-import betbot_strategies.classic_martingale \
    --hidden-import betbot_strategies.fibonacci \
    --hidden-import betbot_strategies.dalembert \
    --hidden-import betbot_strategies.labouchere \
    --hidden-import betbot_strategies.paroli \
    --hidden-import betbot_strategies.oscars_grind \
    --hidden-import betbot_strategies.one_three_two_six \
    --hidden-import betbot_strategies.kelly_capped \
    --hidden-import betbot_strategies.anti_martingale_streak \
    --hidden-import betbot_strategies.fib_loss_cluster \
    --hidden-import betbot_strategies.max_wager_flow \
    --hidden-import betbot_strategies.faucet_cashout \
    --hidden-import betbot_strategies.rng_analysis_strategy \
    --hidden-import betbot_strategies.range50_random \
    --hidden-import betbot_strategies.custom_script \
    duckdice_gui_modern.py 2>&1 | grep -E "(Building|Analyzing|completed successfully)"

# Build Target-Aware Interactive
echo ""
echo "Step 6: Building Target-Aware Interactive..."
pyinstaller --clean --onefile \
    --name "target-aware" \
    --add-data "src:src" \
    --hidden-import betbot_strategies.target_aware \
    run_target_aware.py 2>&1 | grep -E "(Building|Analyzing|completed successfully)"

# Platform-specific packaging
echo ""
echo "Step 7: Creating release packages..."

case "$PLATFORM" in
    Darwin)
        # macOS
        PLATFORM_NAME="macos-$(uname -m)"
        
        # Create ZIP archives
        cd dist
        if [ -f "duckdice-cli" ]; then
            zip -q "$RELEASE_DIR/duckdice-cli-$VERSION-$PLATFORM_NAME.zip" "duckdice-cli"
            echo "  ✓ CLI package created"
        fi
        if [ -f "duckdice-gui" ]; then
            zip -q "$RELEASE_DIR/duckdice-gui-$VERSION-$PLATFORM_NAME.zip" "duckdice-gui"
            echo "  ✓ GUI package created"
        fi
        if [ -f "target-aware" ]; then
            zip -q "$RELEASE_DIR/target-aware-$VERSION-$PLATFORM_NAME.zip" "target-aware"
            echo "  ✓ Target-Aware package created"
        fi
        cd ..
        ;;
        
    Linux)
        # Linux
        PLATFORM_NAME="linux-$(uname -m)"
        
        # Create tar.gz archives
        cd dist
        if [ -f "duckdice-cli" ]; then
            tar czf "$RELEASE_DIR/duckdice-cli-$VERSION-$PLATFORM_NAME.tar.gz" "duckdice-cli"
            echo "  ✓ CLI package created"
        fi
        if [ -f "duckdice-gui" ]; then
            tar czf "$RELEASE_DIR/duckdice-gui-$VERSION-$PLATFORM_NAME.tar.gz" "duckdice-gui"
            echo "  ✓ GUI package created"
        fi
        if [ -f "target-aware" ]; then
            tar czf "$RELEASE_DIR/target-aware-$VERSION-$PLATFORM_NAME.tar.gz" "target-aware"
            echo "  ✓ Target-Aware package created"
        fi
        cd ..
        ;;
        
    MINGW*|MSYS*|CYGWIN*)
        # Windows
        PLATFORM_NAME="windows-x64"
        
        # Create ZIP archives
        cd dist
        if [ -f "duckdice-cli.exe" ]; then
            zip -q "$RELEASE_DIR/duckdice-cli-$VERSION-$PLATFORM_NAME.zip" "duckdice-cli.exe"
            echo "  ✓ CLI package created"
        fi
        if [ -f "duckdice-gui.exe" ]; then
            zip -q "$RELEASE_DIR/duckdice-gui-$VERSION-$PLATFORM_NAME.zip" "duckdice-gui.exe"
            echo "  ✓ GUI package created"
        fi
        if [ -f "target-aware.exe" ]; then
            zip -q "$RELEASE_DIR/target-aware-$VERSION-$PLATFORM_NAME.zip" "target-aware.exe"
            echo "  ✓ Target-Aware package created"
        fi
        cd ..
        ;;
esac

# Copy documentation
echo ""
echo "Step 8: Packaging documentation..."
cp README.md "$RELEASE_DIR/"
cp LICENSE "$RELEASE_DIR/"
cp TARGET_AWARE_STRATEGY.md "$RELEASE_DIR/" 2>/dev/null || true
cp GUI_MODERN_README.md "$RELEASE_DIR/" 2>/dev/null || true
cp QUICK_REFERENCE.md "$RELEASE_DIR/" 2>/dev/null || true
cp QUICK_START_GUI.md "$RELEASE_DIR/" 2>/dev/null || true

# Create README for release
cat > "$RELEASE_DIR/README.txt" << EOF
DuckDice Bot v$VERSION
======================

Platform: $PLATFORM_NAME
Built: $(date)

Contents:
---------
1. duckdice-cli - Command-line interface
2. duckdice-gui - Modern graphical interface
3. target-aware - Interactive target-aware launcher

Documentation:
--------------
- README.md - Main documentation
- TARGET_AWARE_STRATEGY.md - Strategy guide
- GUI_MODERN_README.md - GUI user guide
- QUICK_REFERENCE.md - Quick commands
- QUICK_START_GUI.md - GUI quick start

Quick Start:
------------
CLI:    ./duckdice-cli --help
GUI:    ./duckdice-gui
Target: ./target-aware YOUR_API_KEY

For full documentation, see README.md

License: See LICENSE file
EOF

# Create checksums
echo ""
echo "Step 9: Generating checksums..."
cd "$RELEASE_DIR"
if command -v sha256sum &> /dev/null; then
    sha256sum *.zip *.tar.gz 2>/dev/null > SHA256SUMS || true
elif command -v shasum &> /dev/null; then
    shasum -a 256 *.zip *.tar.gz 2>/dev/null > SHA256SUMS || true
fi
cd "$PROJECT_DIR"

# Summary
echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo ""
echo "Release directory: $RELEASE_DIR"
echo ""
echo "Built packages:"
ls -lh "$RELEASE_DIR" | grep -E "\.(zip|tar\.gz)$" | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Total size: $(du -sh "$RELEASE_DIR" | awk '{print $1}')"
echo ""
