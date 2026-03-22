import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from interfaces.web.runtime_controller import WebRuntimeController


def _seed_controller_events(ctrl: WebRuntimeController, count: int = 5) -> None:
    for i in range(count):
        ctrl._append_event(  # noqa: SLF001 - direct seed for controller accessor tests
            {
                "type": "info",
                "timestamp": float(i),
                "data": {"message": f"e{i}"},
            }
        )


def _seed_timeline(ctrl: WebRuntimeController, count: int = 5) -> None:
    with ctrl._lock:  # noqa: SLF001 - direct seed for controller accessor tests
        for i in range(count):
            ctrl._append_timeline_locked(  # noqa: SLF001
                "info",
                f"t{i}",
                float(i),
                {"i": i},
            )


def _seed_equity(ctrl: WebRuntimeController, count: int = 5) -> None:
    with ctrl._lock:  # noqa: SLF001 - direct seed for controller accessor tests
        for i in range(count):
            ctrl._equity_curve.append(  # noqa: SLF001
                {"timestamp": float(i), "balance": float(100 + i), "profit": float(i)}
            )


def test_get_events_sanitizes_negative_since_and_limit() -> None:
    ctrl = WebRuntimeController()
    _seed_controller_events(ctrl, count=4)

    packet = ctrl.get_events(since=-99, limit=-1)
    assert packet["events"] == []
    assert packet["last_seq"] == 4


def test_get_events_clamps_limit_to_max() -> None:
    ctrl = WebRuntimeController()
    _seed_controller_events(ctrl, count=7)

    packet = ctrl.get_events(since=0, limit=999999)
    assert len(packet["events"]) == 7
    assert packet["events"][-1]["seq"] == 7


def test_get_timeline_and_equity_handle_negative_limit() -> None:
    ctrl = WebRuntimeController()
    _seed_timeline(ctrl, count=3)
    _seed_equity(ctrl, count=3)

    t = ctrl.get_timeline(limit=-5)
    e = ctrl.get_equity(limit=-5)
    assert t["items"] == []
    assert e["points"] == []


def test_get_timeline_and_equity_clamp_large_limit() -> None:
    ctrl = WebRuntimeController()
    _seed_timeline(ctrl, count=6)
    _seed_equity(ctrl, count=6)

    t = ctrl.get_timeline(limit=999999)
    e = ctrl.get_equity(limit=999999)
    assert len(t["items"]) == 6
    assert len(e["points"]) == 6
