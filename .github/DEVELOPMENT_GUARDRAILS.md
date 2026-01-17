# Development Guardrails and Guidelines

**Last Updated**: 2026-01-17  
**Status**: 🔒 **MANDATORY** - These rules apply to ALL future development

---

## 🎯 Core Principles

### 0. Main Branch Protection (MANDATORY)

**Rule**: Main branch MUST always be buildable and deployable.

#### Requirements
- ✅ All commits pass CI/CD tests before merge
- ✅ No direct commits that break builds
- ✅ Every commit must be production-ready
- ✅ Breaking changes require version bump

#### Validation
```bash
# Before EVERY commit to main:
pytest tests/ -v                    # All tests pass
python -m py_compile duckdice_cli.py  # Syntax valid
python -m pip install -e .          # Package builds
duckdice --help                     # CLI works
```

#### Enforcement
- ✅ **CI/CD runs on every push** to main
- ✅ **Tests MUST pass** (Python 3.9-3.12 × 3 OS)
- ✅ **Build MUST succeed** (all platforms)
- ✅ **No broken commits allowed** (immediate revert)

#### Protected Actions
```bash
# ✅ SAFE (tested locally first)
pytest tests/ -v && git push origin main

# ❌ DANGEROUS (untested)
git push origin main  # Hope it works!

# ❌ FORBIDDEN (breaking build intentionally)
git push origin main -f  # Force push
git commit -m "WIP: broken code"  # Work in progress
```

#### Branch Strategy
- `main` - **Always buildable** (production-ready)
- Feature branches - For development (can be broken)
- Tags (v*) - Triggers full release pipeline

---

### 1. CLI-First Architecture (MANDATORY)

**Rule**: Every feature MUST be usable via non-interactive CLI.

#### Requirements
- ✅ All features accessible via command-line arguments
- ✅ No interactive prompts in automated mode
- ✅ Full functionality without GUI/TUI
- ✅ Scriptable and automation-friendly

#### Validation
```bash
# Every feature must work like this:
duckdice run -m sim -c btc -s martingale -P base_bet=0.001

# NOT like this:
duckdice run
> Please select currency: _
```

#### Enforcement
- Interactive mode is OPTIONAL convenience layer
- CLI arguments are PRIMARY interface
- GUI/TUI are OPTIONAL visualization layers
- Core logic never depends on interactive input

---

### 2. Complete Decoupling (MANDATORY)

**Rule**: CLI must be 100% independent from GUI and interactive modes.

#### Architecture
```
┌─────────────────────────────────────────────┐
│           Core Engine & Strategies          │
│         (Zero UI dependencies)              │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│  CLI Layer  │  │  GUI Layer  │
│ (Headless)  │  │ (Optional)  │
└─────────────┘  └─────────────┘
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│ Interactive │  │     TUI     │
│   (Optional)│  │ (Optional)  │
└─────────────┘  └─────────────┘
```

#### Requirements
- ✅ Core engine has NO UI imports
- ✅ Strategies have NO UI dependencies
- ✅ API client is UI-agnostic
- ✅ CLI works without any GUI/TUI modules installed

#### File Structure
```
src/
├── betbot_engine/         # ZERO UI imports
├── betbot_strategies/     # ZERO UI imports
├── duckdice_api/         # ZERO UI imports
└── interfaces/           # UI layers (optional)
    ├── cli/              # Headless CLI
    ├── tui/              # Terminal UI
    └── gui/              # Graphical UI
```

---

### 3. DiceBot Compatibility (MANDATORY)

**Rule**: Strategy interface must be 100% compatible with original DiceBot strategies.

#### Requirements
- ✅ Lua strategy structure supported
- ✅ All DiceBot globals available (balance, chance, nextbet, etc.)
- ✅ `dobet()` function behavior identical
- ✅ No alterations to imported strategies
- ✅ Custom scripts work without modification

#### Compatibility Layer
```python
# DiceBot globals that MUST be supported:
balance      # Current balance
basebet      # Base bet amount
previousbet  # Last bet amount
nextbet      # Next bet amount (strategy sets this)
chance       # Win chance percentage
bethigh      # Bet direction (true/false)
win          # Last bet won (true/false)
currentprofit # Session profit
currentstreak # Current win/loss streak
```

