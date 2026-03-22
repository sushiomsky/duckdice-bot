"""Persistent memory system for the autonomous agent ecosystem.

Stores and retrieves knowledge about the user's gambling ecosystem:
- Casino/wallet/faucet accounts and balances
- Strategy performance records and evaluations
- Session history logs
- User preferences and behavior patterns
- Faucet/contest/promotion opportunities
- Profit and wager goals
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MEMORY_VERSION = 1

_DEFAULT_STRUCTURE: Dict[str, Any] = {
    "accounts": {},
    "balances": {},
    "strategies": {},
    "sessions": [],
    "preferences": {},
    "opportunities": [],
    "goals": {},
    "metadata": {
        "created_at": "",
        "last_updated": "",
        "version": _MEMORY_VERSION,
    },
}

_LIST_CATEGORIES = {"sessions", "opportunities"}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class MemoryManager:
    """Persistent JSON-backed memory for the agent ecosystem."""

    def __init__(self, data_dir: str = "data/agents") -> None:
        self._data_dir = data_dir
        self._filepath = os.path.join(data_dir, "memory.json")
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # Core accessors
    # ------------------------------------------------------------------

    def get(self, category: str, key: Optional[str] = None) -> Any:
        """Return an entire category or a specific key within it."""
        with self._lock:
            cat = self._data.get(category)
            if cat is None:
                return [] if category in _LIST_CATEGORIES else {}
            if key is None:
                return cat
            if isinstance(cat, dict):
                return cat.get(key)
            return None

    def set(self, category: str, key: str, value: Any) -> None:
        """Set a value within a dict-type category."""
        with self._lock:
            if category not in self._data or not isinstance(
                self._data.get(category), dict
            ):
                self._data[category] = {}
            self._data[category][key] = value
            self._touch()
        self.save()

    def append(self, category: str, entry: dict) -> None:
        """Append an entry to a list-type category (sessions, opportunities)."""
        with self._lock:
            if category not in self._data or not isinstance(
                self._data.get(category), list
            ):
                self._data[category] = []
            self._data[category].append(entry)
            self._touch()
        self.save()

    # ------------------------------------------------------------------
    # Convenience writers
    # ------------------------------------------------------------------

    def update_balance(self, account: str, symbol: str, amount: float) -> None:
        """Update a currency balance for the given account."""
        with self._lock:
            balances = self._data.setdefault("balances", {})
            acct = balances.setdefault(account, {})
            acct[symbol] = amount
            self._touch()
        self.save()

    def record_session(self, session_data: dict) -> None:
        """Log a completed session result."""
        entry = dict(session_data)
        entry.setdefault("timestamp", _utcnow_iso())
        self.append("sessions", entry)

    def record_strategy_evaluation(
        self,
        strategy_name: str,
        composite_score: float,
        metrics: dict,
    ) -> None:
        """Store or update a strategy evaluation result."""
        with self._lock:
            strategies = self._data.setdefault("strategies", {})
            strategies[strategy_name] = {
                "name": strategy_name,
                "composite_score": composite_score,
                "metrics": metrics,
                "last_evaluated": _utcnow_iso(),
            }
            self._touch()
        self.save()

    # ------------------------------------------------------------------
    # Convenience readers
    # ------------------------------------------------------------------

    def get_best_strategies(self, top_n: int = 5) -> List[dict]:
        """Return the top *top_n* strategies sorted by composite score."""
        with self._lock:
            strategies = self._data.get("strategies", {})
            ranked = sorted(
                strategies.values(),
                key=lambda s: s.get("composite_score", 0),
                reverse=True,
            )
        return ranked[:top_n]

    def get_recent_sessions(self, count: int = 20) -> List[dict]:
        """Return the most recent *count* sessions."""
        with self._lock:
            sessions = self._data.get("sessions", [])
        return sessions[-count:]

    def search(self, category: str, **filters: Any) -> List[dict]:
        """Filter search within a list-type category.

        Returns entries where every *key=value* filter matches.
        """
        with self._lock:
            data = self._data.get(category, [])
        if not isinstance(data, list):
            return []
        results: List[dict] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            if all(entry.get(k) == v for k, v in filters.items()):
                results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist current memory to disk."""
        with self._lock:
            self._touch()
            data_snapshot = json.loads(json.dumps(self._data))

        os.makedirs(self._data_dir, exist_ok=True)
        tmp_path = self._filepath + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(data_snapshot, fh, indent=2, ensure_ascii=False)
            shutil.move(tmp_path, self._filepath)
            logger.debug("Memory saved to %s", self._filepath)
        except OSError:
            logger.exception("Failed to save memory to %s", self._filepath)

    def load(self) -> None:
        """Load memory from disk, creating a fresh store if needed."""
        with self._lock:
            if not os.path.exists(self._filepath):
                logger.info(
                    "No memory file found at %s — creating fresh", self._filepath
                )
                self._data = _fresh_data()
                return

            try:
                with open(self._filepath, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if not isinstance(loaded, dict):
                    raise ValueError("Root element is not a JSON object")
                self._data = loaded
                # Ensure all expected top-level keys exist.
                for key, default in _DEFAULT_STRUCTURE.items():
                    self._data.setdefault(
                        key,
                        [] if isinstance(default, list) else (
                            {} if isinstance(default, dict) else default
                        ),
                    )
                logger.info("Memory loaded from %s", self._filepath)
            except (json.JSONDecodeError, ValueError, OSError):
                logger.exception(
                    "Corrupt memory file at %s — backing up and creating fresh",
                    self._filepath,
                )
                backup = self._filepath + ".bak"
                try:
                    shutil.copy2(self._filepath, backup)
                    logger.info("Backup saved to %s", backup)
                except OSError:
                    logger.warning("Could not create backup of corrupt memory file")
                self._data = _fresh_data()

    # ------------------------------------------------------------------
    # Export / summary
    # ------------------------------------------------------------------

    def export(self) -> dict:
        """Return the full memory store as a plain dict (deep copy)."""
        with self._lock:
            return json.loads(json.dumps(self._data))

    def summary(self) -> str:
        """Return a human-readable summary of stored knowledge."""
        with self._lock:
            accounts = self._data.get("accounts", {})
            balances = self._data.get("balances", {})
            strategies = self._data.get("strategies", {})
            sessions = self._data.get("sessions", [])
            opportunities = self._data.get("opportunities", [])
            goals = self._data.get("goals", {})
            preferences = self._data.get("preferences", {})
            meta = self._data.get("metadata", {})

        lines = ["=== Agent Memory Summary ==="]

        lines.append(f"Accounts:       {len(accounts)}")
        lines.append(f"Balances:       {len(balances)} account(s) tracked")
        lines.append(f"Strategies:     {len(strategies)} evaluated")
        lines.append(f"Sessions:       {len(sessions)} recorded")
        lines.append(f"Opportunities:  {len(opportunities)}")
        lines.append(f"Goals:          {len(goals)}")
        lines.append(f"Preferences:    {len(preferences)} stored")

        if strategies:
            best = max(
                strategies.values(), key=lambda s: s.get("composite_score", 0)
            )
            lines.append(
                f"Best strategy:  {best.get('name')} "
                f"(score {best.get('composite_score', 0):.4f})"
            )

        if sessions:
            total_profit = sum(s.get("profit", 0) for s in sessions)
            total_bets = sum(s.get("bets", 0) for s in sessions)
            lines.append(f"Total profit:   {total_profit:+.8f}")
            lines.append(f"Total bets:     {total_bets}")

        lines.append(f"Last updated:   {meta.get('last_updated', 'never')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        """Update the last_updated timestamp (caller must hold lock)."""
        meta = self._data.setdefault("metadata", {})
        meta["last_updated"] = _utcnow_iso()


def _fresh_data() -> Dict[str, Any]:
    """Return a new, empty memory structure."""
    data = json.loads(json.dumps(_DEFAULT_STRUCTURE))
    now = _utcnow_iso()
    data["metadata"]["created_at"] = now
    data["metadata"]["last_updated"] = now
    return data
