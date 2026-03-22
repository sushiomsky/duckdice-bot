"""
Runtime controller for the web interface.

Runs betting sessions in a background thread and stores structured engine events
in an in-memory ring buffer for polling-based web clients.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import os
import statistics
import sys
import threading
import time
from collections import deque
from math import ceil, floor
from typing import Any, Deque, Dict, List, Optional, Tuple

try:
    from ...betbot_engine.engine import AutoBetEngine, EngineConfig
    from ...betbot_engine.events import BettingEvent, ErrorEvent, EventType, InfoEvent
    from ...betbot_engine.observers import EventEmitter
    from ...duckdice_api.api import DuckDiceAPI, DuckDiceConfig
except ImportError:
    if __package__ in (None, ""):
        src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if src_root not in sys.path:
            sys.path.insert(0, src_root)
    from betbot_engine.engine import AutoBetEngine, EngineConfig
    from betbot_engine.events import BettingEvent, ErrorEvent, EventType, InfoEvent
    from betbot_engine.observers import EventEmitter
    from duckdice_api.api import DuckDiceAPI, DuckDiceConfig


CONFIG_DIR = Path.home() / ".duckdice"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class RuntimeRequest:
    strategy_name: str
    strategy_params: Dict[str, Any]
    symbol: str = "BTC"
    mode: str = "simulation"  # simulation | live-main | live-faucet | live-tle
    start_balance: str = "100.0"
    max_bets: Optional[int] = None
    stop_loss: float = -0.02
    take_profit: Optional[float] = 0.02
    api_key: Optional[str] = None
    tle_hash: Optional[str] = None


class _SimulationDuckDiceAPI:
    """Minimal API implementation used for dry-run sessions."""

    def __init__(self, symbol: str, starting_balance: str):
        self._symbol = symbol.upper()
        self._starting_balance = str(starting_balance)

    def get_user_info(self) -> Dict[str, Any]:
        return {
            "username": "web_simulation_user",
            "hash": "web_sim",
            "balances": [
                {
                    "currency": self._symbol,
                    "main": self._starting_balance,
                    "faucet": "0",
                }
            ],
        }

    def play_dice(self, *args, **kwargs):  # pragma: no cover - dry-run should not call
        raise NotImplementedError("play_dice should not be called in dry_run mode")

    def play_range_dice(self, *args, **kwargs):  # pragma: no cover - dry-run should not call
        raise NotImplementedError("play_range_dice should not be called in dry_run mode")


class WebRuntimeController:
    """Threaded runtime controller with pollable event history."""

    _MAX_EVENTS_LIMIT = 5000
    _MAX_TIMELINE_LIMIT = 2000
    _MAX_EQUITY_LIMIT = 4000

    def __init__(self, max_events: int = 5000) -> None:
        self._thread: Optional[threading.Thread] = None
        self._request: Optional[RuntimeRequest] = None
        self._summary: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._stop_requested = False
        self._lock = threading.Lock()

        self._seq = 0
        self._events: Deque[Tuple[int, Dict[str, Any]]] = deque(maxlen=max_events)
        self._stats: Dict[str, Any] = self._new_stats()
        self._timeline: Deque[Dict[str, Any]] = deque(maxlen=2000)
        self._equity_curve: Deque[Dict[str, Any]] = deque(maxlen=4000)
        self._profit_samples: Deque[float] = deque(maxlen=4000)
        self._amount_samples: Deque[float] = deque(maxlen=4000)
        self._rolling_outcomes: Deque[bool] = deque(maxlen=20)
        self._win_profit_total = 0.0
        self._loss_profit_total = 0.0
        self._win_profit_count = 0
        self._loss_profit_count = 0
        self._max_single_win: Optional[float] = None
        self._max_single_loss: Optional[float] = None
        self._streak: Dict[str, int] = {
            "current_win": 0,
            "current_loss": 0,
            "max_win": 0,
            "max_loss": 0,
        }

    def _new_stats(self) -> Dict[str, Any]:
        return {
            "starting_balance": None,
            "current_balance": None,
            "profit": None,
            "profit_percent": None,
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "wagered_total": 0.0,
            "avg_bet": None,
            "avg_profit_per_bet": None,
            "last_bet": None,
            "risk": {
                "stop_loss": None,
                "take_profit": None,
                "stop_balance": None,
                "target_balance": None,
                "distance_to_stop": None,
                "distance_to_target": None,
                "drawdown_percent": None,
            },
            "streak": {
                "current_win": 0,
                "current_loss": 0,
                "max_win": 0,
                "max_loss": 0,
            },
            "analytics": {
                "avg_win": None,
                "avg_loss": None,
                "profit_factor": None,
                "win_loss_ratio": None,
                "expectancy_per_bet": None,
                "profit_stddev": None,
                "rolling_win_rate_20": None,
                "max_single_win": None,
                "max_single_loss": None,
                "bet_amount_min": None,
                "bet_amount_p50": None,
                "bet_amount_p90": None,
                "bet_amount_max": None,
            },
        }

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _load_api_key(self, explicit_api_key: Optional[str]) -> Optional[str]:
        if explicit_api_key:
            return explicit_api_key.strip()
        env_key = os.getenv("DUCKDICE_API_KEY", "").strip()
        if env_key:
            return env_key
        if not CONFIG_FILE.exists():
            return None
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                config = json.load(f)
            key = str(config.get("api_key", "")).strip()
            return key or None
        except Exception:
            return None

    def _build_api(self, request: RuntimeRequest) -> DuckDiceAPI:
        if request.mode == "simulation":
            return _SimulationDuckDiceAPI(
                symbol=request.symbol,
                starting_balance=request.start_balance,
            )  # type: ignore[return-value]

        api_key = self._load_api_key(request.api_key)
        if not api_key:
            raise ValueError("Live mode requires DUCKDICE_API_KEY or ~/.duckdice/config.json api_key")
        if request.mode == "live-tle" and not request.tle_hash:
            raise ValueError("Live TLE mode requires a TLE hash")
        return DuckDiceAPI(DuckDiceConfig(api_key=api_key))

    def _serialize_event(self, event: BettingEvent) -> Dict[str, Any]:
        return {
            "type": event.event_type.value,
            "timestamp": event.timestamp,
            "data": dict(event.data or {}),
        }

    def _append_event(self, payload: Dict[str, Any]) -> int:
        with self._lock:
            self._seq += 1
            seq = self._seq
            self._events.append((seq, payload))
            return seq

    def _append_timeline_locked(
        self,
        kind: str,
        message: str,
        timestamp: float,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._timeline.append(
            {
                "timestamp": timestamp,
                "kind": kind,
                "message": message,
                "data": data or {},
            }
        )

    def _to_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _sanitize_since(value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, parsed)

    @staticmethod
    def _sanitize_limit(value: Any, *, default: int, max_limit: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed < 0:
            return 0
        return min(parsed, max_limit)

    def _recompute_risk_metrics_locked(self) -> None:
        start = self._to_float(self._stats.get("starting_balance"))
        cur = self._to_float(self._stats.get("current_balance"))
        stop_loss = self._to_float(self._stats["risk"].get("stop_loss"))
        take_profit = self._to_float(self._stats["risk"].get("take_profit"))
        if start is None or start <= 0:
            return
        if stop_loss is not None:
            self._stats["risk"]["stop_balance"] = start * (1.0 + stop_loss)
        if take_profit is not None:
            self._stats["risk"]["target_balance"] = start * (1.0 + take_profit)
        if cur is None:
            return
        stop_bal = self._to_float(self._stats["risk"].get("stop_balance"))
        target_bal = self._to_float(self._stats["risk"].get("target_balance"))
        self._stats["risk"]["drawdown_percent"] = ((start - cur) / start) * 100.0
        self._stats["risk"]["distance_to_stop"] = None if stop_bal is None else (cur - stop_bal)
        self._stats["risk"]["distance_to_target"] = None if target_bal is None else (target_bal - cur)

    def _reset_analytics_trackers_locked(self) -> None:
        self._profit_samples.clear()
        self._amount_samples.clear()
        self._rolling_outcomes.clear()
        self._win_profit_total = 0.0
        self._loss_profit_total = 0.0
        self._win_profit_count = 0
        self._loss_profit_count = 0
        self._max_single_win = None
        self._max_single_loss = None

    @staticmethod
    def _quantile(values: List[float], q: float) -> Optional[float]:
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        ordered = sorted(values)
        idx = q * (len(ordered) - 1)
        lo = floor(idx)
        hi = ceil(idx)
        if lo == hi:
            return ordered[lo]
        weight = idx - lo
        return ordered[lo] + ((ordered[hi] - ordered[lo]) * weight)

    def _recompute_analytics_locked(self) -> None:
        profits = list(self._profit_samples)
        amounts = list(self._amount_samples)
        analytics = self._stats.setdefault("analytics", {})

        sample_count = len(profits)
        avg_win = None if self._win_profit_count == 0 else (self._win_profit_total / self._win_profit_count)
        avg_loss = None if self._loss_profit_count == 0 else (self._loss_profit_total / self._loss_profit_count)
        profit_factor = None
        if self._loss_profit_total > 0:
            profit_factor = self._win_profit_total / self._loss_profit_total

        win_loss_ratio = None
        if avg_win is not None and avg_loss is not None and avg_loss > 0:
            win_loss_ratio = avg_win / avg_loss

        analytics["avg_win"] = avg_win
        analytics["avg_loss"] = None if avg_loss is None else -avg_loss
        analytics["profit_factor"] = profit_factor
        analytics["win_loss_ratio"] = win_loss_ratio
        analytics["expectancy_per_bet"] = None if sample_count == 0 else (sum(profits) / float(sample_count))
        analytics["profit_stddev"] = (
            None if sample_count < 2 else statistics.pstdev(profits)
        )
        analytics["rolling_win_rate_20"] = (
            None
            if not self._rolling_outcomes
            else (sum(1 for w in self._rolling_outcomes if w) / float(len(self._rolling_outcomes))) * 100.0
        )
        analytics["max_single_win"] = self._max_single_win
        analytics["max_single_loss"] = self._max_single_loss
        analytics["bet_amount_min"] = min(amounts) if amounts else None
        analytics["bet_amount_p50"] = self._quantile(amounts, 0.50)
        analytics["bet_amount_p90"] = self._quantile(amounts, 0.90)
        analytics["bet_amount_max"] = max(amounts) if amounts else None

    def _update_state_from_event(self, event: BettingEvent) -> None:
        with self._lock:
            if event.event_type == EventType.SESSION_STARTED:
                start_raw = event.data.get("starting_balance")
                self._stats = self._new_stats()
                self._stats["starting_balance"] = start_raw
                self._stats["current_balance"] = start_raw
                self._stats["profit"] = "0"
                self._stats["profit_percent"] = 0.0
                self._stats["risk"]["stop_loss"] = self._request.stop_loss if self._request else None
                self._stats["risk"]["take_profit"] = self._request.take_profit if self._request else None
                self._equity_curve.clear()
                self._reset_analytics_trackers_locked()
                self._streak = {"current_win": 0, "current_loss": 0, "max_win": 0, "max_loss": 0}
                self._stats["streak"] = dict(self._streak)
                self._recompute_risk_metrics_locked()
                self._recompute_analytics_locked()
                self._append_timeline_locked(
                    "session",
                    f"Session started ({event.data.get('strategy_name', 'unknown')})",
                    event.timestamp,
                    dict(event.data),
                )
            elif event.event_type == EventType.BET_PLACED:
                amount_raw = str(event.data.get("amount", "0") or "0")
                try:
                    amount_f = abs(float(amount_raw))
                    self._stats["wagered_total"] = float(self._stats["wagered_total"]) + amount_f
                    self._amount_samples.append(amount_f)
                except Exception:
                    pass
                self._stats["last_bet"] = {
                    "bet_number": event.data.get("bet_number"),
                    "amount": amount_raw,
                    "chance": event.data.get("chance"),
                    "prediction": event.data.get("prediction"),
                }
                self._recompute_analytics_locked()
            elif event.event_type == EventType.BET_RESULT:
                self._stats["current_balance"] = event.data.get("balance")
                win = bool(event.data.get("win"))
                if win:
                    self._streak["current_win"] += 1
                    self._streak["current_loss"] = 0
                    self._streak["max_win"] = max(self._streak["max_win"], self._streak["current_win"])
                else:
                    self._streak["current_loss"] += 1
                    self._streak["current_win"] = 0
                    self._streak["max_loss"] = max(self._streak["max_loss"], self._streak["current_loss"])
                self._stats["streak"] = dict(self._streak)
                profit_f = self._to_float(event.data.get("profit"))
                if profit_f is not None:
                    self._profit_samples.append(profit_f)
                    self._rolling_outcomes.append(win)
                    if profit_f >= 0:
                        self._win_profit_total += profit_f
                        self._win_profit_count += 1
                        self._max_single_win = (
                            profit_f
                            if self._max_single_win is None
                            else max(self._max_single_win, profit_f)
                        )
                    else:
                        loss_abs = abs(profit_f)
                        self._loss_profit_total += loss_abs
                        self._loss_profit_count += 1
                        self._max_single_loss = (
                            profit_f
                            if self._max_single_loss is None
                            else min(self._max_single_loss, profit_f)
                        )
                    self._equity_curve.append(
                        {
                            "timestamp": event.timestamp,
                            "balance": self._to_float(event.data.get("balance")),
                            "profit": profit_f,
                        }
                    )
                self._recompute_risk_metrics_locked()
                self._recompute_analytics_locked()
            elif event.event_type == EventType.STATS_UPDATED:
                total_bets = int(event.data.get("total_bets", 0))
                self._stats["total_bets"] = total_bets
                self._stats["wins"] = int(event.data.get("wins", 0))
                self._stats["losses"] = int(event.data.get("losses", 0))
                self._stats["win_rate"] = event.data.get("win_rate")
                self._stats["profit"] = event.data.get("profit")
                self._stats["profit_percent"] = event.data.get("profit_percent")
                self._stats["current_balance"] = event.data.get("current_balance")
                if total_bets > 0:
                    self._stats["avg_bet"] = float(self._stats["wagered_total"]) / float(total_bets)
                    pf = self._to_float(self._stats.get("profit"))
                    self._stats["avg_profit_per_bet"] = None if pf is None else (pf / float(total_bets))
                self._recompute_risk_metrics_locked()
                self._recompute_analytics_locked()
            elif event.event_type == EventType.SESSION_ENDED:
                summary = event.data.get("summary")
                if isinstance(summary, dict):
                    self._summary = summary
                self._append_timeline_locked(
                    "session",
                    f"Session ended ({event.data.get('stop_reason', 'unknown')})",
                    event.timestamp,
                    dict(event.data),
                )
            elif event.event_type == EventType.WARNING:
                self._append_timeline_locked(
                    "warning",
                    str(event.data.get("message", "warning")),
                    event.timestamp,
                    dict(event.data),
                )
            elif event.event_type == EventType.ERROR:
                self._append_timeline_locked(
                    "error",
                    str(event.data.get("message", "error")),
                    event.timestamp,
                    dict(event.data),
                )
            elif event.event_type == EventType.INFO:
                msg = str(event.data.get("message", ""))
                if msg.startswith("[start]") or msg.startswith("[summary]"):
                    self._append_timeline_locked("info", msg, event.timestamp, dict(event.data))

    def _on_engine_event(self, event: BettingEvent) -> None:
        payload = self._serialize_event(event)
        self._append_event(payload)
        self._update_state_from_event(event)

    def start(self, request: RuntimeRequest) -> None:
        with self._lock:
            if self.is_running:
                raise RuntimeError("Session already running")
            self._request = request
            self._summary = None
            self._last_error = None
            self._stop_requested = False
            self._events.clear()
            self._timeline.clear()
            self._equity_curve.clear()
            self._reset_analytics_trackers_locked()
            self._stats = self._new_stats()
            self._thread = threading.Thread(
                target=self._run_session,
                args=(request,),
                daemon=True,
                name="duckdice-web-runtime",
            )
            self._thread.start()

    def request_stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            self._append_timeline_locked("control", "Stop requested by user", time.time())

    def _should_stop(self) -> bool:
        with self._lock:
            return self._stop_requested

    def get_events(self, since: int = 0, limit: int = 500) -> Dict[str, Any]:
        since_safe = self._sanitize_since(since)
        limit_safe = self._sanitize_limit(limit, default=500, max_limit=self._MAX_EVENTS_LIMIT)
        with self._lock:
            items = [{"seq": seq, **event} for (seq, event) in self._events if seq > since_safe][:limit_safe]
            last_seq = self._seq
        return {"events": items, "last_seq": last_seq}

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            req = asdict(self._request) if self._request else None
            return {
                "running": self.is_running,
                "request": req,
                "summary": self._summary,
                "last_error": self._last_error,
                "stats": dict(self._stats),
                "last_seq": self._seq,
            }

    def get_timeline(self, limit: int = 200) -> Dict[str, Any]:
        limit_safe = self._sanitize_limit(limit, default=200, max_limit=self._MAX_TIMELINE_LIMIT)
        with self._lock:
            items = list(self._timeline)[-limit_safe:] if limit_safe > 0 else []
        return {"items": items}

    def get_equity(self, limit: int = 1000) -> Dict[str, Any]:
        limit_safe = self._sanitize_limit(limit, default=1000, max_limit=self._MAX_EQUITY_LIMIT)
        with self._lock:
            points = list(self._equity_curve)[-limit_safe:] if limit_safe > 0 else []
        return {"points": points}

    def get_analytics(self) -> Dict[str, Any]:
        with self._lock:
            analytics = dict(self._stats.get("analytics", {}))
            sample_size = len(self._profit_samples)
            amount_sample_size = len(self._amount_samples)
        return {
            "analytics": analytics,
            "sample_size": sample_size,
            "amount_sample_size": amount_sample_size,
        }

    def get_dashboard(self) -> Dict[str, Any]:
        with self._lock:
            req = asdict(self._request) if self._request else None
            return {
                "running": self.is_running,
                "request": req,
                "summary": self._summary,
                "stats": dict(self._stats),
                "timeline": list(self._timeline)[-120:],
                "equity": list(self._equity_curve)[-800:],
                "last_seq": self._seq,
            }

    def _run_session(self, request: RuntimeRequest) -> None:
        emitter = EventEmitter()
        emitter.add_callback(self._on_engine_event)
        try:
            api = self._build_api(request)
            config = EngineConfig(
                symbol=request.symbol.upper(),
                dry_run=request.mode == "simulation",
                faucet=request.mode == "live-faucet",
                tle_hash=request.tle_hash if request.mode == "live-tle" else None,
                max_bets=request.max_bets,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
            )
            engine = AutoBetEngine(api=api, config=config)
            self._summary = engine.run(
                strategy_name=request.strategy_name,
                params=request.strategy_params,
                printer=lambda msg: self._on_engine_event(
                    InfoEvent(timestamp=time.time(), message=str(msg))
                ),
                stop_checker=self._should_stop,
                emitter=emitter,
            )
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
            self._on_engine_event(
                ErrorEvent(
                    timestamp=time.time(),
                    message="Web runtime failed",
                    exception=exc,
                )
            )
