# Getting Started with DuckDice Bot

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/duckdice-bot.git
cd duckdice-bot

# Install dependencies
pip install -r requirements.txt
```

### 2. Choose Your Interface

#### Option A: Textual TUI (Recommended)
```bash
python3 duckdice_tui.py
```

Use `Ctrl+S` to start, `Ctrl+X` to stop, `Ctrl+Q` to quit.

#### Option B: Classic ncurses TUI
```bash
python3 duckdice_tui.py --ncurses
```

#### Option C: Command Line
```bash
python3 duckdice_cli.py interactive
```

#### Option D: Web Dashboard (Phase 1)
```bash
python3 duckdice_web.py --host 127.0.0.1 --port 8080
```
Then open: `http://127.0.0.1:8080`

### 3. Get Your API Key

1. Go to https://duckdice.io
2. Login to your account
3. Navigate to: Account → Settings → Bot API
4. Generate or copy your API key

### 4. Start Betting

**Textual TUI:**
1. Launch `duckdice_tui.py`
2. Select strategy, symbol, and mode
3. If live mode, configure API key in `~/.duckdice/config.json` or `DUCKDICE_API_KEY`
4. Set stop conditions (max bets, stop loss, take profit)
5. Press `Ctrl+S` to start, monitor event log/analytics, press `Ctrl+X` to stop

## Documentation

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Deployment**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Interfaces**: [docs/INTERFACES/README.md](docs/INTERFACES/README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

## Features

- 🎯 17 built-in betting strategies
- 🖥️ Modern terminal UI (Textual + ncurses)
- 📊 Real-time analytics and charts
- 💾 Bet history and session tracking
- 🔒 Secure API integration
- 🎨 Dark/Light themes
- 📈 Live profit/loss tracking

## Need Help?

- Check [USER_GUIDE.md](USER_GUIDE.md)
- Read [CONTRIBUTING.md](CONTRIBUTING.md)
- Review documentation in [docs/](docs/)

## Safety First

⚠️ **Important**: 
- Always test in simulation mode first
- Use stop-loss limits
- Never bet more than you can afford to lose
- This is for educational purposes

---

**Ready to start?** Choose your interface and follow the steps above!
