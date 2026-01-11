# 📘 DuckDice Bot - User Guide

**Version**: 4.0.0 (NiceGUI Complete Edition)  
**Date**: January 11, 2026  
**Audience**: End Users

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Launch the Application

```bash
# Make scripts executable (macOS/Linux only)
chmod +x run_nicegui.sh

# Start the web interface
./run_nicegui.sh
# OR: python gui/app.py
```

### Step 3: Open Browser

Navigate to: **http://localhost:8080**

---

## 🎨 User Interface Overview

The application has **6 main tabs**:

### 1. 📊 Dashboard
Your main control center showing live statistics and charts.

**Features:**
- Real-time statistics (balance, bets, win rate, profit)
- Control buttons (Start, Stop, Pause, Resume)
- 4 interactive charts (expandable)
- Session information
- Loading spinner when bot is active

**How to Use:**
1. Configure strategy in **Strategies** tab first
2. Set up API key in **Settings** tab (for live mode)
3. Click **Start Bot** to begin
4. Monitor statistics in real-time
5. Click **Stop Bot** when done

### 2. 🧠 Strategies
Configure your betting strategy.

**Available Strategies (17 total):**
- **Martingale**: Double bet after loss
- **Anti-Martingale**: Double bet after win
- **D'Alembert**: Increase/decrease by fixed unit
- **Fibonacci**: Follow Fibonacci sequence
- **Labouchere**: Cross off numbers from list
- **Paroli**: Progressive betting after wins
- **Oscar's Grind**: Conservative profit locking
- **Pyramid**: Gradual bet increase
- **Reverse Pyramid**: Gradual bet decrease
- **Double Street**: Two-level progression
- **Flat Betting**: Consistent bet size
- **Percentage Betting**: Fixed % of balance
- **Kelly Criterion**: Optimal bet sizing
- **Reverse D'Alembert**: Opposite of D'Alembert
- **1-3-2-6 System**: Structured progression
- **Whittaker**: Conservative progression
- **Pluscoup**: Win/loss tracking system

**How to Use:**
1. Select strategy from dropdown
2. View strategy details (risk level, pros/cons, tips)
3. Configure parameters in auto-generated form
4. **Save Profile**: Click to save configuration with a name
5. **Load Profile**: Restore previously saved configurations
6. **Delete Profile**: Remove saved profiles

**Example - Martingale Setup:**
```
Strategy: Martingale
Base Bet: 0.00000100 BTC
Target Chance: 49.5%
Max Losses: 5
Multiplier: 2.0
```

### 3. 🧪 Simulator
Test strategies without risking real money.

**Features:**
- Run simulations with virtual balance
- Configurable starting balance
- Number of bets to simulate
- View results instantly

**How to Use:**
1. Set starting balance (e.g., 0.01 BTC)
2. Configure number of bets (e.g., 100)
3. Click **Run Simulation**
4. Review results:
   - Final balance
   - Total profit/loss
   - Win rate
   - Number of wins/losses

**Best Practice:**
Always test new strategies in simulation mode before using real money!

### 4. 📜 History
View all your betting history.

**Features:**
- Complete bet log with all details
- Pagination (25/50/100 bets per page)
- CSV export for analysis
- Filter by session, strategy, date

**Columns:**
- Timestamp
- Amount (bet size)
- Target (win chance %)
- Roll (actual result)
- Won (✓/✗)
- Profit (gain/loss)
- Balance (after bet)
- Strategy used

**How to Export:**
1. Click **Export to CSV** button
2. Opens CSV file with all history
3. Analyze in Excel/Google Sheets

### 5. 📈 Analytics
Comprehensive performance metrics and analysis.

**Key Metrics (6 Cards):**
1. **Win Rate**: % of bets won
2. **Total Profit**: Net profit/loss
3. **ROI**: Return on investment %
4. **Max Drawdown**: Largest balance drop
5. **Profit Factor**: Wins/losses ratio
6. **Sharpe Ratio**: Risk-adjusted return

**Detailed Statistics (Expandable):**
- Total bets, wins, losses
- Total wagered amount
- Gross profit, gross loss
- Average bet size
- Average win, average loss
- Largest win, largest loss
- Longest win streak, longest loss streak
- Current streak
- Standard deviation
- Variance
- Expected value per bet

**Historical Comparison:**
- Compare all sessions side-by-side
- Session ID, strategy name
- Bets, wins, losses, win rate
- Starting balance, ending balance
- Profit, profit %
- Duration

**Best Performers:**
- Top sessions by ROI
- Top sessions by win rate
- Top sessions by total profit

**How to Use:**
1. Run bot to collect data
2. Click **Analytics** tab
3. Review current session metrics
4. Expand **Detailed Statistics** for full breakdown
5. Check **Historical Comparison** to compare sessions
6. Click **Refresh** button to update with latest data

### 6. ⚙️ Settings
Configure application settings and API connection.

**Settings:**

**API Configuration:**
- **API Key**: Your DuckDice Bot API key (required for live mode)
- **Test Connection**: Verify API key works
- **Get API Key**: Link to DuckDice settings

