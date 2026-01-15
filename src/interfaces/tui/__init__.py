"""TUI (Text User Interface) implementations using curses/textual."""

from .textual_interface import DuckDiceTUI, run_tui
from .ncurses_interface import NCursesInterface, run_ncurses

__all__ = ['DuckDiceTUI', 'run_tui', 'NCursesInterface', 'run_ncurses']

