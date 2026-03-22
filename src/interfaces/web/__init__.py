"""Web interface package.

`app` is exported lazily to avoid importing `web_server` as a side-effect when
consumers only need submodules like `runtime_controller`.
"""

from typing import Any

__all__ = ["app"]


def __getattr__(name: str) -> Any:
    if name == "app":
        from .web_server import app as web_app

        return web_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
