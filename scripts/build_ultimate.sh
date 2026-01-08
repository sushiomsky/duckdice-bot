#!/bin/bash
#
# Cross-Platform Build Script for DuckDice Bot Ultimate
# Creates standalone executables for Windows, macOS, and Linux
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Version
VERSION=${VERSION:-"3.1.0"}
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
RELEASE_DIR="$PROJECT_DIR/releases/v$VERSION"

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║        🚀 DuckDice Bot Ultimate - Release Builder v$VERSION        ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Clean first
echo "📦 Step 1: Cleaning build environment..."
bash scripts/clean.sh

# Create directories
echo ""
echo "📁 Step 2: Creating build directories..."
mkdir -p "$RELEASE_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Detect platform
PLATFORM=$(uname -s)
ARCH=$(uname -m)
echo ""
echo "🖥️  Platform: $PLATFORM ($ARCH)"

# Install dependencies
echo ""
echo "📦 Step 3: Installing dependencies..."
echo "   → Upgrading pip..."
pip3 install --upgrade pip setuptools wheel --break-system-packages 2>&1 | tail -3 || pip3 install --upgrade pip setuptools wheel

echo "   → Installing runtime dependencies..."
pip3 install -r requirements.txt --break-system-packages 2>&1 | tail -3 || pip3 install -r requirements.txt

echo "   → Installing build tools..."
pip3 install pyinstaller --break-system-packages 2>&1 | tail -3 || pip3 install pyinstaller

# Build with spec file
echo ""
echo "🔨 Step 4: Building Ultimate GUI with PyInstaller..."
pyinstaller --clean duckdice_gui_ultimate.spec 2>&1 | grep -E "(Building|Analyzing|completed successfully|WARNING|ERROR)" || true

# Platform-specific packaging
echo ""
echo "📦 Step 5: Creating release packages..."

case "$PLATFORM" in
    Darwin)
        # macOS
        PLATFORM_NAME="macos-$ARCH"
        
        echo "   → Packaging for macOS..."
        cd dist
        
        # If .app bundle was created
        if [ -d "DuckDiceBot.app" ]; then
            # Create DMG (if tools available)
            if command -v create-dmg &> /dev/null; then
                create-dmg \
                    --volname "DuckDice Bot" \
                    --window-pos 200 120 \
                    --window-size 600 400 \
                    --icon-size 100 \
                    --app-drop-link 425 120 \
                    "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.dmg" \
                    "DuckDiceBot.app" 2>&1 | tail -5
                echo "     ✓ DMG package created"
            fi
            
            # Also create ZIP
            zip -r -q "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.zip" "DuckDiceBot.app"
            echo "     ✓ ZIP package created"
        fi
        
        # If standalone executable
        if [ -f "DuckDiceBot" ]; then
            chmod +x "DuckDiceBot"
            zip -q "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.zip" "DuckDiceBot"
            echo "     ✓ Standalone executable packaged"
        fi
        
        cd ..
        ;;
        
    Linux)
        # Linux
        PLATFORM_NAME="linux-$ARCH"
        
        echo "   → Packaging for Linux..."
        cd dist
        
        if [ -f "DuckDiceBot" ]; then
            chmod +x "DuckDiceBot"
            
            # Create tar.gz
            tar czf "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.tar.gz" "DuckDiceBot"
            echo "     ✓ TAR.GZ package created"
            
            # Also create ZIP for compatibility
            zip -q "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.zip" "DuckDiceBot"
            echo "     ✓ ZIP package created"
            
            # Create AppImage (if tools available)
            if command -v appimagetool &> /dev/null; then
                # Create AppDir structure
                mkdir -p AppDir/usr/bin
                mkdir -p AppDir/usr/share/applications
                mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
                
                cp "DuckDiceBot" AppDir/usr/bin/
                
                # Create desktop entry
                cat > AppDir/usr/share/applications/duckdicebot.desktop << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=DuckDice Bot
Comment=Advanced betting automation for DuckDice.io
Exec=DuckDiceBot
Icon=duckdicebot
Categories=Utility;Finance;
Terminal=false
DESKTOP
                
                # Create AppRun
                cat > AppDir/AppRun << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/DuckDiceBot" "$@"
APPRUN
                chmod +x AppDir/AppRun
                
                # Build AppImage
                ARCH=$ARCH appimagetool AppDir "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.AppImage" 2>&1 | tail -5
                echo "     ✓ AppImage created"
            fi
        fi
        
        cd ..
        ;;
        
    MINGW*|MSYS*|CYGWIN*)
        # Windows
        PLATFORM_NAME="windows-x64"
        
        echo "   → Packaging for Windows..."
        cd dist
        
        if [ -f "DuckDiceBot.exe" ]; then
            # Create ZIP
            zip -q "$RELEASE_DIR/DuckDiceBot-$VERSION-$PLATFORM_NAME.zip" "DuckDiceBot.exe"
            echo "     ✓ ZIP package created"
            
            # Create installer with NSIS (if available)
            if command -v makensis &> /dev/null; then
                # Create NSIS script
                cat > installer.nsi << 'NSIS'
