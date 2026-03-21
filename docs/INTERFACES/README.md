# DuckDice Bot Interfaces

DuckDice Bot provides three interfaces for different use cases:

## 🖥️ CLI (Command-Line Interface)
**Best for**: Automation, scripting, headless servers

```bash
# Quick start
duckdice run --strategy classic-martingale --bets 100

# See all options
duckdice --help
```

📖 **[Complete CLI Guide](./CLI_GUIDE.md)**

---

## 🎨 TUI (Text User Interface)
**Best for**: Interactive terminal use, live monitoring

```bash
# Launch interactive mode
duckdice interactive
```

Features:
- ✅ Live bet visualization
- ✅ Real-time statistics
- ✅ Strategy switching
- ✅ Keyboard shortcuts

📖 **[Complete TUI Guide](./TUI_GUIDE.md)**

---

## 🐍 Python API
**Best for**: Custom integrations, advanced automation

```python
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig

api = DuckDiceAPI(DuckDiceConfig(api_key="your-key"))
result = api.get_user_info()
```

📖 **[API Documentation](../API_REFERENCE.md)**

---

## Choosing an Interface

| Interface | Automation | Interactive | Monitoring | Ease of Use |
|-----------|------------|-------------|------------|-------------|
| **CLI**   | ✅ Best    | ❌          | ⚠️ Limited | ⭐⭐⭐      |
| **TUI**   | ❌         | ✅ Best     | ✅ Best    | ⭐⭐⭐⭐    |
| **API**   | ✅ Best    | ❌          | ✅ Custom  | ⭐⭐        |

---

## Quick Reference

### CLI One-Liners
```bash
# Run strategy for 50 bets
duckdice run -s martingale -b 50

# Run until profit target
duckdice run -s kelly-capped --profit-target 1.0

# Run with custom config
duckdice run -s adaptive-survival --config my-config.json

# List all strategies
duckdice list-strategies
```

### TUI Keyboard Shortcuts
- `Space` - Pause/Resume
- `q` - Quit
- `s` - Change strategy
- `↑/↓` - Adjust bet amount
- `h` - Toggle high/low
- `?` - Help

### API Common Patterns
```python
# Canonical runtime client path
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig

api = DuckDiceAPI(DuckDiceConfig(api_key="key"))
result = api.play_dice(symbol="BTC", amount="0.00000001", chance="49.5", is_high=True)

# Get balance
balance = api.get_main_balance("BTC")
```

---

**See Also**:
- [All Strategies](../STRATEGIES/README.md)
- [Configuration Guide](../CONFIGURATION.md)
- [Architecture Overview](../ARCHITECTURE/README.md)
