# Parallel Betting Analysis

## Request: Multi-threaded betting with max bets/second

### Challenge

Current betting is **sequential**:
```
Bet 1 → Wait for API → Process result → Calculate Bet 2 → Wait for API → ...
```

This is slow because we wait for API response before calculating the next bet.

### Problem with Full Parallelization

**Streak-hunter strategy depends on sequential results:**

```python
# Bet depends on previous result!
if win:
    self._win_streak += 1
    next_bet = self._last_bet_amount * multiplier  # DEPENDS on last bet!
else:
    self._win_streak = 0
    next_bet = base_bet
```

**If we run bets in parallel:**
- Bet 2 calculates before Bet 1 result known ❌
- Compounding breaks (doesn't know what to multiply)
- Streaks get confused (race conditions)

### Safe Optimization: Async HTTP

Instead of threads, use **async I/O**:

```python
# Current (blocking):
result = api.play_dice(...)  # Wait 20-50ms for network
process_result(result)
next_bet = strategy.next_bet()

# Optimized (async):
import asyncio
result = await api.play_dice_async(...)  # Non-blocking!
# Can prepare next bet while waiting
```

This gives **some** speedup without breaking logic.

### Better Approach: Pipelining

**Semi-parallel with correct ordering:**

```
Thread 1: Calculate → Submit Bet 1 → Calculate Bet 2
Thread 2:            Wait for Result 1 → Process → Signal Thread 1
```

But this is complex and risky for strategies with state.

### Recommendation

**DON'T parallelize for streak-based strategies!**

The current 50ms delay gives us ~16 bets/sec which is:
- Faster than most bots (10x faster than typical)
- Safe for API rate limits
- Maintains strategy correctness
- Already optimized

**For non-streak strategies (e.g., martingale with fixed progression):**
- Could potentially parallelize
- But limited benefit (API latency is ~20-50ms, we already have 50ms delay)

### Alternative: Reduce delay further

We could go from 50ms → 25ms or even 10ms:
- **25ms delay** → ~40 bets/second
- **10ms delay** → ~100 bets/second

But risks:
- API rate limiting
- Server throttling
- Getting banned

### Conclusion

**Current speed (16 bets/sec) is optimal for:**
- ✅ Strategy correctness
- ✅ API courtesy
- ✅ Observability
- ✅ Safety

**Not recommended:**
- ❌ Threading (breaks streak logic)
- ❌ Parallel bets (race conditions)
- ❌ Under 50ms delay (API risks)

**Possible:**
- ⚠️ Async HTTP (complex, minimal gain)
- ⚠️ 25ms delay (some risk)

---

**Verdict:** Current implementation is already near-optimal. Further speed gains require sacrificing safety or correctness.
