# Refactoring & Improvement Plan - v3.9.0+

## 🎯 Objectives
1. Improve code organization and modularity
2. Enhance performance and reduce redundancy
3. Strengthen error handling and type safety
4. Better documentation and maintainability
5. Add testing infrastructure

---

## 📊 Code Quality Analysis Results

### Complexity Issues Found:
1. **betting.py** - 2 functions >50 lines (quick_bet_panel: 207, auto_bet_panel: 175)
2. **library.py** - 4 functions >50 lines (scripts_panel: 140, strategies_panel: 107)
3. **engine.py** - run_auto_bet: 261 lines, 7 parameters
4. **TODOs Found**: 6 items needing implementation

### Files by Size (largest):
1. target_aware.py - 649 lines
2. ux_improvements.py - 605 lines
3. bet_logger.py - 478 lines
4. statistics_dashboard.py - 475 lines
5. betting.py - 435 lines

---

## 🔧 Refactoring Tasks

### Priority 1: Code Organization (High Impact)

#### Task 1.1: Extract Betting Components
**File**: `app/ui/pages/betting.py`
**Issues**: 
- quick_bet_panel (207 lines) - too long
- auto_bet_panel (175 lines) - too long
- Mixed concerns (UI + logic)

**Solution**:
```
app/ui/components/
  ├── betting/
  │   ├── __init__.py
  │   ├── quick_bet.py      # Extract quick_bet_panel
  │   ├── auto_bet.py       # Extract auto_bet_panel
  │   └── bet_controls.py   # Shared controls
```

**Benefits**:
- 50% reduction in file size
- Better testability
- Easier maintenance
- Reusable components

---

#### Task 1.2: Split Library Page
**File**: `app/ui/pages/library.py` (410 lines)
**Issues**:
- strategies_panel (107 lines)
- scripts_panel (140 lines)
- Handles two different concerns

**Solution**:
```
app/ui/components/
  ├── library/
  │   ├── __init__.py
  │   ├── strategy_browser.py  # Extract strategies_panel
  │   ├── script_browser.py    # Extract scripts_panel
  │   └── shared.py            # Common utilities
```

---

#### Task 1.3: Refactor Auto-Bet Engine
**File**: `src/betbot_engine/engine.py`
**Issues**:
- run_auto_bet: 261 lines (too long)
- 7 parameters (too many)
- Mixed concerns (execution + logging + limits)

**Solution**:
```python
# Extract classes
class BetExecutor:
    """Handles individual bet execution"""
    
class SessionManager:
    """Manages session state and limits"""
    
class BetLogger:
    """Handles bet logging"""

# Simplified function
def run_auto_bet(
    api: DuckDiceAPI,
    strategy_name: str,
    config: AutoBetConfig  # Single config object instead of 7 params
) -> SessionSummary:
    executor = BetExecutor(api, config)
    manager = SessionManager(config.limits)
    logger = BetLogger(config.log_dir)
    
    return executor.run_session(strategy_name, manager, logger)
```

**Benefits**:
- 70% reduction in function size
- Better separation of concerns
- Easier to test each component
- More maintainable

---

### Priority 2: Performance Optimization

#### Task 2.1: Implement Response Caching
**Files**: `app/services/backend.py`, `src/duckdice_api/api.py`
**Issue**: Redundant API calls for user info, balances

**Solution**:
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedAPIClient:
    def __init__(self, api: DuckDiceAPI):
        self.api = api
        self._cache = {}
        self._cache_ttl = {}
    
    def get_user_info(self, ttl: int = 30):
        """Get user info with caching (30s default TTL)"""
        cache_key = 'user_info'
        if cache_key in self._cache:
            if datetime.now() < self._cache_ttl[cache_key]:
                return self._cache[cache_key]
        
        result = self.api.get_user_info()
        self._cache[cache_key] = result
        self._cache_ttl[cache_key] = datetime.now() + timedelta(seconds=ttl)
        return result
