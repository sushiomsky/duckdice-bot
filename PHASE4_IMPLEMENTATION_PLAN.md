# 📋 Phase 4: Complete Simulator - Implementation Plan

**Status**: 🔄 In Progress  
**Estimated Time**: 5-7 hours  
**Priority**: MEDIUM  
**Dependencies**: Phase 2 (Script System)

---

## 🎯 Goals

Build a comprehensive simulation system that allows users to:
1. Test strategies with virtual balance (no real money)
2. Backtest strategies against historical patterns
3. Analyze performance metrics and risk
4. Make data-driven decisions before live betting

---

## 📊 Requirements Analysis

### Current State
- ✅ Basic simulation exists in GUI (uses mock API responses)
- ✅ Script system supports strategy execution
- ✅ Bet verification validates provably fair outcomes
- ❌ No historical data playback
- ❌ No performance metrics tracking
- ❌ No risk analysis tools
- ❌ No backtesting framework

### Target State
- ✅ Full simulation engine with virtual balance
- ✅ Historical bet data playback
- ✅ Comprehensive performance metrics
- ✅ Risk analysis (drawdown, variance, bankroll requirements)
- ✅ Backtesting framework for strategy validation
- ✅ Export simulation results

---

## 🏗️ Architecture

```
src/simulator/
├── __init__.py                  # Package exports
├── simulation_engine.py         # Core simulation engine
├── backtest_engine.py          # Backtesting framework
├── performance_metrics.py      # Metrics calculation
├── risk_analyzer.py            # Risk analysis tools
└── models.py                   # Data models

app/ui/pages/
├── simulator.py                # Enhanced simulator page
└── backtest.py                 # NEW: Backtesting page

app/ui/components/
└── metrics_display.py          # NEW: Metrics visualization
```

---

## 📝 Detailed Tasks

### Task 4.1: Build Simulation Engine (2h)

**File**: `src/simulator/simulation_engine.py`

**Components**:
1. **SimulationEngine** class
   - Virtual balance tracking
   - Bet execution with outcome generation
   - Session state management
   - Real-time metric updates

2. **VirtualBalance** class
   - Starting balance
   - Current balance
   - Profit/loss tracking
   - Currency conversion

3. **OutcomeGenerator** interface
   - Random outcomes (house edge aware)
   - Historical replay mode
   - Pattern-based generation

**Features**:
- Execute bets without API calls
- Track all bet details
- Support strategy execution
- House edge simulation (configurable %)
- Seed-based reproducibility

**Testing**:
```python
engine = SimulationEngine(starting_balance=100.0, currency='USD')
result = engine.execute_bet(amount=1.0, chance=50.0, roll_over=True)
assert result.profit == (1.0 * (100 / 50.0) * 0.97) - 1.0  # 97% RTP
```

---

### Task 4.2: Build Performance Metrics (1.5h)

**File**: `src/simulator/performance_metrics.py`

**Metrics to Calculate**:

1. **Basic Metrics**
   - Total bets
   - Win/loss count
   - Win rate %
   - Total wagered
   - Total profit/loss
   - ROI %

2. **Advanced Metrics**
   - Largest win streak
   - Largest loss streak
   - Average bet size
   - Average win/loss amount
   - Profit factor (gross profit / gross loss)
   - Expected value (EV)

3. **Risk Metrics** (from RiskAnalyzer)
   - Maximum drawdown (absolute & %)
   - Current drawdown
   - Variance
   - Standard deviation
   - Sharpe ratio (if applicable)
   - Bankroll requirement estimate

**Data Model**:
```python
@dataclass
class PerformanceMetrics:
    total_bets: int
    wins: int
    losses: int
    win_rate: float
    total_wagered: Decimal
    profit_loss: Decimal
    roi: float
    max_win_streak: int
    max_loss_streak: int
    profit_factor: float
    expected_value: float
```

---

### Task 4.3: Build Risk Analyzer (1.5h)

**File**: `src/simulator/risk_analyzer.py`

**Components**:

1. **RiskAnalyzer** class
   - Drawdown calculation (peak-to-trough)
   - Variance analysis
   - Bankroll requirement estimation
   - Risk of ruin calculation

2. **DrawdownTracker**
   - Track peak balance
   - Calculate current drawdown
   - Track max drawdown
   - Drawdown % from peak

3. **BankrollEstimator**
   - Kelly Criterion calculation
   - Risk of ruin modeling
   - Suggested minimum bankroll
   - Bet sizing recommendations

