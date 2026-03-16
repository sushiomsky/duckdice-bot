from __future__ import annotations
"""
Balance Sweep Sniper
====================
Multi-coin lottery sweeper for dust/small balances.

Logic:
  1. Scan ALL coin balances; collect every coin where:
       balance_usd  < usd_threshold  (default $20)
       balance_coin > min_bet
  2. For each eligible coin, bet $0.01 USD worth per roll on a
     0.02%-wide Range Dice window (2 slots of 10 000).
  3. Move to the next coin when the current coin hits OR when its
     balance falls below min_bet.
  4. If a hit occurs anywhere → session ends (jackpot ~4 950×).
  5. When ALL coins are exhausted with no hit, sleep poll_interval_sec
     and re-scan; repeat up to max_wait_cycles times, then stop.

Since every coin is managed via direct API calls inside next_bet(),
the engine's symbol is used only as the session anchor (lifecycle,
logging, Ctrl-C support). Set --symbol to any coin you own.

USD price is fetched from CoinGecko once per session; falls back to
a built-in table and finally to a safe 1 USD/unit floor.
"""

import random
import time
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN = 10_000  # Range Dice slot domain 0–9999
_WIDTH = 2        # 0.02% of 10 000 = 2 slots  ⟹ ~4 950× payout
_UNIT = Decimal("0.00000001")

# CoinGecko IDs for coins commonly found on DuckDice
_COINGECKO_IDS: Dict[str, str] = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "DOGE": "dogecoin",
    "LTC":  "litecoin",
    "XRP":  "ripple",
    "TRX":  "tron",
    "BNB":  "binancecoin",
    "SOL":  "solana",
    "USDT": "tether",
    "USDC": "usd-coin",
    "BCH":  "bitcoin-cash",
    "DASH": "dash",
    "ZEC":  "zcash",
    "ETC":  "ethereum-classic",
    "XLM":  "stellar",
    "ADA":  "cardano",
    "MATIC": "matic-network",
    "XAUT": "tether-gold",
    "DECOY": None,  # internal test coin – treat as $0
}

# Fallback prices (USD) when CoinGecko is unreachable
_FALLBACK_PRICES: Dict[str, float] = {
    "BTC":   60_000.0,
    "ETH":    3_000.0,
    "DOGE":       0.15,
    "LTC":      80.0,
    "XRP":       0.60,
    "TRX":       0.12,
    "BNB":     380.0,
    "SOL":     150.0,
    "USDT":      1.0,
    "USDC":      1.0,
    "BCH":     350.0,
    "DASH":     40.0,
    "ZEC":      25.0,
    "ETC":      25.0,
    "XLM":       0.12,
    "ADA":       0.45,
    "MATIC":     0.70,
    "XAUT":  2_000.0,
    "DECOY":     0.0,
}


