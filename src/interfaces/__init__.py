"""Betting engine interfaces.

This package provides different interface implementations for the betting engine:
- CLI: Rich-based command-line interface
- TUI: Curses/Textual-based terminal UI
- Web: Flask/FastAPI-based web interface
- Base: Abstract base classes and headless implementation
"""

from .base import BettingInterface, HeadlessInterface
from .cli import RichInterface

__all__ = ['BettingInterface', 'HeadlessInterface', 'RichInterface']
