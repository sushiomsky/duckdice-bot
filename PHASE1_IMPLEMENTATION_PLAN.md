# 🎯 Phase 1: Enhanced Faucet System - Implementation Plan

## Overview
Implement accurate faucet mechanics with smart "Faucet Grind" strategy that auto-claims and makes optimal all-in bets to reach $20 cashout threshold.

---

## 📋 Detailed Task Breakdown

### Task 1.1: Faucet API Enhancement (2 hours)
**Goal**: Update API client with accurate claim mechanics

**Subtasks**:
1. Research DuckDice faucet API endpoints
   - Document actual claim value range
   - Confirm cooldown behavior
   - Verify 24h claim limits

2. Update `src/duckdice_api/api.py`:
   ```python
   def claim_faucet(
       self,
       currency: str
   ) -> Dict[str, Any]:
       """
       Claim faucet for currency.
       Returns: {
           'amount': float,  # $0.01 - $0.46
           'cooldown': int,  # 0-60 seconds
           'claims_remaining': int,  # 35-60 per 24h
           'next_reset': timestamp
       }
       """
   ```

3. Add faucet balance tracking:
   ```python
   def get_faucet_balance_usd(self, currency: str) -> float:
       """Get faucet balance in USD equivalent"""
   ```

4. Add cashout endpoint:
   ```python
   def cashout_faucet(self, currency: str, amount: float) -> bool:
       """Transfer faucet balance to main (min $20)"""
   ```

**Files to Modify**:
- `src/duckdice_api/api.py`

**Tests**:
- Test claim returns value in $0.01-$0.46 range
- Test cooldown is 0-60 seconds
- Test 24h limit enforcement
- Test cashout with $20 threshold

---

### Task 1.2: Enhanced Faucet Manager (2 hours)
**Goal**: Track claims, enforce limits, manage cashout

**Subtasks**:
1. Create `src/faucet_manager/claim_tracker.py`:
   ```python
   class ClaimTracker:
       """Track faucet claims and enforce 24h limits"""
       
       def __init__(self):
           self.claims_today: List[ClaimRecord] = []
           self.total_claimed_usd: float = 0.0
           self.last_claim_time: float = 0.0
       
       def can_claim(self) -> Tuple[bool, str]:
           """Check if claim is allowed"""
       
       def record_claim(self, amount_usd: float, cooldown: int):
           """Record successful claim"""
       
       def get_next_claim_time(self) -> float:
           """When can next claim happen"""
       
       def reset_daily(self):
           """Reset 24h counter"""
   ```

2. Create `src/faucet_manager/cashout_manager.py`:
   ```python
   class CashoutManager:
       """Manage faucet to main cashout"""
       
       CASHOUT_THRESHOLD_USD = 20.0
       
       def can_cashout(self, balance_usd: float) -> bool:
           """Check if cashout threshold reached"""
       
       def execute_cashout(self, api, currency: str) -> bool:
           """Perform cashout operation"""
       
       def get_progress(self, balance_usd: float) -> float:
           """Get % progress to cashout (0-100)"""
   ```

3. Update `src/faucet_manager/faucet_manager.py`:
   - Integrate ClaimTracker
   - Integrate CashoutManager
   - Add USD conversion support
   - Enhanced logging

**Files to Create**:
- `src/faucet_manager/claim_tracker.py`
- `src/faucet_manager/cashout_manager.py`

**Files to Modify**:
- `src/faucet_manager/faucet_manager.py`

**Tests**:
- Test claim tracking
- Test 24h limit enforcement
- Test cashout threshold
- Test USD conversion

---

### Task 1.3: Faucet Grind Strategy (3 hours)
**Goal**: Create smart strategy that grinds faucet to $20

**Subtasks**:
1. Create `src/betbot_strategies/faucet_grind.py`:
   ```python
   @register("faucet-grind")
   class FaucetGrind:
       """
       Auto-claim faucet and make optimal all-in bets.
       
       Logic:
       1. Claim faucet
       2. Calculate chance needed for $20+ payout
       3. Place all-in bet at that chance
       4. If win: cashout to main
       5. If loss: wait 60s, claim next, repeat
       
       Parameters:
       - target_usd: Target payout (default $20)
       - min_chance: Minimum bet chance (default 1.0%)
       - max_chance: Maximum bet chance (default 95.0%)
       - house_edge: Faucet house edge (3%)
       """
       
       def calculate_optimal_chance(
           self,
           balance: float,
           target: float,
           house_edge: float = 0.03
       ) -> float:
           """
           Calculate chance needed for target payout.
           
           Formula:
           payout = balance * (100 / chance) * (1 - house_edge)
           
           Solving for chance:
           chance = (balance * 100 * (1 - house_edge)) / target
           """
   ```

2. Implement strategy logic:
   - Check if faucet can be claimed
   - If yes: claim faucet
   - Wait for cooldown
   - Calculate optimal chance for $20 payout
   - Place all-in bet
   - If win: attempt cashout
   - If loss: wait 60s, repeat

3. Add safety checks:
   - Ensure chance is within valid range (1-95%)
   - Handle API errors gracefully
   - Track consecutive losses
   - Add max attempts parameter

4. Add progress tracking:
   - Bets placed
   - Total claimed
   - Current balance
   - Progress to $20
   - Time elapsed

**Files to Create**:
- `src/betbot_strategies/faucet_grind.py`

**Files to Modify**:
- `src/betbot_strategies/__init__.py` (register strategy)

