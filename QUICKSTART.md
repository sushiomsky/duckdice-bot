# 🚀 Quick Start - DuckDice Bot Web Interface

**Version**: v3.10.0  
**Status**: ✅ Production Ready (Simulation Mode)  
**Last Updated**: January 9, 2026

---

## Launch in 30 Seconds

```bash
cd /Users/tempor/Documents/duckdice-bot
./run_nicegui.sh
```

Opens at: **http://localhost:8080**

---

## First-Time Setup

### 1. Configure Settings
Go to **Settings** tab:
- ✅ Verify "Simulation Mode" is enabled (default)
- Set stop conditions:
  - Max Profit %: 10
  - Max Loss %: 5
  - Max Bets: 100

### 2. Choose Strategy
Go to **Strategies** tab:
- Select strategy: **Martingale** (recommended for testing)
- Configure parameters:
  - Base Bet: 0.00000001 BTC
  - Win Chance: 49.5%
  - Multiplier: 2.0
- Click **"Apply to Bot"**

### 3. Run Simulation
Go to **Simulator** tab:
- Starting Balance: **0.001 BTC**
- Number of Rolls: **100**
- Click **"Run Simulation"**
- Watch results in real-time
- Export CSV when complete

### 4. View Results
Go to **History** tab:
- See all bets with details
- View summary statistics
- Export to CSV for analysis

---

## Available Features

### 📊 Dashboard
- Real-time bot control (Start/Stop/Pause/Resume)
- Live statistics (balance, P/L, win rate, streaks)
- Auto-refresh every 250ms
- Emergency stop always accessible

### 🎲 Strategies (5 Available)
1. **Martingale** - Double on loss
2. **Reverse Martingale** - Double on win
3. **D'Alembert** - Incremental adjustments
4. **Fibonacci** - Fibonacci sequence
5. **Fixed Bet** - Constant amount

### 🧪 Simulator
- Offline testing (no real money)
- Configurable balance and roll count
- Real-time analytics
- CSV export

### 📈 History
- Paginated bet table (50/page)
- Summary statistics
- CSV export
- Clear history option

### ⚙️ Settings
- API configuration
- Stop conditions (4 types)
- Simulation/Live mode toggle
- Dark mode
- Advanced settings

---

## Safety Features

✅ **Simulation by default** - No real money at risk  
✅ **No auto-start** - Manual control required  
✅ **Emergency stop** - Always accessible  
✅ **Input validation** - All fields checked  
✅ **Stop conditions** - Auto-stop on limits  

---

## Alternative Launch Methods

```bash
# Method 1: Quick script
./run_nicegui.sh

# Method 2: Alternative script
./run_gui_web.sh

# Method 3: Direct Python
source venv/bin/activate
python3 gui/app.py
```

---

## Troubleshooting

### Port Already in Use
```bash
lsof -ti:8080 | xargs kill -9
./run_nicegui.sh
```

### UI Not Updating
- Refresh browser (F5)
- Check console for errors
- Restart application

### Dependencies Missing
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## Documentation

- **[START_HERE.md](START_HERE.md)** - Navigation guide
- **[GUI_README.md](GUI_README.md)** - Complete manual (9 KB)
- **[NICEGUI_IMPLEMENTATION.md](NICEGUI_IMPLEMENTATION.md)** - Technical docs
- **[TEST_RESULTS.md](TEST_RESULTS.md)** - Test results

---

## Tips

1. **Always start in simulation mode** to test strategies
2. **Set stop conditions** before live trading
3. **Export results** regularly for analysis
4. **Monitor actively** during operation
5. **Test thoroughly** before using real money

---

## Next Steps

1. ✅ Launch interface: `./run_nicegui.sh`
2. ✅ Test in simulator
3. ✅ Try different strategies
4. ✅ Export results to CSV
5. 📖 Read full documentation

---

**Ready to start? Run: `./run_nicegui.sh`** 🚀

*All features tested and working • No real money at risk in simulation mode*
