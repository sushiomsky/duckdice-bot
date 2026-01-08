# Changelog

All notable changes to DuckDice Bot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.2.0] - 2026-01-08 - Ultimate Edition 🎉

### Added
- **Auto-Update System**
  - Automatic update checking on startup (configurable)
  - Manual update check via Help → Check for Updates
  - One-click download and installation from GitHub releases
  - Automatic backup before update with rollback on failure
  - Background update checking (non-blocking)
  - Version comparison logic for semantic versioning
  
- **Modern UI/UX Redesign**
  - Clear mode indicator banner (Simulation vs Live) - impossible to confuse modes
  - Modern status bar showing connection, mode, and balance
  - Beautiful color scheme with light/dark theme support (ModernColorScheme)
  - Enhanced visual feedback with toast notifications
  - ConnectionStatusBar component for bottom status display
  
- **Dynamic Currency Fetching**
  - Auto-loads available currencies from DuckDice API (`get_available_currencies()`)
  - Smart caching to config for offline use
  - Manual refresh option (View → Refresh Currencies or F6)
  - No more hardcoded currency lists - shows your actual available currencies
  
- **Professional Script Editor** (DiceBot-Compatible)
  - Full-featured code editor with syntax highlighting (keywords, comments, numbers, strings)
  - Line numbers display with synchronized scrolling
  - Auto-save every 30 seconds
  - Version history (keeps last 10 versions)
  - File management (New, Open, Save, Save As)
  - DiceBot API compatibility layer with all standard variables
  - 4 pre-loaded example scripts (Simple Martingale, Target Profit, Anti-Martingale, Streak Counter)
  - Script execution engine with state management
  - New "📝 Script Editor" tab in main GUI
  - Status bar showing file state and cursor position
  
- **Enhanced Keyboard Shortcuts**
  - F6: Refresh currencies from API
  - All existing shortcuts preserved and documented

### Changed
- Currency dropdown now uses dynamic data from API instead of hardcoded `["BTC", "ETH", "DOGE", ...]`
- Quick Bet currency selector updates automatically when connecting to API
- Status bar completely redesigned with modern look and feel
- Mode switching now updates all UI components consistently (banner + status bar)
- API integration improved with better error handling and user feedback

### Improved
- Configuration management now includes currency caching
- Thread safety for all background API operations
- User feedback with comprehensive toast notifications for all actions
- Documentation massively updated with screenshots, feature highlights, and usage guides
- README.md redesigned with modern formatting and badges
- Project structure documentation updated to include new modules

### Technical
- New module: `src/script_editor/` containing:
  - `editor.py` - ScriptEditor widget (12 KB)
  - `dicebot_compat.py` - DiceBot API layer (6 KB)
  - `__init__.py` - Module exports
- Enhanced `src/duckdice_api/api.py` with `get_available_currencies()` method
- Enhanced `src/gui_enhancements/modern_ui.py` with mode indicator and status components
- Improved `duckdice_gui_ultimate.py` with:
  - Script editor integration
  - Dynamic currency management
  - Enhanced menu with currency refresh
  - Better state management
- CI/CD pipeline optimized for faster builds (GitHub Actions)

### Documentation
- README.md completely redesigned with marketing focus
- Added screenshots section (placeholders for actual images)
- Created CHANGELOG.md with comprehensive version history
- Updated SESSION2_PROGRESS.md documenting this release
- Updated IMPLEMENTATION_STATUS.md showing 60% overall progress

---

## [3.1.0] - 2025-12-XX - Enhanced Strategies

### Added
- **Enhanced Strategy Information System**
  - StrategyMetadata dataclass with comprehensive fields
  - Strategy info dialogs with scrollable, color-coded sections
  - Risk emoji indicators in strategy dropdown (🟢🟡🟠🔴⚪)
  - Comprehensive metadata for all 16 strategies:
    - 70+ pros across all strategies
    - 65+ cons with honest warnings
    - 90+ expert tips and best practices
    - Risk levels, bankroll requirements, volatility ratings
    - Time-to-profit estimates
  - Beautiful info dialog with green pros, red cons, orange tips
  
- **Windows Build Support**
  - `build_windows.bat` script for one-click Windows builds
  - `WINDOWS_BUILD.md` with complete build documentation
  - PyInstaller `.spec` configuration optimized for Windows
  - Detailed troubleshooting guide
  
- **GitHub Actions CI/CD**
  - Automated multi-platform builds (Windows `.exe`, macOS `.app`, Linux binary)
  - Test matrix (Python 3.9, 3.11 on Ubuntu, Windows, macOS)
  - Auto-release creation when version tags pushed
  - Artifact uploads for easy distribution via GitHub Releases
  - Build caching for faster execution

