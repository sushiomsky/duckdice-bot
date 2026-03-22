# TUI Interface Guide

## DuckDice Bot Terminal User Interface (TUI)

Two powerful terminal interfaces for DuckDice Bot:

### 1. Modern Textual Interface (Recommended)

**Features:**
- Beautiful, modern terminal UI
- Real-time statistics display
- Interactive bet history table
- Progress indicators
- Rich color scheme
- Mouse support

**Requirements:**
```bash
pip install duckdice-betbot[tui]
# or
pip install textual
```

**Launch:**
```bash
duckdice-tui
# or
python duckdice_tui.py
```

**Keyboard Shortcuts:**
- `Ctrl+S` - Start betting
- `Ctrl+X` - Stop betting
- `Ctrl+Q` - Quit application

**Screenshot:**
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Session Statistics          🎮 Controls                 │
│  💰 Balance: 0.01000000 BTC     Status: ▶ RUNNING          │
│  📈 Profit: +0.00012500 BTC     [Start] [Stop]             │
│  🎲 Bets: 125 (W: 63, L: 62)                                │
│  📊 Win Rate: 50.40%                                        │
├─────────────────────────────────────────────────────────────┤
│  📈 Progress                                                │
│  ████████████████░░░░░░░░░░░░░░ 65%                        │
│  Status: Betting Active                                     │
├─────────────────────────────────────────────────────────────┤
│  📜 BET HISTORY                                             │
│  Time     Amount      Chance  Roll   Result    Profit      │
│  ─────────────────────────────────────────────────────────  │
│  12:34:56 0.00000100  50.00%  45.23  ✓ WIN    +0.00000100 │
│  12:34:57 0.00000100  50.00%  67.89  ✗ LOSS   -0.00000100 │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. Classic NCurses Interface

**Features:**
- Lightweight and fast
- No external dependencies (uses Python stdlib)
- Works on any Unix-like system
- Minimal resource usage
- Classic terminal aesthetics

**Requirements:**
- Python 3.9+ (ncurses included)
- No additional packages needed

**Launch:**
```bash
duckdice-tui --ncurses
# or
python duckdice_tui.py --ncurses
```

**Keyboard Controls:**
- `S` - Start/Resume betting
- `P` - Pause betting
- `X` - Stop betting
- `Q` - Quit

**Screenshot:**
```
        🎲 DUCKDICE BOT - NCURSES INTERFACE 🎲

┌─────────── 📊 STATISTICS ───────────┐ ┌────────── 🎮 CONTROLS ──────────┐
│                                      │ │                                  │
│  Balance:     0.01012500 BTC         │ │  Status:    ▶ RUNNING           │
│  Profit:     +0.00012500 BTC         │ │                                  │
│  Profit %:   +1.25%                  │ │  Keyboard Shortcuts:             │
│                                      │ │    [S] Start/Resume              │
│  Bets: 125                           │ │    [P] Pause                     │
│  Wins: 63        Losses: 62          │ │    [X] Stop                      │
│  Win Rate: 50.40%                    │ │    [Q] Quit                      │
│                                      │ │                                  │
└──────────────────────────────────────┘ └──────────────────────────────────┘

┌──────────────────────────── 📜 BET HISTORY ────────────────────────────────┐
│  Time      Amount        Chance    Roll      Result      Profit            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  12:34:56  0.00000100    50.00%    45.23     WIN ✓      +0.00000100       │
│  12:34:57  0.00000100    50.00%    67.89     LOSS ✗     -0.00000100       │
│  12:34:58  0.00000100    50.00%    23.45     WIN ✓      +0.00000100       │
│  ...                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

              DuckDice Bot v4.9.2 | Made with ❤️ | Press Q to quit
```

---

## Comparison

| Feature              | Textual          | NCurses          |
|---------------------|------------------|------------------|
| Dependencies        | textual package  | None (stdlib)    |
| Resource Usage      | Moderate         | Very Low         |
| Visual Appeal       | Modern, Rich     | Classic, Simple  |
| Mouse Support       | Yes              | No               |
| Colors              | Full RGB         | 8 colors         |
| Animations          | Yes              | No               |
| Compatibility       | Linux/macOS/Win  | Linux/macOS      |
| Installation Size   | ~5 MB            | 0 MB             |

---

## Installation

### Quick Install (Textual)
```bash
# From PyPI (when published)
pip install duckdice-betbot[tui]

# From source
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
pip install -e .[tui]
```

### Minimal Install (NCurses only)
```bash
# No extra dependencies needed
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
pip install -e .
duckdice-tui --ncurses
```

---

## Usage Examples

### Launch with Specific Interface
```bash
# Modern Textual (default)
duckdice-tui

# Classic NCurses
duckdice-tui --ncurses

# Show help
duckdice-tui --help

# Show version
duckdice-tui --version
```

### Direct Python Execution
```bash
# Textual
python src/interfaces/tui/textual_interface.py

# NCurses
python src/interfaces/tui/ncurses_interface.py
```

---

## Features

### Real-time Statistics
- Current balance
- Profit/loss (absolute and percentage)
- Total bets placed
- Win/loss count
- Win rate percentage

### Bet History
- Last 15-20 bets displayed
- Time, amount, chance, roll, result, profit
- Color-coded wins (green) and losses (red)
- Auto-scrolling table
- Dedicated live event log (warnings/errors/session transitions/stats checkpoints)

### Interactive Controls
- Start betting with selected strategy
- Select mode: Simulation, Live (Main), Live (Faucet), Live (TLE)
- Provide TLE hash for Live (TLE) sessions
- Select symbol (BTC/ETH/DOGE/LTC/XRP/TRX/SOL)
- Configure start balance (simulation), max bets, stop loss, and take profit
- Mode-aware fields: TLE hash enabled only in Live (TLE), start balance enabled only in Simulation
- Critical controls are locked while a session is running
- Stop and view summary
- Quit anytime

### Visual Feedback
- Status indicators (Starting, Running, Stop Requested, Complete, Error)
- Progress bars (Textual only)
- Color-coded profit/loss
- Smooth updates
- Strategy description + schema default preview
- Live risk panel: drawdown %, PnL %, stop-loss balance, take-profit balance
- Live analytics line: current/max streaks, average bet, average P/L
- Session summary line after run completion
- Engine text output is streamed into the live event log panel

---

## Tips

1. **Performance**: NCurses is faster for slower terminals
2. **Visuals**: Textual looks better in modern terminal emulators
3. **SSH**: NCurses works better over SSH
4. **Local**: Textual recommended for local usage
5. **Resources**: Use NCurses on resource-constrained systems

---

## Troubleshooting

### Textual not found
```bash
pip install textual
```

### NCurses display issues
```bash
# Set terminal type
export TERM=xterm-256color

# Or use different terminal emulator
```

### Colors not working
```bash
# Enable 256 colors
export TERM=xterm-256color
```

---

## Future Enhancements

- [ ] Live strategy switching during active session
- [ ] Real-time charts (Textual)
- [ ] Configuration persistence
- [ ] Multiple session tabs
- [ ] Export bet history
- [ ] Custom themes

---

**Choose your interface and start betting with style! 🎲**
