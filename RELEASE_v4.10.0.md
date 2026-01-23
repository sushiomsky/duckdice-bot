# Release v4.10.0

## 🎉 Major New Features

### 📊 Complete Database Logging
Track every bet for debugging and strategy improvement:
- **Complete betting stream** logged to SQLite database
- **24-column schema** captures bet specs, results, balance progression
- **Strategy state snapshots** in JSON for deep analysis
- **Session tracking** with comprehensive metrics
- **CSV export** for external analysis
- **Query tools** for debugging and optimization

**Usage:**
```bash
# Database logging enabled by default
python duckdice_cli.py run -m simulation -s martingale --max-bets 100

# Query your data
python scripts/query_database.py
```

**Documentation:** [DATABASE_LOGGING.md](docs/DATABASE_LOGGING.md)

---

### 🧠 Adaptive Survival Meta-Strategy
Cautious but opportunistic player with pattern detection:
- **Pattern detection** - Identifies calm vs chaos phases
- **4 competing approaches** - Conservative, Moderate, Opportunistic, Recovery
- **Performance tracking** - Automatically selects best-performing approach
- **Survival safeguards** - Multiple safety layers for long-term survival
- **Smooth transitions** - No sudden behavioral changes

**Usage:**
```bash
python duckdice_cli.py run -m simulation -s adaptive-survival \
  -P base_bet_pct=0.01 \
  -P conservative_chance=75 \
  -P moderate_chance=50 \
  -P opportunistic_chance=40
```

**Documentation:** [ADAPTIVE_SURVIVAL_GUIDE.md](docs/ADAPTIVE_SURVIVAL_GUIDE.md)

---

### 🎲 Simple Progression 40% Strategy
Clean win-progression strategy:
- **40% win chance** for good odds
- **45% increase on each win** for aggressive growth
- **Reset on loss** to base bet (1% of balance)
- **Safety caps** - Max 25% of balance per bet

**Usage:**
```bash
python duckdice_cli.py run -m simulation -s simple-progression-40 -b 100
```

---

### 🌐 API Fallback Domain Support
Automatic failover to alternative domains:
- **Primary:** duckdice.io (default)
- **Fallback #1:** duckdice.live
- **Fallback #2:** duckdice.net

**Features:**
- Automatic domain switching on connection errors
- Domain caching for performance
- Transparent - no configuration needed
- Works with all betting modes

**Documentation:** [API_FALLBACK.md](docs/API_FALLBACK.md)

---

## 🔧 Improvements

### Database Logging
- ✅ Optional feature (can be disabled with `--no-db-log`)
- ✅ Non-blocking - betting continues even if DB write fails
- ✅ Indexed for fast queries
- ✅ Tracks wins/losses accurately (fixed estimation bug)

### Strategy Engine
- ✅ All strategies can export internal state via `get_state()`
- ✅ State snapshots logged to database for debugging
- ✅ Better integration with betting engine

### API Client
- ✅ Intelligent retry logic with fallback domains
- ✅ Better error messages when all domains fail
- ✅ Connection pooling and keep-alive preserved

---

## 📦 Installation

### PyPI (Recommended)
```bash
pip install duckdice-betbot
```

### From Source
```bash
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
pip install -r requirements.txt
```

### Standalone Executables
Download for your platform:
- Windows: `duckdice-bot-windows.exe`
- macOS: `duckdice-bot-macos`
- Linux: `duckdice-bot-linux`

---

## 📚 Documentation

**New Guides:**
- [DATABASE_LOGGING.md](docs/DATABASE_LOGGING.md) - Complete database guide
- [ADAPTIVE_SURVIVAL_GUIDE.md](docs/ADAPTIVE_SURVIVAL_GUIDE.md) - Meta-strategy deep dive
- [API_FALLBACK.md](docs/API_FALLBACK.md) - Fallback domain documentation

**Existing Guides:**
- [README.md](README.md) - Quick start and overview
- [USER_GUIDE.md](USER_GUIDE.md) - Comprehensive usage guide
- [CLI_GUIDE.md](CLI_GUIDE.md) - Command-line reference
- [GETTING_STARTED.md](GETTING_STARTED.md) - Step-by-step tutorial

---

## 🧪 Testing

All tests passing:
```bash
pytest tests/ -v
# 12 passed, 3 skipped
```

Test the new features:
```bash
# Database logging
python test_database_demo.sh

# Adaptive survival
python duckdice_cli.py run -m simulation -s adaptive-survival --max-bets 30

# Simple progression
python duckdice_cli.py run -m simulation -s simple-progression-40 --max-bets 30

# API fallback
python test_api_fallback.py
```

---

## 🔄 Migration Notes

### From v4.9.x

No breaking changes! All existing functionality preserved.

**New defaults:**
- Database logging is enabled by default
- Database location: `data/duckdice_bot.db`
- API fallback domains automatically configured

**Optional migration:**
```bash
# Disable database logging if not wanted
python duckdice_cli.py run --no-db-log ...

# Custom database location
python duckdice_cli.py run --db-path /path/to/custom.db ...
```

---

## 📈 Statistics

**Codebase:**
- 22 total strategies (2 new: adaptive-survival, simple-progression-40)
- 500+ lines of new database code
- 650+ lines for adaptive survival strategy
- 4700 characters of new documentation

**Commits:**
```
511f191 chore: Bump version to 4.10.0
c7ae49e docs: Add API fallback documentation
e2ec5d4 feat: Add API fallback domain support
0c52fa9 feat: Add simple-progression-40 strategy
36a945e feat: Add adaptive-survival meta-strategy
2113560 feat: Add comprehensive database logging
```

---

## 🙏 Thanks

Special thanks to all testers and contributors!

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

**Full Changelog:** https://github.com/sushiomsky/duckdice-bot/compare/v4.9.2...v4.10.0