def _fetch_coingecko_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch USD prices from CoinGecko for the given symbols."""
    try:
        import requests  # already in requirements

        ids = [
            _COINGECKO_IDS[s.upper()]
            for s in symbols
            if s.upper() in _COINGECKO_IDS and _COINGECKO_IDS[s.upper()]
        ]
        if not ids:
            return {}

        url = "https://api.coingecko.com/api/v3/simple/price"
        resp = requests.get(
            url,
            params={"ids": ",".join(ids), "vs_currencies": "usd"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        result: Dict[str, float] = {}
        for sym in symbols:
            cg_id = _COINGECKO_IDS.get(sym.upper())
            if cg_id and cg_id in data:
                result[sym.upper()] = float(data[cg_id].get("usd", 0))
        return result
    except Exception:
        return {}


def _safe_dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return Decimal("0")


@register("balance-sweep-sniper")
class BalanceSweepSniper:
    """
    Multi-coin sweep: bet $0.01 USD / roll on every small balance coin
    using a 0.02% Range Dice window; stop on first hit.
    """

    @classmethod
    def name(cls) -> str:
        return "balance-sweep-sniper"

    @classmethod
    def describe(cls) -> str:
        return (
            "Multi-coin balance sweeper: scans all coins with USD value < threshold "
            "and bets $0.01 per roll on a 0.02% Range Dice window. Stops on first hit. "
            "Waits and retries when all balances are depleted."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="None (uses existing small balances)",
            volatility="Extreme",
            time_to_profit="Rare / Burst",
            recommended_for="Advanced",
            pros=[
                "Sweeps dust/small balances across ALL coins automatically",
                "Massive payout on hit (~4 950× bet)",
                "Only uses balances below the USD threshold – safe for main funds",
                "Waits and retries when no eligible balance is present",
                "Low per-bet cost thanks to small $0.01 USD sizing",
            ],
            cons=[
                "0.02% win rate – expect ~5 000 bets per coin between wins",
                "All swept coins could be fully depleted before a hit",
                "Negative expected value due to house edge",
                "Requires a CoinGecko price fetch at session start",
            ],
            best_use_case=(
                "Turning idle small / dust balances into lottery tickets. "
                "Run alongside other strategies or after faucet claims."
            ),
            tips=[
                "Lower usd_threshold to sweep only very small balances (e.g. 5.0)",
                "Raise poll_interval_sec for a gentler retry cadence",
                "Set max_wait_cycles=0 to exit instead of waiting when depleted",
                "Use dry_run=true to test without spending real balance",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "usd_threshold": {
                "type": "float",
                "default": 20.0,
                "desc": (
                    "Only bet coins whose total USD value is below this threshold. "
                    "Default $20."
                ),
            },
            "bet_usd": {
                "type": "float",
                "default": 0.01,
                "desc": "Target bet size in USD per roll. Floored to min_bet if too small.",
            },
            "window_mode": {
                "type": "str",
                "default": "random",
                "desc": "Window placement: 'random' | 'sequential' | 'fixed'.",
            },
            "poll_interval_sec": {
                "type": "int",
                "default": 300,
                "desc": "Seconds to wait before re-scanning balances when all coins depleted.",
            },
            "max_wait_cycles": {
                "type": "int",
                "default": 12,
                "desc": (
                    "Max number of wait-and-rescan cycles before giving up. "
                    "0 = exit immediately when all balances are depleted."
                ),
            },
            "delay_ms": {
                "type": "int",
                "default": 600,
                "desc": "Milliseconds to pause between individual bets.",
            },
            "skip_coins": {
                "type": "str",
                "default": "DECOY",
                "desc": "Comma-separated list of coin symbols to skip (e.g. 'DECOY,USDT').",
            },
        }

    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.usd_threshold = float(params.get("usd_threshold", 20.0))
        self.bet_usd = float(params.get("bet_usd", 0.01))
        self.window_mode = str(params.get("window_mode", "random")).lower()
        self.poll_interval_sec = int(params.get("poll_interval_sec", 300))
        self.max_wait_cycles = int(params.get("max_wait_cycles", 12))
        self.delay_ms = int(params.get("delay_ms", 600))

        skip_raw = str(params.get("skip_coins", "DECOY"))
        self.skip_coins = {s.strip().upper() for s in skip_raw.split(",") if s.strip()}

        # State
        self._usd_prices: Dict[str, float] = {}
        self._min_bets: Dict[str, Decimal] = {}
        self._done = False
        self._hit_coin: Optional[str] = None
        self._hit_result: Optional[Dict[str, Any]] = None
        self._total_bets = 0
        self._total_coins_swept = 0
        self._seq_pos = 0
        self._rng = random.Random()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_session_start(self) -> None:
        self._done = False
        self._hit_coin = None
        self._hit_result = None
        self._total_bets = 0
        self._total_coins_swept = 0
        self._seq_pos = 0

        self.ctx.printer(
            f"[balance-sweep-sniper] session start | "
            f"threshold=${self.usd_threshold} | bet=${self.bet_usd:.4f} USD | "
            f"window={self.window_mode} | poll={self.poll_interval_sec}s | "
            f"max_wait={self.max_wait_cycles}"
        )
        self.ctx.printer(
            "[balance-sweep-sniper] fetching USD prices from CoinGecko …"
        )

    def on_session_end(self, reason: str) -> None:
        if self._hit_coin:
            self.ctx.printer(
                f"[balance-sweep-sniper] 🎉 HIT on {self._hit_coin}! "
                f"bets_placed={self._total_bets} | coins_swept={self._total_coins_swept}"
            )
        else:
            self.ctx.printer(
                f"[balance-sweep-sniper] ended ({reason}) | "
                f"bets_placed={self._total_bets} | coins_swept={self._total_coins_swept} | no hit"
            )

    # ── main loop (engine calls this once; all work is done internally) ────────

    def next_bet(self) -> Optional[BetSpec]:
        """
        Run the full multi-coin sweep.  Returns None when done.

        All bets are placed directly via ctx.api.play_range_dice() so that
        any coin can be targeted, not only ctx.symbol.  The engine's betting
        loop therefore runs this method once and the strategy handles
        everything internally, including per-bet delays and wait-cycles.
        """
        if self._done:
            return None

        wait_cycles_used = 0

        while True:
            # ── 1. Fetch balances & prices ───────────────────────────────
            balances = self._get_balances()
            if not balances:
                self.ctx.printer(
                    "[balance-sweep-sniper] ⚠️  Could not fetch balances – retrying…"
                )
                time.sleep(10)
                continue

            all_symbols = list(balances.keys())

            # Refresh prices once per scan cycle
            fetched = _fetch_coingecko_prices(all_symbols)
            if fetched:
                self._usd_prices.update(fetched)
                self.ctx.printer(
                    "[balance-sweep-sniper] USD prices updated via CoinGecko"
                )
            else:
                # Seed from fallback table for any missing symbol
                for sym in all_symbols:
                    if sym not in self._usd_prices:
                        self._usd_prices[sym] = _FALLBACK_PRICES.get(sym, 1.0)
                if not fetched and not self._usd_prices:
                    self.ctx.printer(
                        "[balance-sweep-sniper] ⚠️  CoinGecko unreachable – using fallback prices"
                    )

            # ── 2. Build eligible queue ──────────────────────────────────
            queue = self._build_queue(balances)

            if not queue:
                if self.max_wait_cycles == 0 or wait_cycles_used >= self.max_wait_cycles:
                    self.ctx.printer(
                        "[balance-sweep-sniper] no eligible coins and wait limit reached – stopping."
                    )
                    self._done = True
                    return None

                wait_cycles_used += 1
                self.ctx.printer(
                    f"[balance-sweep-sniper] no eligible coins – waiting "
                    f"{self.poll_interval_sec}s … (cycle {wait_cycles_used}/{self.max_wait_cycles})"
                )
                time.sleep(self.poll_interval_sec)
                continue

            # ── 3. Sweep eligible coins ──────────────────────────────────
            self.ctx.printer(
                f"[balance-sweep-sniper] sweep round | "
                f"eligible coins: {[c for c, *_ in queue]}"
            )

            hit = self._sweep_queue(queue)

            if hit:
                self._done = True
                return None

            # All coins in this round exhausted – go back to wait logic
            wait_cycles_used = 0  # reset after each productive sweep

    # ── sweep helpers ─────────────────────────────────────────────────────────

    def _sweep_queue(
        self, queue: List[Tuple[str, Decimal, Decimal]]
    ) -> bool:
        """
        Bet on each coin until it hits, is depleted, or USD threshold is exceeded.
        Returns True if a hit occurred.
        """
        for symbol, balance, min_bet in queue:
            if symbol in self.skip_coins:
                continue

            usd_price = self._usd_prices.get(symbol, 1.0)
            balance_usd = float(balance) * usd_price
            if balance_usd >= self.usd_threshold:
                self.ctx.printer(
                    f"[balance-sweep-sniper] ⏭  {symbol} now ${balance_usd:.2f} "
                    f"≥ threshold ${self.usd_threshold} – skipping"
                )
                continue

            self.ctx.printer(
                f"[balance-sweep-sniper] → betting {symbol} "
                f"(bal={float(balance):.8f}, ~${balance_usd:.4f} USD, minbet={float(min_bet):.8f})"
            )
            self._total_coins_swept += 1

            hit = self._bet_coin_until_done(symbol, balance, min_bet, usd_price)
            if hit:
                return True

        return False

    def _bet_coin_until_done(
        self,
        symbol: str,
        starting_balance: Decimal,
        min_bet: Decimal,
        usd_price: float,
    ) -> bool:
        """
        Place bets on `symbol` until it hits or balance falls below min_bet.
        Returns True on a win.
        """
        balance = starting_balance

        while balance >= min_bet:
            usd_value = float(balance) * usd_price
            if usd_value >= self.usd_threshold:
                self.ctx.printer(
                    f"[balance-sweep-sniper] ⏭  {symbol} reached "
                    f"${usd_value:.2f} – stopping this coin"
                )
                break

            bet_amount = self._calc_bet_amount(symbol, usd_price, min_bet)
            if bet_amount <= Decimal("0"):
                break

            start, end = self._pick_window()

            try:
                api_raw = self.ctx.api.play_range_dice(
                    symbol=symbol,
                    amount=format(bet_amount, "f"),
                    range_values=[start, end],
                    is_in=True,
                    faucet=False,
                )
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                self.ctx.printer(
                    f"[balance-sweep-sniper] ⚠️  API error for {symbol}: {exc}"
                )
                # Back off a little on API errors
                time.sleep(5)
                break

            self._total_bets += 1

            # Parse result
            balance, won = self._parse_result(api_raw, balance)

            if won:
                payout = float(api_raw.get("payout", api_raw.get("profit", 0)))
                self.ctx.printer(
                    f"[balance-sweep-sniper] 🎉 HIT! coin={symbol} "
                    f"window=[{start},{end}] payout={payout:.8f} "
                    f"new_balance={float(balance):.8f} total_bets={self._total_bets}"
                )
                self._hit_coin = symbol
                self._hit_result = api_raw
                return True

            # Periodic progress log
            if self._total_bets % 500 == 0:
                self.ctx.printer(
                    f"[balance-sweep-sniper] {symbol} | bets={self._total_bets} | "
                    f"bal={float(balance):.8f} (~${float(balance)*usd_price:.4f} USD)"
                )

            # Delay between bets
            if self.delay_ms > 0:
                time.sleep(self.delay_ms / 1000.0)

        self.ctx.printer(
            f"[balance-sweep-sniper] ✓ {symbol} exhausted "
            f"(bal={float(balance):.8f}, minbet={float(min_bet):.8f})"
        )
        return False

    # ── balance / queue helpers ───────────────────────────────────────────────

    def _get_balances(self) -> Dict[str, Decimal]:
        """Return {SYMBOL: balance_decimal} for all coins."""
        try:
            user_info = self.ctx.api.get_user_info()
            if not user_info or "balances" not in user_info:
                return {}
            result: Dict[str, Decimal] = {}
            for entry in user_info["balances"]:
                sym = (entry.get("currency") or "").upper()
                if not sym:
                    continue
                main = entry.get("main", "0") or "0"
                result[sym] = _safe_dec(main)
            return result
        except Exception as exc:
            self.ctx.printer(
                f"[balance-sweep-sniper] ⚠️  get_balances error: {exc}"
            )
            return {}

    def _get_min_bet(self, symbol: str) -> Decimal:
        """Return the minimum bet for *symbol*, using the cache then a default."""
        if symbol in self._min_bets:
            return self._min_bets[symbol]
        try:
            from betbot_engine.min_bet_cache import get_min_bet as _cached
            cached = _cached(symbol)
            if cached and cached > 0:
                self._min_bets[symbol] = cached
                return cached
        except Exception:
            pass
        fallback = Decimal("0.00000001")
        self._min_bets[symbol] = fallback
        return fallback

    def _build_queue(
        self, balances: Dict[str, Decimal]
    ) -> List[Tuple[str, Decimal, Decimal]]:
        """
        Return list of (symbol, balance, min_bet) for coins that are:
          - not in skip_coins
          - balance > min_bet
          - USD value of balance < usd_threshold
        """
        queue: List[Tuple[str, Decimal, Decimal]] = []
        for sym, bal in sorted(balances.items()):
            if sym in self.skip_coins:
                continue
            if bal <= Decimal("0"):
                continue
            min_bet = self._get_min_bet(sym)
            if bal < min_bet:
                continue
            usd_price = self._usd_prices.get(sym, _FALLBACK_PRICES.get(sym, 1.0))
            if usd_price <= 0:
                continue  # skip coins with no known price (e.g. DECOY)
            balance_usd = float(bal) * usd_price
            if balance_usd >= self.usd_threshold:
                continue
            queue.append((sym, bal, min_bet))
        return queue

    # ── bet sizing / window ───────────────────────────────────────────────────

    def _calc_bet_amount(
        self, symbol: str, usd_price: float, min_bet: Decimal
    ) -> Decimal:
        """Bet $bet_usd worth of *symbol*, clamped to [min_bet, balance]."""
        if usd_price <= 0:
            return Decimal("0")
        raw = Decimal(str(self.bet_usd)) / Decimal(str(usd_price))
        raw = raw.quantize(_UNIT, rounding=ROUND_DOWN)
        amt = max(raw, min_bet)
        return amt

    def _pick_window(self) -> Tuple[int, int]:
        max_start = _DOMAIN - _WIDTH  # 9998
        if self.window_mode == "fixed":
            start = 4999
        elif self.window_mode == "sequential":
            start = self._seq_pos
            self._seq_pos = (self._seq_pos + 1) % (max_start + 1)
        else:  # random (default)
            start = self._rng.randint(0, max_start)
        return start, start + _WIDTH - 1

    # ── result parsing ────────────────────────────────────────────────────────

    def _parse_result(
        self, api_raw: Dict[str, Any], fallback_balance: Decimal
    ) -> Tuple[Decimal, bool]:
        """Return (new_balance, won) from a raw API response."""
        won = bool(
            api_raw.get("win")
            or api_raw.get("isWin")
            or api_raw.get("won")
        )

        # DuckDice balance fields vary slightly by endpoint version
        for field in ("balance", "userBalance", "user_balance", "newBalance"):
            raw_val = api_raw.get(field)
            if raw_val is not None:
                parsed = _safe_dec(raw_val)
                if parsed > Decimal("0") or won:
                    return parsed, won

        # Fall back: apply profit to known balance
        profit = _safe_dec(api_raw.get("profit", "0"))
        return fallback_balance + profit, won

    # ── protocol stubs (engine requires these) ────────────────────────────────

    def on_bet_result(self, result: BetResult) -> None:
        # All results are handled internally; this is a no-op.
        pass
