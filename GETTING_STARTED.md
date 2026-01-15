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

#### Option A: NiceGUI Web Interface (Recommended)
```bash
python3 run_nicegui.sh
# or
python3 -m gui.app
```

Then open: http://localhost:8080

#### Option B: Tkinter Desktop GUI
```bash
python3 duckdice_gui_ultimate.py
```

#### Option C: Command Line
```bash
python3 duckdice.py
```

### 3. Get Your API Key

1. Go to https://duckdice.io
2. Login to your account
3. Navigate to: Account → Settings → Bot API
4. Generate or copy your API key

### 4. Start Betting

**Web Interface:**
1. Open http://localhost:8080
2. Go to Settings → Enter API key
3. Click "Test Connection"
4. Choose a strategy
5. Configure parameters
6. Start betting!

**Desktop GUI:**
1. Launch `duckdice_gui_ultimate.py`
2. Enter API key
3. Select strategy and currency
4. Configure auto-bet settings
5. Click Start!

## Documentation

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Deployment**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Tkinter Enhancements**: [docs/tkinter/](docs/tkinter/)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

## Features

- 🎯 17 built-in betting strategies
- 🌐 Modern web interface (NiceGUI)
- 🖥️ Desktop GUI (Tkinter)
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