**Basic Settings:**
- **Currency**: btc, eth, ltc, doge, etc.
- **Starting Balance**: For simulation mode

**Bot Control:**
- **Bet Delay**: Seconds between bets (default: 1)
- **Mode**: Simulation or Live

**Stop Conditions:**
- **Profit Target**: Stop when profit reaches %
- **Loss Limit**: Stop when loss reaches %
- **Max Bets**: Stop after X bets
- **Min Balance**: Stop if balance drops below

**How to Get API Key:**
1. Visit https://duckdice.io
2. Log in to your account
3. Go to Account Settings
4. Navigate to **Bot API** section
5. Click **Generate API Key**
6. Copy the key
7. Paste into Settings → API Key field
8. Click **Test Connection** to verify

---

## 🎮 Usage Workflows

### Workflow 1: Test a Strategy (Simulation)

```
1. Open application (http://localhost:8080)
2. Go to **Strategies** tab
3. Select "Martingale"
4. Set parameters:
   - Base Bet: 0.00000100
   - Target: 49.5
   - Max Losses: 5
   - Multiplier: 2.0
5. Go to **Settings** tab
6. Ensure Mode: Simulation
7. Set Starting Balance: 0.01
8. Set Stop Conditions:
   - Profit Target: 50%
   - Loss Limit: 30%
   - Max Bets: 100
9. Go to **Dashboard** tab
10. Click **Start Bot**
11. Watch real-time statistics
12. Bot stops automatically at conditions
13. Go to **Analytics** tab
14. Review performance metrics
15. Decide if strategy is viable
```

### Workflow 2: Run Live Betting

```
1. Test strategy in simulation first!
2. Go to **Settings** tab
3. Enter API Key
4. Click **Test Connection** (must be successful)
5. Set Mode: Live
6. Set conservative Stop Conditions:
   - Profit Target: 20%
   - Loss Limit: 10%
   - Max Bets: 50
   - Min Balance: 0.001
7. Set Bet Delay: 1-2 seconds
8. Go to **Strategies** tab
9. Configure strategy with small bets
10. Go to **Dashboard** tab
11. Click **Start Bot**
12. WARNING appears: "Live mode - using real money"
13. Confirm and proceed
14. Monitor closely
15. Stop manually or wait for auto-stop
16. Review results in Analytics
```

### Workflow 3: Save and Reuse Strategies

```
1. Go to **Strategies** tab
2. Select and configure strategy
3. Click **Save Profile** button
4. Enter profile name: "Conservative Martingale"
5. Success notification appears
6. Profile listed in profiles section

Later:
7. Go to **Strategies** tab
8. Click **Load Profile** button
9. Select "Conservative Martingale"
10. All parameters restored
11. Ready to use
```

### Workflow 4: Analyze Performance

```
1. Run bot for multiple sessions
2. Go to **Analytics** tab
3. Review current session:
   - Win Rate: 51.2%
   - ROI: +15.3%
   - Profit Factor: 1.25
   - Max Drawdown: -8.5%
4. Expand **Detailed Statistics**
5. Check streaks:
   - Longest win streak: 7
   - Longest loss streak: 4
6. Scroll to **Historical Comparison**
7. Compare all sessions:
   - Session 1: Martingale, ROI: +12%
   - Session 2: Fibonacci, ROI: -5%
   - Session 3: D'Alembert, ROI: +8%
8. Review **Best Performers**
9. Identify most profitable strategy
10. Focus future sessions on winners
```

### Workflow 5: Export Data for Analysis

```
1. Go to **History** tab
2. Click **Export to CSV** button
3. File downloads: bet_history_YYYYMMDD_HHMMSS.csv
4. Open in Excel/Google Sheets
5. Create pivot tables
6. Generate custom charts
7. Perform statistical analysis

Alternative:
8. Go to **Dashboard** tab
9. Scroll to Charts section
10. Click **Export All Charts**
11. 4 PNG files saved:
    - balance_over_time.png
    - profit_loss.png
    - win_loss_distribution.png
    - streak_analysis.png
12. Use in reports/presentations
```

---

## 📊 Understanding the Charts

### Chart 1: Balance Over Time
**What it shows:**
- Line chart of your balance throughout session
- Blue line = balance trend
- Blue fill = area under curve

**How to read:**
- Upward trend = profitable session
- Downward trend = losing session
- Volatility = risk level

### Chart 2: Cumulative Profit/Loss
**What it shows:**
- Running total of profit/loss
- Green zones = profitable periods
- Red zones = losing periods

**How to read:**
- Above zero = net profit
- Below zero = net loss
- Steeper slope = faster profit/loss rate

### Chart 3: Win/Loss Distribution
**What it shows:**
- Pie chart: Win/Loss ratio
- Histogram: Distribution of outcomes

**How to read:**
- Larger green slice = more wins
- Histogram peaks = most common results

### Chart 4: Streak Analysis
**What it shows:**
- Bar chart of winning and losing streaks
- Green bars = win streaks
- Red bars = loss streaks
- Annotations show maximum streaks

**How to read:**
- Tall green bars = good win streaks
- Tall red bars = risky losing streaks
- Balanced = consistent performance

