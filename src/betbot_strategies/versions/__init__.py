"""
Strategy version snapshots.

Each file in this directory registers a versioned strategy under the name
"strategy-name@vN" (e.g. "nano-range-hunter@v3").

Selection::

    duckdice run --strategy nano-range-hunter@v3 ...

Listing::

    duckdice list          # shows all names including versioned ones
    duckdice list -v       # shows version changelogs where available
"""
from __future__ import annotations
import importlib
import pkgutil
from pathlib import Path

# Auto-import every module in this package so version classes self-register
for _info in pkgutil.iter_modules([str(Path(__file__).parent)]):
    importlib.import_module(f"{__name__}.{_info.name}")