### Changed
- All 16 strategies enhanced with `metadata()` classmethod
- Strategy selection dropdown now shows risk indicators with emoji
- Strategy imports restructured to ensure proper registration
- Documentation massively expanded with technical guides

### Fixed
- Strategy registration ensuring all modules load via explicit imports
- Build configuration for reliable cross-platform compatibility
- Git push authentication (switched from SSH to HTTPS)

### Technical
- Created `src/betbot_strategies/base.py` with StrategyMetadata
- Enhanced all 16 strategy files with comprehensive metadata
- Created `test_strategy_info.py` for validation (passes 16/16)
- Created `scripts/enhance_strategies.py` for batch updates
- Updated `.github/workflows/build-release.yml` with matrix builds

---

## [3.0.0] - 2025-11-XX - Ultimate GUI Edition

### Added
- Complete GUI redesign with modern tabbed interface
- **Dashboard Tab** with real-time metrics:
  - Current balance card
  - Session profit card
  - Total bets counter
  - Win rate display
- **Quick Bet Tab** for manual single bets
- **Auto Bet Tab** with 16 automated strategies:
  - Classic: Martingale, Anti-Martingale, Fibonacci, D'Alembert, Paroli
  - Advanced: Labouchere, Oscar's Grind, 1-3-2-6, Kelly Criterion (Capped)
  - Intelligent: Target-Aware, Faucet Cashout, Max Wager Flow
  - Pattern-Based: RNG Analysis, Fibonacci Loss Cluster, Range50 Random
  - Custom: Script Editor
- **History Tab** with detailed bet logs and filters
- **Statistics Tab** with charts and performance analysis
- Emergency stop system (Ctrl+Shift+Esc hotkey)
- Sound notifications for wins/losses
- Comprehensive keyboard shortcuts
- Settings dialog with API key management
- Session export to JSON/CSV
- Toast notifications for user feedback
- Loading overlays for async operations
- Onboarding wizard for first-time users

### Changed
- Moved from simple Tkinter GUI to comprehensive Ultimate GUI
- Enhanced error handling with user-friendly messages
- Improved configuration management with JSON storage
- Restructured codebase into modular components

### Technical
- Created `src/gui_enhancements/` module with:
  - Dashboard components
  - Statistics visualizations
  - Toast notifications
  - Loading overlays
  - Keyboard shortcut manager
  - Emergency stop system
  - Sound manager

---

## [2.0.0] - 2025-XX-XX - RNG Analysis Edition

### Added
- **RNG Analysis Toolkit** (Educational)
  - Statistical analysis (Chi-square, Kolmogorov-Smirnov, runs test)
  - Machine Learning predictors (Random Forest, XGBoost)
  - Deep Learning models (LSTM, GRU, CNN-LSTM with attention)
  - Pattern detection and visualization
  - Strategy generation from analysis results
- Multiple betting strategies with auto-bet engine
- Basic GUI interface for easier interaction
- Comprehensive documentation explaining why RNG cannot be beaten

### Changed
- Restructured project layout into `src/` modules
- Enhanced API client with better error handling
- Improved code organization and modularity

### Educational
- Demonstrated cryptographic RNG resistance to attacks
- Showed limitations of ML/DL for random prediction
- Explained house edge and long-term casino profit
- Valuable learning tool for statistics and ML concepts

---

## [1.0.0] - 2024-XX-XX - Initial CLI Release

### Added
- Complete DuckDice Bot API implementation
- Support for Original Dice game (high/low betting)
- Support for Range Dice game (in/out betting)
- Currency statistics retrieval
- User information and account details
- Faucet mode support
- Wagering bonus hash support
- Time Limited Events (TLE) support
- Human-readable output with emojis
- JSON output format for scripting
- Comprehensive error handling
- Environment variable support via `.env`
- Example scripts:
  - `auto_bet.py` - Automated betting strategies
  - `balance_tracker.py` - Balance monitoring
  - `stats_monitor.sh` - Real-time statistics
- Unit tests for core functionality
- Complete documentation

### Features
- CLI tool (`duckdice.py`) for all API operations
- Session management with requests library
- Timeout and retry configuration
- Multiple currency support
- Wrapper scripts for Unix (`.sh`) and Windows (`.bat`)

---

## Version Numbering

- **Major version (X.0.0)**: Breaking changes, major new features
- **Minor version (0.X.0)**: New features, enhancements, backward compatible
- **Patch version (0.0.X)**: Bug fixes, small improvements

## How to Update

```bash
git pull origin main
pip install -r requirements.txt
```

## Links

- [GitHub Repository](https://github.com/sushiomsky/duckdice-bot)
- [Releases](../../releases)
- [Documentation](README.md)
- [Quick Start Guide](QUICKSTART.md)
- [Issue Tracker](../../issues)
