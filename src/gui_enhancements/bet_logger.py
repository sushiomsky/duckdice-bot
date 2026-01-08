"""
SQLite Bet Logger
Persistent storage for live and simulation bet history
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager


class BetLogger:
    """
    SQLite-based bet logger with separate tables for live and simulation bets.
    Provides efficient querying, statistics, and export capabilities.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize bet logger.
        
        Args:
            db_path: Path to SQLite database file. Defaults to ~/.duckdice/bets.db
        """
        if db_path is None:
            db_path = Path.home() / ".duckdice" / "bets.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Live bets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS live_bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT,
                    bet_amount REAL NOT NULL,
                    chance REAL NOT NULL,
                    payout REAL NOT NULL,
                    is_high INTEGER NOT NULL,
                    is_win INTEGER NOT NULL,
                    profit REAL NOT NULL,
                    balance REAL NOT NULL,
                    roll_value REAL,
                    target_value REAL,
                    multiplier REAL,
                    metadata TEXT
                )
            """)
            
            # Simulation bets table (same structure)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT,
                    bet_amount REAL NOT NULL,
                    chance REAL NOT NULL,
                    payout REAL NOT NULL,
                    is_high INTEGER NOT NULL,
                    is_win INTEGER NOT NULL,
                    profit REAL NOT NULL,
                    balance REAL NOT NULL,
                    roll_value REAL,
                    target_value REAL,
                    multiplier REAL,
                    metadata TEXT
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    is_simulation INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    strategy TEXT,
                    initial_balance REAL,
                    final_balance REAL,
                    total_bets INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_live_timestamp 
                ON live_bets(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_live_session 
                ON live_bets(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_live_strategy 
                ON live_bets(strategy)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sim_timestamp 
                ON simulation_bets(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sim_session 
                ON simulation_bets(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sim_strategy 
                ON simulation_bets(strategy)
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
    
    def log_bet(self, bet_data: Dict[str, Any], is_simulation: bool = False):
        """
        Log a bet to the database.
        
        Args:
            bet_data: Dictionary with bet information
            is_simulation: Whether this is a simulation bet
        """
        table = "simulation_bets" if is_simulation else "live_bets"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                INSERT INTO {table} (
                    timestamp, session_id, symbol, strategy,
                    bet_amount, chance, payout, is_high, is_win,
                    profit, balance, roll_value, target_value,
                    multiplier, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet_data.get('timestamp', datetime.now().isoformat()),
                bet_data.get('session_id', 'default'),
                bet_data.get('symbol', ''),
                bet_data.get('strategy', ''),
                float(bet_data.get('bet_amount', 0)),
                float(bet_data.get('chance', 0)),
                float(bet_data.get('payout', 0)),
                1 if bet_data.get('is_high', True) else 0,
                1 if bet_data.get('is_win', False) else 0,
                float(bet_data.get('profit', 0)),
                float(bet_data.get('balance', 0)),
                float(bet_data.get('roll_value', 0)) if bet_data.get('roll_value') else None,
                float(bet_data.get('target_value', 0)) if bet_data.get('target_value') else None,
                float(bet_data.get('multiplier', 0)) if bet_data.get('multiplier') else None,
                json.dumps(bet_data.get('metadata', {}))
            ))
            
            conn.commit()
    
    def get_bets(
        self,
        is_simulation: bool = False,
        session_id: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query bets with filters.
        
        Args:
            is_simulation: Query simulation or live bets
            session_id: Filter by session ID
            strategy: Filter by strategy
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of bet dictionaries
        """
        table = "simulation_bets" if is_simulation else "live_bets"
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def get_statistics(
        self,
        is_simulation: bool = False,
        session_id: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for bets matching filters.
        
        Returns:
            Dictionary with statistics: total_bets, wins, losses, win_rate,
            total_profit, avg_profit, max_win, max_loss, etc.
        """
        table = "simulation_bets" if is_simulation else "live_bets"
        
        query = f"""
            SELECT 
                COUNT(*) as total_bets,
                SUM(is_win) as total_wins,
                SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as total_losses,
                SUM(profit) as total_profit,
                AVG(profit) as avg_profit,
                MAX(CASE WHEN is_win = 1 THEN profit ELSE NULL END) as max_win,
                MIN(CASE WHEN is_win = 0 THEN profit ELSE NULL END) as max_loss,
                AVG(bet_amount) as avg_bet,
                MIN(balance) as min_balance,
                MAX(balance) as max_balance
            FROM {table}
            WHERE 1=1
        """
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            row = cursor.fetchone()
            if not row:
                return self._empty_statistics()
            
            total_bets = row['total_bets'] or 0
            total_wins = row['total_wins'] or 0
            total_losses = row['total_losses'] or 0
            
            return {
                'total_bets': total_bets,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'win_rate': (total_wins / total_bets * 100) if total_bets > 0 else 0,
                'total_profit': row['total_profit'] or 0,
                'avg_profit': row['avg_profit'] or 0,
                'max_win': row['max_win'] or 0,
                'max_loss': row['max_loss'] or 0,
                'avg_bet': row['avg_bet'] or 0,
                'min_balance': row['min_balance'] or 0,
                'max_balance': row['max_balance'] or 0,
            }
    
    def start_session(
        self,
        session_id: str,
        is_simulation: bool,
        strategy: Optional[str] = None,
        initial_balance: Optional[Decimal] = None,
        metadata: Optional[Dict] = None
    ):
        """Start a new betting session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (
                    id, is_simulation, start_time, strategy,
                    initial_balance, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                1 if is_simulation else 0,
                datetime.now().isoformat(),
                strategy,
                float(initial_balance) if initial_balance else None,
                json.dumps(metadata or {})
            ))
            
            conn.commit()
    
    def end_session(
        self,
        session_id: str,
        final_balance: Optional[Decimal] = None
    ):
        """End a betting session and compute statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute("SELECT is_simulation FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return
            
            is_simulation = bool(row['is_simulation'])
            
            # Get session statistics
            stats = self.get_statistics(is_simulation=is_simulation, session_id=session_id)
            
            # Update session
            cursor.execute("""
                UPDATE sessions SET
                    end_time = ?,
                    final_balance = ?,
                    total_bets = ?,
                    total_wins = ?,
                    total_profit = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                float(final_balance) if final_balance else None,
                stats['total_bets'],
                stats['total_wins'],
                stats['total_profit'],
                session_id
            ))
            
            conn.commit()
    
    def get_sessions(self, is_simulation: Optional[bool] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of sessions."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        
        if is_simulation is not None:
            query += " AND is_simulation = ?"
            params.append(1 if is_simulation else 0)
        
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary."""
        d = dict(row)
        
        # Convert boolean fields
        if 'is_win' in d:
            d['is_win'] = bool(d['is_win'])
        if 'is_high' in d:
            d['is_high'] = bool(d['is_high'])
        if 'is_simulation' in d:
            d['is_simulation'] = bool(d['is_simulation'])
        
        # Parse metadata
        if 'metadata' in d and d['metadata']:
            try:
                d['metadata'] = json.loads(d['metadata'])
            except:
                d['metadata'] = {}
        
        return d
    
    def _empty_statistics(self) -> Dict[str, Any]:
        """Return empty statistics dictionary."""
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
    
    def export_to_csv(
        self,
        output_path: Path,
        is_simulation: bool = False,
        **filters
    ):
        """Export bets to CSV file."""
        import csv
        
        bets = self.get_bets(is_simulation=is_simulation, limit=100000, **filters)
        
        if not bets:
            return
        
        with open(output_path, 'w', newline='') as f:
            fieldnames = [
                'timestamp', 'session_id', 'symbol', 'strategy',
                'bet_amount', 'chance', 'payout', 'is_win',
                'profit', 'balance'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(bets)
    
    def clear_old_data(self, days: int = 90):
        """Delete bets older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM live_bets WHERE timestamp < ?", (cutoff_iso,))
            cursor.execute("DELETE FROM simulation_bets WHERE timestamp < ?", (cutoff_iso,))
            
            deleted_live = cursor.rowcount
            deleted_sim = cursor.rowcount
            
            conn.commit()
            
            return {'live': deleted_live, 'simulation': deleted_sim}
