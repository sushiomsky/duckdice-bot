import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.interfaces.web import web_server


def _extract_heartbeat_payload(stream_text: str) -> dict:
    lines = [ln for ln in stream_text.splitlines() if ln.startswith("data: ")]
    assert lines, f"Expected SSE data lines, got: {stream_text!r}"
    payload = lines[-1][len("data: "):]
    return json.loads(payload)


def _extract_sse_id(stream_text: str) -> int:
    id_lines = [ln for ln in stream_text.splitlines() if ln.startswith("id: ")]
    assert id_lines, f"Expected SSE id line, got: {stream_text!r}"
    return int(id_lines[-1][len("id: "):])


def test_stream_heartbeat_clamps_last_seq_when_since_is_ahead():
    original_runtime = web_server.runtime
    runtime = web_server.WebRuntimeController()
    web_server.runtime = runtime
    runtime._append_event(  # noqa: SLF001 - controlled seed for SSE regression test
        {"type": "info", "timestamp": time.time(), "data": {"message": "seed"}}
    )

    # Ask for a cursor far ahead and ensure heartbeat reports actual last_seq.
    import asyncio

    async def _read_once():
        class _Req:
            headers = {}

            async def is_disconnected(self):
                return False

        resp = await web_server.runtime_stream(
            request=_Req(),
            since=9999,
            poll_ms=50,
            heartbeat_sec=0.01,
        )
        iterator = resp.body_iterator
        try:
            chunk = await anext(iterator)
            return chunk.decode("utf-8") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        finally:
            await iterator.aclose()

    try:
        stream_text = asyncio.run(_read_once())
        hb = _extract_heartbeat_payload(stream_text)
        assert hb["type"] == "heartbeat"
        assert hb["last_seq"] == runtime.get_events(since=0, limit=1)["last_seq"]
        assert _extract_sse_id(stream_text) == hb["last_seq"]
    finally:
        web_server.runtime = original_runtime


def test_stream_uses_last_event_id_header_when_present():
    original_runtime = web_server.runtime
    runtime = web_server.WebRuntimeController()
    web_server.runtime = runtime
    runtime._append_event(  # noqa: SLF001
        {"type": "info", "timestamp": time.time(), "data": {"message": "seed1"}}
    )
    runtime._append_event(  # noqa: SLF001
        {"type": "info", "timestamp": time.time(), "data": {"message": "seed2"}}
    )

    import asyncio

    async def _read_once():
        class _Req:
            headers = {"last-event-id": "1"}

            async def is_disconnected(self):
                return False

        resp = await web_server.runtime_stream(
            request=_Req(),
            since=0,
            poll_ms=50,
            heartbeat_sec=1.0,
        )
        iterator = resp.body_iterator
        try:
            chunk = await anext(iterator)
            return chunk.decode("utf-8") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        finally:
            await iterator.aclose()

    try:
        stream_text = asyncio.run(_read_once())
        assert "event: runtime" in stream_text
        assert _extract_sse_id(stream_text) == 2
    finally:
        web_server.runtime = original_runtime
