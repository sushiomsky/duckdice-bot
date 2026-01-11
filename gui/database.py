"""
Database module for DuckDice Bot GUI.

Handles SQLite persistence for:
- Bet history
- Strategy profiles
- Session data
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from gui.state import BetRecord

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for bet history and profiles."""
    
    def __init__(self, db_path: str = "data/duckdice_bot.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_database()
    
    def _ensure_db_dir(self):
        """Create database directory if it doesn't exist."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Bet history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bet_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    amount REAL NOT NULL,
                    target REAL NOT NULL,
                    roll REAL NOT NULL,
                    won INTEGER NOT NULL,
                    profit REAL NOT NULL,
                    balance REAL NOT NULL,
                    strategy TEXT NOT NULL,
                    currency TEXT DEFAULT 'btc',
                    simulation_mode INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Strategy profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    strategy_name TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Session history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    strategy_name TEXT NOT NULL,
                    starting_balance REAL,
                    ending_balance REAL,
                    total_bets INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    profit REAL DEFAULT 0,
                    profit_percent REAL DEFAULT 0,
                    simulation_mode INTEGER DEFAULT 1,
                    started_at TEXT,
                    ended_at TEXT,
                    stop_reason TEXT
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bet_session 
                ON bet_history(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bet_timestamp 
                ON bet_history(timestamp DESC)
            """)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def save_bet(self, bet: BetRecord, session_id: str, currency: str = "btc", 
                 simulation_mode: bool = True) -> int:
        """
        Save a bet to the database.
        
        Args:
            bet: BetRecord to save
            session_id: Unique session identifier
            currency: Currency used (btc, doge, etc.)
            simulation_mode: Whether this was a simulation bet
        
        Returns:
            Row ID of inserted bet
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bet_history 
                (session_id, timestamp, amount, target, roll, won, profit, balance, 
                 strategy, currency, simulation_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                bet.timestamp.isoformat(),
                bet.amount,
                bet.target,
                bet.roll,
                1 if bet.won else 0,
                bet.profit,
                bet.balance,
                bet.strategy,
                currency,
                1 if simulation_mode else 0
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_bet_history(self, session_id: Optional[str] = None, 
                       limit: int = 1000, offset: int = 0) -> List[BetRecord]:
        """
        Load bet history from database.
        
        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of bets to return
            offset: Number of bets to skip
        
        Returns:
            List of BetRecord objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT timestamp, amount, target, roll, won, profit, balance, strategy
                    FROM bet_history
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (session_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT timestamp, amount, target, roll, won, profit, balance, strategy
                    FROM bet_history
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            bets = []
            for row in cursor.fetchall():
                bet = BetRecord(
                    timestamp=datetime.fromisoformat(row[0]),
                    amount=row[1],
                    target=row[2],
                    roll=row[3],
                    won=bool(row[4]),
                    profit=row[5],
                    balance=row[6],
                    strategy=row[7]
                )
                bets.append(bet)
            
            return bets
    
    def get_bet_count(self, session_id: Optional[str] = None) -> int:
        """Get total number of bets in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT COUNT(*) FROM bet_history WHERE session_id = ?
                """, (session_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM bet_history")
            
            return cursor.fetchone()[0]
    
    def clear_bet_history(self, session_id: Optional[str] = None):
        """Clear bet history from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("DELETE FROM bet_history WHERE session_id = ?", (session_id,))
            else:
                cursor.execute("DELETE FROM bet_history")
            
            conn.commit()
            logger.info(f"Cleared bet history{' for session ' + session_id if session_id else ''}")
    
    def save_strategy_profile(self, name: str, strategy_name: str, 
                              parameters: Dict[str, Any], description: str = "") -> int:
        """
        Save a strategy profile.
        
        Args:
            name: Profile name (must be unique)
            strategy_name: Name of strategy (e.g., 'classic-martingale')
            parameters: Strategy parameters dict
            description: Optional description
        
        Returns:
            Row ID of saved profile
        """
        params_json = json.dumps(parameters)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to update first
            cursor.execute("""
                UPDATE strategy_profiles 
                SET strategy_name = ?, parameters = ?, description = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (strategy_name, params_json, description, name))
            
            if cursor.rowcount == 0:
                # Insert new profile
                cursor.execute("""
                    INSERT INTO strategy_profiles (name, strategy_name, parameters, description)
                    VALUES (?, ?, ?, ?)
                """, (name, strategy_name, params_json, description))
            
            conn.commit()
            return cursor.lastrowid
    
    def load_strategy_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a strategy profile by name.
        
        Returns:
            Dict with 'strategy_name', 'parameters', 'description' or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT strategy_name, parameters, description
                FROM strategy_profiles
                WHERE name = ?
            """, (name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'strategy_name': row[0],
                    'parameters': json.loads(row[1]),
                    'description': row[2]
                }
            return None
    
    def list_strategy_profiles(self) -> List[Dict[str, Any]]:
        """
        List all strategy profiles.
        
        Returns:
            List of dicts with profile information
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, strategy_name, description, created_at, updated_at
                FROM strategy_profiles
                ORDER BY updated_at DESC
            """)
            
            profiles = []
            for row in cursor.fetchall():
                profiles.append({
                    'name': row[0],
                    'strategy_name': row[1],
                    'description': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                })
            
            return profiles
    
    def delete_strategy_profile(self, name: str):
        """Delete a strategy profile."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM strategy_profiles WHERE name = ?", (name,))
            conn.commit()
            logger.info(f"Deleted profile: {name}")
    
    def save_session(self, session_id: str, **kwargs):
        """
        Save or update session information.
        
        Args:
            session_id: Unique session identifier
            **kwargs: Session fields (strategy_name, starting_balance, etc.)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute("SELECT id FROM sessions WHERE session_id = ?", (session_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Build update query dynamically
                fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
                values = list(kwargs.values()) + [session_id]
                cursor.execute(f"""
                    UPDATE sessions SET {fields} WHERE session_id = ?
                """, values)
            else:
                # Insert new session
                fields = ", ".join(["session_id"] + list(kwargs.keys()))
                placeholders = ", ".join(["?"] * (len(kwargs) + 1))
                values = [session_id] + list(kwargs.values())
                cursor.execute(f"""
                    INSERT INTO sessions ({fields}) VALUES ({placeholders})
                """, values)
            
            conn.commit()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session information."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]


# Global singleton instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
