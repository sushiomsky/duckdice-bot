# Adaptive Survival Strategy Guide

## Overview

**adaptive-survival** is a sophisticated meta-strategy that implements cautious opportunistic betting with long-term survival focus. It combines pattern detection, multiple competing approaches, and adaptive selection to navigate changing market conditions while prioritizing capital preservation.

## Philosophy

**Role**: Cautious but opportunistic player  
**Goal**: Long-term survival, not fast wins  
**Approach**: Multiple sub-strategies compete based on performance

## Core Principles

### 1. Observation Before Action
- Analyzes last 20 bets before making decisions
- Never assumes patterns will continue
- Continuously re-evaluates conditions

### 2. Pattern Detection
- **Calm Phase**: Low variance, predictable, clustering of outcomes
- **Chaos Phase**: High variance, random, volatile results
- **Transition**: Moving between states
- **Unknown**: Insufficient data

### 3. Multi-Approach System
Four independent betting approaches:

#### Conservative (Fallback)
- Chance: 75% (default)
- Bet Size: 0.5% of balance
- Purpose: Safe fallback, always available
- Active: When in doubt, chaos, or unknown

#### Moderate (Balanced)
- Chance: 50% (default)  
- Bet Size: 1% of balance
- Purpose: Balanced approach for calm conditions
- Active: Calm phases with good performance

####Opportunistic (Aggressive)
- Chance: 40% (default)
- Bet Size: 1.5% of balance
- Purpose: Maximize profit in strong calm signals
- Active: Calm phases with high confidence

#### Recovery (Ultra-Safe)
- Chance: 85% (default)
- Bet Size: 0.3% of balance
- Purpose: Capital preservation after drawdown
- Active: Triggered at -5% drawdown

### 4. Adaptive Selection
- Each approach tracked independently
- Performance scored on: win rate (40%), profit trend (30%), stability (30%)
- Best-performing approach selected automatically
- Smooth transitions between modes

### 5. Survival Safeguards
- Maximum bet: 2% of balance (default)
- Loss streak limit: 5 consecutive → conservative mode
- Drawdown protection: -5% triggers recovery mode
- Chaos detection: Auto-reduce exposure
- Never chase losses

## Parameters

```bash
--param base_bet_pct=0.01          # Base bet as % of balance (1%)
--param max_bet_pct=0.02           # Maximum bet % (2%)
--param conservative_chance=75     # Conservative approach win chance
--param moderate_chance=50         # Moderate approach win chance
--param opportunistic_chance=40    # Opportunistic approach win chance
--param recovery_chance=85         # Recovery mode win chance
--param drawdown_threshold=-0.05   # Trigger recovery at -5%
--param loss_streak_limit=5        # Consecutive losses before conservative
--param pattern_window=20          # Bets to analyze for patterns
--param performance_threshold=0.3  # Minimum score to use approach (0-1)
```

## Usage Examples

### Basic Usage (Defaults)
```bash
python duckdice_cli.py run -m simulation -c btc -s adaptive-survival -b 100 --max-bets 100
```

### Conservative Configuration
```bash
python duckdice_cli.py run -m simulation -c btc -s adaptive-survival \
    -b 100 \
    -P base_bet_pct=0.005 \
    -P conservative_chance=80 \
    -P moderate_chance=60 \
    --max-bets 200
```

### Moderate Risk Configuration
```bash
python duckdice_cli.py run -m simulation -c btc -s adaptive-survival \
    -b 100 \
    -P base_bet_pct=0.015 \
    -P max_bet_pct=0.03 \
    -P opportunistic_chance=35 \
    --max-bets 150
```

### Long-Term Survival Mode
```bash
python duckdice_cli.py run -m live-faucet -c btc -s adaptive-survival \
    -P base_bet_pct=0.005 \
    -P drawdown_threshold=-0.03 \
    -P loss_streak_limit=3 \
    -P performance_threshold=0.4 \
    --max-duration 3600
```

## How It Works

### Pattern Detection Algorithm

1. **Variance Analysis**: Measures profit volatility
2. **Clustering Detection**: Identifies consecutive same outcomes
3. **Win Rate Tracking**: Monitors win distribution
4. **Phase Classification**:
   - Calm: Low variance + clustering + balanced win rate
   - Chaos: High variance + no clustering + extreme win rate
   - Transition: Mixed signals
   - Unknown: Not enough data

### Approach Selection Logic

```
IF in_recovery OR loss_streak >= limit:
    SELECT Conservative

ELSE IF phase == CHAOS:
    SELECT Conservative
    
ELSE IF phase == CALM:
    scores = calculate_performance_scores()
    best = max(scores)
    IF best >= threshold:
        SELECT best_approach
    ELSE:
        SELECT Conservative
        
ELSE:
    SELECT Conservative  # Default fallback
```

### Bet Calculation

