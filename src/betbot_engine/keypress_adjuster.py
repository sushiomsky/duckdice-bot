"""
Keypress-driven bet-size adjuster.

Runs a background thread that listens for single keypresses on stdin.

  +  / =   raise offset by one step
  -        lower offset by one step (floor: 0)
  0        reset offset to 0

The offset is added to every strategy-calculated bet amount by the engine.
Step defaults to 0.00000001 and is typically set to the strategy's min_bet_abs.

Usage::

    adj = KeypressAdjuster(step=0.000001)
    adj.start()
    # ... pass adj.get_offset to engine ...
    adj.stop()
"""
from __future__ import annotations

import sys
import threading
from decimal import Decimal
from typing import Optional, Callable


class KeypressAdjuster:
    """Non-blocking keypress listener that maintains a cumulative bet offset."""

    def __init__(
        self,
        step: float = 0.00000001,
        printer: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._step    = Decimal(str(step))
        self._offset  = Decimal("0")
        self._lock    = threading.Lock()
        self._stop_ev = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._printer = printer or print

    # ------------------------------------------------------------------
    def get_offset(self) -> Decimal:
        with self._lock:
            return self._offset

    def set_step(self, step: float) -> None:
        self._step = Decimal(str(step))

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_ev.clear()
        target = self._run_windows if sys.platform == "win32" else self._run_unix
        self._thread = threading.Thread(target=target, daemon=True, name="keypress-adjuster")
        self._thread.start()
        self._printer(
            f"\n⌨️  Bet-size adjuster active  │  + raise  │  - lower  │  0 reset"
            f"  │  step={float(self._step):.8f}\n"
        )

    def stop(self) -> None:
        self._stop_ev.set()
        # Restore terminal on Unix
        if sys.platform != "win32":
            try:
                import termios
                if self._saved_attrs is not None:
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved_attrs)
            except Exception:
                pass

    # ------------------------------------------------------------------
    def _handle_key(self, ch: str) -> None:
        with self._lock:
            if ch in ("+", "="):
                self._offset += self._step
                new = float(self._offset)
                self._printer(f"  ➕ Bet offset  +{float(self._step):.8f}  →  total +{new:.8f}")
            elif ch == "-":
                self._offset = max(Decimal("0"), self._offset - self._step)
                new = float(self._offset)
                self._printer(f"  ➖ Bet offset  -{float(self._step):.8f}  →  total +{new:.8f}")
            elif ch == "0":
                self._offset = Decimal("0")
                self._printer(f"  🔄 Bet offset reset to 0")

    # ------------------------------------------------------------------
    # Unix implementation (termios raw mode + select)
    # ------------------------------------------------------------------
    _saved_attrs = None

    def _run_unix(self) -> None:
        import termios, tty, select

        fd = sys.stdin.fileno()
        try:
            self._saved_attrs = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            # stdin not a tty (piped/CI) — silently skip
            return

        try:
            while not self._stop_ev.is_set():
                ready, _, _ = select.select([sys.stdin], [], [], 0.15)
                if ready:
                    ch = sys.stdin.read(1)
                    if ch:
                        self._handle_key(ch)
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, self._saved_attrs)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Windows implementation (msvcrt non-blocking)
    # ------------------------------------------------------------------
    def _run_windows(self) -> None:
        import msvcrt, time

        while not self._stop_ev.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                self._handle_key(ch)
            else:
                time.sleep(0.05)
