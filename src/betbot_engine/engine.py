from __future__ import annotations
"""
Auto-betting engine orchestrating strategy execution and API interaction.

Packaged variant that depends on:
- duckdice_api (client)
- betbot_strategies (registry + base types)
"""
import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal, getcontext, InvalidOperation
from typing import Any, Callable, Dict, Optional

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_strategies.base import StrategyContext, SessionLimits, BetSpec, BetResult
from betbot_strategies import list_strategies, get_strategy  # noqa: F401

# Ensure built-in precision is high enough for currency math
getcontext().prec = 28

# Import strategies modules to register them (built-ins)
try:
    # These imports populate the registry via decorators in module import.
    from betbot_strategies import anti_martingale_streak  # noqa: F401
    from betbot_strategies import fib_loss_cluster  # noqa: F401
    from betbot_strategies import kelly_capped  # noqa: F401
    from betbot_strategies import range50_random  # noqa: F401
    from betbot_strategies import max_wager_flow  # noqa: F401
    from betbot_strategies import faucet_cashout  # noqa: F401
    from betbot_strategies import rng_analysis_strategy  # noqa: F401
    # New dicebot-inspired strategies
    from betbot_strategies import classic_martingale  # noqa: F401
    from betbot_strategies import dalembert  # noqa: F401
    from betbot_strategies import fibonacci  # noqa: F401
    from betbot_strategies import labouchere  # noqa: F401
    from betbot_strategies import paroli  # noqa: F401
    from betbot_strategies import oscars_grind  # noqa: F401
    from betbot_strategies import one_three_two_six  # noqa: F401
    # Target-aware strategy
    from betbot_strategies import target_aware  # noqa: F401
    # Scripting engine
    from betbot_strategies import custom_script  # noqa: F401
except Exception:
    # Registration may be deferred if modules missing; CLI listing will show none
    pass


@dataclass
class EngineConfig:
    symbol: str
    delay_ms: int = 50  # Default: fast (50ms)
    jitter_ms: int = 25  # Default: minimal jitter
    dry_run: bool = False
    faucet: bool = False
    stop_loss: float = -0.02  # -2%
    take_profit: float = 0.02  # +2%
    max_bet: Optional[str] = None  # decimal string cap
    max_bets: Optional[int] = None
    max_losses: Optional[int] = None
    max_duration_sec: Optional[int] = None
    seed: Optional[int] = None
    log_dir: str = os.path.join("bet_history", "auto")
    
    @staticmethod
    def get_speed_preset(preset: str = "fast"):
        """
        Get delay/jitter values for speed presets.
        
        Presets:
        - ultra: 10ms delay, 5ms jitter (~80 bets/sec) - RISKY, may hit rate limits
        - turbo: 25ms delay, 10ms jitter (~30 bets/sec) - Aggressive but safer
        - fast: 50ms delay, 25ms jitter (~16 bets/sec) - RECOMMENDED, balanced
        - normal: 150ms delay, 50ms jitter (~5 bets/sec) - Conservative, very safe
        - slow: 500ms delay, 250ms jitter (~1.5 bets/sec) - Maximum observability
        """
        presets = {
            "ultra": (10, 5),
            "turbo": (25, 10),
            "fast": (50, 25),
            "normal": (150, 50),
            "slow": (500, 250),
        }
        return presets.get(preset, (50, 25))  # Default to fast


