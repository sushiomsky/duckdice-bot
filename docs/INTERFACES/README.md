# DuckDice Bot Interfaces

DuckDice Bot provides four interfaces for different use cases:

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

## 🌐 Web Interface
**Best for**: Browser-based monitoring and control

```bash
python3 duckdice_web.py --host 127.0.0.1 --port 8080
```

Features:
- ✅ Runtime start/stop controls
- ✅ Live event log (SSE with polling fallback)
- ✅ SSE auto-reconnect with exponential backoff (`0.5s` → `10s` cap)
- ✅ SSE endpoint is disconnect-aware and cooperatively yields during burst delivery
- ✅ Recent bets table
- ✅ Strategy schema-driven param defaults
- ✅ Risk panel + session timeline + equity curve
- ✅ Analytics panel (expectancy, profit factor, volatility, bet quantiles)
- ✅ Strategy param validation endpoint and deterministic bet preview
- ✅ Log search/filter controls

API endpoints:
- `GET /api/runtime/dashboard` (aggregated UI payload)
- `GET /api/runtime/events?since=...` (limit is bounded server-side)
- `GET /api/runtime/stream` (SSE with `id` frames; supports `Last-Event-ID` resume, with `since` fallback)
- `GET /api/runtime/timeline` (limit is bounded server-side)
- `GET /api/runtime/equity` (limit is bounded server-side)
- `GET /api/runtime/analytics`
- `POST /api/strategy/{name}/validate` (validates symbol and positive starting_balance)
- `POST /api/strategy/{name}/preview` (validates symbol and positive starting_balance)
- `POST /api/runtime/start` (validates mode/symbol/start_balance/max_bets/stop_loss/take_profit; `live-tle` requires `tle_hash`)
- `POST /api/runtime/stop`

Developer note:
- `interfaces.web` exports `app` lazily, so importing `interfaces.web.runtime_controller`
  does not force-load FastAPI server wiring.

---

## Choosing an Interface

| Interface | Automation | Interactive | Monitoring | Ease of Use |
|-----------|------------|-------------|------------|-------------|
| **CLI**   | ✅ Best    | ❌          | ⚠️ Limited | ⭐⭐⭐      |
| **TUI**   | ❌         | ✅ Best     | ✅ Best    | ⭐⭐⭐⭐    |
| **Web**   | ⚠️ Basic   | ✅ Good     | ✅ Good    | ⭐⭐⭐⭐    |
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
- Textual: `Ctrl+S` start, `Ctrl+X` stop, `Ctrl+Q` quit
- Ncurses: `S` start/resume, `P` pause, `X` stop, `Q` quit

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
