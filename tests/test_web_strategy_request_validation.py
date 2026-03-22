import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.interfaces.web import web_server


def _base_req() -> dict:
    return {
        "params": {"base_bet": 1.0},
        "symbol": "btc",
        "starting_balance": "100.0",
    }


def test_strategy_params_request_normalizes_symbol():
    req = web_server.StrategyParamsRequest(**_base_req())
    assert req.symbol == "BTC"


def test_strategy_params_request_rejects_non_alnum_symbol():
    payload = _base_req()
    payload["symbol"] = "b$t"
    with pytest.raises(Exception):
        web_server.StrategyParamsRequest(**payload)


def test_strategy_params_request_rejects_non_positive_starting_balance():
    payload = _base_req()
    payload["starting_balance"] = "0"
    with pytest.raises(Exception):
        web_server.StrategyParamsRequest(**payload)


def test_strategy_validate_uses_normalized_symbol():
    req = web_server.StrategyParamsRequest(**_base_req())
    resp = web_server.strategy_validate("kelly-capped", req)
    assert resp["name"] == "kelly-capped"
    assert resp["valid"] is True


def test_strategy_preview_rejects_invalid_request_payload_before_handler():
    payload = _base_req()
    payload["starting_balance"] = "-10"
    with pytest.raises(Exception):
        web_server.StrategyParamsRequest(**payload)
