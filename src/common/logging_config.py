from __future__ import annotations

import logging
import os
from typing import Optional

_DEFAULT_LOG_LEVEL = "INFO"
_VALID_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def resolve_log_level(default: str = _DEFAULT_LOG_LEVEL) -> str:
    """Resolve normalized log level from LOG_LEVEL env var."""
    level = os.getenv("LOG_LEVEL", default)
    normalized = str(level).upper().strip()
    if normalized in _VALID_LEVELS:
        return normalized
    return default


def configure_logging(level: Optional[str] = None) -> str:
    """Initialize root logging once and return effective level."""
    resolved = str(level).upper().strip() if level else resolve_log_level()
    if resolved not in _VALID_LEVELS:
        resolved = _DEFAULT_LOG_LEVEL
    logging.basicConfig(level=getattr(logging, resolved), format=_FORMAT)
    return resolved