!define APP_NAME "DuckDice Bot"
!define COMP_NAME "DuckDice"
!define VERSION "3.1.0"
!define INSTALLER_NAME "DuckDiceBot-Setup.exe"

OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES64\${APP_NAME}"

Section "Main"
    SetOutPath $INSTDIR
    File "DuckDiceBot.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\DuckDiceBot.exe"
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\DuckDiceBot.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\DuckDiceBot.exe"
    Delete "$INSTDIR\Uninstall.exe"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    RMDir "$INSTDIR"
SectionEnd
NSIS
                makensis installer.nsi
                mv "DuckDiceBot-Setup.exe" "$RELEASE_DIR/"
                echo "     ✓ Windows installer created"
            fi
        fi
        
        cd ..
        ;;
esac

# Copy documentation
echo ""
echo "📄 Step 6: Packaging documentation..."
cp README.md "$RELEASE_DIR/" 2>/dev/null || true
cp LICENSE "$RELEASE_DIR/" 2>/dev/null || true
cp COMPLETE_FEATURES.md "$RELEASE_DIR/" 2>/dev/null || true
cp DATABASE_AND_CHARTS.md "$RELEASE_DIR/" 2>/dev/null || true
cp QUICK_START_GUIDE.md "$RELEASE_DIR/" 2>/dev/null || true
cp UX_ENHANCEMENTS.md "$RELEASE_DIR/" 2>/dev/null || true

# Create release README
cat > "$RELEASE_DIR/README.txt" << EOF
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                   DuckDice Bot Ultimate v$VERSION                    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

Platform: $PLATFORM_NAME
Built: $(date)

🎯 FEATURES
═══════════════════════════════════════════════════════════════════════
✓ 17 Built-in Betting Strategies
✓ Offline Simulation Mode (no API needed)
✓ Quick Bet (manual betting)
✓ Auto Bet (strategy automation)
✓ SQLite Database (persistent history)
✓ Live Charts (pure Tkinter)
✓ Outstanding UX (Material Design 3)
✓ Toast Notifications
✓ Keyboard Shortcuts (13 shortcuts)
✓ Onboarding Wizard

📦 INSTALLATION
═══════════════════════════════════════════════════════════════════════
macOS:
  1. Unzip DuckDiceBot-$VERSION-$PLATFORM_NAME.zip
  2. Double-click DuckDiceBot.app (or DuckDiceBot executable)
  3. If security warning: Right-click → Open

Linux:
  1. Extract DuckDiceBot-$VERSION-$PLATFORM_NAME.tar.gz
  2. Make executable: chmod +x DuckDiceBot
  3. Run: ./DuckDiceBot

Windows:
  1. Unzip DuckDiceBot-$VERSION-$PLATFORM_NAME.zip
  2. Run DuckDiceBot.exe
  3. If SmartScreen warning: More Info → Run Anyway

🚀 QUICK START
═══════════════════════════════════════════════════════════════════════
1. Launch application
2. Onboarding wizard appears (first time)
3. Toggle "Simulation" mode (for offline testing)
4. Go to Quick Bet tab
5. Place a bet!

For API betting:
1. Get API key from https://duckdice.io
2. Settings → API Configuration
3. Enter and save API key
4. Click "Connect"

⌨️  KEYBOARD SHORTCUTS
═══════════════════════════════════════════════════════════════════════
Ctrl+K  - Quick Connect
F5      - Refresh Balances
Ctrl+1-5- Switch Tabs
F1      - Quick Start Guide
Ctrl+/  - Show All Shortcuts

📚 DOCUMENTATION
═══════════════════════════════════════════════════════════════════════
• README.md             - Main documentation
• COMPLETE_FEATURES.md  - Feature guide
• DATABASE_AND_CHARTS.md- Database & charts
• QUICK_START_GUIDE.md  - User guide
• UX_ENHANCEMENTS.md    - UX features

🆘 SUPPORT
═══════════════════════════════════════════════════════════════════════
• GitHub: https://github.com/sushiomsky/duckdice
• Issues: https://github.com/sushiomsky/duckdice/issues

📜 LICENSE
═══════════════════════════════════════════════════════════════════════
MIT License - See LICENSE file

═══════════════════════════════════════════════════════════════════════
Built with ❤️ using Python & Tkinter
No external dependencies required!
EOF

# Create checksums
echo ""
echo "🔐 Step 7: Generating checksums..."
cd "$RELEASE_DIR"
if command -v sha256sum &> /dev/null; then
    sha256sum * 2>/dev/null | grep -v "SHA256SUMS" > SHA256SUMS || true
elif command -v shasum &> /dev/null; then
    shasum -a 256 * 2>/dev/null | grep -v "SHA256SUMS" > SHA256SUMS || true
fi
cd "$PROJECT_DIR"

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║                    ✅ BUILD COMPLETE!                                ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Release directory: $RELEASE_DIR"
echo ""
echo "📦 Built packages:"
ls -lh "$RELEASE_DIR" | grep -E "\.(zip|tar\.gz|dmg|AppImage|exe)$" | awk '{print "   " $9 " (" $5 ")"}'
echo ""
echo "📊 Total size: $(du -sh "$RELEASE_DIR" | awk '{print $1}')"
echo ""
echo "🎉 Ready for distribution!"
echo ""
