# GitHub Copilot Workspace Instructions

This file provides additional context for GitHub Copilot when working with this repository.

## Quick Context

**Project**: DuckDice Bot - Automated betting toolkit for DuckDice.io  
**Primary Interface**: CLI (duckdice_cli.py) with optional GUI  
**Version**: 4.9.2  
**Status**: Production Ready ✅

## File Organization

```
duckdice-bot/
├── src/
│   ├── betbot_engine/      # Core betting engine
│   ├── betbot_strategies/  # 18 betting strategies
│   ├── duckdice_api/       # API client
│   └── cli_display/        # CLI interface components
├── gui/                    # Optional NiceGUI web interface
├── tests/                  # Test suite
├── docs/                   # Documentation
│   └── archive/           # Historical docs
├── scripts/               # Utility scripts
└── .github/               # GitHub Actions workflows
```

## Common Tasks

### Adding a New Feature
1. Determine which module it belongs to
2. Follow existing patterns (see similar features)
3. Add tests in tests/ directory
4. Update documentation
5. Run test suite before committing

### Debugging Issues
1. Check logs and error messages
2. Run relevant tests: `pytest tests/ -v`
3. Use simulation mode for betting logic
4. Check API connectivity for live issues

### Working with Strategies
- Strategies located in: `src/betbot_strategies/`
- Each strategy implements `calculate_next_bet()` interface
- All 18 strategies work in both simulation and live modes
- Add new strategies by following existing patterns

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_strategy_integration.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Code Quality Standards

- Python 3.9+ required
- Type hints preferred
- Docstrings for public APIs
- Follow PEP 8 style guide
- Keep functions small and focused
- Comprehensive error handling

## Testing Requirements

- Unit tests for new functionality
- Integration tests for API interactions
- Simulation mode tests for strategies
- All tests must pass before merge

## Safety Principles

- User must always be in control
- No auto-start behavior
- Clear error messages
- Input validation on all user input
- Stop conditions always enforced
- Fail-safe defaults

## Documentation

When adding features, update:
- Code docstrings
- README.md (if user-facing)
- CHANGELOG.md (version changes)
- USER_GUIDE.md (new features)

## Resources

- Main README: `README.md`
- User guide: `USER_GUIDE.md`
- Deployment: `DEPLOYMENT_GUIDE.md`
- Contributing: `CONTRIBUTING.md`
- Strategies: `RNG_STRATEGY_GUIDE.md`

---

**Remember**: Safety, clarity, and predictability are the top priorities.
