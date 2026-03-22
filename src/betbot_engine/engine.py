from __future__ import annotations
"""
Auto-betting engine orchestrating strategy execution and API interaction.

Packaged variant that depends on:
- duckdice_api (client)
- betbot_strategies (registry + base types)
"""
import json
import os
import re
import time
import random
from dataclasses import dataclass
from decimal import Decimal, getcontext, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_strategies.base import StrategyContext, SessionLimits, BetSpec, BetResult
from betbot_strategies import list_strategies, get_strategy  # noqa: F401

try:
    from .events import (
        SessionStartedEvent, BetPlacedEvent, BetResultEvent, 
        StatsUpdatedEvent, SessionEndedEvent, WarningEvent, ErrorEvent
    )
    from .observers import EventEmitter
    _EVENTS_AVAILABLE = True
except ImportError:
    _EVENTS_AVAILABLE = False

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
    # Low-end jackpot hunter
    from betbot_strategies import low_hunter  # noqa: F401
    # Volatility spike hunter (quant-grade state machine)
    from betbot_strategies import volatility_spike_hunter  # noqa: F401
    # Combined High-Roller System (Kelly Hybrid / Streak Harvester / Volatility Breakout)
    from betbot_strategies import combined_high_roller  # noqa: F401
    # TLE wager farming strategy
    from betbot_strategies import tle_wager_farming  # noqa: F401
    # Wager Loop Stabilizer V2 strategy
    from betbot_strategies import wager_loop_stabilizer_v2  # noqa: F401
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
    db_log: bool = True  # Enable database logging
    db_path: Optional[str] = None  # Custom database path
    tle_hash: Optional[str] = None  # Time Limited Event hash for TLE bets
    lottery_enabled: bool = False  # Engine-level lottery shots
    lottery_min_gap: int = 10  # Minimum bets between lottery shots
    lottery_max_gap: int = 50  # Maximum bets between lottery shots
    lottery_min_chance: float = 0.01  # Min lottery chance (%)
    lottery_max_chance: float = 1.0  # Max lottery chance (%)
    
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
        self.emitter = EventEmitter() if _EVENTS_AVAILABLE else None

    def run(
        self,
        strategy_name: str,
        params: Dict[str, Any],
        printer: Optional[Callable[[str], None]] = None,
        json_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_checker: Optional[Callable[[], bool]] = None,
        emitter: Optional['EventEmitter'] = None,
        resume_state: Optional[Dict[str, Any]] = None,
        bet_offset_fn: Optional[Callable[[], 'Decimal']] = None,
    ) -> Dict[str, Any]:
        """Run a session using stored api+config and return a summary.
        Delegates to run_auto_bet to preserve behavior.
        
        Args:
            strategy_name: Name of the betting strategy
            params: Strategy parameters
            printer: Optional callback for text output (legacy)
            json_sink: Optional callback for structured events (legacy)
            stop_checker: Optional callback to check if session should stop
            emitter: Optional EventEmitter to use instead of self.emitter
            resume_state: Optional dict with prior session state to restore
        """
        return run_auto_bet(
            api=self.api,
            strategy_name=strategy_name,
            params=params,
            config=self.config,
            printer=printer,
            json_sink=json_sink,
            stop_checker=stop_checker,
            emitter=emitter or self.emitter,
            resume_state=resume_state,
            bet_offset_fn=bet_offset_fn,
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


def _validate_and_adjust_bet(
    bet: BetSpec,
    current_balance: Decimal,
    min_bet: Decimal = Decimal("0.00000001"),
    max_chance: Decimal = Decimal("98"),
    min_chance: Decimal = Decimal("0.01"),
    printer: Optional[Callable[[str], None]] = None,
) -> Optional[BetSpec]:
    """
    Validate and adjust bet to meet minimum constraints.
    
    Adjustments made (in priority order):
    1. Enforce minimum bet amount
    2. Cap bet to available balance
    3. Ensure chance is within valid range
    4. Attempt to meet minimum profit constraint by adjusting bet or chance
    
    Returns:
        Adjusted BetSpec if valid bet can be constructed, None otherwise
    """
    def print_line(msg: str) -> None:
        if printer:
            printer(msg)
    
    # Extract bet parameters
    try:
        amount_dec = _decimal(bet.get("amount", "0"))
    except (ValueError, InvalidOperation):
        print_line("⚠️  Invalid bet amount format")
        return None
    
    game = bet.get("game", "dice")
    
    # For dice game, extract chance
    if game == "dice":
        try:
            chance_dec = _decimal(bet.get("chance", "50"))
        except (ValueError, InvalidOperation):
            print_line("⚠️  Invalid chance format")
            return None
    else:
        # Range dice doesn't use chance parameter
        chance_dec = None
    
    # 1. Enforce minimum bet
    original_amount = amount_dec
    if amount_dec < min_bet:
        amount_dec = min_bet
        if printer:
            print_line(f"   📈 Adjusted bet from {original_amount} to minimum {min_bet}")
    
    # 2. Cap at available balance
    if amount_dec > current_balance:
        if current_balance < min_bet:
            # Cannot place any valid bet
            print_line(f"⚠️  Insufficient balance ({current_balance}) for minimum bet ({min_bet})")
            return None
        amount_dec = current_balance
        print_line(f"   ⚖️  Capped bet to available balance: {amount_dec}")
    
    # 3. Validate chance range (dice only)
    if game == "dice" and chance_dec is not None:
        if chance_dec > max_chance:
            chance_dec = max_chance
            print_line(f"   ⚖️  Capped chance to maximum: {chance_dec}%")
        elif chance_dec < min_chance:
            chance_dec = min_chance
            print_line(f"   📈 Raised chance to minimum: {chance_dec}%")
    
    # 4. Check minimum profit constraint (dice only)
    # profit = bet * (payout_multiplier - 1)
    # payout_multiplier ≈ 99 / chance (house edge ~1%)
    # For profit >= min_bet: bet * ((99/chance) - 1) >= min_bet
    if game == "dice" and chance_dec is not None and chance_dec > Decimal("0"):
        try:
            payout_multiplier = Decimal("99") / chance_dec
            expected_profit = amount_dec * (payout_multiplier - Decimal("1"))
            
            if expected_profit < min_bet:
                # Try to fix by increasing bet amount
                required_bet = min_bet / (payout_multiplier - Decimal("1"))
                
                if required_bet <= current_balance:
                    # Can increase bet to meet profit requirement
                    print_line(f"   💰 Increased bet from {amount_dec} to {required_bet} to meet minimum profit")
                    amount_dec = required_bet
                else:
                    # Try to fix by decreasing chance (higher multiplier)
                    # profit = bet * ((99/chance) - 1) >= min_bet
                    # (99/chance) >= (min_bet/bet) + 1
                    # chance <= 99 / ((min_bet/bet) + 1)
                    max_valid_chance = Decimal("99") / ((min_bet / amount_dec) + Decimal("1"))
                    
                    if max_valid_chance >= min_chance:
                        print_line(f"   🎯 Reduced chance from {chance_dec}% to {max_valid_chance}% to meet minimum profit")
                        chance_dec = max_valid_chance
                    else:
                        # Cannot satisfy constraints
                        print_line(f"⚠️  Cannot construct valid bet: profit ({expected_profit}) < minimum ({min_bet})")
                        print_line(f"      Balance too low for this chance setting")
                        return None
        except (InvalidOperation, ZeroDivisionError):
            # Calculation failed, allow bet to proceed
            pass
    
    # Build adjusted bet
    # Use reasonable precision for API (8 decimal places for crypto)
    adjusted_bet = dict(bet)
    
    # Quantize to 8 decimal places and strip trailing zeros
    amount_quantized = amount_dec.quantize(Decimal("0.00000001"))
    adjusted_bet["amount"] = str(amount_quantized)
    
    if game == "dice" and chance_dec is not None:
        # Quantize chance to 2 decimal places (e.g., 95.50%)
        chance_quantized = chance_dec.quantize(Decimal("0.01"))
        adjusted_bet["chance"] = str(chance_quantized)
    
    return adjusted_bet


def _load_starting_balance(
    api: DuckDiceAPI,
    symbol: str,
    printer: Optional[Callable[[str], None]],
    emitter: Optional['EventEmitter'],
) -> Decimal:
    try:
        user_info = api.get_user_info()
        return _parse_user_symbol_balance(user_info, symbol)
    except Exception as e:
        if printer:
            printer(f"⚠️  Warning: Failed to fetch balance: {e}")
        if emitter and _EVENTS_AVAILABLE:
            emitter.emit(WarningEvent(
                timestamp=time.time(),
                message=f"Failed to fetch balance: {e}",
                details={"exception": str(e)},
            ))
        return Decimal(0)


def _build_limits(config: EngineConfig) -> SessionLimits:
    return SessionLimits(
        symbol=config.symbol,
        stop_loss=config.stop_loss,
        take_profit=config.take_profit,
        max_bet=_decimal(config.max_bet) if config.max_bet else None,
        max_bets=config.max_bets,
        max_losses=config.max_losses,
        max_duration_sec=config.max_duration_sec,
    )


def _init_db_logger(config: EngineConfig, printer: Optional[Callable[[str], None]]):
    if not config.db_log:
        return None
    try:
        from .bet_database import BetDatabase
        db_path = Path(config.db_path) if config.db_path else None
        return BetDatabase(db_path)
    except Exception as e:
        if printer:
            printer(f"⚠️  Database logging disabled: {e}")
        return None


def _build_sink(
    log_file: str,
    json_sink: Optional[Callable[[Dict[str, Any]], None]],
) -> Callable[[Dict[str, Any]], None]:
    class _BufferedJsonlSink:
        def __init__(self, path: str, external_sink: Optional[Callable[[Dict[str, Any]], None]], flush_every: int = 50):
            self._external_sink = external_sink
            self._flush_every = max(1, int(flush_every))
            self._count = 0
            self._fh = open(path, "a", encoding="utf-8")

        def __call__(self, rec: Dict[str, Any]) -> None:
            if self._external_sink:
                self._external_sink(rec)
            self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._count += 1
            if self._count % self._flush_every == 0 or rec.get("event") == "summary":
                self._fh.flush()

        def close(self) -> None:
            if not self._fh.closed:
                self._fh.flush()
                self._fh.close()

    return _BufferedJsonlSink(log_file, json_sink)


def _init_lottery_state(config: EngineConfig, rng: random.Random) -> tuple[int, int, int]:
    lottery_min_gap = max(1, int(config.lottery_min_gap))
    lottery_max_gap = max(lottery_min_gap, int(config.lottery_max_gap))
    lottery_countdown = (
        rng.randint(lottery_min_gap, lottery_max_gap)
        if config.lottery_enabled
        else -1
    )
    return lottery_min_gap, lottery_max_gap, lottery_countdown


def _resolve_discovered_min_bet(
    api: DuckDiceAPI,
    config: EngineConfig,
    print_line: Callable[[str], None],
) -> Decimal:
    discovered_api_min_bet = Decimal("0.00000001")
    try:
        from betbot_engine.min_bet_cache import ensure_probed as _ensure_probed
        probe_fn = _ensure_probed if not config.dry_run else None
    except Exception:
        probe_fn = None

    if probe_fn is not None:
        try:
            discovered_api_min_bet = probe_fn(api, config.symbol, print_line)
        except Exception:
            pass
    else:
        try:
            from betbot_engine.min_bet_cache import get_min_bet as _get_cached_min_bet
            cached = _get_cached_min_bet(config.symbol)
            if cached:
                discovered_api_min_bet = cached
        except Exception:
            pass
    return discovered_api_min_bet


def _prepare_bet_for_execution(
    bet: BetSpec,
    *,
    ctx: StrategyContext,
    limits: SessionLimits,
    config: EngineConfig,
    rng: random.Random,
    lottery_countdown: int,
    lottery_min_gap: int,
    lottery_max_gap: int,
    current_balance: Decimal,
    discovered_api_min_bet: Decimal,
    bet_offset_fn: Optional[Callable[[], 'Decimal']],
    print_line: Callable[[str], None],
) -> tuple[Optional[BetSpec], Optional[str], bool, Optional[str], int, str]:
    if bet_offset_fn is not None:
        try:
            offset = bet_offset_fn()
            if offset and offset > 0:
                raw = _decimal(bet.get("amount", "0"))
                bet["amount"] = format(raw + offset, 'f')
        except Exception:
            pass

    bet.setdefault("faucet", ctx.faucet)
    original_game = str(bet.get("game", "dice"))
    lottery_applied = False
    lottery_chance: Optional[str] = None

    if limits.max_bet is not None:
        try:
            amount_dec = _decimal(bet.get("amount", "0"))
            if amount_dec > limits.max_bet:
                bet["amount"] = format(limits.max_bet, 'f')
                print_line(f"   ⚖️  Capped bet to session max_bet: {limits.max_bet}")
        except (ValueError, InvalidOperation):
            pass

    if config.lottery_enabled:
        if lottery_countdown <= 0:
            lottery_applied = True
            chance_val = Decimal(
                str(round(rng.uniform(config.lottery_min_chance, config.lottery_max_chance), 4))
            )
            chance_val = max(Decimal("0.01"), min(Decimal("1.00"), chance_val))
            bet = dict(bet)
            bet["game"] = "dice"
            bet["chance"] = format(chance_val, "f")
            if "is_high" not in bet:
                bet["is_high"] = bool(rng.getrandbits(1))
            lottery_chance = bet["chance"]
            lottery_countdown = rng.randint(lottery_min_gap, lottery_max_gap)
        else:
            lottery_countdown -= 1

    validated_bet = _validate_and_adjust_bet(
        bet=bet,
        current_balance=current_balance,
        min_bet=discovered_api_min_bet,
        printer=print_line,
    )
    if validated_bet is None:
        return None, "insufficient_balance", lottery_applied, lottery_chance, lottery_countdown, original_game

    return validated_bet, None, lottery_applied, lottery_chance, lottery_countdown, original_game


def run_auto_bet(
    api: DuckDiceAPI,
    strategy_name: str,
    params: Dict[str, Any],
    config: EngineConfig,
    printer: Optional[Callable[[str], None]] = None,
    json_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    stop_checker: Optional[Callable[[], bool]] = None,
    emitter: Optional['EventEmitter'] = None,
    resume_state: Optional[Dict[str, Any]] = None,
    bet_offset_fn: Optional[Callable[[], 'Decimal']] = None,
) -> Dict[str, Any]:
    """Run an auto-betting session and return a summary dict.

    - printer: called with human-readable log lines (CLI/GUI) [LEGACY]
    - json_sink: called with structured records per bet (optional) [LEGACY]
    - stop_checker: if provided and returns True, the session stops gracefully
    - emitter: EventEmitter for event-driven interfaces (recommended)
    - bet_offset_fn: if provided, its return value is added to every bet amount
                     (used by the keypress bet-size adjuster)
    """
    start_ts = time.time()
    _ensure_dir(config.log_dir)

    starting_balance = _load_starting_balance(api, config.symbol, printer, emitter)
    limits = _build_limits(config)
    db = _init_db_logger(config, printer)

    # Logger
    session_id = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(config.log_dir, f"{session_id}_{config.symbol}_{strategy_name}.jsonl")
    sink = _build_sink(log_file, json_sink)

    # Random
    rng = random.Random(config.seed or int(time.time() * 1000) & 0xFFFFFFFF)
    lottery_min_gap, lottery_max_gap, lottery_countdown = _init_lottery_state(config, rng)

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
        printer=printer if printer else print,
    )
    strategy = StrategyCls(params, ctx)  # type: ignore[call-arg]

    # Session state
    bets_done = 0
    wins_count = 0
    losses_count = 0
    losses_in_row = 0
    current_balance = starting_balance
    def print_line(msg: str) -> None:
        if printer:
            printer(msg)

    discovered_api_min_bet = _resolve_discovered_min_bet(api, config, print_line)

    # Start
    strategy.on_session_start()
    # Restore prior session state (if resuming a cancelled session)
    if resume_state and hasattr(strategy, 'on_resume'):
        try:
            strategy.on_resume(resume_state)
        except Exception as e:
            print_line(f"⚠️  State restore failed (starting fresh): {e}")
    start_msg = f"[start] strategy={strategy_name} symbol={config.symbol} dry_run={config.dry_run} faucet={config.faucet}"
    if resume_state:
        start_msg += f" resumed_from={resume_state.get('resumed_from', 'unknown')}"
    print_line(start_msg)
    
    # Start database session
    if db:
        try:
            db.start_session(
                session_id=session_id,
                strategy_name=strategy_name,
                symbol=config.symbol,
                simulation_mode=config.dry_run,
                starting_balance=starting_balance,
                strategy_params=params,
                limits={
                    'stop_loss': config.stop_loss,
                    'take_profit': config.take_profit,
                    'max_bet': config.max_bet,
                    'max_bets': config.max_bets,
                    'max_losses': config.max_losses,
                    'max_duration_sec': config.max_duration_sec,
                },
                metadata={'resumed_from': resume_state.get('resumed_from')} if resume_state else None,
            )
        except Exception as e:
            print_line(f"⚠️  Database session start failed: {e}")
    
    if emitter and _EVENTS_AVAILABLE:
        emitter.emit(SessionStartedEvent(
            timestamp=start_ts,
            strategy_name=strategy_name,
            config=params,
            starting_balance=starting_balance,
            currency=config.symbol
        ))

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

            prepared_bet, stop_reason, lottery_applied, lottery_chance, lottery_countdown, original_game = (
                _prepare_bet_for_execution(
                    bet,
                    ctx=ctx,
                    limits=limits,
                    config=config,
                    rng=rng,
                    lottery_countdown=lottery_countdown,
                    lottery_min_gap=lottery_min_gap,
                    lottery_max_gap=lottery_max_gap,
                    current_balance=current_balance,
                    discovered_api_min_bet=discovered_api_min_bet,
                    bet_offset_fn=bet_offset_fn,
                    print_line=print_line,
                )
            )
            if prepared_bet is None:
                stopped_reason = stop_reason or "insufficient_balance"
                break

            bet = prepared_bet
            amount_dec = _decimal(bet["amount"])

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
                            tle_hash=config.tle_hash or None,
                        )
                    else:
                        r = bet.get("range") or (0, 0)
                        api_raw = api.play_range_dice(
                            symbol=config.symbol,
                            amount=bet["amount"],
                            range_values=[int(r[0]), int(r[1])],
                            is_in=bool(bet.get("is_in")),
                            faucet=bool(bet.get("faucet")),
                            tle_hash=config.tle_hash or None,
                        )
                except Exception as e:
                    # Handle API errors gracefully
                    error_msg = str(e)

                    # Build full search text from response body if available
                    response_text = ""
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        response_text = e.response.text
                    search_text = response_text if response_text else error_msg

                    # Try to parse a new minimum bet from the error
                    # (covers initial too-small bet AND mid-session min-bet changes)
                    try:
                        from betbot_engine.min_bet_cache import (
                            parse_min_bet_from_error as _parse_min,
                            set_min_bet as _set_cached_min_bet,
                        )
                        api_min_bet = _parse_min(search_text)
                    except Exception:
                        api_min_bet = None

                    if api_min_bet is not None:
                        # Add a tiny buffer (1%) so we never hit the floor again
                        api_min_bet_buffered = (api_min_bet * Decimal("1.01")).quantize(
                            Decimal("0.00000001")
                        )
                        # Update session floor and persist to cache
                        discovered_api_min_bet = api_min_bet_buffered
                        print_line(
                            f"⚠️  Min bet changed. API minimum: {api_min_bet} "
                            f"→ using {api_min_bet_buffered} (+1% buffer)"
                        )
                        try:
                            _set_cached_min_bet(config.symbol, api_min_bet_buffered)
                        except Exception:
                            pass

                        # Retry with new minimum
                        if api_min_bet_buffered <= current_balance:
                            print_line(f"   🔄 Retrying with: {api_min_bet_buffered}")
                            bet["amount"] = str(api_min_bet_buffered)
                            amount_dec = api_min_bet_buffered
                            try:
                                if bet.get("game") == "dice":
                                    api_raw = api.play_dice(
                                        symbol=config.symbol,
                                        amount=bet["amount"],
                                        chance=bet["chance"],
                                        is_high=bool(bet.get("is_high")),
                                        faucet=bool(bet.get("faucet")),
                                        tle_hash=config.tle_hash or None,
                                    )
                                else:
                                    r = bet.get("range") or (0, 0)
                                    api_raw = api.play_range_dice(
                                        symbol=config.symbol,
                                        amount=bet["amount"],
                                        range_values=[int(r[0]), int(r[1])],
                                        is_in=bool(bet.get("is_in")),
                                        faucet=bool(bet.get("faucet")),
                                        tle_hash=config.tle_hash or None,
                                    )
                            except Exception as retry_error:
                                print_line(f"⚠️  Retry failed: {retry_error}")
                                stopped_reason = "api_error"
                                break
                        else:
                            print_line(
                                f"⚠️  Insufficient balance ({current_balance}) "
                                f"for minimum bet ({api_min_bet_buffered})"
                            )
                            stopped_reason = "insufficient_balance"
                            break
                    elif "insufficient balance" in error_msg.lower():
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

            # Emit placed-bet event with the actual executed amount/chance payload.
            if emitter and _EVENTS_AVAILABLE:
                try:
                    placed_chance = float(chance) if chance not in (None, "") else float(bet.get("chance", 0.0))
                except Exception:
                    placed_chance = 0.0
                try:
                    placed_payout = float(payout) if payout not in (None, "") else float(bet.get("payout_multiplier", 0.0))
                except Exception:
                    placed_payout = 0.0

                if str(bet.get("game", "dice")) == "range-dice":
                    rr = bet.get("range") or range_vals or (0, 0)
                    try:
                        prediction = f"{'in' if bool(bet.get('is_in')) else 'out'}[{int(rr[0])},{int(rr[1])}]"
                    except Exception:
                        prediction = "range"
                else:
                    prediction = "high" if bool(bet.get("is_high", True)) else "low"

                emitter.emit(BetPlacedEvent(
                    timestamp=ts,
                    bet_number=bets_done + 1,
                    amount=amount_dec,
                    chance=placed_chance,
                    payout_multiplier=placed_payout,
                    prediction=prediction,
                ))

            # Loss streaks and win/loss tracking
            if win:
                losses_in_row = 0
                wins_count += 1
            else:
                losses_in_row += 1
                losses_count += 1

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
                "lottery": {
                    "applied": lottery_applied,
                    "chance": lottery_chance,
                    "original_game": original_game,
                },
            })
            
            # Log to database
            if db:
                try:
                    # Get strategy state if available
                    strategy_state = None
                    if hasattr(strategy, 'get_state'):
                        try:
                            strategy_state = strategy.get_state()
                        except:
                            pass
                    
                    db.log_bet(
                        session_id=session_id,
                        bet_data={
                            "symbol": config.symbol,
                            "strategy": strategy_name,
                            **bet
                        },
                        result_data=result,
                        bet_number=bets_done + 1,
                        balance=current_balance,
                        loss_streak=losses_in_row,
                        simulation_mode=config.dry_run,
                        strategy_state=strategy_state
                    )
                except Exception as e:
                    # Don't fail bet on database error
                    pass
            
            # Emit bet result event
            if emitter and _EVENTS_AVAILABLE:
                emitter.emit(BetResultEvent(
                    timestamp=ts,
                    bet_number=bets_done + 1,
                    win=win,
                    profit=profit,
                    balance=current_balance,
                    result_data=result
                ))

            # Strategy callback
            ctx.recent_results.append(result)   # keeps current_balance_str() live
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
            
            # Emit stats update
            if emitter and _EVENTS_AVAILABLE:
                win_rate = (wins_count / bets_done * 100) if bets_done > 0 else 0
                emitter.emit(StatsUpdatedEvent(
                    timestamp=ts,
                    total_bets=bets_done,
                    wins=wins_count,
                    losses=losses_count,
                    win_rate=win_rate,
                    profit=pl,
                    profit_percent=float(pct),
                    current_balance=current_balance
                ))

            # Sleep
            ctx.sleep_with_jitter()

    except KeyboardInterrupt:
        stopped_reason = "cancelled"

    # End
    strategy.on_session_end(stopped_reason)

    duration = time.time() - start_ts
    
    # End database session
    if db:
        try:
            db.end_session(
                session_id=session_id,
                ending_balance=current_balance,
                stop_reason=stopped_reason,
                total_bets=bets_done,
                wins=wins_count,
                losses=losses_count
            )
        except Exception as e:
            print_line(f"⚠️  Database session end failed: {e}")
    
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
    if db:
        db.flush()
    if hasattr(sink, "close"):
        sink.close()
    print_line(f"[summary] {json.dumps(summary)}")
    
    # Emit session ended event
    if emitter and _EVENTS_AVAILABLE:
        emitter.emit(SessionEndedEvent(
            timestamp=time.time(),
            stop_reason=stopped_reason,
            summary=summary
        ))
    
    return summary
