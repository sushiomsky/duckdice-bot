from __future__ import annotations
"""
Persistent cache for per-coin minimum bet amounts discovered via the API.

File: data/min_bets.json
Format: {"BTC": "0.00000001", "ETH": "0.000001", "DOGE": "1.0", ...}

Written by: duckdice probe-min-bets
Read by:    run_auto_bet() to pre-populate discovered_api_min_bet
"""
import json
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

_DEFAULT_PATH = Path("data/min_bets.json")


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
