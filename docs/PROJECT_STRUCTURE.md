# Project Structure

This document describes the organization of the DuckDice Bot codebase.

## 📁 Directory Structure

```
duckdice-bot/
├── .github/                    # GitHub configuration
│   └── workflows/             # GitHub Actions CI/CD
│       ├── build-release.yml  # Build and release workflow
│       ├── ci.yml            # Continuous integration
│       └── release.yml       # PyPI release workflow
│
├── assets/                    # Static assets
│   └── sounds/               # Sound files for notifications
│
├── docs/                      # Documentation
│   ├── API_REFERENCE.md      # API documentation
│   ├── CUSTOM_SCRIPTS.md     # Custom script guide
│   ├── ENHANCED_STRATEGY_INFO.md  # Strategy documentation
│   ├── PROJECT_STRUCTURE.md  # This file
│   ├── ROADMAP.md            # Development roadmap
│   ├── ARCHITECTURE.md       # Technical architecture
│   └── archive/              # Archived documentation
│
├── scripts/                   # Build and utility scripts
│   ├── build_macos.sh        # macOS build script
│   ├── build_windows.bat     # Windows build script
│   └── test_build.sh         # Build testing script
│
├── src/                       # Core library code
│   ├── betbot_strategies/    # Betting strategy implementations (22 total)
│   │   ├── __init__.py
│   │   ├── base.py          # Base strategy class
│   │   ├── classic_martingale.py
│   │   ├── anti_martingale_streak.py
│   │   ├── fibonacci.py
│   │   ├── dalembert.py
│   │   ├── labouchere.py
│   │   ├── paroli.py
│   │   ├── oscars_grind.py
│   │   ├── one_three_two_six.py
│   │   ├── kelly_capped.py
│   │   ├── faucet_grind.py
│   │   ├── faucet_cashout.py
│   │   ├── target_aware.py
│   │   ├── streak_hunter.py
│   │   ├── micro_exponential.py
│   │   ├── micro_exponential_safe.py
│   │   ├── fib_loss_cluster.py
│   │   ├── rng_analysis_strategy.py
│   │   ├── range50_random.py
│   │   ├── max_wager_flow.py
│   │   └── custom_script.py
│   │
│   ├── betbot_engine/        # Core betting engine
│   │   ├── __init__.py
│   │   ├── engine.py        # Main betting logic
│   │   ├── session.py       # Session management
│   │   └── analytics.py     # Analytics engine
│   │
│   ├── duckdice_api/         # DuckDice API client
│   │   ├── __init__.py
│   │   ├── api.py           # API client implementation
│   │   ├── models.py        # Data models
│   │   └── exceptions.py    # Custom exceptions
│   │
│   ├── interfaces/           # User interfaces
│   │   └── tui/             # Terminal User Interfaces
│   │       ├── textual_interface.py  # Modern Textual TUI
│   │       └── ncurses_interface.py  # Classic NCurses TUI
│   │
│   ├── faucet_manager/       # Faucet automation
│   ├── simulation_engine.py  # Offline simulation
│   ├── cli_display.py        # CLI display utilities
│   └── utils/                # Utility modules
│
├── tests/                     # Test suite
│   ├── test_strategies.py   # Strategy tests
│   ├── test_api.py          # API tests
│   ├── test_cli.py          # CLI tests
│   └── ...                  # More tests
│
├── duckdice_cli.py           # � Main CLI interface (920+ lines)
├── duckdice_tui.py           # 🎮 TUI launcher (Textual/NCurses)
├── duckdice.py               # Legacy command-line interface
├── strategy_comparison.py    # Strategy comparison tool
│
├── requirements.txt          # Python dependencies
├── requirements-build.txt    # Build dependencies
├── pyproject.toml           # Python project configuration
│
├── build_release.sh         # Multi-platform build script
├── build_windows.bat        # Windows build script
│
├── .env.example            # Environment variables template
├── .gitignore             # Git ignore rules
├── LICENSE                # MIT License
│
└── Documentation files:
    ├── README.md                   # Main documentation
    ├── CHANGELOG.md               # Version history
    ├── CONTRIBUTING.md            # Contribution guide
    ├── GETTING_STARTED.md         # Quick start
    ├── CLI_GUIDE.md               # CLI reference
    ├── TUI_GUIDE.md               # TUI reference
    ├── USER_GUIDE.md              # Complete user guide
    ├── DEPLOYMENT_GUIDE.md        # Deployment instructions
    ├── STATUS.md                  # Current project status
    └── docs/PROJECT_STRUCTURE.md  # This file
```