#### Testing
Every new strategy implementation must:
1. Have equivalent Lua version documented
2. Pass compatibility test suite
3. Work with zero modifications if imported from DiceBot

---

### 4. Repository Cleanliness (MANDATORY)

**Rule**: Repository must stay clean with NO legacy, historical, or outdated content.

#### Forbidden Content
- ❌ Historical documentation (STATUS_OLD.md, etc.)
- ❌ Legacy code files (.bak, .old, _deprecated)
- ❌ Commented-out code blocks (delete, don't comment)
- ❌ Unused imports or functions
- ❌ Duplicate documentation
- ❌ "Archive" directories (if needed, use git history)

#### Allowed Content
- ✅ Current production code
- ✅ Active documentation
- ✅ Working tests
- ✅ Build artifacts (in .gitignore)

#### Maintenance
```bash
# Before ANY commit:
- Remove all .bak, .old files
- Delete commented code blocks
- Remove unused imports
- Archive to git, not filesystem
```

#### File Naming
```
✅ GOOD:
- feature.py
- GUIDE.md
- test_feature.py

❌ BAD:
- feature_old.py
- feature.py.bak
- GUIDE_v1.md
- GUIDE_ARCHIVED.md
- docs/archive/
```

---

### 5. Documentation Synchronization (MANDATORY)

**Rule**: Changes MUST reflect in documentation immediately.

#### Update Matrix

| Code Change | Documentation to Update |
|-------------|------------------------|
| New strategy | README.md, strategy docs, CLI help |
| New feature | User guide, CLI guide, README |
| API change | API docs, examples, guides |
| Config change | Config guide, examples |
| Bug fix | Changelog, affected guides |

#### Enforcement
- Documentation updates in SAME commit as code
- No "TODO: update docs" comments
- No stale examples in documentation
- All guides reflect current behavior

#### Documentation Rules
1. **Single Source of Truth**: No duplicate info across files
2. **Living Documents**: Update, don't create new versions
3. **Remove Outdated**: Delete old sections, don't archive
4. **Examples Work**: All code examples must be tested
5. **Version Consistency**: Docs match code version exactly

---

### 6. Continuous Deployment (MANDATORY)

**Rule**: Every commit to main triggers multi-platform releases and PyPI publishing.

#### CI/CD Pipeline

```yaml
Commit to main → Trigger workflow
      ↓
  Run tests (Python 3.9-3.12)
      ↓
  Build artifacts:
      ├── Windows .exe
      ├── macOS universal binary
      ├── Linux executable
      └── Python package
      ↓
  Publish to PyPI (if version bumped)
      ↓
  Create GitHub release (with all artifacts)
```

#### Version Management

**Semantic Versioning** (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes (2.0.0 → 3.0.0)
- **MINOR**: New features (2.1.0 → 2.2.0)
- **PATCH**: Bug fixes (2.1.1 → 2.1.2)

#### Release Requirements
- ✅ **All tests pass** (Python 3.9-3.12 × 3 OS)
- ✅ **Build succeeds** on all platforms
- ✅ **Main branch buildable** (no broken commits)
- ✅ Version number bumped in `pyproject.toml`
- ✅ Changelog entry added
- ✅ Documentation updated
- ✅ No merge conflicts

#### Artifact Requirements
- ✅ Windows CLI executable (PyInstaller)
- ✅ macOS universal binary (x86_64 + arm64)
- ✅ Linux executable (statically linked)
- ✅ Python package (sdist + wheel)
- ✅ SHA256 checksums for all files

#### PyPI Publishing
- Automatic on version tag (v*)
- Uses trusted publishing (no tokens in repo)
- Rollback procedure documented
- Test PyPI deployment first

---

## 🔍 Pre-Commit Checklist

Before EVERY commit to main:

```bash
# 0. Build Validation (CRITICAL)
□ All tests pass: pytest tests/ -v
□ Syntax valid: python -m py_compile duckdice_cli.py
□ Package builds: pip install -e .
□ CLI works: duckdice --help
□ No breaking changes (or version bumped)

# 1. CLI Independence
□ Feature works via CLI arguments only
□ No interactive prompts in core functionality
□ GUI/TUI are optional layers

# 2. Decoupling
□ Core engine has no UI imports
□ Strategies have no UI dependencies
□ CLI works without GUI/TUI modules

# 3. DiceBot Compatibility
□ Strategy interface unchanged
□ Lua compatibility maintained
□ dobet() behavior identical

# 4. Repository Cleanliness
□ No .bak, .old, _deprecated files
□ No commented-out code
□ No historical documentation
□ No duplicate files

# 5. Documentation
□ Docs updated in same commit
□ Examples tested and working
□ No stale information
□ Version numbers consistent

# 6. CI/CD Readiness
□ All tests pass locally
□ Version bumped (if release)
□ Changelog updated
□ Build artifacts verified
```

---

## 🛠️ Implementation Standards

### Code Quality

```python
# ✅ GOOD: CLI-first with optional interactive
def run(mode, currency, strategy, **params):
    """Core run function - fully parameterized."""
    engine.start(mode, currency, strategy, params)

def interactive_run():
    """Optional wrapper for interactive mode."""
    mode = prompt("Mode?")  # Only in wrapper
    run(mode, ...)

# ❌ BAD: Interactive mixed with core
def run():
    """Mixed interactive and core logic."""
    if sys.stdin.isatty():
        mode = input("Mode? ")
    else:
        mode = os.getenv("MODE")
    # Core logic intertwined with interactive
```

### Decoupling

```python
# ✅ GOOD: Zero UI dependencies
# src/betbot_engine/engine.py
from decimal import Decimal
from betbot_strategies import get_strategy

class Engine:
    def __init__(self, api_client):
        self.api = api_client  # No UI here

# ❌ BAD: UI dependency in core
# src/betbot_engine/engine.py
from rich.console import Console  # ❌ UI import
console = Console()
```

### DiceBot Compatibility

```python
# ✅ GOOD: Compatible interface
class MartingaleStrategy:
    def dobet(self):
        """DiceBot-compatible dobet function."""
        if self.win:
            self.nextbet = self.basebet
        else:
            self.nextbet = self.previousbet * 2

# ❌ BAD: Non-compatible interface
class MartingaleStrategy:
    def calculate_next_bet_amount(self, won: bool) -> Decimal:
        # Not DiceBot compatible
        pass
```

---

## 📋 File Structure Standards

### Allowed Structure
```
duckdice-bot/
├── src/                       # Core code (no UI)
│   ├── betbot_engine/
│   ├── betbot_strategies/
│   └── duckdice_api/
├── duckdice_cli.py           # CLI entry point
├── duckdice_tui.py           # TUI entry point (optional)
├── tests/                    # Test suite
├── docs/                     # Current docs only
├── .github/
│   ├── workflows/            # CI/CD
│   └── DEVELOPMENT_GUARDRAILS.md  # This file
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

### Forbidden Structure
```
❌ src/legacy/
❌ old_code/
❌ docs/archive/
❌ backup/
❌ deprecated/
❌ scripts/old/
❌ *_old.py
❌ *.bak
❌ *_archived.md
```

---

## 🚨 Violation Consequences

### Immediate Actions
1. **Revert commit** if guardrails violated
2. **Fix in new commit** with guardrail compliance
3. **Update this document** if new patterns emerge

### Review Process
- Every PR must confirm guardrail compliance
- Automated checks enforce where possible
- Manual review for architectural decisions

---

## 🔄 Guardrail Updates

This document is living and may be updated when:
- New patterns emerge
- Better practices discovered
- Architecture evolves
- Community feedback received

**Update Process**:
1. Propose change in PR
2. Document rationale
3. Update affected code
4. Merge together

---

## 📚 Related Documents

- `.github/workflows/build-and-release.yml` - CI/CD implementation
- `CONTRIBUTING.md` - Contribution guidelines
- `README.md` - Project overview
- `docs/ARCHITECTURE.md` - System architecture (to be created)

---

## ✅ Summary

**Remember**:
0. 🔒 **Buildable**: Main always builds and passes tests
1. 🎯 **CLI-first**: Every feature via command-line
2. 🔌 **Decoupled**: Core has zero UI dependencies
3. 🎲 **Compatible**: DiceBot strategies work unmodified
4. 🧹 **Clean**: No legacy/historical content
5. 📝 **Documented**: Changes reflect immediately
6. 🚀 **Automated**: Every commit triggers releases

**These are not suggestions. These are requirements.**

---

*Established: 2026-01-17*  
*Authority: Project Maintainer*  
*Enforcement: Mandatory*
