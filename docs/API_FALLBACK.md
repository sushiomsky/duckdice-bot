# API Fallback Domain Support

## Overview

The DuckDice bot now supports automatic failover to alternative API domains when the primary domain is unavailable. This improves resilience and ensures your bot can continue operating even when one domain has connectivity issues.

## How It Works

### Default Behavior

By default, the bot tries API endpoints in this order:

1. **https://duckdice.io/api** (primary)
2. **https://duckdice.live/api** (fallback #1)
3. **https://duckdice.net/api** (fallback #2)

### Automatic Switching

When an API call fails due to:
- Connection errors (server unreachable)
- Timeout errors (server too slow)
- HTTP errors (500, 502, 503, etc.)

The bot automatically tries the next domain in the list.

### Domain Caching

Once a working domain is found, the bot remembers it and uses it for all subsequent requests in that session. This improves performance by avoiding unnecessary retries.

## Example Output

```
⚠ duckdice.io unavailable, trying next...
✓ Switched to https://duckdice.live/api
```

## Configuration

### Using Default Fallback Domains

No configuration needed! The fallback domains are enabled by default:

```bash
# All these commands use fallback automatically
duckdice run -m live-main -c btc -s martingale
```

### Custom Fallback Domains

If you want to customize the fallback list, you can do so in code:

```python
from src.duckdice_api.api import DuckDiceAPI, DuckDiceConfig

config = DuckDiceConfig(
    api_key='your_api_key',
    base_url='https://duckdice.io/api',
    fallback_domains=[
        'https://duckdice.io/api',
        'https://duckdice.live/api',
        'https://custom-mirror.com/api',  # Your custom domain
    ]
)

api = DuckDiceAPI(config)
```

### Disable Fallback

To disable fallback and only use the primary domain:

```python
config = DuckDiceConfig(
    api_key='your_api_key',
    base_url='https://duckdice.io/api',
    fallback_domains=[],  # Empty list = no fallback
)
```

## Testing

To verify the fallback functionality:

```bash
# Run the test script
python test_api_fallback.py

# Run a simulation
python duckdice_cli.py run -m simulation -c btc -s simple-progression-40 -b 100 --max-bets 10
```

## Benefits

1. **Improved Uptime**: Bot continues running even when primary domain is down
2. **Automatic Recovery**: No manual intervention needed
3. **Transparent**: Works seamlessly without changing your commands
4. **Performance**: Caches working domain to avoid retry overhead
5. **Configurable**: Can customize fallback list or disable entirely

## Technical Details

### Implementation

The fallback logic is implemented in `src/duckdice_api/api.py`:

- `DuckDiceConfig`: Configuration with `fallback_domains` list
- `DuckDiceAPI._make_request()`: Automatic retry with fallback domains
- `DuckDiceAPI.current_base_url`: Tracks the currently working domain

### Error Handling

The following exceptions trigger a fallback attempt:
- `requests.exceptions.ConnectionError`
- `requests.exceptions.Timeout`
- `requests.exceptions.HTTPError`

Other exceptions (like JSON decode errors) do NOT trigger fallback, as they indicate issues with the response data rather than connectivity.

### Timeout Configuration

Each domain attempt uses the configured timeout (default: 10 seconds):

```python
config = DuckDiceConfig(
    api_key='your_api_key',
    timeout=5,  # Try each domain for max 5 seconds
)
```

With 3 fallback domains and 5-second timeout, worst case is 15 seconds before giving up.

## Troubleshooting

### All Domains Failing

If all fallback domains fail, you'll see:

```
⚠ duckdice.io unavailable, trying next...
⚠ duckdice.live unavailable, trying next...
❌ All API endpoints failed
Request Error: [exception details]
```

**Possible causes**:
- Internet connection down
- Firewall blocking all domains
- API key invalid
- All DuckDice domains experiencing outage

**Solutions**:
1. Check your internet connection
2. Verify firewall settings
3. Confirm API key is valid
4. Check DuckDice status page

### Frequent Domain Switches

If the bot switches domains frequently during a session:

```
✓ Switched to https://duckdice.live/api
... (some bets) ...
✓ Switched to https://duckdice.net/api
... (some bets) ...
✓ Switched to https://duckdice.io/api
```

**Possible causes**:
- Unstable network connection
- DuckDice load balancing issues
- DNS resolution problems

**Solutions**:
1. Check network stability
2. Try wired connection instead of WiFi
3. Flush DNS cache
4. Contact DuckDice support if persistent

## See Also

- [User Guide](USER_GUIDE.md) - General usage instructions
- [CLI Guide](CLI_GUIDE.md) - Command-line options
- [Getting Started](GETTING_STARTED.md) - Quick start guide
