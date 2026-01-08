"""
DiceBot-compatible Script Editor

Provides a modern script editor with:
- Syntax highlighting for Lua scripts
- DiceBot API compatibility layer
- Save/load script versions
- Simulation testing
- Auto-completion
"""

from .editor import ScriptEditor
from .dicebot_compat import DiceBotAPI

__all__ = ['ScriptEditor', 'DiceBotAPI']