## 🎯 Key Components

### CLI Interface (`duckdice_cli.py`)
The main command-line interface. This is the **primary interface** for users.

**Features:**
- Complete betting interface with interactive mode
- 22 strategy implementations
- Real-time statistics display with Rich library
- Offline simulator
- Profile management with database persistence
- Faucet automation
- Risk controls (stop-loss, take-profit, max bets)
- Session history and analytics

**Key Functions:**
- `main()`: Entry point and argument parsing
- `interactive_mode()`: Guided configuration workflow
- `run_betting_session()`: Execute betting with selected strategy
- `display_statistics()`: Real-time stats display
- Profile save/load functionality

### TUI Interfaces (`duckdice_tui.py`, `src/interfaces/tui/`)
Terminal User Interfaces for visual terminal interaction.

**Two Implementations:**
1. **Textual Interface** (Modern):
   - Beautiful, modern terminal UI
   - Real-time statistics dashboard
   - Interactive bet history table
   - Progress indicators and rich colors
   - Mouse support
   - Requires: `textual` package

2. **NCurses Interface** (Classic):
   - Lightweight and fast
   - No external dependencies
   - Works on any Unix-like system
   - Classic terminal aesthetics
   - Minimal resource usage

**Features:**
- Real-time bet tracking
- Live statistics display
- Interactive controls (Start/Pause/Stop)
- Keyboard shortcuts
- Session management

### Core Library (`src/`)
Reusable components used by all interfaces.

**Modules:**
- `duckdice_api/`: DuckDice API client with connection pooling
- `betbot_strategies/`: All 22 betting strategy implementations
- `betbot_engine/`: Core betting logic and session management
- `interfaces/tui/`: Terminal user interface implementations
- `faucet_manager/`: Faucet automation system
- `simulation_engine.py`: Offline simulation
- `cli_display.py`: CLI display utilities
- `utils/`: Helper functions and utilities

### Strategies (`src/betbot_strategies/`)
All betting strategies inherit from `BaseStrategy`:

```python
class BaseStrategy:
    def calculate_next_bet(self, last_bet, won, balance) -> float:
        """Calculate next bet amount."""
        raise NotImplementedError
```

**Available Strategies (22 total):**
- **Conservative**: D'Alembert, Oscar's Grind, 1-3-2-6
- **Moderate**: Fibonacci, Labouchere, Paroli, Fib Loss Cluster
- **Aggressive**: Classic Martingale, Anti-Martingale Streak, Streak Hunter
- **Specialized**: Faucet Grind, Faucet Cashout, Kelly Capped, Target Aware, RNG Analysis, Range50 Random, Max Wager Flow, Micro Exponential, Micro Exponential Safe, Custom Script

### Tests (`tests/`)
Pytest-based test suite.

**Test Categories:**
- Unit tests for strategies
- API integration tests
- Verification algorithm tests
- GUI component tests (planned)

### Build System

**GitHub Actions** (`.github/workflows/`):
- `build-release.yml`: Builds executables for Windows, macOS, Linux on tag push
- `ci.yml`: Runs tests on pull requests
- `release.yml`: Publishes to PyPI (if configured)

