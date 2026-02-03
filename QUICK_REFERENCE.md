# Quick Reference

**DuckDice Bot v4.11.2** - Command cheat sheet

---

## 🚀 Quick Start

```bash
# Install
pip install duckdice-betbot

# Set API key
export DUCKDICE_API_KEY="your-key"

# Run strategy
duckdice run --strategy martingale --bets 50

# Interactive mode
duckdice interactive
```

---

## 📋 Common Commands

### Information
```bash
# List all strategies
duckdice list-strategies

# Describe specific strategy
duckdice describe-strategy classic-martingale

# Show version
duckdice --version

# Get help
duckdice --help
duckdice run --help
```

### Running Strategies
```bash
# Basic run
duckdice run --strategy STRATEGY_NAME --bets 100

# With profit target
duckdice run --strategy paroli --profit-target 1.0

# With stop loss
duckdice run --strategy fibonacci --stop-loss -0.5

# Time-limited
duckdice run --strategy dalembert --duration 3600

# Custom parameters
duckdice run --strategy labouchere --param sequence="1,2,3,4"

# Specific currency
duckdice run --strategy martingale --currency usdt

# From config file
duckdice run --config my-config.json
```

---

**See full guide**: [README.md](README.md) | [All Docs](docs/)

**Version**: 4.11.2 | **Updated**: 2026-02-03
