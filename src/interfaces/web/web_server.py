"""
Minimal web interface server for DuckDice Bot.

Provides:
- Runtime API (start/stop/state/events)
- Strategy/schema discovery
- A browser dashboard page
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import json
import random
from pathlib import Path
import time
from typing import Any, ClassVar, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from ...betbot_strategies import get_strategy, list_strategies
from ...betbot_strategies.base import SessionLimits, StrategyContext
from .runtime_controller import RuntimeRequest, WebRuntimeController


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"

app = FastAPI(title="DuckDice Web Interface", version="0.1.0")
runtime = WebRuntimeController()


class StartRequest(BaseModel):
    ALLOWED_MODES: ClassVar[set[str]] = {"simulation", "live-main", "live-faucet", "live-tle"}

    strategy_name: str = Field(..., min_length=1)
    strategy_params: Dict[str, Any] = Field(default_factory=dict)
    symbol: str = "BTC"
    mode: str = "simulation"
    start_balance: str = "100.0"
    max_bets: int | None = None
    stop_loss: float = -0.02
    take_profit: float | None = 0.02
    api_key: str | None = None
    tle_hash: str | None = None

    @field_validator("strategy_name")
    @classmethod
    def _validate_strategy_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("strategy_name is required")
        return name

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, value: str) -> str:
        sym = value.strip().upper()
        if not sym:
            raise ValueError("symbol is required")
        if not sym.isalnum():
            raise ValueError("symbol must be alphanumeric")
        if len(sym) > 10:
            raise ValueError("symbol must be <= 10 chars")
        return sym

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        mode = value.strip().lower()
        if mode not in cls.ALLOWED_MODES:
            raise ValueError(f"mode must be one of: {', '.join(sorted(cls.ALLOWED_MODES))}")
        return mode

    @field_validator("start_balance")
    @classmethod
    def _validate_start_balance(cls, value: str) -> str:
        raw = str(value).strip()
        try:
            parsed = Decimal(raw)
        except Exception as exc:
            raise ValueError("start_balance must be a decimal string") from exc
        if parsed <= 0:
            raise ValueError("start_balance must be > 0")
        return str(parsed)

    @field_validator("max_bets")
    @classmethod
    def _validate_max_bets(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("max_bets must be > 0")
        if value > 1_000_000:
            raise ValueError("max_bets must be <= 1000000")
        return value

    @field_validator("stop_loss")
    @classmethod
    def _validate_stop_loss(cls, value: float) -> float:
        if value >= 0:
            raise ValueError("stop_loss must be negative")
        if value < -0.999999:
            raise ValueError("stop_loss is too low")
        return value

    @field_validator("take_profit")
    @classmethod
    def _validate_take_profit(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("take_profit must be positive")
        return value

    @field_validator("api_key", "tle_hash")
    @classmethod
    def _trim_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @model_validator(mode="after")
    def _validate_mode_requirements(self) -> "StartRequest":
        if self.mode == "live-tle" and not self.tle_hash:
            raise ValueError("tle_hash is required for live-tle mode")
        return self


class StrategyParamsRequest(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)
    symbol: str = "BTC"
    starting_balance: str = "100.0"

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, value: str) -> str:
        sym = value.strip().upper()
        if not sym:
            raise ValueError("symbol is required")
        if not sym.isalnum():
            raise ValueError("symbol must be alphanumeric")
        if len(sym) > 10:
            raise ValueError("symbol must be <= 10 chars")
        return sym

    @field_validator("starting_balance")
    @classmethod
    def _validate_starting_balance(cls, value: str) -> str:
        raw = str(value).strip()
        try:
            parsed = Decimal(raw)
        except Exception as exc:
            raise ValueError("starting_balance must be a decimal string") from exc
        if parsed <= 0:
            raise ValueError("starting_balance must be > 0")
        return str(parsed)


class _PreviewDuckDiceAPI:
    """Minimal API object used for strategy preview contexts."""

    def __init__(self, symbol: str, starting_balance: str):
        self._symbol = symbol.upper()
        self._starting_balance = str(starting_balance)

    def get_user_info(self) -> Dict[str, Any]:
        return {
            "username": "web_preview_user",
            "hash": "web_preview",
            "balances": [
                {"currency": self._symbol, "main": self._starting_balance, "faucet": "0"}
            ],
        }


def _normalize_params(schema: Dict[str, Any], raw_params: Dict[str, Any]) -> tuple[Dict[str, Any], list[str]]:
    normalized: Dict[str, Any] = {}
    errors: list[str] = []

    def _coerce_value(param_name: str, spec: Dict[str, Any], value: Any) -> Any:
        expected_type = str(spec.get("type", "str")).lower()
        if expected_type in ("int", "integer"):
            coerced = int(value)
        elif expected_type in ("float", "number", "decimal"):
            coerced = float(value)
        elif expected_type in ("bool", "boolean"):
            if isinstance(value, bool):
                coerced = value
            elif isinstance(value, (int, float)) and value in (0, 1):
                coerced = bool(value)
            elif isinstance(value, str):
                v = value.strip().lower()
                if v in ("true", "1", "yes", "y", "on"):
                    coerced = True
                elif v in ("false", "0", "no", "n", "off"):
                    coerced = False
                else:
                    raise ValueError("expected boolean value")
            else:
                raise ValueError("expected boolean value")
        else:
            coerced = str(value)

        min_v = spec.get("min")
        max_v = spec.get("max")
        if isinstance(coerced, (int, float)):
            if min_v is not None and coerced < float(min_v):
                raise ValueError(f"must be >= {min_v}")
            if max_v is not None and coerced > float(max_v):
                raise ValueError(f"must be <= {max_v}")
        return coerced

    for key, spec in schema.items():
        candidate = raw_params.get(key, spec.get("default"))
        if candidate is None:
            continue
        try:
            normalized[key] = _coerce_value(key, spec if isinstance(spec, dict) else {}, candidate)
        except Exception as exc:
            errors.append(f"{key}: {exc}")

    # Preserve unknown fields from raw input to avoid destructive edits.
    for key, value in raw_params.items():
        if key not in normalized and key not in schema:
            normalized[key] = value

    return normalized, errors


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def _build_preview_result(win: bool, balance: Decimal, chance: str) -> Dict[str, Any]:
    return {
        "win": win,
        "profit": "1" if win else "-1",
        "balance": str(balance),
        "number": 5000,
        "payout": "2.0",
        "chance": chance,
        "is_high": True,
        "range": None,
        "is_in": None,
        "api_raw": {"preview": True},
        "simulated": True,
        "timestamp": time.time(),
    }


def _build_strategy_context(symbol: str, starting_balance: str) -> StrategyContext:
    return StrategyContext(
        api=_PreviewDuckDiceAPI(symbol=symbol, starting_balance=starting_balance),  # type: ignore[arg-type]
        symbol=symbol.upper(),
        faucet=False,
        dry_run=True,
        rng=random.Random(42),
        logger=lambda _event: None,
        limits=SessionLimits(symbol=symbol.upper()),
        delay_ms=0,
        jitter_ms=0,
        starting_balance=str(starting_balance),
        printer=lambda _msg: None,
    )


@app.get("/", response_class=HTMLResponse)
def ui_root() -> str:
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=500, detail="Web UI assets missing")
    return INDEX_HTML.read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "running": runtime.is_running}


@app.get("/api/strategies")
def strategies() -> Dict[str, Any]:
    return {"items": list_strategies()}


@app.get("/api/strategy/{name}")
def strategy_detail(name: str) -> Dict[str, Any]:
    try:
        cls = get_strategy(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    schema: Dict[str, Any] = {}
    if hasattr(cls, "schema"):
        schema = cls.schema()  # type: ignore[attr-defined]

    description = ""
    if hasattr(cls, "describe"):
        try:
            description = cls.describe()  # type: ignore[attr-defined]
        except Exception:
            description = ""

    return {
        "name": name,
        "description": description,
        "schema": schema,
    }


@app.post("/api/strategy/{name}/validate")
def strategy_validate(name: str, req: StrategyParamsRequest) -> Dict[str, Any]:
    try:
        cls = get_strategy(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    schema: Dict[str, Any] = {}
    if hasattr(cls, "schema"):
        schema = cls.schema()  # type: ignore[attr-defined]

    normalized, errors = _normalize_params(schema, req.params)
    return {
        "name": name,
        "valid": len(errors) == 0,
        "errors": errors,
        "normalized_params": normalized,
    }


@app.post("/api/strategy/{name}/preview")
def strategy_preview(name: str, req: StrategyParamsRequest) -> Dict[str, Any]:
    try:
        strategy_cls = get_strategy(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    schema: Dict[str, Any] = {}
    if hasattr(strategy_cls, "schema"):
        schema = strategy_cls.schema()  # type: ignore[attr-defined]
    normalized, errors = _normalize_params(schema, req.params)
    if errors:
        return {
            "name": name,
            "valid": False,
            "errors": errors,
            "normalized_params": normalized,
            "preview": None,
        }

    def _instantiate():
        ctx = _build_strategy_context(symbol=req.symbol, starting_balance=req.starting_balance)
        strat = strategy_cls(normalized, ctx)  # type: ignore[call-arg]
        strat.on_session_start()
        return strat, ctx

    try:
        # Baseline first bet
        strat_first, _ctx_first = _instantiate()
        first_bet = strat_first.next_bet()

        # Path after win
        strat_win, _ctx_win = _instantiate()
        first_for_win = strat_win.next_bet()
        after_win = None
        if first_for_win is not None:
            chance_val = str(first_for_win.get("chance", "50"))
            balance_win = Decimal(str(req.starting_balance)) + Decimal("1")
            strat_win.on_bet_result(_build_preview_result(True, balance_win, chance_val))  # type: ignore[arg-type]
            after_win = strat_win.next_bet()

        # Path after loss
        strat_loss, _ctx_loss = _instantiate()
        first_for_loss = strat_loss.next_bet()
        after_loss = None
        if first_for_loss is not None:
            chance_val = str(first_for_loss.get("chance", "50"))
            balance_loss = Decimal(str(req.starting_balance)) - Decimal("1")
            strat_loss.on_bet_result(_build_preview_result(False, balance_loss, chance_val))  # type: ignore[arg-type]
            after_loss = strat_loss.next_bet()

        return {
            "name": name,
            "valid": True,
            "errors": [],
            "normalized_params": normalized,
            "preview": {
                "first": _to_jsonable(first_bet),
                "after_win": _to_jsonable(after_win),
                "after_loss": _to_jsonable(after_loss),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Preview failed: {exc}") from exc


@app.post("/api/runtime/start")
def start_session(req: StartRequest) -> Dict[str, Any]:
    try:
        get_strategy(req.strategy_name)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy_name}") from exc

    try:
        runtime.start(
            RuntimeRequest(
                strategy_name=req.strategy_name,
                strategy_params=req.strategy_params,
                symbol=req.symbol,
                mode=req.mode,
                start_balance=req.start_balance,
                max_bets=req.max_bets,
                stop_loss=req.stop_loss,
                take_profit=req.take_profit,
                api_key=req.api_key,
                tle_hash=req.tle_hash,
            )
        )
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runtime/stop")
def stop_session() -> Dict[str, Any]:
    runtime.request_stop()
    return {"ok": True}


@app.get("/api/runtime/state")
def runtime_state() -> Dict[str, Any]:
    return runtime.get_state()


@app.get("/api/runtime/events")
def runtime_events(since: int = 0, limit: int = 500) -> Dict[str, Any]:
    return runtime.get_events(since=since, limit=limit)


@app.get("/api/runtime/export")
def runtime_export() -> Dict[str, Any]:
    state = runtime.get_state()
    events = runtime.get_events(since=0, limit=5000)
    return {"state": state, "events": events}


@app.get("/api/runtime/timeline")
def runtime_timeline(limit: int = 200) -> Dict[str, Any]:
    return runtime.get_timeline(limit=limit)


@app.get("/api/runtime/equity")
def runtime_equity(limit: int = 1000) -> Dict[str, Any]:
    return runtime.get_equity(limit=limit)


@app.get("/api/runtime/analytics")
def runtime_analytics() -> Dict[str, Any]:
    return runtime.get_analytics()


@app.get("/api/runtime/dashboard")
def runtime_dashboard() -> Dict[str, Any]:
    return runtime.get_dashboard()


@app.get("/api/runtime/stream")
async def runtime_stream(
    request: Request,
    since: int = 0,
    poll_ms: int = 250,
    heartbeat_sec: float = 10.0,
) -> StreamingResponse:
    """
    Server-Sent Events stream for runtime events.

    Streams each runtime event as:
      event: runtime
      data: {...event payload...}

    Also emits periodic heartbeat events to keep the connection alive.
    """

    def _parse_seq(raw: Any) -> int | None:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
        return max(0, value)

    async def _event_generator():
        cursor_query = max(0, int(since))
        cursor_header = _parse_seq(request.headers.get("last-event-id"))
        cursor = cursor_header if cursor_header is not None else cursor_query
        wait_s = max(0.05, min(2.0, poll_ms / 1000.0))
        hb_interval = max(1.0, float(heartbeat_sec))
        last_heartbeat = time.time()

        while True:
            if await request.is_disconnected():
                break
            packet = runtime.get_events(since=cursor, limit=300)
            last_seq = max(0, int(packet.get("last_seq", cursor)))
            if cursor > last_seq:
                # If client cursor is ahead of server state, clamp to known sequence.
                cursor = last_seq
            events = packet.get("events", [])
            if events:
                for ev in events:
                    seq = max(cursor, int(ev.get("seq", cursor)))
                    cursor = seq
                    payload = json.dumps(ev)
                    yield f"id: {seq}\nevent: runtime\ndata: {payload}\n\n"
                    await asyncio.sleep(0)
                last_heartbeat = time.time()
            else:
                now = time.time()
                if (now - last_heartbeat) >= hb_interval:
                    hb_payload = json.dumps(
                        {
                            "type": "heartbeat",
                            "timestamp": now,
                            "last_seq": cursor,
                        }
                    )
                    yield f"id: {cursor}\nevent: heartbeat\ndata: {hb_payload}\n\n"
                    last_heartbeat = now
                    await asyncio.sleep(0)
                await asyncio.sleep(wait_s)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
