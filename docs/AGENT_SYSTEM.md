# Autonomous Agent System

The agent system provides autonomous strategy evaluation, optimization, and adaptive execution for the DuckDice bot.

## Architecture

```
src/agents/
├── __init__.py             # Package exports
├── simulation.py           # StrategySimulator — drives real strategies with provably-fair dice
├── metrics.py              # EV, Sharpe, drawdown, risk of ruin, composite scoring
├── strategy_analyst.py     # Evaluate, rank, prune, optimize, hall of fame
├── gambler_agent.py        # Adaptive strategy selection and risk management
└── memory.py               # Persistent JSON-backed ecosystem knowledge store
```

## CLI Commands

### `analyze` — Evaluate strategies

```bash
# Evaluate all strategies
python duckdice_cli.py analyze

# Evaluate a single strategy with custom settings
python duckdice_cli.py analyze -s kelly-capped -r 1000 --seeds 20

# Exclude specific strategies
python duckdice_cli.py analyze --exclude nano-range-hunter oracle-engine
```

**Flags:**
| Flag | Default | Description |
|------|---------|-------------|
| `-s` / `--strategy` | (all) | Evaluate a single strategy |
| `-r` / `--rounds` | 500 | Simulation rounds per seed |
| `--seeds` | 10 | Number of random seeds |
| `-b` / `--balance` | 100.0 | Starting balance |
| `--exclude` | (none) | Strategies to skip |
| `--data-dir` | `data/agents` | Output directory |

### `optimize` — Grid-search parameter optimization

```bash
# Optimize base_amount for a strategy
python duckdice_cli.py optimize -s kelly-capped \
  --grid base_amount=0.00001,0.0001,0.001

# Multi-parameter search
python duckdice_cli.py optimize -s martingale-classic \
  --grid base_amount=0.00001,0.0001 \
  --grid multiplier=1.5,2.0,2.5
```

**Flags:**
| Flag | Default | Description |
|------|---------|-------------|
| `-s` / `--strategy` | (required) | Strategy to optimize |
| `--grid` | (required) | `key=val1,val2,...` (repeatable) |
| `-r` / `--rounds` | 500 | Rounds per evaluation |
| `--seeds` | 10 | Seeds per evaluation |

### `agent-report` — View results

```bash
# Show last evaluation results
python duckdice_cli.py agent-report

# Show hall of fame (top strategies across all evaluations)
python duckdice_cli.py agent-report --hall-of-fame

# Show session history
python duckdice_cli.py agent-report --sessions

# Show memory summary
python duckdice_cli.py agent-report --memory
```

### `run-autonomous` — Full autonomous pipeline

Runs the complete analyst → select → simulate → report pipeline in one command.

```bash
# Default autonomous run (balanced mode)
python duckdice_cli.py run-autonomous

# Aggressive mode with evolution enabled
python duckdice_cli.py run-autonomous --mode aggressive --evolve

# Conservative with custom session length
python duckdice_cli.py run-autonomous --mode conservative --session-rounds 2000

# Wager farming with custom risk
python duckdice_cli.py run-autonomous --mode wager_farming --stop-loss -0.50 --take-profit 3.0
```

**Flags:**
| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `balanced` | `conservative`, `balanced`, `aggressive`, `wager_farming` |
| `--session-rounds` | 1000 | Bets in the simulation session |
| `--stop-loss` | -0.35 | Stop-loss percentage |
| `--take-profit` | 2.0 | Take-profit percentage |
| `--evolve` | off | Enable strategy evolution before session |
| `--mutations` | 3 | Mutations per top strategy |

### `evolve` — Strategy evolution

Mutates parameters of top performers and re-evaluates.

```bash
# Evolve top 3 strategies with 3 mutations each
python duckdice_cli.py evolve

# Evolve top 5 with more mutations
python duckdice_cli.py evolve --top 5 --mutations 5
```

## Metrics Computed

Each strategy evaluation produces:

| Metric | Description |
|--------|-------------|
| Expected Value (EV) | Average per-bet return |
| Profit Factor | Gross wins / gross losses |
| ROI | Return on investment (%) |
| Max Drawdown | Worst peak-to-trough decline |
| Risk of Ruin | Fraction of simulations ending in ruin |
| Sharpe Ratio | Risk-adjusted return (EV / volatility) |
| Survival Rate | Fraction completing all rounds |
| Worst Loss Streak | Longest consecutive losses |
| Composite Score | Weighted combination for ranking |

## Composite Scoring

Strategies are ranked by a composite score:

```
score = 0.20 × EV + 0.15 × profit_factor + 0.15 × ROI
      + 0.20 × Sharpe + 0.15 × survival
      - 0.10 × drawdown_penalty - 0.15 × ruin_penalty
```

## Strategy Selection Modes (Gambler Agent)

| Mode | Strategy |
|------|----------|
| `conservative` | Highest survival rate (risk of ruin < 30%) |
| `balanced` | Highest composite score |
| `aggressive` | Highest average ROI |
| `wager_farming` | Highest total wagered |

## Switching Logic

The gambler agent monitors live performance and switches strategies when:
- Loss streak ≥ 8 bets
- Drawdown exceeds 25% of session peak
- Win rate over last 50 bets falls below 35%

A cooldown period (default: 50 bets) prevents excessive switching.

## Memory System

The `MemoryManager` persists agent knowledge to `data/agents/memory.json`:
- Account balances and tracking
- Strategy evaluation history
- Session logs and outcomes
- User preferences and goals

Data is auto-saved after every mutation, thread-safe, and includes corrupt-file recovery.

## Data Files

All agent data is stored in `data/agents/` (git-ignored):

| File | Contents |
|------|----------|
| `memory.json` | Full ecosystem knowledge |
| `hall_of_fame.json` | Top strategy configurations |
| `evaluation_results.json` | Last full evaluation |
| `session_logs.json` | Session history |
