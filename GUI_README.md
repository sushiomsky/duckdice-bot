# NiceGUI Web Interface

Modern, safety-focused web interface for DuckDice Bot built with [NiceGUI](https://nicegui.io/).

## Quick Start

```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Run the web interface
python gui/app.py

# Or use the convenience script
./run_gui_web.sh
```

The interface will open automatically at **http://localhost:8080**

## Features

### 🎯 Dashboard
- **Live bot control**: Start, Stop, Pause, Resume buttons
- **Real-time statistics**: Balance, profit/loss, win rate, current streak
- **Status indicators**: Color-coded status badges (green=running, yellow=paused, red=stopped)
- **Session info**: Strategy, mode, total bets, uptime
- **Auto-updates**: UI refreshes every 250ms during operation

### 🎲 Strategies
- **Strategy selector**: Choose from Martingale, Reverse Martingale, D'Alembert, Fibonacci, Fixed Bet
- **Dynamic parameters**: Configure base bet, target chance, multipliers, limits
- **Validation**: Real-time input validation for all parameters
- **Profiles**: Save and load strategy configurations as JSON files
- **Apply to bot**: One-click application of strategy settings

### 🧪 Simulator
- **Offline testing**: Run simulations without risking real funds
- **Configurable**: Set starting balance and number of rolls
- **Live results**: Watch simulation progress in real-time
- **Analytics**: Final balance, profit/loss, win rate, max drawdown
- **History view**: See last 10 bets with results
- **CSV export**: Download simulation results for analysis

### 📊 History
- **Bet table**: Paginated view of all bets (50 per page)
- **Summary stats**: Total bets, wins, losses, win rate, P/L
- **Detailed records**: Timestamp, result, bet amount, chance, roll, payout, profit, balance
- **CSV export**: Download complete bet history
- **Clear history**: Reset all records (with confirmation)

### ⚙️ Settings
- **API configuration**: Enter and test DuckDice API key
- **Stop conditions**: Auto-stop on profit%, loss%, max bets, min balance
- **Simulation mode**: Toggle between safe simulation and live betting
- **Dark mode**: Switch between dark/light themes
- **Advanced**: Bet delay, log level, update interval

## Safety Features

### 🛡️ Core Safety Principles
1. **Simulation by default**: Always starts in simulation mode
2. **No auto-start**: Bot never starts automatically
3. **Emergency stop**: Stop button always visible and accessible when running
4. **Visual warnings**: Color-coded indicators for status and risk
5. **Input validation**: All parameters validated before use

### ⚠️ Live Mode Protection
- Simulation mode toggle with warning dialog
- Red "LIVE" badge when in real money mode
- API key required for live trading
- Confirmation dialogs for dangerous actions

### 🔒 Thread Safety
- All state updates use thread-safe locking
- Bot runs in background thread, never blocks UI
- Clean shutdown with event-based stopping
- No race conditions in concurrent access

## Architecture

### Component Structure
```
gui/
├── app.py              # Entry point, tab navigation
├── state.py            # Thread-safe global state
├── bot_controller.py   # Bot execution engine
├── utils.py            # Validation & formatting
├── dashboard.py        # Main control interface
├── strategies_ui.py    # Strategy configuration
├── simulator.py        # Offline simulation
├── history.py          # Bet history & analytics
└── settings.py         # Configuration & preferences
```

### State Management
- **AppState**: Single source of truth for all bot state
- **Thread-safe**: Uses `threading.Lock` for concurrent access
- **Singleton pattern**: Global `app_state` instance
- **Reactive updates**: UI components watch state changes

### Bot Controller
- **BotController**: Manages bot lifecycle (start/stop/pause/resume)
- **Background thread**: Bot runs in daemon thread
- **Event-based**: Uses `threading.Event` for clean control
- **Callback pattern**: Updates UI via registered callback function
- **Simulation mode**: Generates fake bets for safe testing

### Update Cycle
```
Bot Thread (every 250ms):
1. Generate/execute bet
2. Update app_state
3. Call update_callback()
   └─> Dashboard.update_display()
       └─> Refresh UI elements
```

## Usage Guide

### First Time Setup
1. **Start the interface**: `python gui/app.py`
2. **Go to Settings**: Configure stop conditions and preferences
3. **Choose Strategy**: Go to Strategies tab, select and configure
4. **Test in Simulator**: Go to Simulator tab, run offline tests
5. **Review Results**: Check History tab for bet records

### Running Simulations
1. Go to **Simulator** tab
2. Set starting balance (e.g., 0.001 BTC)
3. Set number of rolls (e.g., 100)
4. Configure strategy in **Strategies** tab if needed
5. Click **Run Simulation**
6. Watch results in real-time
7. Export CSV when complete

### Live Trading (Real Money)
⚠️ **WARNING**: Live mode uses real Bitcoin. Test thoroughly first!

1. Get API key from DuckDice account settings
2. Go to **Settings** tab
3. Enter API key and click **Test Connection**
4. **Disable** Simulation Mode (toggle will show warning)
5. Set stop conditions (profit%, loss%, max bets)
6. Go to **Dashboard** tab
7. Verify strategy is correct
8. Click **Start Bot**
9. Monitor in real-time
10. Use **Emergency Stop** if needed

### Stop Conditions
Configure auto-stop triggers in Settings:
- **Max Profit %**: Stop when profit reaches X% of starting balance
- **Max Loss %**: Stop when loss reaches X% of starting balance
- **Max Bets**: Stop after N total bets
- **Min Balance**: Stop when balance falls below X BTC

Set to 0 to disable any condition.

## Keyboard Shortcuts
(Not yet implemented - planned feature)
- `Ctrl+S`: Start/Stop bot
- `Ctrl+P`: Pause/Resume bot
- `Ctrl+E`: Emergency stop
- `Ctrl+D`: Toggle dark mode

## Performance

### Response Times
- Button clicks: <100ms
- Page load: <1 second
- UI updates: Every 250ms
- Bet execution: 1-2 seconds (with delay)

### Resource Usage
- RAM: ~50-100MB
- CPU: <5% during operation
- Network: Minimal (only API calls in live mode)

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or change port in app.py
ui.run(port=8081)
```

### UI Not Updating
- Check browser console for JavaScript errors
- Refresh page (F5)
- Restart application

### Bot Not Starting
- Check strategy is configured in Strategies tab
- Verify simulation mode or API key for live mode
- Check console logs for errors

### Simulation vs Live Mode
- **Simulation**: Green badge, generates fake bets
- **Live**: Red badge, requires API key, uses real money

## Development

### Adding New Features
See `.copilot-instructions.md` for development guidelines:
- Follow UX/Safety rules strictly
- Use thread-safe state updates
- Add validation for all inputs
- Test in simulation mode first

### Code Style
- Type hints for all functions
- Docstrings for classes and methods
- Keep functions focused and small
- Use descriptive variable names

### Testing
```bash
# Run in simulation mode
python gui/app.py

# Check thread safety
# - Rapid start/stop cycles
# - Multiple parameter changes
# - Stop condition triggers
```

## Known Limitations

### Current Limitations
1. **Strategy loading**: Hardcoded strategies, not dynamically loaded from `src/betbot_strategies/`
2. **API integration**: Live mode not fully implemented (raises NotImplementedError)
3. **Charts**: Text-based results, matplotlib charts planned
4. **Keyboard shortcuts**: Not yet implemented
5. **Multi-user**: Single user only (shared state)

### Planned Features
- [ ] Dynamic strategy loading from src/
- [ ] Matplotlib charts for balance history
- [ ] Real-time API connection testing
- [ ] Multi-currency support
- [ ] Backup/restore bet history
- [ ] Custom strategy editor
- [ ] Mobile-responsive layout
- [ ] Webhook notifications

## Security

### Best Practices
1. **Never commit API keys**: Keep them in environment variables or secure storage
2. **Use simulation mode**: Test all strategies offline first
3. **Set stop losses**: Always configure max loss% for live trading
4. **Monitor actively**: Watch the bot during live operation
5. **Start small**: Begin with tiny bets to verify behavior

### API Key Storage
Currently stored in app_state (memory only). For production:
```python
# Use environment variable
import os
api_key = os.getenv('DUCKDICE_API_KEY')

# Or encrypted file
from cryptography.fernet import Fernet
# ... encryption code
```

## Support

### Getting Help
1. Check this documentation
2. Review `.copilot-instructions.md` for technical details
3. Check `PROJECT_STRUCTURE.md` for architecture
4. See `CONTRIBUTING.md` for development guidelines

### Reporting Issues
Include:
- Steps to reproduce
- Expected vs actual behavior
- Console logs
- Screenshots if UI-related

## License

Same as DuckDice Bot main project - see LICENSE file.

---

**Built with ❤️ using NiceGUI | Safety First, Always**
