# GitHub Copilot Workspace Instructions

This file provides additional context for GitHub Copilot when working with this repository.

## 🔒 MANDATORY DEVELOPMENT GUARDRAILS

**READ FIRST**: `.github/DEVELOPMENT_GUARDRAILS.md`

### Non-Negotiable Rules

1. **CLI-First**: Every feature MUST work via non-interactive CLI
2. **100% Decoupled**: Core/strategies have ZERO UI dependencies
3. **DiceBot Compatible**: Strategy interface 100% compatible (no alterations to imported strategies)
4. **Clean Repository**: NO legacy/historical/archived files (use git history)
5. **Documentation Sync**: Changes MUST reflect in docs (same commit)
6. **Auto-Release**: Every commit to main triggers OS builds + PyPI publish

**Violation = Immediate Revert**

---

## Quick Context

**Project**: DuckDice Bot - Automated betting toolkit for DuckDice.io  
**Primary Interface**: CLI (headless, scriptable, automation-friendly)  
**Version**: 4.9.2  
**Status**: Production Ready ✅

## Architecture Hierarchy

```
Core Engine (No UI)
       ↓
CLI Interface (Headless - PRIMARY)
       ↓
Interactive Mode (Optional wrapper)
       ↓
TUI/GUI (Optional visualization)
```

**Data Flow**: Always top-down, never bottom-up.

## File Organization

```
duckdice-bot/
├── src/                    # Core (ZERO UI imports allowed)
│   ├── betbot_engine/      # Betting engine
│   ├── betbot_strategies/  # 18 strategies (DiceBot compatible)
│   └── duckdice_api/       # API client
├── duckdice_cli.py         # PRIMARY interface (headless)
├── duckdice_tui.py         # Optional TUI wrapper
├── tests/                  # Test suite
├── docs/                   # Current docs only (no archives)
└── .github/
    ├── workflows/          # CI/CD (builds + PyPI)
    └── DEVELOPMENT_GUARDRAILS.md  # Full ruleset
```

## Common Tasks

### Adding a Feature ✅ CORRECT
```bash
# 1. Implement in core (no UI deps)
# 2. Add CLI argument
duckdice run --new-feature value

# 3. Add optional interactive wrapper
# 4. Update docs (same commit)
# 5. Commit to main → auto-release
```

### Adding a Feature ❌ WRONG
```python
# DON'T: Mix interactive in core
def run():
    if interactive:
        value = input("Value? ")  # ❌ Wrong layer
    engine.start(value)

# DON'T: Add UI imports to core
from rich.console import Console  # ❌ in src/betbot_engine/
```

### Working with Strategies

**DiceBot Compatibility Required**:
- All strategies support `dobet()` pattern
- Globals: balance, basebet, nextbet, chance, bethigh, win
- Imported Lua strategies work WITHOUT modification
- Test with original DiceBot script

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_strategy_integration.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Code Quality Standards

- Python 3.9+ required
- Type hints preferred
- Docstrings for public APIs
- NO commented code blocks (delete them)
- NO .bak/.old files (use git)
- Keep functions small and focused

## CI/CD Pipeline

**Trigger**: Commit to main  
**Actions**:
1. Test on Python 3.9-3.12 × 3 OS
2. Build Windows exe, macOS binary, Linux executable
3. Build Python package (sdist + wheel)
4. Publish to PyPI (if version bumped)
5. Create GitHub release with all artifacts

**Version bump required for release**:
```toml
# pyproject.toml
version = "4.9.3"  # Increment before commit
```

## Safety Checklist

Before committing:
- [ ] Feature works via CLI args (no interactive prompts in core)
- [ ] Core has no UI imports
- [ ] DiceBot compatibility maintained
- [ ] No .bak/.old/archive files
- [ ] Documentation updated (same commit)
- [ ] All tests pass
- [ ] Version bumped (if releasing)

## Documentation

When adding features, update (same commit):
- New strategy → README.md + strategy docs + CLI help
- New feature → User guide + CLI guide
- Config change → Config docs + examples
- Bug fix → Changelog

**NO separate "update docs" commits allowed.**

## Resources

- **Guardrails**: `.github/DEVELOPMENT_GUARDRAILS.md` (MANDATORY READ)
- **User Guide**: `docs/` (always current)
- **CI/CD**: `.github/workflows/build-and-release.yml`
- **Validation**: `docs/BET_VALIDATION.md`

---

**Remember**: CLI-first, decoupled, compatible, clean, documented, automated.
