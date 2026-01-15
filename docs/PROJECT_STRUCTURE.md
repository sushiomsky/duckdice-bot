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
├── app/                       # NiceGUI web interface (🚧 under development)
│   ├── ui/                   # User interface components
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page layouts
│   │   ├── layout.py        # Main layout
│   │   └── theme.py         # Theming and styling
│   ├── services/            # Business logic services
│   ├── state/               # Application state management
│   ├── utils/               # Utility functions
│   ├── config.py            # Configuration
│   └── main.py              # Entry point for web app
│
├── assets/                    # Static assets
│   └── sounds/               # Sound files for notifications
│
├── docs/                      # Documentation
│   ├── API_REFERENCE.md      # API documentation
│   ├── CUSTOM_SCRIPTS.md     # Custom script guide
│   └── ENHANCED_STRATEGY_INFO.md  # Strategy documentation
│
├── scripts/                   # Build and utility scripts
│   ├── build_macos.sh        # macOS build script
│   ├── build_windows.bat     # Windows build script
│   └── test_build.sh         # Build testing script
│
├── src/                       # Core library code
│   ├── strategies/           # Betting strategy implementations
│   │   ├── __init__.py
│   │   ├── base.py          # Base strategy class
│   │   ├── martingale.py    # Martingale strategy
│   │   ├── fibonacci.py     # Fibonacci strategy
│   │   ├── dalembert.py     # D'Alembert strategy
│   │   ├── labouchere.py    # Labouchere strategy
│   │   ├── paroli.py        # Paroli strategy
│   │   └── ...              # More strategies
│   │
│   ├── utils/                # Utility modules
│   │   ├── bet_logger.py    # Bet history logging
│   │   ├── config.py        # Configuration management
│   │   ├── simulator.py     # Offline simulation
│   │   └── stats.py         # Statistics calculation
│   │
│   ├── api.py               # DuckDice API client
│   ├── bet_verifier.py      # Provably fair verification
│   └── constants.py         # Global constants
│
├── templates/                 # Template files
│   └── custom_scripts/       # Custom script templates
│
├── tests/                     # Test suite
│   ├── test_strategies.py   # Strategy tests
│   ├── test_api.py          # API tests
│   ├── test_verifier.py     # Verification tests
│   └── ...                  # More tests
│
├── duckdice_gui_ultimate.py  # 🎮 Main desktop GUI (Tkinter)
├── duckdice.py               # Command-line interface
├── duckdice_gui_ultimate.spec # PyInstaller spec for GUI
│
├── requirements.txt          # Python dependencies
├── requirements-build.txt    # Build dependencies
├── pyproject.toml           # Python project configuration
│
├── build_release.sh         # Multi-platform build script
├── build_windows.bat        # Windows build script
├── run_gui.sh              # Launch desktop GUI (Linux/macOS)
├── run_nicegui.sh          # Launch web interface (Linux/macOS)
│
├── .env.example            # Environment variables template
├── .gitignore             # Git ignore rules
├── LICENSE                # MIT License
│
└── Documentation files:
    ├── README.md                   # Main documentation
    ├── CHANGELOG.md               # Version history
    ├── CONTRIBUTING.md            # Contribution guide
    ├── INSTALL.md                 # Installation guide
    ├── QUICK_START_GUIDE.md       # Quick start
    ├── COMPLETE_FEATURES.md       # Feature list
    ├── WINDOWS_BUILD.md           # Windows build guide
    ├── RELEASE_CHECKLIST.md       # Release process
    ├── RELEASE_NOTES_v3.9.0.md   # Release notes
    ├── ROADMAP.md                 # Future plans
    ├── CLEANUP_SUMMARY.md         # Cleanup documentation
    └── PROJECT_STRUCTURE.md       # This file
```

## 🎯 Key Components

### Desktop GUI (`duckdice_gui_ultimate.py`)
The main Tkinter-based desktop application. This is the **recommended interface** for users.

**Features:**
- Complete betting interface
- 16 strategy implementations
- Real-time statistics dashboard
- Offline simulator
- Custom script editor
- Faucet automation
- Bet verification

**Key Classes:**
- `DuckDiceGUIApp`: Main application class
- `BetLogger`: Logs bets to JSONL format
- `StatisticsWindow`: Statistics dashboard
- `StrategyManager`: Manages betting strategies
- `CustomScriptEditor`: Monaco-based script editor

### Web Interface (`app/`)
NiceGUI-based web interface (🚧 **under development**).

**Structure:**
```
app/
├── main.py              # Entry point, routing
├── config.py            # Configuration
├── ui/
│   ├── layout.py        # App layout
│   ├── theme.py         # Theming
│   ├── components/      # Reusable components
│   └── pages/           # Page implementations
├── services/
│   └── betting.py       # Betting logic
└── state/
    └── store.py         # State management
```

### Core Library (`src/`)
Reusable components used by both interfaces.

**Modules:**
- `api.py`: DuckDice API client with connection pooling
- `strategies/`: All betting strategy implementations
- `utils/`: Utilities (logging, config, stats, simulation)
- `bet_verifier.py`: Provably fair verification

### Strategies (`src/strategies/`)
All betting strategies inherit from `BaseStrategy`:

```python
class BaseStrategy:
    def calculate_next_bet(self, last_bet, won, balance) -> float:
        """Calculate next bet amount."""
        raise NotImplementedError
```

**Available Strategies:**
- Martingale, Anti-Martingale
- Fibonacci, Reverse Fibonacci
- D'Alembert, Reverse D'Alembert
- Labouchere, Reverse Labouchere
- Paroli, Oscar's Grind
- Kelly Criterion, Flat Betting
- 1-3-2-6, Fixed Percentage
- Loss Recovery, Profit Target

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
duckdice_gui_ultimate.py
    ↓
src/strategies/
    ↓
src/api.py
    ↓
DuckDice API
```

### Reusability
Core `src/` modules are interface-agnostic and can be:
- Used by desktop GUI
- Used by web interface
- Imported as a library
- Used from command line

## 🚀 Entry Points

**For Users:**
```bash
# Desktop GUI (recommended)
python duckdice_gui_ultimate.py

# Web interface
python app/main.py

# Command line
python duckdice.py
```

**For Developers:**
```bash
# Run tests
python -m pytest

# Build executable
./build_release.sh

# Format code
black .

# Type checking (if configured)
mypy src/
```

## 📚 Import Conventions

```python
# Absolute imports for src modules
from src.api import DuckDiceAPI
from src.strategies.martingale import MartingaleStrategy

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

Last updated: January 9, 2026