**Formulas**:
```python
# Maximum Drawdown
max_dd = max(peak_balance - current_balance for each point in time)
max_dd_pct = (max_dd / peak_balance) * 100

# Variance
variance = sum((outcome - mean)^2) / n

# Risk of Ruin (simplified)
ror = ((1 - win_rate) / win_rate) ^ (bankroll / avg_bet_size)
```

---

### Task 4.4: Build Backtesting Framework (1.5h)

**File**: `src/simulator/backtest_engine.py`

**Components**:

1. **BacktestEngine** class
   - Load historical bet patterns
   - Replay with strategy
   - Generate performance report

2. **HistoricalDataLoader**
   - Load from CSV/JSON
   - Load from bet_history/ directory
   - Parse and validate data

3. **BacktestResult** model
   - All performance metrics
   - Bet-by-bet results
   - Summary statistics
   - Export to CSV/JSON

**Features**:
- Replay historical outcomes
- Compare multiple strategies
- Monte Carlo simulation (random variations)
- What-if analysis (change parameters)

**Usage**:
```python
engine = BacktestEngine()
engine.load_history('bet_history/2025-01-09.json')
result = engine.run_backtest(strategy='martingale', starting_balance=100)
print(f"Final balance: {result.final_balance}")
print(f"Max drawdown: {result.max_drawdown_pct}%")
```

---

### Task 4.5: Enhanced Simulator UI (1.5h)

**File**: `app/ui/pages/simulator.py` (enhance existing)

**Enhancements**:

1. **Configuration Panel**
   - Starting balance
   - Currency selection
   - House edge % (default 3%)
   - Number of bets to simulate
   - Seed for reproducibility

2. **Strategy Selection**
   - Choose from script library
   - Configure strategy parameters
   - Save configurations

3. **Real-time Display**
   - Current balance
   - Profit/loss (with color coding)
   - Win/loss count
   - Win rate %
   - Current streak
   - Progress bar

4. **Results Dashboard**
   - Performance metrics table
   - Risk analysis section
   - Charts (balance over time, bet sizes)
   - Export results button

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Simulator Configuration                     │
│ ┌─────────────────────────────────────────┐ │
│ │ Starting Balance: [100.00] [USD ▼]      │ │
│ │ House Edge: [3.0]%                       │ │
│ │ Number of Bets: [1000]                   │ │
│ │ Strategy: [Martingale ▼]                 │ │
│ │ Seed: [12345] (optional)                 │ │
│ │ [▶ Start Simulation] [⏹ Stop] [📊 Export] │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Current Session                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Balance: $102.50 (+2.50, +2.5%)         │ │
│ │ Bets: 125/1000                          │ │
│ │ Wins: 62 | Losses: 63 (49.6%)           │ │
│ │ [████████░░] 12.5%                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Performance Metrics                         │
│ ┌─────────────────────────────────────────┐ │
│ │ Total Wagered: $1,250.00                │ │
│ │ ROI: 2.0%                               │ │
│ │ Max Win Streak: 7                       │ │
│ │ Max Loss Streak: 8                      │ │
│ │ Max Drawdown: -$5.20 (-5.2%)            │ │
│ │ Profit Factor: 1.05                     │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [📈 Balance Chart] [📊 Bet Size Chart]      │
└─────────────────────────────────────────────┘
```

---

### Task 4.6: Backtesting UI (NEW, 1h)

**File**: `app/ui/pages/backtest.py`

**Features**:

1. **Data Source Selection**
   - Upload CSV/JSON
   - Select from bet_history/
   - Use generated patterns

2. **Strategy Comparison**
   - Run multiple strategies
   - Side-by-side comparison
   - Best performer highlighting

3. **Results Table**
   - Strategy name
   - Final balance
   - ROI %
   - Max drawdown %
   - Win rate
   - Total bets

4. **Detailed View**
   - Click strategy for full report
   - Bet-by-bet replay
   - Charts and graphs

---

### Task 4.7: Integration & Testing (0.5h)

**Changes**:

1. **app/main.py**
   - Add `/simulator` route (enhance existing)
   - Add `/backtest` route (new)

2. **app/ui/layout.py**
   - Update Simulator navigation item
   - Add Backtest navigation item

3. **Testing**
   - Test simulation engine with various strategies
   - Test backtest with historical data
   - Test metric calculations
   - Test UI responsiveness

---

## 📦 Data Models

**src/simulator/models.py**:

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

@dataclass
class SimulationConfig:
    """Configuration for simulation."""
    starting_balance: Decimal
    currency: str
    house_edge: float  # 0-100 (default 3.0)
    max_bets: Optional[int] = None
    seed: Optional[int] = None
    
@dataclass
class SimulatedBet:
    """Result of a simulated bet."""
    bet_number: int
    timestamp: datetime
    amount: Decimal
    chance: float
    roll_over: bool
    outcome: float  # 0-100
    won: bool
    profit: Decimal
    balance_after: Decimal

@dataclass
class SimulationResult:
    """Complete simulation results."""
    config: SimulationConfig
    bets: List[SimulatedBet]
    metrics: 'PerformanceMetrics'
    risk_analysis: 'RiskAnalysis'
    final_balance: Decimal
    total_time: float  # seconds
    
@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    total_bets: int
    wins: int
    losses: int
    win_rate: float
    total_wagered: Decimal
    profit_loss: Decimal
    roi: float
    max_win_streak: int
    max_loss_streak: int
    avg_bet_size: Decimal
    avg_win_amount: Decimal
    avg_loss_amount: Decimal
    profit_factor: float
    expected_value: float

@dataclass
class RiskAnalysis:
    """Risk analysis metrics."""
    max_drawdown: Decimal
    max_drawdown_pct: float
    current_drawdown: Decimal
    current_drawdown_pct: float
    peak_balance: Decimal
    variance: float
    std_deviation: float
    suggested_bankroll: Decimal
    risk_of_ruin: float  # 0-1
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
# test_simulation_engine.py
def test_virtual_balance():
    engine = SimulationEngine(100.0, 'USD')
    assert engine.balance == 100.0
    
def test_bet_execution_win():
    engine = SimulationEngine(100.0, 'USD', seed=42)
    # Seed 42 produces known outcome
    result = engine.execute_bet(1.0, 50.0, True)
    assert result.won == True
    assert engine.balance > 100.0

def test_bet_execution_loss():
    engine = SimulationEngine(100.0, 'USD', seed=999)
    result = engine.execute_bet(1.0, 50.0, True)
    assert result.won == False
    assert engine.balance == 99.0

# test_performance_metrics.py
def test_win_rate_calculation():
    metrics = calculate_metrics([...])
    assert metrics.win_rate == 0.5  # 50% win rate

def test_roi_calculation():
    metrics = calculate_metrics([...])
    assert metrics.roi == 5.0  # 5% ROI

# test_risk_analyzer.py
def test_max_drawdown():
    analyzer = RiskAnalyzer([100, 110, 105, 95, 90, 100])
    assert analyzer.max_drawdown == 20  # 110 -> 90
    assert analyzer.max_drawdown_pct == 18.18

def test_risk_of_ruin():
    ror = calculate_risk_of_ruin(
        bankroll=100, avg_bet=1, win_rate=0.49
    )
    assert 0 <= ror <= 1
```