```

**Benefits**:
- 50-80% reduction in API calls
- Faster response times
- Reduced server load
- Better user experience

---

#### Task 2.2: Batch Balance Updates
**Issue**: Multiple sequential balance calls

**Solution**:
```python
async def refresh_all_balances_batch(self):
    """Refresh all balances in single API call"""
    user_info = await asyncio.to_thread(self.api.get_user_info)
    
    # Update all currencies at once
    balances = user_info.get('balances', [])
    for balance in balances:
        currency = balance.get('currency')
        main = float(balance.get('main', 0))
        faucet = float(balance.get('faucet', 0))
        # Update store in batch
        store.update_currency_balance(currency, main, faucet)
```

---

### Priority 3: Error Handling Improvements

#### Task 3.1: Standardize Error Handling
**Create**: `app/utils/errors.py`

```python
"""Centralized error handling and custom exceptions"""

class BotError(Exception):
    """Base exception for all bot errors"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}
        self.timestamp = datetime.now()

class APIError(BotError):
    """API-related errors"""
    
class ConfigError(BotError):
    """Configuration errors"""
    
class StrategyError(BotError):
    """Strategy execution errors"""

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle(error: Exception, context: str = "") -> tuple[bool, str]:
        """Handle error and return (success, message)"""
        if isinstance(error, BotError):
            log_error(f"{context}: {error}", error.details)
            return False, str(error)
        elif isinstance(error, requests.RequestException):
            return False, f"Network error: {str(error)}"
        else:
            log_error(f"Unexpected error in {context}: {error}")
            return False, "An unexpected error occurred"
```

---

#### Task 3.2: Add Retry Decorators
**Create**: `app/utils/retry.py`

```python
from functools import wraps
import time

def retry_on_failure(max_attempts=3, delay=1, backoff=2):
    """Decorator for retrying failed operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    
                    log_warning(f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator

# Usage
@retry_on_failure(max_attempts=3, delay=0.5)
async def place_bet_with_retry(self, amount, chance, target):
    return await self.place_bet(amount, chance, target)
```

---

### Priority 4: Type Safety

#### Task 4.1: Add Missing Type Hints
**Files**: All Python files missing type hints

**Script to find missing hints**:
```bash
mypy app/ src/ --ignore-missing-imports --disallow-untyped-defs 2>&1 | grep "Function is missing"
```

**Solution**: Add type hints systematically
```python
# Before
def process_bet(bet_data):
    return bet_data['result']

# After
def process_bet(bet_data: Dict[str, Any]) -> float:
    """Process bet data and extract result."""
    return float(bet_data.get('result', 0.0))
```

---

#### Task 4.2: Create Type Definitions
**Create**: `app/types/__init__.py`

```python
"""Type definitions for the bot"""
from typing import TypedDict, Literal
from decimal import Decimal

class BetParams(TypedDict):
    """Parameters for placing a bet"""
    amount: Decimal
    chance: float
    target: float
    currency: str
    is_high: bool
    faucet: bool

class BetResponse(TypedDict):
    """Response from bet API"""
    bet_id: str
    result: float
    profit: Decimal
    win: bool
    payout: float

BettingMode = Literal['main', 'faucet']
SimulationMode = Literal['simulation', 'live']
```

---

### Priority 5: Documentation

#### Task 5.1: Add Comprehensive Docstrings
**Standard format**:
```python
def function_name(param1: str, param2: int) -> bool:
    """
    Short description (one line).
    
    Longer description explaining what the function does,
    when to use it, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param1 is empty
        APIError: When API call fails
    
    Example:
        >>> result = function_name("test", 5)
        >>> print(result)
        True
    """
    pass
```

---

#### Task 5.2: Create Architecture Documentation
**Create**: `docs/architecture/`
```
docs/architecture/
  ├── overview.md          # System overview
  ├── data-flow.md         # Data flow diagrams
  ├── api-design.md        # API client design
  ├── ui-components.md     # UI architecture
  └── deployment.md        # Deployment guide
```

---

### Priority 6: Testing Infrastructure

#### Task 6.1: Add Unit Tests
**Create**: `tests/unit/`
```
tests/
  ├── __init__.py
  ├── unit/
  │   ├── test_api_client.py
  │   ├── test_backend.py
  │   ├── test_strategies.py
  │   └── test_utils.py
  ├── integration/
  │   ├── test_betting_flow.py
  │   └── test_faucet.py
  └── conftest.py          # Pytest fixtures
```

**Example test**:
```python
import pytest
from app.services.backend import Backend

@pytest.fixture
def backend():
    return Backend()

def test_connect_success(backend, mocker):
    """Test successful API connection"""
    mock_api = mocker.patch('app.services.backend.DuckDiceAPI')
    mock_api.return_value.get_user_info.return_value = {
        'username': 'test_user',
        'balances': []
    }
    
    success, message = await backend.connect('test_api_key')
    assert success is True
    assert 'test_user' in message
```

---

#### Task 6.2: Integration Tests
**Create**: `tests/integration/test_betting_flow.py`
```python
@pytest.mark.integration
async def test_full_betting_cycle():
    """Test complete betting cycle: connect → bet → verify → disconnect"""
    backend = Backend()
    
    # Connect
    success, _ = await backend.connect(TEST_API_KEY)
    assert success
    
    # Place bet
    success, _, result = await backend.place_bet(0.001, 50.0, 50.0)
    assert success
    assert result is not None
    
    # Verify bet exists in history
    assert len(store.bet_history) > 0
    
    # Disconnect
    await backend.disconnect()
    assert not store.connected
```

---

### Priority 7: Code Cleanup

#### Task 7.1: Remove Unused Imports
**Script**:
```bash
# Find unused imports
autoflake --remove-all-unused-imports --check app/ src/
```

#### Task 7.2: Remove Dead Code
**Files to check**:
- `src/gui_enhancements/` - Old Tkinter GUI (605 lines in ux_improvements.py)
- Duplicate bet history implementations
- Unused strategy templates

#### Task 7.3: Consolidate Constants
**Create**: `app/constants.py`
```python
"""Application-wide constants"""

# API
API_TIMEOUT = 30
API_MAX_RETRIES = 3
API_BASE_URL = "https://duckdice.io/api"

# Performance
DEFAULT_BET_DELAY_MS = 750
TURBO_MODE_DELAY_MS = 0
CONNECTION_POOL_SIZE = 10

# Limits
MAX_BET_HISTORY = 1000
MAX_CONCURRENT_BETS = 1
BALANCE_REFRESH_INTERVAL = 30

# UI
TOAST_DURATION = 3
ANIMATION_DURATION = 300
```

---

## 📈 Expected Improvements

### Code Quality:
- ✅ 40-60% reduction in function sizes
- ✅ 30% reduction in code duplication
- ✅ 100% type hint coverage
- ✅ 80%+ test coverage

### Performance:
- ✅ 50-80% reduction in API calls (caching)
- ✅ 30% faster page loads (optimized rendering)
- ✅ 20% less memory usage (better data structures)

### Maintainability:
- ✅ Modular architecture (easier to extend)
- ✅ Comprehensive documentation
- ✅ Automated testing
- ✅ Clear error messages

---

## 🚀 Implementation Priority

**Phase 1 (Critical - 2-3 hours):**
1. Extract betting components (Task 1.1)
2. Refactor auto-bet engine (Task 1.3)
3. Implement error handling (Task 3.1)

**Phase 2 (High - 2-3 hours):**
1. Add response caching (Task 2.1)
2. Split library page (Task 1.2)
3. Add retry decorators (Task 3.2)

**Phase 3 (Medium - 3-4 hours):**
1. Add type hints (Task 4.1)
2. Create type definitions (Task 4.2)
3. Unit tests (Task 6.1)

**Phase 4 (Low - 2-3 hours):**
1. Documentation (Task 5.1, 5.2)
2. Code cleanup (Task 7.1, 7.2, 7.3)
3. Integration tests (Task 6.2)

**Total Estimated Time**: 10-14 hours

---

## 📝 Success Metrics

- [ ] All functions < 100 lines
- [ ] All functions < 5 parameters
- [ ] 80%+ test coverage
- [ ] 100% type hint coverage
- [ ] Zero pylint warnings
- [ ] 50%+ reduction in API calls
- [ ] All TODOs resolved

---

## 🎯 Next Steps

1. Start with Phase 1 (critical refactoring)
2. Measure performance before/after
3. Run tests to ensure no regressions
4. Document all changes
5. Create pull request with detailed notes
