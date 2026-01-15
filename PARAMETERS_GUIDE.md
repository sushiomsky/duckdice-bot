# Strategy Parameters Guide

All strategies support customizable parameters. You can pass them via command-line, configure them interactively, or save them in profiles.

## Methods to Configure Parameters

### 1. Command-Line Parameters

Use `-P` or `--param` to pass individual parameters:

```bash
python3 duckdice_cli.py run \
  -s classic-martingale \
  -m simulation \
  -P base_amount=0.00001 \
  -P multiplier=1.5 \
  -P max_streak=6
```

### 2. Interactive Configuration

Use `-I` or `--interactive-params` to be prompted for each parameter:

```bash
python3 duckdice_cli.py run -s fibonacci -I
```

This will prompt:
```
Configure parameters (press Enter for current value):
base_amount (Base bet amount (1 unit)) [0.000001]: 0.0001
chance (Win chance percent) [49.5]: 50
is_high (Bet on High or Low) [True]: True
max_level (Maximum Fibonacci level) [15]: 10
```

### 3. Save in Profiles

Create a profile with configured parameters:

```bash
# Interactive profile creation
python3 duckdice_cli.py save-profile my-aggressive-martingale \
  -s classic-martingale

# Then configure parameters when prompted
```

Use the profile:
```bash
python3 duckdice_cli.py run -p my-aggressive-martingale -m simulation
```

## View Strategy Parameters

### Show All Strategies with Parameters

```bash
python3 duckdice_cli.py strategies --verbose
```

### Show Specific Strategy Details

```bash
python3 duckdice_cli.py show classic-martingale
```

This displays:
- Description
- Risk level and metadata
- Full parameter list with types and defaults
- Usage example

## Common Parameters by Strategy

### Classic Martingale

```bash
-P base_amount=0.000001    # Base bet (decimal string)
-P chance=49.5             # Win chance %
-P is_high=true           # Bet High (true) or Low (false)
-P multiplier=2.0         # Loss multiplier (typically 2.0)
-P max_streak=10          # Max losses before reset
-P reset_on_win=true      # Reset to base on win
```

### Fibonacci

```bash
-P base_amount=0.000001    # Base bet (1 unit)
-P chance=49.5             # Win chance %
-P is_high=true           # Bet High or Low
-P max_level=15           # Max Fibonacci level
```

### D'Alembert

```bash
-P base_amount=0.000001    # Base bet
-P chance=49.5             # Win chance %
-P is_high=true           # Bet High or Low
-P step=0.000001          # Increase/decrease step
-P max_increase=10        # Max bet increases
```

### Paroli

```bash
-P base_amount=0.000001    # Base bet
-P chance=49.5             # Win chance %
-P is_high=true           # Bet High or Low
-P multiplier=2.0         # Win multiplier
-P target_streak=3        # Target win streak
```

### RNG Analysis Strategy

```bash
-P base_amount=0.000001    # Base bet
-P chance=50               # Win chance %
-P is_high=false          # Bet High or Low
-P win_threshold=0.5      # Win rate for increase
-P loss_multiplier=1.5    # Loss multiplier
-P win_multiplier=1.0     # Win multiplier
-P max_multiplier=8.0     # Max bet multiplier
-P use_patterns=false     # Use pattern detection
-P pattern_window=10      # Pattern analysis window
```

### Kelly Capped

```bash
-P base_amount=0.000001    # Base bet
-P chance=49.5             # Win chance %
-P kelly_fraction=0.1     # Kelly fraction (conservative)
-P max_bet_fraction=0.05  # Max % of bankroll
-P min_bet=0.000001       # Minimum bet
```

### Faucet Grind

```bash
-P target_usd=20.0        # Target USD value
-P base_chance=50.0       # Base win chance
-P aggressive=false       # Aggressive mode
```

## Parameter Types

The CLI automatically converts parameter types:

| Type | Example | Notes |
|------|---------|-------|
| `str` | `base_amount=0.00001` | Decimal amounts |
| `int` | `max_streak=5` | Whole numbers |
| `float` | `multiplier=1.5` | Decimals |
| `bool` | `is_high=true` | true/false, 1/0, yes/no |

## Examples

### Conservative Martingale

```bash
python3 duckdice_cli.py run \
  -s classic-martingale \
  -m simulation \
  -P base_amount=0.00000100 \
  -P multiplier=1.5 \
  -P max_streak=6 \
  -P chance=49.5 \
  --stop-loss -0.2 \
  --max-bets 100
```

### Aggressive Fibonacci

```bash
python3 duckdice_cli.py run \
  -s fibonacci \
  -m simulation \
  -P base_amount=0.0001 \
  -P max_level=20 \
  -P chance=48 \
  --take-profit 1.0 \
  --max-bets 500
```

### Experimental RNG Analysis

```bash
python3 duckdice_cli.py run \
  -s rng-analysis-strategy \
  -m simulation \
  -P base_amount=0.0001 \
  -P use_patterns=true \
  -P pattern_window=5 \
  -P loss_multiplier=1.3 \
  -P max_multiplier=5.0 \
  --max-bets 200
```

### Profile-Based Betting

```bash
# Create profile
python3 duckdice_cli.py save-profile safe-dalembert \
  -s dalembert

# Configure when prompted:
# base_amount: 0.00001
# step: 0.00001
# max_increase: 5
# chance: 49.5

# Use profile
python3 duckdice_cli.py run \
  -p safe-dalembert \
  -m simulation \
  --max-bets 100
```

## Tips

💡 **Start Conservative**: Use smaller base_amount and lower multipliers  
💡 **Test First**: Always test in simulation before live betting  
💡 **Check Defaults**: Run `python3 duckdice_cli.py show <strategy>` to see defaults  
💡 **Save Profiles**: Save working configurations for reuse  
💡 **Combine with Limits**: Always use --stop-loss and --take-profit  

## Validation

The CLI validates parameters:
- Type checking (int, float, bool, string)
- Unknown parameters trigger warnings
- Invalid values fall back to defaults
- Schema-based validation

Example validation:
```bash
# Invalid type
-P max_streak=abc  # Warning: Invalid value, using default

# Unknown parameter
-P invalid_param=123  # Warning: Unknown parameter

# Valid
-P max_streak=5  # ✓ Accepted
```

## Quick Reference

| Task | Command |
|------|---------|
| See all strategy parameters | `python3 duckdice_cli.py show <strategy>` |
| List strategies with params | `python3 duckdice_cli.py strategies -v` |
| Pass parameters | `-P key=value` (multiple allowed) |
| Interactive params | `-I` or `--interactive-params` |
| Save configured profile | `python3 duckdice_cli.py save-profile <name> -s <strategy>` |
| Use profile | `python3 duckdice_cli.py run -p <profile>` |

---

**See also**: CLI_GUIDE.md, README.md
