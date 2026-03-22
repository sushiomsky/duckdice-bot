#!/usr/bin/env python3
"""
DuckDice Bot Web Interface launcher.

Phase 1:
- Minimal FastAPI runtime API
- Lightweight dashboard at /
"""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DuckDice Bot Web Interface (Phase 1)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "src.interfaces.web.web_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

