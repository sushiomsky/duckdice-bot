"""Betting engine interfaces.

This package provides different interface implementations for the betting engine:
- TUI: Curses/Textual-based terminal UI
- Base: Abstract base classes and headless implementation
"""

from .base import BettingInterface, HeadlessInterface

__all__ = ['BettingInterface', 'HeadlessInterface']
