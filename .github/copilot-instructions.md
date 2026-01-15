# GitHub Copilot Workspace Instructions

This file provides additional context for GitHub Copilot when working with this repository.

## Quick Context

**Project**: DuckDice Bot - Automated betting toolkit for DuckDice.io  
**Primary Interface**: NiceGUI web application (gui/app.py)  
**Version**: 4.0.0  
**Status**: Production Ready ✅

## File Organization

```
duckdice-bot/
├── gui/                    # NiceGUI web interface (PRIMARY)
│   ├── app.py             # Main entry point
│   ├── dashboard.py       # Main dashboard
│   ├── strategies_ui.py   # Strategy configuration
│   ├── analytics_ui.py    # Analytics dashboard
│   ├── bot_controller.py  # Bot execution
│   ├── database.py        # SQLite persistence
│   ├── charts.py          # Matplotlib charts
│   └── ...
├── src/                   # Core bot logic
│   └── betbot_strategies/ # 17 betting strategies
├── tests/                 # Test suite
│   └── gui/              # GUI tests (7 passing)
├── data/                  # Database storage
│   └── duckdice_bot.db   # SQLite database
└── docs/                  # Documentation
```

## Common Tasks

### Adding a New Feature
1. Determine which module it belongs to (ui/, bot_controller.py, database.py, etc.)
2. Follow existing patterns (see similar features)
3. Update tests if needed
4. Test in simulation mode first
5. Update documentation

### Debugging Issues
1. Check `gui/app.py` for startup issues
2. Check `gui/bot_controller.py` for bot execution issues
3. Check `gui/database.py` for data persistence issues
4. Run tests: `cd tests/gui && python3 test_gui_components.py`

### Working with Strategies
- Strategies located in: `src/betbot_strategies/`
- Strategy loader: `gui/strategy_loader.py`
- Strategy integration: `gui/strategy_integration.py`
- All 17 strategies should work in both simulation and live modes

### Database Changes
- Schema in: `gui/database.py` (lines 28-95)
- 3 tables: bet_history, strategy_profiles, sessions
- Always test migrations carefully
- Backup database before schema changes

## Important Patterns

### State Management
- Global state in `gui/state.py`
- Thread-safe with locks
- BetRecord dataclass for bet data
- AppState dataclass for application state

### Threading
- Bot runs in background thread
- UI updates via callbacks
- Use `app_state.lock` for thread safety
- Stop flag checked before each bet

### Error Handling
- Always catch exceptions
- Log errors with context
- Show user-friendly notifications
- Never crash silently

### API Integration
- API wrapper in `gui/live_api.py`
- Test connection before betting
- Handle rate limiting
- Retry with exponential backoff

## Code Quality Standards

- Python 3.8+ required
- Type hints preferred
- Docstrings for public APIs
- Comments for complex logic only
- Follow existing code style
- Keep functions small and focused

## Testing Requirements

- All GUI tests must pass (7/7)
- Test in simulation mode
- Test with real API (optional)
- Verify database operations
- Check chart generation

## Safety Checklist

Before submitting changes:
- [ ] Simulation mode works correctly
- [ ] Stop button functional
- [ ] No auto-start behavior
- [ ] All inputs validated
- [ ] Error messages clear
- [ ] Database operations safe
- [ ] No memory leaks
- [ ] Thread cleanup proper

## Documentation

When adding features, update:
- User-facing: `USER_GUIDE.md`
- Technical: `IMPLEMENTATION_COMPLETE.md`
- Deployment: `DEPLOYMENT_GUIDE.md` (if relevant)
- Code comments (for complex logic)

## Resources

- Main instructions: `.copilot-instructions.md`
- User guide: `USER_GUIDE.md`
- Technical docs: `IMPLEMENTATION_COMPLETE.md`
- Deployment: `DEPLOYMENT_GUIDE.md`
- Feature status: `TODO_FEATURES.md`

---

**Remember**: Safety, clarity, and predictability are the top priorities.