class AutoBetEngine:
    """
    Encapsulated auto-betting engine for convenient reuse.

    This class wraps the procedural run_auto_bet() while providing
    a simpler object-oriented API and convenience constructors.
    """

    def __init__(self, api: DuckDiceAPI, config: EngineConfig):
        self.api = api
        self.config = config

    def run(
        self,
        strategy_name: str,
        params: Dict[str, Any],
        printer: Optional[Callable[[str], None]] = None,
        json_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_checker: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Run a session using stored api+config and return a summary.
        Delegates to run_auto_bet to preserve behavior.
        """
        return run_auto_bet(
            api=self.api,
            strategy_name=strategy_name,
            params=params,
            config=self.config,
            printer=printer,
            json_sink=json_sink,
            stop_checker=stop_checker,
        )

    @classmethod
    def from_api_key(
        cls,
        api_key: str,
        *,
        symbol: str,
        base_url: str = "https://duckdice.io/api",
        timeout: int = 30,
        **config_overrides: Any,
    ) -> "AutoBetEngine":
        """
        Convenience constructor creating API and EngineConfig in one call.
        """
        api = DuckDiceAPI(DuckDiceConfig(api_key=api_key, base_url=base_url, timeout=timeout))
        # symbol is required for EngineConfig; other fields can be overridden
        cfg = EngineConfig(symbol=symbol, **config_overrides)
        return cls(api, cfg)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _decimal(s: str) -> Decimal:
    try:
        return Decimal(str(s))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Invalid decimal value: {s}") from e


def _parse_user_symbol_balance(user_info: Dict[str, Any], symbol: str) -> Decimal:
    balances = user_info.get("balances") or []
    # Case-insensitive comparison since API returns uppercase currency codes
    symbol_upper = symbol.upper()
    for b in balances:
        currency = (b or {}).get("currency")
        if currency and currency.upper() == symbol_upper:
            main = (b or {}).get("main")
            if main is None:
                return Decimal(0)
            return _decimal(str(main))
    return Decimal(0)


def run_auto_bet(
    api: DuckDiceAPI,
    strategy_name: str,
    params: Dict[str, Any],
    config: EngineConfig,
    printer: Optional[Callable[[str], None]] = None,
    json_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    stop_checker: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Run an auto-betting session and return a summary dict.

    - printer: called with human-readable log lines (CLI/GUI)
    - json_sink: called with structured records per bet (optional)
    - stop_checker: if provided and returns True, the session stops gracefully
    """
    start_ts = time.time()
    _ensure_dir(config.log_dir)

    # Starting balance
    try:
        user_info = api.get_user_info()
        starting_balance = _parse_user_symbol_balance(user_info, config.symbol)
    except Exception as e:
        if printer:
            printer(f"⚠️  Warning: Failed to fetch balance: {e}")
        starting_balance = Decimal(0)

    # Limits
    limits = SessionLimits(
        symbol=config.symbol,
        stop_loss=config.stop_loss,
        take_profit=config.take_profit,
        max_bet=_decimal(config.max_bet) if config.max_bet else None,
        max_bets=config.max_bets,
        max_losses=config.max_losses,
        max_duration_sec=config.max_duration_sec,
    )

    # Logger
    session_id = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(config.log_dir, f"{session_id}_{config.symbol}_{strategy_name}.jsonl")

    def file_sink(rec: Dict[str, Any]) -> None:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def sink(rec: Dict[str, Any]) -> None:
        if json_sink:
            json_sink(rec)
        file_sink(rec)

    # Random
    import random

    rng = random.Random(config.seed or int(time.time() * 1000) & 0xFFFFFFFF)

    # Strategy
    StrategyCls = get_strategy(strategy_name)
    ctx = StrategyContext(
        api=api,
        symbol=config.symbol,
        faucet=config.faucet,
        dry_run=config.dry_run,
        rng=rng,
        logger=sink,
        limits=limits,
        delay_ms=config.delay_ms,
        jitter_ms=config.jitter_ms,
        starting_balance=format(starting_balance, 'f'),
    )
    strategy = StrategyCls(params, ctx)  # type: ignore[call-arg]

    # Session state
    bets_done = 0
    losses_in_row = 0
    current_balance = starting_balance

    def print_line(msg: str) -> None:
        if printer:
            printer(msg)

    # Start
    strategy.on_session_start()
    print_line(f"[start] strategy={strategy_name} symbol={config.symbol} dry_run={config.dry_run} faucet={config.faucet}")

    stopped_reason = "completed"

    try:
        while True:
            # External stop (GUI/other)
            if stop_checker and stop_checker():
                stopped_reason = "stopped"
                break
            # Max duration
            if limits.max_duration_sec and (time.time() - start_ts) >= limits.max_duration_sec:
                stopped_reason = "max_duration"
                break
            if limits.max_bets is not None and bets_done >= limits.max_bets:
                stopped_reason = "max_bets"
                break
            bet = strategy.next_bet()
            if bet is None:
                stopped_reason = "strategy_stopped"
                break

            # Enforce symbol and faucet default
            bet.setdefault("faucet", ctx.faucet)

            # Amount cap
            amount_dec = _decimal(bet["amount"]) if "amount" in bet else Decimal(0)
            if limits.max_bet is not None and amount_dec > limits.max_bet:
                amount_dec = limits.max_bet
                bet["amount"] = format(amount_dec, 'f')
            
            # Balance validation - prevent betting more than available
            if amount_dec > current_balance:
                print_line(f"⚠️  Warning: Strategy requested {amount_dec} but only {current_balance} available")
                # Stop if can't afford minimum bet
                if current_balance <= Decimal("0.00000001"):
                    stopped_reason = "insufficient_balance"
                    break
                # Otherwise cap to current balance
                amount_dec = current_balance
                bet["amount"] = format(amount_dec, 'f')
                print_line(f"   Adjusted bet to {amount_dec} (all available balance)")

            # Execute bet
            ts = time.time()
            api_raw: Dict[str, Any]
            simulated = False
            win = False
            profit = Decimal(0)
            number = None
            payout = None
            chance = None
            is_high = bet.get("is_high") if bet.get("game") == "dice" else None
            range_vals = bet.get("range") if bet.get("game") == "range-dice" else None
            is_in = bet.get("is_in") if bet.get("game") == "range-dice" else None

            if ctx.dry_run:
                simulated = True
                # Simple simulation model
                if bet.get("game") == "dice":
                    chance = str(bet.get("chance"))
                    p = float(Decimal(chance) / Decimal(100)) if chance else 0.5
                    win = rng.random() < p
                    # Approx payout formula typical for dice sites (approximation): 99/chance
                    try:
                        payout_val = float(Decimal(99) / Decimal(chance))
                    except Exception:
                        payout_val = 2.0
                    amount_val = float(amount_dec)
                    profit = Decimal(str((payout_val - 1.0) * amount_val if win else -amount_val))
                    number = int(rng.random() * 10000)
                    payout = str(payout_val)
                else:
                    # range dice: assume 0..9999, inclusive of endpoints
                    r = range_vals or (0, 0)
                    size = max(0, (r[1] - r[0] + 1))
                    p = min(1.0, max(0.0, size / 10000.0))
                    win = (rng.random() < p) if is_in else (rng.random() >= p)
                    payout_val = 1.0 / max(1e-9, (p if is_in else (1.0 - p))) * 0.99
                    amount_val = float(amount_dec)
                    profit = Decimal(str((payout_val - 1.0) * amount_val if win else -amount_val))
                    number = int(rng.random() * 10000)
                    payout = str(payout_val)
                    chance = str(round(p * 100, 5))
                current_balance += profit
                api_raw = {"simulated": True}
            else:
                try:
                    if bet.get("game") == "dice":
                        api_raw = api.play_dice(
                            symbol=config.symbol,
                            amount=bet["amount"],
                            chance=bet["chance"],
                            is_high=bool(bet.get("is_high")),
                            faucet=bool(bet.get("faucet")),
                        )
                    else:
                        r = bet.get("range") or (0, 0)
                        api_raw = api.play_range_dice(
                            symbol=config.symbol,
                            amount=bet["amount"],
                            range_values=[int(r[0]), int(r[1])],
                            is_in=bool(bet.get("is_in")),
                            faucet=bool(bet.get("faucet")),
                        )
                except Exception as e:
                    # Handle API errors gracefully
                    error_msg = str(e)
                    if "insufficient balance" in error_msg.lower() or "422" in error_msg:
                        print_line(f"⚠️  API Error: Insufficient balance to place bet of {amount_dec}")
                        stopped_reason = "insufficient_balance"
                        break
                    else:
                        # Re-raise other errors
                        raise
                
                # Parse
                b = (api_raw or {}).get("bet", {})
                u = (api_raw or {}).get("user", {})
                win = bool(b.get("result"))
                profit = _decimal(str(b.get("profit", "0")))
                current_balance = _decimal(str(u.get("balance", str(current_balance))))
                number = int(b.get("number", 0)) if b.get("number") is not None else None
                payout = str(b.get("payout", ""))
                chance = str(b.get("chance", ""))

            result: BetResult = {
                "win": win,
                "profit": format(profit, 'f'),
                "balance": format(current_balance, 'f'),
                "number": number if number is not None else 0,
                "payout": payout or "",
                "chance": chance or "",
                "is_high": is_high,
                "range": range_vals,  # type: ignore[assignment]
                "is_in": is_in,
                "api_raw": api_raw,
                "simulated": simulated,
                "timestamp": ts,
            }

            # Loss streaks
            if win:
                losses_in_row = 0
            else:
                losses_in_row += 1

            # Log
            sink({
                "event": "bet",
                "time": ts,
                "strategy": strategy_name,
                "symbol": config.symbol,
                "bet": bet,
                "result": result,
                "balance": format(current_balance, 'f'),
                "loss_streak": losses_in_row,
                "bets_done": bets_done + 1,
            })

            # Strategy callback
            strategy.on_bet_result(result)
            bets_done += 1

            # Risk checks
            if limits.max_losses is not None and losses_in_row >= limits.max_losses:
                stopped_reason = "max_losses"
                break
            if starting_balance > 0:
                change_ratio = (current_balance - starting_balance) / starting_balance
                if change_ratio <= Decimal(str(limits.stop_loss)):
                    stopped_reason = "stop_loss"
                    break
                # Only check take_profit if it's set (not None)
                if limits.take_profit is not None and change_ratio >= Decimal(str(limits.take_profit)):
                    stopped_reason = "take_profit"
                    break

            # Output to console
            pl = (current_balance - starting_balance) if starting_balance else Decimal(0)
            pct = (pl / starting_balance * 100) if starting_balance else Decimal(0)
            print_line(f"bet#{bets_done} win={'Y' if win else 'N'} profit={format(profit, 'f')} bal={format(current_balance, 'f')} P/L={format(pl, 'f')} ({pct:.4f}%)")

            # Sleep
            ctx.sleep_with_jitter()

    except KeyboardInterrupt:
        stopped_reason = "cancelled"

    # End
    strategy.on_session_end(stopped_reason)

    duration = time.time() - start_ts
    summary = {
        "strategy": strategy_name,
        "symbol": config.symbol,
        "bets": bets_done,
        "duration_sec": duration,
        "stop_reason": stopped_reason,
        "starting_balance": format(starting_balance, 'f'),
        "ending_balance": format(current_balance, 'f'),
        "profit": format(current_balance - starting_balance, 'f'),
    }
    sink({"event": "summary", **summary})
    print_line(f"[summary] {json.dumps(summary)}")
    return summary
