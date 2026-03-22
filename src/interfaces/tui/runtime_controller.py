"""
Runtime controller for the Textual TUI.

Runs the betting engine in a background thread and exposes engine events
through a thread-safe queue so UI code can poll and render updates safely.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional


try:
    from ...betbot_engine.engine import AutoBetEngine, EngineConfig
    from ...betbot_engine.events import BettingEvent, ErrorEvent, InfoEvent
    from ...betbot_engine.observers import EventEmitter
    from ...duckdice_api.api import DuckDiceAPI, DuckDiceConfig
except ImportError:
    # Support direct execution paths like: python src/interfaces/tui/textual_interface.py
    if __package__ in (None, ""):
        src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if src_root not in sys.path:
            sys.path.insert(0, src_root)
    from betbot_engine.engine import AutoBetEngine, EngineConfig
    from betbot_engine.events import BettingEvent, ErrorEvent, InfoEvent
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
            "username": "tui_simulation_user",
            "hash": "tui_sim",
            "balances": [
                {
                    "currency": self._symbol,
                    "main": self._starting_balance,
                    "faucet": "0",
                }
            ],
        }

    def play_dice(self, *args, **kwargs):  # pragma: no cover - should never be called in dry_run
        raise NotImplementedError("play_dice should not be called in dry_run mode")

    def play_range_dice(self, *args, **kwargs):  # pragma: no cover - should never be called in dry_run
        raise NotImplementedError("play_range_dice should not be called in dry_run mode")


class TextualRuntimeController:
    """Runs engine sessions in a thread and provides queued events to the UI."""

    def __init__(self) -> None:
        self._event_queue: Queue[BettingEvent] = Queue()
        self._thread: Optional[threading.Thread] = None
        self._request: Optional[RuntimeRequest] = None
        self._summary: Optional[Dict[str, Any]] = None
        self._last_error: Optional[Exception] = None
        self._stop_requested = False
        self._lock = threading.Lock()

    @property
    def current_request(self) -> Optional[RuntimeRequest]:
        return self._request

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def summary(self) -> Optional[Dict[str, Any]]:
        return self._summary

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error

    def start(self, request: RuntimeRequest) -> None:
        with self._lock:
            if self.is_running:
                raise RuntimeError("Session already running")

            self._drain_queue()
            self._summary = None
            self._last_error = None
            self._request = request
            self._stop_requested = False

            self._thread = threading.Thread(
                target=self._run_session,
                args=(request,),
                daemon=True,
                name="duckdice-tui-runtime",
            )
            self._thread.start()

    def request_stop(self) -> None:
        with self._lock:
            self._stop_requested = True

    def poll_events(self, max_items: int = 200) -> List[BettingEvent]:
        items: List[BettingEvent] = []
        for _ in range(max_items):
            try:
                items.append(self._event_queue.get_nowait())
            except Empty:
                break
        return items

    def _drain_queue(self) -> None:
        while True:
            try:
                self._event_queue.get_nowait()
            except Empty:
                break

    def _should_stop(self) -> bool:
        with self._lock:
            return self._stop_requested

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

    def _run_session(self, request: RuntimeRequest) -> None:
        emitter = EventEmitter()
        emitter.add_callback(self._event_queue.put)

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
                printer=lambda msg: self._event_queue.put(
                    InfoEvent(timestamp=time.time(), message=str(msg))
                ),
                stop_checker=self._should_stop,
                emitter=emitter,
            )
        except Exception as exc:
            self._last_error = exc
            self._event_queue.put(
                ErrorEvent(
                    timestamp=time.time(),
                    message="TUI runtime failed",
                    exception=exc,
                )
            )