---

## 🔒 Safety Features

### 1. Simulation Mode Default
Application always starts in simulation mode. You must explicitly enable live mode.

### 2. API Key Validation
Cannot start live betting without valid API key and successful connection test.

### 3. Auto-Stop Conditions
Bot automatically stops when any condition is met:
- Profit target reached
- Loss limit exceeded
- Maximum bets reached
- Balance drops below minimum

### 4. Live Mode Warnings
Clear warnings when starting bot in live mode with real money.

### 5. Rate Limiting
Configurable delay between bets prevents aggressive betting patterns.

### 6. Stop Button
Emergency stop button always available during bot operation.

---

## 💡 Tips and Best Practices

### General Tips
1. **Start Small**: Test with minimal bets
2. **Use Simulation**: Always test strategies first
3. **Set Limits**: Configure stop conditions
4. **Monitor Closely**: Watch during live sessions
5. **Be Conservative**: Better safe than sorry
6. **Track Performance**: Use analytics regularly
7. **Diversify**: Try different strategies
8. **Learn Gradually**: Master one strategy at a time

### Strategy Selection
- **Low Risk**: Flat Betting, Percentage Betting
- **Medium Risk**: D'Alembert, Oscar's Grind, Fibonacci
- **High Risk**: Martingale, Anti-Martingale, Labouchere

### Risk Management
- Never bet more than 1-2% of balance per bet
- Set loss limit to 10-20% maximum
- Use profit targets to lock in gains
- Diversify across multiple strategies
- Keep emergency funds separate

### When to Stop
- Reached profit target ✓
- Hit loss limit ✗
- Feeling emotional 😰
- Unclear performance 🤔
- Extended losing streak 📉
- Need to reassess strategy 🔄

---

## 🐛 Common Issues

### Issue 1: "Port already in use"
**Solution:**
```bash
# Kill existing process
lsof -ti:8080 | xargs kill -9

# Or use different port
python gui/app.py --port 8081
```

### Issue 2: "Module not found"
**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 3: "API connection failed"
**Solution:**
1. Check internet connectivity
2. Verify API key is correct
3. Test connection in Settings tab
4. Check DuckDice API status

### Issue 4: Charts not displaying
**Solution:**
1. Run bot for at least 10 bets
2. Refresh page
3. Check browser console for errors

### Issue 5: Database locked
**Solution:**
```bash
# Close all connections
# Restart application
python gui/app.py
```

---

## 📖 Glossary

**API Key**: Authentication token for DuckDice Bot API

**Balance**: Current amount in your account

**Base Bet**: Starting bet size for strategy

**BTC**: Bitcoin cryptocurrency

**CSV**: Comma-separated values file format

**Drawdown**: Decline from peak balance

**Live Mode**: Real betting with actual money

**Martingale**: Betting strategy that doubles after losses

**Profit Factor**: Ratio of gross profit to gross loss

**ROI**: Return on investment percentage

**Session**: Single bot run from start to stop

**Sharpe Ratio**: Risk-adjusted return metric

**Simulation Mode**: Testing with virtual money

**Stop Condition**: Rule that triggers auto-stop

**Strategy**: Betting system/algorithm

**Target Chance**: Probability of winning bet (%)

**Win Rate**: Percentage of bets won

---

## 🎓 Advanced Features

### Profile Management
Save unlimited strategy configurations for quick reuse.

### Session Comparison
Compare performance across different sessions and strategies.

### Data Export
Export all data for advanced analysis in external tools.

### Chart Export
Save professional charts as PNG images.

### Real-time Updates
Dashboard updates live as bets are placed.

### Database Persistence
All data automatically saved to SQLite database.

---

## 📞 Getting Help

### Documentation
- **User Guide**: This file
- **Deployment Guide**: DEPLOYMENT_GUIDE.md
- **Technical Details**: IMPLEMENTATION_COMPLETE.md
- **README**: README.md

### Support
- **GitHub Issues**: Report bugs and request features
- **DuckDice Support**: Contact for API issues

### Community
- Share strategies
- Compare results
- Learn from others

---

## ✅ Quick Reference

### Essential Commands
```bash
# Start application
python gui/app.py

# Run tests
cd tests/gui && python test_gui_components.py

# Export database
sqlite3 data/duckdice_bot.db ".dump" > backup.sql

# Check logs
tail -f logs/app.log
```

### Essential URLs
- **Web Interface**: http://localhost:8080
- **DuckDice**: https://duckdice.io
- **API Settings**: https://duckdice.io/account/settings

### Keyboard Shortcuts
- **Ctrl+C**: Stop server
- **Ctrl+R**: Refresh page
- **Ctrl+W**: Close tab

---

## 🎉 Congratulations!

You're now ready to use the DuckDice Bot effectively!

**Remember:**
- 🧪 Test in simulation first
- 💰 Bet responsibly
- 📊 Monitor analytics
- 🛡️ Use stop conditions
- 📚 Keep learning

**Happy betting!** 🎲

---

**Version**: 4.0.0  
**Last Updated**: January 11, 2026  
**Status**: Production Ready ✅
