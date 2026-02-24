"""
Database logger for complete betting stream persistence.
Provides SQLite storage for debugging and strategy improvement analysis.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager


class BetDatabase:
    """
    SQLite-based bet logger for comprehensive betting stream capture.
    Stores complete bet data for debugging, analysis, and strategy improvement.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize bet database.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/duckdice_bot.db
        """
        if db_path is None:
            db_path = Path("data") / "duckdice_bot.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize or verify database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main bet history table (complete stream)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bet_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    bet_number INTEGER NOT NULL,
                    
                    -- Bet specification
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    amount REAL NOT NULL,
                    chance REAL,
                    target REAL,
                    is_high INTEGER,
                    range_low INTEGER,
                    range_high INTEGER,
                    is_in INTEGER,
                    game_type TEXT DEFAULT 'dice',
                    
                    -- Result
                    roll REAL,
                    won INTEGER NOT NULL,
                    profit REAL NOT NULL,
                    payout REAL,
                    
                    -- State
                    balance REAL NOT NULL,
                    loss_streak INTEGER DEFAULT 0,
                    
                    -- Metadata
                    simulation_mode INTEGER DEFAULT 0,
                    api_raw TEXT,
                    strategy_state TEXT,
                    
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Sessions tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    strategy_name TEXT NOT NULL,
                    
                    -- Configuration
                    symbol TEXT NOT NULL,
                    simulation_mode INTEGER DEFAULT 0,
                    strategy_params TEXT,
                    
                    -- Initial state
                    starting_balance REAL,
                    started_at TEXT,
                    
                    -- Session limits
                    stop_loss REAL,
                    take_profit REAL,
                    max_bet REAL,
                    max_bets INTEGER,
                    max_losses INTEGER,
                    max_duration_sec INTEGER,
                    
                    -- Final state
                    ending_balance REAL,
                    ended_at TEXT,
                    stop_reason TEXT,
                    
                    -- Statistics
                    total_bets INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    profit REAL DEFAULT 0,
                    profit_percent REAL DEFAULT 0,
                    duration_seconds REAL,
                    
                    -- Metadata
                    metadata TEXT
                )
            """)
            
            # Strategy profiles (saved configurations)
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
            
            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bet_session 
                ON bet_history(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bet_timestamp 
                ON bet_history(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bet_strategy 
                ON bet_history(strategy)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bet_simulation 
                ON bet_history(simulation_mode)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_timestamp 
                ON sessions(started_at DESC)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def start_session(
        self,
        session_id: str,
        strategy_name: str,
        symbol: str,
        simulation_mode: bool = False,
        starting_balance: Optional[Decimal] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        limits: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Start a new betting session.
        
        Args:
            session_id: Unique session identifier
            strategy_name: Name of the strategy
            symbol: Trading symbol/currency
            simulation_mode: Whether this is a simulation
            starting_balance: Initial balance
            strategy_params: Strategy parameters
            limits: Session limits (stop_loss, take_profit, etc.)
            metadata: Additional metadata
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            limits = limits or {}
            
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (
                    session_id, strategy_name, symbol, simulation_mode,
                    starting_balance, started_at, strategy_params,
                    stop_loss, take_profit, max_bet, max_bets,
                    max_losses, max_duration_sec, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                strategy_name,
                symbol,
                1 if simulation_mode else 0,
                float(starting_balance) if starting_balance else None,
                datetime.now().isoformat(),
                json.dumps(strategy_params or {}),
                limits.get('stop_loss'),
                limits.get('take_profit'),
                limits.get('max_bet'),
                limits.get('max_bets'),
                limits.get('max_losses'),
                limits.get('max_duration_sec'),
                json.dumps(metadata or {})
            ))
            
            conn.commit()
    
    def log_bet(
        self,
        session_id: str,
        bet_data: Dict[str, Any],
        result_data: Dict[str, Any],
        bet_number: int,
        balance: Decimal,
        loss_streak: int = 0,
        simulation_mode: bool = False,
        strategy_state: Optional[Dict[str, Any]] = None
    ):
        """
        Log a complete bet with all details.
        
        Args:
            session_id: Session identifier
            bet_data: Bet specification (amount, chance, etc.)
            result_data: Bet result (win, profit, roll, etc.)
            bet_number: Sequential bet number in session
            balance: Current balance after bet
            loss_streak: Current loss streak
            simulation_mode: Whether this is simulated
            strategy_state: Internal strategy state snapshot
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Extract bet specification
            amount = float(bet_data.get('amount', 0))
            chance = float(bet_data.get('chance', 0)) if bet_data.get('chance') else None
            is_high = 1 if bet_data.get('is_high') else 0
            game_type = bet_data.get('game', 'dice')
            
            # Extract range for range dice
            range_vals = bet_data.get('range')
            range_low = int(range_vals[0]) if range_vals else None
            range_high = int(range_vals[1]) if range_vals else None
            is_in = 1 if bet_data.get('is_in') else 0
            
            # Extract result
            win = 1 if result_data.get('win', False) else 0
            profit = float(result_data.get('profit', 0))
            roll = float(result_data.get('number', 0)) if result_data.get('number') is not None else None
            payout = float(result_data.get('payout', 0)) if result_data.get('payout') else None
            timestamp = result_data.get('timestamp', datetime.now().isoformat())
            
            # Calculate target from chance and is_high (for dice)
            target = None
            if game_type == 'dice' and chance is not None:
                if is_high:
                    target = 100 - chance
                else:
                    target = chance
            
            cursor.execute("""
                INSERT INTO bet_history (
                    session_id, timestamp, bet_number,
                    symbol, strategy, amount, chance, target,
                    is_high, range_low, range_high, is_in, game_type,
                    roll, won, profit, payout,
                    balance, loss_streak, simulation_mode,
                    api_raw, strategy_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                timestamp,
                bet_number,
                bet_data.get('symbol', ''),
                bet_data.get('strategy', ''),
                amount,
                chance,
                target,
                is_high,
                range_low,
                range_high,
                is_in,
                game_type,
                roll,
                win,
                profit,
                payout,
                float(balance),
                loss_streak,
                1 if simulation_mode else 0,
                json.dumps(result_data.get('api_raw', {})),
                json.dumps(strategy_state or {})
            ))
            
            conn.commit()
    
    def end_session(
        self,
        session_id: str,
        ending_balance: Decimal,
        stop_reason: str,
        total_bets: int,
        wins: int,
        losses: int
    ):
        """
        End a betting session and compute final statistics.
        
        Args:
            session_id: Session identifier
            ending_balance: Final balance
            stop_reason: Reason for stopping
            total_bets: Total number of bets placed
            wins: Number of winning bets
            losses: Number of losing bets
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session start info
            cursor.execute(
                "SELECT starting_balance, started_at FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return
            
            starting_balance = Decimal(str(row['starting_balance'] or 0))
            started_at = datetime.fromisoformat(row['started_at'])
            ended_at = datetime.now()
            
            # Calculate statistics
            profit = ending_balance - starting_balance
            profit_percent = (profit / starting_balance * 100) if starting_balance > 0 else 0
            duration = (ended_at - started_at).total_seconds()
            
            # Update session
            cursor.execute("""
                UPDATE sessions SET
                    ending_balance = ?,
                    ended_at = ?,
                    stop_reason = ?,
                    total_bets = ?,
                    wins = ?,
                    losses = ?,
                    profit = ?,
                    profit_percent = ?,
                    duration_seconds = ?
                WHERE session_id = ?
            """, (
                float(ending_balance),
                ended_at.isoformat(),
                stop_reason,
                total_bets,
                wins,
                losses,
                float(profit),
                float(profit_percent),
                duration,
                session_id
            ))
            
            conn.commit()
    
    def get_session_bets(
        self,
        session_id: str,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """Get all bets for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bet_history
                WHERE session_id = ?
                ORDER BY bet_number ASC
                LIMIT ?
            """, (session_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_sessions(
        self,
        simulation_mode: Optional[bool] = None,
        strategy_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of sessions with optional filters."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        
        if simulation_mode is not None:
            query += " AND simulation_mode = ?"
            params.append(1 if simulation_mode else 0)
        
        if strategy_name:
            query += " AND strategy_name = ?"
            params.append(strategy_name)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_last_cancelled_session(
        self,
        strategy_name: Optional[str] = None,
        simulation_mode: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the most recent session that was cancelled by the user."""
        query = "SELECT * FROM sessions WHERE stop_reason = 'cancelled'"
        params: list = []
        if strategy_name:
            query += " AND strategy_name = ?"
            params.append(strategy_name)
        if simulation_mode is not None:
            query += " AND simulation_mode = ?"
            params.append(1 if simulation_mode else 0)
        query += " ORDER BY started_at DESC LIMIT 1"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_tail_state(self, session_id: str) -> Dict[str, Any]:
        """Return restorable state from the last bet of a session.

        Returns a dict with: loss_streak, bet_number, last_balance.
        Used by strategies that implement on_resume() to restore internal state.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bet_number, loss_streak, balance
                FROM bet_history WHERE session_id = ?
                ORDER BY bet_number DESC LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()
            if not row:
                return {}
            return {
                "loss_streak": row["loss_streak"] or 0,
                "bet_number": row["bet_number"] or 0,
                "last_balance": row["balance"] or 0,
            }

    def get_statistics(
        self,
        session_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        simulation_mode: Optional[bool] = None,
        since: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregate statistics with optional filters."""
        query = """
            SELECT 
                COUNT(*) as total_bets,
                SUM(won) as total_wins,
                SUM(CASE WHEN won = 0 THEN 1 ELSE 0 END) as total_losses,
                SUM(profit) as total_profit,
                AVG(profit) as avg_profit,
                MAX(CASE WHEN won = 1 THEN profit ELSE NULL END) as max_win,
                MIN(CASE WHEN won = 0 THEN profit ELSE NULL END) as max_loss,
                AVG(amount) as avg_bet,
                MIN(balance) as min_balance,
                MAX(balance) as max_balance
            FROM bet_history
            WHERE 1=1
        """
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if strategy_name:
            query += " AND strategy = ?"
            params.append(strategy_name)
        
        if simulation_mode is not None:
            query += " AND simulation_mode = ?"
            params.append(1 if simulation_mode else 0)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if not row or not row['total_bets']:
                return {
                    'total_bets': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'win_rate': 0,
                    'total_profit': 0,
                    'avg_profit': 0,
                    'max_win': 0,
                    'max_loss': 0,
                    'avg_bet': 0,
                    'min_balance': 0,
                    'max_balance': 0,
                }
            
            total_bets = row['total_bets']
            total_wins = row['total_wins'] or 0
            
            return {
                'total_bets': total_bets,
                'total_wins': total_wins,
                'total_losses': row['total_losses'] or 0,
                'win_rate': (total_wins / total_bets * 100) if total_bets > 0 else 0,
                'total_profit': row['total_profit'] or 0,
                'avg_profit': row['avg_profit'] or 0,
                'max_win': row['max_win'] or 0,
                'max_loss': row['max_loss'] or 0,
                'avg_bet': row['avg_bet'] or 0,
                'min_balance': row['min_balance'] or 0,
                'max_balance': row['max_balance'] or 0,
            }
    
    def get_recent_rolls(
        self,
        symbol: Optional[str] = None,
        limit: int = 5000,
    ) -> List[float]:
        """Return the rolled numbers from the most recent `limit` bets.

        Used by strategies for frequency-aware range placement.
        Returns a list of floats (0.0 – 9999.0) ordered oldest-first.
        """
        query = """
            SELECT roll FROM (
                SELECT id, roll FROM bet_history
                WHERE roll IS NOT NULL
                {symbol_filter}
                ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
        """
        params: List[Any] = [limit]
        symbol_filter = ""
        if symbol:
            symbol_filter = "AND symbol = ?"
            params = [symbol, limit]

        query = query.format(symbol_filter=symbol_filter)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [float(row[0]) for row in cursor.fetchall()]

    def export_to_csv(
        self,
        output_path: Path,
        session_id: Optional[str] = None,
        **filters
    ):
        """Export bets to CSV file."""
        import csv
        
        query = "SELECT * FROM bet_history WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        query += " ORDER BY timestamp ASC LIMIT 100000"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            bets = [dict(row) for row in cursor.fetchall()]
        
        if not bets:
            return
        
        with open(output_path, 'w', newline='') as f:
            fieldnames = [
                'timestamp', 'session_id', 'bet_number', 'strategy',
                'symbol', 'amount', 'chance', 'target', 'roll',
                'won', 'profit', 'balance', 'loss_streak'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(bets)