```
base_amount = balance * approach.bet_pct

IF phase == CHAOS:
    amount = base_amount * 0.5  # Reduce exposure
    chance = approach.chance + 10  # Safer
    
ELSE IF phase == CALM:
    amount = min(base_amount * 1.5, balance * max_bet_pct)
    chance = approach.chance
    
ELSE:
    amount = base_amount
    chance = approach.chance

# Safety caps
amount = min(amount, balance * max_bet_pct)
amount = max(amount, minimum_bet)
```

## Strategy State Logging

Each bet logs the current strategy state to the database:

```json
{
  "current_approach": "MODERATE",
  "phase": "CALM",
  "phase_confidence": 0.75,
  "loss_streak": 0,
  "in_recovery": false,
  "approach_scores": {
    "CONSERVATIVE": 0.65,
    "MODERATE": 0.72,
    "OPPORTUNISTIC": 0.58,
    "RECOVERY": 0.50
  }
}
```

Query strategy states:
```bash
sqlite3 data/duckdice_bot.db "
SELECT bet_number, won, strategy_state 
FROM bet_history 
WHERE strategy='adaptive-survival' 
ORDER BY bet_number DESC 
LIMIT 10;
"
```

## Performance Characteristics

### Strengths
- ✅ Adapts to changing conditions
- ✅ Multiple independent approaches reduce risk
- ✅ Automatic pattern detection
- ✅ Conservative fallback always available
- ✅ Smooth risk transitions
- ✅ Long-term capital preservation

### Weaknesses
- ❌ Slower profit accumulation
- ❌ Requires 20+ bets for pattern detection
- ❌ Complex decision-making
- ❌ May be overly conservative
- ❌ Not optimized for quick wins

### Best For
- Long-term play sessions
- Capital preservation focus
- Patient players
- Risk-averse betting
- Learning market patterns

### Not Recommended For
- Quick profit targets
- Aggressive betting
- Small sample sizes
- Impatient players
- High-frequency trading

## Tips

1. **Give it time**: Let strategy observe 20+ bets before judging performance
2. **Monitor phases**: Check logs to see if phase detection aligns with reality
3. **Adjust thresholds**: Tune `performance_threshold` based on your risk tolerance
4. **Trust the fallback**: Conservative mode is there for a reason
5. **Long sessions**: Works best over 100+ bets
6. **Combine with limits**: Use `--stop-loss` and `--take-profit` for safety
7. **Review states**: Use database queries to analyze decision-making

## Advanced Usage

### Analyzing Phase Detection
```python
from src.betbot_engine.bet_database import BetDatabase
import json

db = BetDatabase()
session_id = '20260123_140000'  # Your session
bets = db.get_session_bets(session_id)

phases = []
for bet in bets:
    state = json.loads(bet['strategy_state'])
    phases.append({
        'bet': bet['bet_number'],
        'phase': state['phase'],
        'confidence': state['phase_confidence'],
        'approach': state['current_approach']
    })

# Analyze phase transitions
for p in phases:
    print(f"Bet {p['bet']}: {p['phase']} ({p['confidence']:.2f}) -> {p['approach']}")
```

### Custom Risk Profile
```bash
# Ultra-conservative
-P base_bet_pct=0.003 \
-P conservative_chance=90 \
-P moderate_chance=70 \
-P opportunistic_chance=50 \
-P drawdown_threshold=-0.02

# Moderate risk
-P base_bet_pct=0.015 \
-P max_bet_pct=0.025 \
-P opportunistic_chance=35 \
-P drawdown_threshold=-0.08

# Opportunistic (within safety bounds)
-P base_bet_pct=0.02 \
-P max_bet_pct=0.03 \
-P performance_threshold=0.25 \
-P opportunistic_chance=30
```

## Comparison with Other Strategies

| Strategy | Risk | Speed | Adaptivity | Complexity |
|----------|------|-------|------------|------------|
| adaptive-survival | Low | Slow | High | High |
| classic-martingale | Very High | Fast | None | Low |
| target-aware | Low | Moderate | Medium | Medium |
| kelly-capped | Medium | Moderate | Low | Medium |
| dalembert | Medium | Moderate | None | Low |

## FAQ

**Q: Why is it so slow to profit?**  
A: The strategy prioritizes survival over speed. It's cautious by design.

**Q: Why does it keep using Conservative approach?**  
A: Either the phase is chaotic, or other approaches aren't performing well enough.

**Q: Can I make it more aggressive?**  
A: Yes, increase `base_bet_pct`, lower `performance_threshold`, and adjust chances.

**Q: What if I want faster decisions?**  
A: Reduce `pattern_window` to 10-15 bets, but this reduces detection accuracy.

**Q: Does pattern detection actually work?**  
A: It detects variance and clustering, which can indicate favorable conditions. However, dice outcomes are ultimately random.

**Q: Should I use this for quick sessions?**  
A: No. This strategy needs 50+ bets to show its adaptive capabilities.

## See Also

- [Strategy Comparison Guide](STRATEGY_COMPARISON_GUIDE.md)
- [Database Logging](DATABASE_LOGGING.md)
- [User Guide](USER_GUIDE.md)
- [CLI Guide](CLI_GUIDE.md)