**Tests**:
- Test chance calculation
- Test all-in betting
- Test claim → bet → repeat cycle
- Test cashout trigger

---

### Task 1.4: GUI Integration - NiceGUI (2 hours)
**Goal**: Update web interface for enhanced faucet

**Subtasks**:
1. Update `app/ui/pages/faucet.py`:
   - Show claims remaining today
   - Show total claimed today (USD)
   - Show progress bar to $20 cashout
   - Add "Faucet Grind" strategy selector
   - Show strategy status (claiming, betting, waiting)
   - Add "Start Grind" / "Stop Grind" button

2. Add real-time updates:
   - Claim countdown timer
   - Next claim in X seconds
   - Current faucet balance (USD)
   - Progress to cashout (%)

3. Add statistics panel:
   - Claims today: X / 60
   - Total claimed: $X.XX
   - Current balance: $X.XX
   - Bets placed: X
   - Win rate: X%
   - Time to $20 (estimated)

**Files to Modify**:
- `app/ui/pages/faucet.py`

**Tests**:
- Test UI updates on claim
- Test progress bar accuracy
- Test strategy controls

---

### Task 1.5: GUI Integration - Tkinter (1 hour)
**Goal**: Update desktop GUI for enhanced faucet

**Subtasks**:
1. Update faucet tab in `duckdice_gui_ultimate.py`:
   - Add claims counter
   - Add progress bar to $20
   - Add "Faucet Grind" option
   - Show strategy status

2. Add control buttons:
   - Start/Stop Grind
   - Manual claim
   - Cashout (enabled at $20)

**Files to Modify**:
- `duckdice_gui_ultimate.py`

**Tests**:
- Test faucet tab displays
- Test grind start/stop
- Test manual cashout

---

### Task 1.6: USD Conversion Service (1 hour)
**Goal**: Convert all currencies to USD for unified tracking

**Subtasks**:
1. Create `src/utils/currency_converter.py`:
   ```python
   class CurrencyConverter:
       """Convert crypto to USD using CoinGecko API"""
       
       COIN_GECKO_IDS = {
           'BTC': 'bitcoin',
           'ETH': 'ethereum',
           'DOGE': 'dogecoin',
           # ... all supported currencies
       }
       
       def __init__(self):
           self._cache: Dict[str, Tuple[float, float]] = {}
           self._cache_ttl = 300  # 5 minutes
       
       def to_usd(self, amount: float, currency: str) -> float:
           """Convert crypto amount to USD"""
       
       def get_price(self, currency: str) -> float:
           """Get current USD price of currency"""
   ```

2. Integrate with faucet manager:
   - All faucet values in USD
   - All strategy calculations in USD
   - Display both crypto and USD amounts

**Files to Create**:
- `src/utils/currency_converter.py`

**Files to Modify**:
- `src/faucet_manager/faucet_manager.py`

**Tests**:
- Test price fetching
- Test caching
- Test conversion accuracy

---

### Task 1.7: Testing & Documentation (1 hour)
**Goal**: Ensure everything works and is documented

**Subtasks**:
1. Create `tests/test_faucet_grind.py`:
   - Test claim mechanics
   - Test chance calculation
   - Test all-in betting
   - Test cashout logic

2. Create `docs/FAUCET_GRIND_STRATEGY.md`:
   - Strategy explanation
   - How to use
   - Expected results
   - Tips and warnings

3. Update `CHANGELOG.md`

4. Update `README.md` with faucet grind info

**Files to Create**:
- `tests/test_faucet_grind.py`
- `docs/FAUCET_GRIND_STRATEGY.md`

**Files to Modify**:
- `CHANGELOG.md`
- `README.md`

---

## 📊 Implementation Timeline

| Task | Duration | Dependencies | Status |
|------|----------|--------------|--------|
| 1.1 API Enhancement | 2h | None | ⬜ TODO |
| 1.2 Faucet Manager | 2h | 1.1 | ⬜ TODO |
| 1.3 Faucet Grind | 3h | 1.1, 1.2 | ⬜ TODO |
| 1.4 NiceGUI Integration | 2h | 1.2, 1.3 | ⬜ TODO |
| 1.5 Tkinter Integration | 1h | 1.2, 1.3 | ⬜ TODO |
| 1.6 USD Converter | 1h | None | ⬜ TODO |
| 1.7 Testing & Docs | 1h | All | ⬜ TODO |

**Total**: 12 hours

---

## 🧪 Testing Strategy

### Unit Tests
- Claim tracker logic
- Cashout threshold
- Chance calculation
- USD conversion

### Integration Tests
- API → Faucet Manager
- Faucet Manager → Strategy
- Strategy → GUI

### Manual Tests
1. Claim faucet manually
2. Start faucet grind
3. Watch auto-claim → bet cycle
4. Verify $20 cashout
5. Check 24h limit enforcement

---

## 📈 Success Metrics

Phase 1 is complete when:
- ✅ Faucet claims return $0.01-$0.46
- ✅ Cooldown properly enforced (0-60s)
- ✅ 24h claim limit working (35-60 claims)
- ✅ Cashout triggers at $20
- ✅ Faucet Grind strategy runs automatically
- ✅ Chance calculated correctly for $20 payout
- ✅ All-in bets placed successfully
- ✅ Loss recovery works (wait → claim → bet)
- ✅ GUI shows accurate progress
- ✅ USD conversion accurate

---

## 🚀 Ready to Start?

Confirm approval to begin Task 1.1: Faucet API Enhancement.

**Next Action**: Research actual DuckDice faucet API behavior and document exact mechanics.
