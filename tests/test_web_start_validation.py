import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.interfaces.web import web_server


def _valid_payload() -> dict:
    return {
        "strategy_name": "kelly-capped",
        "strategy_params": {"base_bet": 1.0, "chance": 49.5},
        "symbol": "btc",
        "mode": "simulation",
        "start_balance": "100.0",
        "max_bets": 10,
        "stop_loss": -0.2,
        "take_profit": 0.2,
    }


def _call_start(payload: dict):
    req = web_server.StartRequest(**payload)
    return web_server.start_session(req)


def test_start_request_rejects_invalid_mode():
    payload = _valid_payload()
    payload["mode"] = "paper"
    with pytest.raises(Exception):
        web_server.StartRequest(**payload)


def test_start_request_rejects_non_positive_start_balance():
    payload = _valid_payload()
    payload["start_balance"] = "0"
    with pytest.raises(Exception):
        web_server.StartRequest(**payload)


def test_start_request_rejects_non_alnum_symbol():
    payload = _valid_payload()
    payload["symbol"] = "bt$"
    with pytest.raises(Exception):
        web_server.StartRequest(**payload)


def test_start_request_rejects_non_negative_stop_loss():
    payload = _valid_payload()
    payload["stop_loss"] = 0.0
    with pytest.raises(Exception):
        web_server.StartRequest(**payload)


def test_start_request_rejects_non_positive_take_profit():
    payload = _valid_payload()
    payload["take_profit"] = 0.0
    with pytest.raises(Exception):
        web_server.StartRequest(**payload)


def test_start_request_requires_tle_hash_for_live_tle():
    payload = _valid_payload()
    payload["mode"] = "live-tle"
    payload["tle_hash"] = "   "
    with pytest.raises(Exception):
        web_server.StartRequest(**payload)


def test_start_request_trims_optional_fields():
    payload = _valid_payload()
    payload["api_key"] = "  abc123  "
    payload["tle_hash"] = "  tle_hash_value  "
    req = web_server.StartRequest(**payload)
    assert req.api_key == "abc123"
    assert req.tle_hash == "tle_hash_value"


def test_start_session_normalizes_symbol_and_mode():
    original_runtime = web_server.runtime

    class _StubRuntime:
        def __init__(self):
            self.req = None

        def start(self, req):
            self.req = req

        def request_stop(self):
            pass

        @property
        def is_running(self):
            return False

    stub = _StubRuntime()
    web_server.runtime = stub
    try:
        payload = _valid_payload()
        payload["api_key"] = "  key  "
        resp = _call_start(payload)
        assert resp["ok"] is True
        assert stub.req is not None
        assert stub.req.symbol == "BTC"
        assert stub.req.mode == "simulation"
        assert stub.req.api_key == "key"
    finally:
        web_server.runtime = original_runtime