**Local Builds:**
- `build_release.sh`: Multi-platform build script
- `build_windows.bat`: Windows-specific build
- `scripts/`: Platform-specific build helpers

## 📦 Build Artifacts

When building executables:
```
dist/
├── DuckDiceBot              # Linux executable
├── DuckDiceBot.exe          # Windows executable
└── DuckDiceBot.app/         # macOS application bundle
```

Packaged releases:
```
- DuckDiceBot-Windows-x64.zip
- DuckDiceBot-macOS-universal.zip
- DuckDiceBot-Linux-x64.tar.gz
```

## 🔧 Runtime Directories

Created at runtime (gitignored):
```
bet_history/           # Bet logs (JSONL format)
logs/                  # Application logs
user_scripts/          # User-saved custom scripts
.env                   # Environment variables (if used)
```

## 📝 Configuration

### Environment Variables
Optional `.env` file (see `.env.example`):
```
DUCKDICE_API_KEY=your-api-key
LOG_LEVEL=INFO
```

`LOG_LEVEL` controls unified runtime logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
CLI/TUI user output remains readable while subsystem diagnostics are emitted via Python logging.

### Config Files
- `pyproject.toml`: Python project metadata
- `requirements.txt`: Python dependencies
- `requirements-build.txt`: Build tools (PyInstaller)

## 🎨 Code Organization Principles

### Separation of Concerns
- **UI**: Desktop GUI and web interface
- **Core Logic**: Strategies, API, verification
- **Utilities**: Logging, config, stats
- **Tests**: Isolated test suite

### Module Dependencies
```
duckdice_cli.py / duckdice_tui.py
    ↓
src/betbot_engine/
    ↓
src/betbot_strategies/
    ↓
src/duckdice_api/
    ↓
DuckDice API
```

### Reusability
Core `src/` modules are interface-agnostic and can be:
- Used by CLI interface
- Used by TUI interfaces (Textual/NCurses)
- Imported as a library
- Used in custom scripts

## 🚀 Entry Points

**For Users:**
```bash
# CLI (recommended for automation)
python duckdice_cli.py

# TUI - Modern Textual interface
python duckdice_tui.py

# TUI - Classic NCurses interface
python duckdice_tui.py --ncurses

# Installed commands (after pip install)
duckdice              # CLI
duckdice-tui          # TUI
duckdice-compare      # Strategy comparison
```

**For Developers:**
```bash
# Run tests
python -m pytest

# Run specific test
python -m pytest tests/test_cli.py

# Format code
black .

# Type checking (if configured)
mypy src/
```

## 📚 Import Conventions

```python
# Absolute imports for src modules
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_strategies import get_strategy

# Relative imports within packages
from .base import BaseStrategy
from ..utils import log_info
```

## 🔄 Data Flow

### Betting Flow
```
User Input
    ↓
GUI/Web Interface
    ↓
Strategy Calculation
    ↓
API Request
    ↓
DuckDice Server
    ↓
Response
    ↓
Update UI + Log Bet
```

### Verification Flow
```
Bet Result
    ↓
Get Server Seed + Client Seed + Nonce
    ↓
SHA-256 Calculation
    ↓
Convert to Number (0-99.99)
    ↓
Compare with Target
    ↓
Display Result (✅ or ❌)
```

## 🛠️ Development Workflow

1. **Setup**: Clone, create venv, install deps
2. **Branch**: Create feature/fix branch
3. **Code**: Write code, following style guide
4. **Test**: Add/run tests
5. **Format**: Run Black formatter
6. **Commit**: Use conventional commits
7. **Push**: Push to fork
8. **PR**: Create pull request
9. **Review**: Address feedback
10. **Merge**: Merge when approved

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📖 Related Documentation

- [README.md](README.md) - Main documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [INSTALL.md](INSTALL.md) - Installation guide
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [ROADMAP.md](ROADMAP.md) - Future plans

---

Last updated: January 16, 2026