### Integration Tests

```python
# test_backtest.py
def test_backtest_with_history():
    engine = BacktestEngine()
    engine.load_history('test_data.csv')
    result = engine.run_backtest('martingale', 100)
    assert result.final_balance > 0
    assert result.metrics.total_bets > 0
```

---

## 📈 Success Criteria

**Phase 4 Complete When**:
- ✅ Simulation engine executes bets without API
- ✅ Virtual balance tracks accurately
- ✅ Performance metrics calculate correctly
- ✅ Risk analysis provides actionable insights
- ✅ Backtesting framework works with historical data
- ✅ UI displays real-time simulation progress
- ✅ Results can be exported (CSV/JSON)
- ✅ All tests pass
- ✅ Documentation complete

---

## 🚀 Implementation Order

1. **Task 4.1** - Simulation Engine (core foundation)
2. **Task 4.2** - Performance Metrics (calculation logic)
3. **Task 4.3** - Risk Analyzer (risk assessment)
4. **Task 4.4** - Backtesting Framework (historical replay)
5. **Task 4.5** - Enhanced Simulator UI (user interface)
6. **Task 4.6** - Backtesting UI (comparison interface)
7. **Task 4.7** - Integration & Testing (final polish)

---

## 📝 Notes

### House Edge Simulation
- Default: 3% (DuckDice standard)
- Configurable for testing other scenarios
- Applied to payout calculation: `payout = (bet * multiplier * (1 - house_edge))`

### Reproducibility
- Use seed parameter for deterministic outcomes
- Enables A/B testing of strategies
- Useful for documentation/tutorials

### Performance Considerations
- Simulate 10,000+ bets efficiently
- Use generators for memory efficiency
- Progress updates every 100 bets (not every bet)

### Future Enhancements
- Monte Carlo simulation (run 1000s of simulations)
- Strategy optimization (auto-tune parameters)
- ML-based outcome prediction integration
- Real-time strategy comparison dashboard

---

**Created**: 2025-01-09  
**Author**: DuckDice Bot Team  
**Status**: Ready to Implement
