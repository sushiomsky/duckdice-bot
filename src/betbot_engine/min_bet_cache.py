from __future__ import annotations
"""
Persistent cache for per-coin minimum bet amounts discovered via the API.

File: data/min_bets.json
Format: {"BTC": "0.00000001", "ETH": "0.000001", "DOGE": "1.0", ...}

Written by: duckdice probe-min-bets  AND  auto-probed on every live session start
Read by:    run_auto_bet() to pre-populate discovered_api_min_bet
"""
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Optional, Dict

_DEFAULT_PATH = Path("data/min_bets.json")
_PROBE_AMOUNT = "0.00000001"


def load(path: Path = _DEFAULT_PATH) -> Dict[str, str]:
    """Return {SYMBOL: amount_str} from cache file, empty dict if missing."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return {}


def save(data: Dict[str, str], path: Path = _DEFAULT_PATH) -> None:
    """Write {SYMBOL: amount_str} to cache file (creates parent dirs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def get_min_bet(symbol: str, path: Path = _DEFAULT_PATH) -> Optional[Decimal]:
    """Return Decimal min-bet for *symbol* from cache, or None if not cached."""
    cache = load(path)
    val = cache.get(symbol.upper())
    if val:
        try:
            return Decimal(val)
        except Exception:
            pass
    return None


def set_min_bet(symbol: str, amount: Decimal, path: Path = _DEFAULT_PATH) -> None:
    """Upsert *symbol* → *amount* in cache and persist immediately."""
    cache = load(path)
    cache[symbol.upper()] = str(amount)
    save(cache, path)


def parse_min_bet_from_error(error_text: str) -> Optional[Decimal]:
    """Extract a minimum-bet Decimal from an API error string/response body.

    DuckDice error format:
        {"error":"The minimum bet is 1 DOGE","params":{"amount":"1.00000000","symbol":"DOGE"}}
    Falls back to scanning for the first number after 'minimum'.
    Returns None if no value could be extracted.
    """
    # Primary: structured params.amount field
    match = re.search(r'"amount"\s*:\s*"([0-9]+\.?[0-9]*)"', error_text)
    if match and "minimum" in error_text.lower():
        try:
            return Decimal(match.group(1))
        except InvalidOperation:
            pass
    # Fallback: first number in "minimum bet is X" style message
    fallback = re.search(r"minimum\s+bet.*?([0-9]+\.?[0-9]*)", error_text, re.IGNORECASE)
    if fallback:
        try:
            return Decimal(fallback.group(1))
        except InvalidOperation:
            pass
    return None


def probe_coin(
    api,
    symbol: str,
    printer: Optional[Callable[[str], None]] = None,
    path: Path = _DEFAULT_PATH,
) -> Optional[Decimal]:
    """Place a tiny probe bet to discover the API minimum for *symbol*.

    - If the probe bet is accepted (min ≤ 0.00000001) the bet really executes
      (negligible amount).
    - If rejected with a "minimum bet" error the minimum is read from the
      response body.
    - The result is persisted to the cache and returned.
    - Returns None only if the error could not be parsed at all.
    """
    try:
        api.play_dice(
            symbol=symbol,
            amount=_PROBE_AMOUNT,
            chance="49.50",
            is_high=False,
            faucet=False,
        )
        # Bet accepted — min is at most the probe amount
        min_bet = Decimal(_PROBE_AMOUNT)
        set_min_bet(symbol, min_bet, path)
        if printer:
            printer(f"   🔍 {symbol} min bet: ≤ {_PROBE_AMOUNT}")
        return min_bet
    except Exception as exc:
        err_str = str(exc)
        resp_text = ""
        if hasattr(exc, "response") and hasattr(exc.response, "text"):
            resp_text = exc.response.text
        search_text = resp_text if resp_text else err_str

        min_bet = parse_min_bet_from_error(search_text)
        if min_bet is not None:
            set_min_bet(symbol, min_bet, path)
            if printer:
                printer(f"   🔍 {symbol} min bet: {min_bet}")
            return min_bet

        if printer:
            printer(f"   ⚠️  {symbol} min bet unknown — {search_text[:120]}")
        return None


def ensure_probed(
    api,
    symbol: str,
    printer: Optional[Callable[[str], None]] = None,
    path: Path = _DEFAULT_PATH,
) -> Decimal:
    """Return the known min-bet for *symbol*, probing the API if not yet cached.

    Always returns a usable Decimal (falls back to 0.00000001 if probe fails).
    """
    cached = get_min_bet(symbol, path)
    if cached is not None:
        return cached
    if printer:
        printer(f"   🔍 Probing min bet for {symbol}…")
    probed = probe_coin(api, symbol, printer, path)
    return probed if probed is not None else Decimal(_PROBE_AMOUNT)
