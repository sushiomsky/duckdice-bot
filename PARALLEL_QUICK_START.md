# Parallel Betting Quick Start Guide

## What is Parallel Betting?

Parallel betting allows the bot to submit **multiple bets simultaneously** to the DuckDice API, significantly increasing throughput while maintaining correct strategy logic.

### Key Benefit
**Speed**: Up to 3-4x faster than sequential mode!

### How It Works
- Multiple worker threads submit bets concurrently
- Results are processed in order to preserve streak logic
- Thread-safe design protects strategy state

## Usage

### Enable Parallel Mode
Add two flags to your existing commands:

```bash
--parallel                    # Enable parallel mode
--max-concurrent N            # Number of concurrent bets (default: 5)
```

### Examples

#### Simulation (Safe Testing)
```bash
# Sequential (default) - ~16 bets/sec
python3 duckdice_cli.py run -m simulation -s streak-hunter --max-bets 100

# Parallel with 3 concurrent - ~30-40 bets/sec
python3 duckdice_cli.py run -m simulation -s streak-hunter --max-bets 100 \
    --parallel --max-concurrent 3
```

#### Live Betting (Use Caution!)
```bash
# Start with low concurrency
python3 duckdice_cli.py run -m live-main -s classic-martingale \
    -k YOUR_API_KEY --max-bets 50 \
    --parallel --max-concurrent 2
```

## Recommended Settings

| Concurrency | Speed | Risk | Use Case |
|-------------|-------|------|----------|
| 2 | Moderate | Low | Safe live betting |
| 3 | Good | Medium | Balanced performance |
| 5 | Fast | Higher | Simulation/testing |
| 10+ | Very Fast | High | Advanced users only |

## When to Use Parallel

✅ **Good for:**
- High-volume simulations
- Backtesting strategies
- Simple strategies (martingale, fibonacci)
- When API latency is the bottleneck

❌ **Avoid for:**
- First time using the bot
- Learning how strategies work
- If unsure about API rate limits
- When observing each bet is important

## Safety Tips

1. **Start Small**: Begin with `--max-concurrent 2`
2. **Set Limits**: Always use `--max-bets`, `--stop-loss`, or `--take-profit`
3. **Test First**: Run in simulation before going live
4. **Monitor**: Watch for API errors or throttling
5. **Gradual Increase**: Increase concurrency slowly if needed

## Troubleshooting

### "API calls should not happen in dry_run mode"
- Fixed in v4.7.0 - update your code

### Bets seem out of order
- Results are processed in order internally
- Display may show concurrent submissions
- Strategy logic is correct

### API errors or timeouts
- Reduce `--max-concurrent` value
- API may be rate limiting
- Check network connection

## Performance Comparison

```bash
# Test sequential vs parallel
./demo_parallel.sh
```

Expected results (20 bets):
- Sequential: ~1.2 seconds
- Parallel (3): ~0.6 seconds
- Parallel (5): ~0.4 seconds

## Technical Details

### Thread Safety
- Strategy state: Protected by lock
- Bet generation: Sequential
- API calls: Parallel
- Result processing: Sequential (ordered)

### Compatibility
- ✅ Works with all strategies
- ✅ Simulation and live modes
- ✅ All session limits respected
- ✅ Lottery feature compatible

## Version
Parallel betting available in **v4.7.0+**

## Questions?

See full documentation: `PARALLEL_BETTING_COMPLETE.md`
