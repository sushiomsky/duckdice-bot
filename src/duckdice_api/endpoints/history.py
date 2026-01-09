"""
Bet history endpoint and local tracking.

Note: DuckDice API may not provide a dedicated bet history endpoint.
This implementation uses local tracking and provides filtering/pagination.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from ..models.bet import BetResult, BetHistoryPage, BetStatistics
from ..utils.pagination import Paginator
from ..utils.filters import FilterSet, DateRangeFilter, ValueFilter, BooleanFilter


class BetHistoryManager:
    """
    Manages bet history with local storage and filtering.
    
    Note: Since DuckDice may not provide a history API endpoint,
    we track bets locally and provide filtering/pagination.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize bet history manager.
        
        Args:
            storage_dir: Directory for storing bet history (defaults to ~/.duckdice/history)
        """
        if storage_dir is None:
            storage_dir = Path.home() / '.duckdice' / 'history'
        
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: List[BetResult] = []
    
    def add_bet(self, bet: BetResult) -> None:
        """
        Add a bet to history.
        
        Args:
            bet: BetResult to add
        """
        self.current_session.append(bet)
        
        # Persist to daily file
        self._save_to_daily_file(bet)
    
    def _save_to_daily_file(self, bet: BetResult) -> None:
        """Save bet to daily history file"""
        date_str = bet.timestamp.strftime('%Y-%m-%d')
        file_path = self.storage_dir / f"{date_str}.jsonl"
        
        # Append to JSONL file
        with open(file_path, 'a') as f:
            bet_dict = {
                'bet_id': bet.bet_id,
                'timestamp': bet.timestamp.isoformat(),
                'currency': bet.currency,
                'amount': str(bet.amount),
                'chance': str(bet.chance),
                'target': str(bet.target),
                'result': str(bet.result),
                'payout': str(bet.payout),
                'profit': str(bet.profit),
                'is_win': bet.is_win,
                'game_type': bet.game_type,
                'server_seed': bet.server_seed,
                'client_seed': bet.client_seed,
                'nonce': bet.nonce,
            }
            f.write(json.dumps(bet_dict) + '\n')
    
    def load_history(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_days: int = 30
    ) -> List[BetResult]:
        """
        Load bet history from files.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            max_days: Maximum days to load
            
        Returns:
            List of BetResult objects
        """
        bets = []
        
        # Determine date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            from datetime import timedelta
            start_date = end_date - timedelta(days=max_days)
        
        # Load from daily files
        current = start_date.date()
        while current <= end_date.date():
            file_path = self.storage_dir / f"{current.isoformat()}.jsonl"
            if file_path.exists():
                bets.extend(self._load_from_file(file_path))
            
            from datetime import timedelta
            current += timedelta(days=1)
        
        return bets
    
    def _load_from_file(self, file_path: Path) -> List[BetResult]:
        """Load bets from JSONL file"""
        bets = []
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        bet_dict = json.loads(line)
                        
                        # Reconstruct BetResult
                        bet = BetResult(
                            bet_id=bet_dict.get('bet_id'),
                            timestamp=datetime.fromisoformat(bet_dict['timestamp']),
                            currency=bet_dict['currency'],
                            amount=Decimal(bet_dict['amount']),
                            chance=Decimal(bet_dict['chance']),
                            target=Decimal(bet_dict['target']),
                            result=Decimal(bet_dict['result']),
                            payout=Decimal(bet_dict['payout']),
                            profit=Decimal(bet_dict['profit']),
                            is_win=bet_dict['is_win'],
                            game_type=bet_dict.get('game_type', 'dice'),
                            server_seed=bet_dict.get('server_seed'),
                            client_seed=bet_dict.get('client_seed'),
                            nonce=bet_dict.get('nonce'),
                        )
                        bets.append(bet)
        except Exception as e:
            # Log error but don't fail
            print(f"Error loading from {file_path}: {e}")
        
        return bets
    
    def get_history(
        self,
        page: int = 1,
        page_size: int = 50,
        currency: Optional[str] = None,
        game_type: Optional[str] = None,
        wins_only: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BetHistoryPage:
        """
        Get paginated bet history with filters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            currency: Filter by currency
            game_type: Filter by game type ('dice' or 'range')
            wins_only: Filter wins (True), losses (False), or all (None)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            BetHistoryPage with filtered and paginated results
        """
        # Load history
        bets = self.load_history(start_date, end_date)
        
        # Apply filters
        filter_set = FilterSet()
        
        if start_date or end_date:
            filter_set.add(
                DateRangeFilter(start_date, end_date),
                lambda b: b.timestamp
            )
        
        if currency:
            filter_set.add(
                ValueFilter(currency, 'eq'),
                lambda b: b.currency
            )
        
        if game_type:
            filter_set.add(
                ValueFilter(game_type, 'eq'),
                lambda b: b.game_type
            )
        
        if wins_only is not None:
            filter_set.add(
                BooleanFilter(wins_only),
                lambda b: b.is_win
            )
        
        filtered_bets = filter_set.apply(bets)
        
        # Paginate
        paginator = Paginator(filtered_bets, page, page_size)
        page_bets = paginator.get_page()
        
        return BetHistoryPage(
            bets=page_bets,
            total=paginator.total,
            page=page,
            page_size=page_size,
            has_next=paginator.has_next,
            has_prev=paginator.has_prev
        )
    
    def get_statistics(
        self,
        currency: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BetStatistics:
        """
        Get aggregated statistics.
        
        Args:
            currency: Filter by currency
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            BetStatistics with aggregated data
        """
        # Load and filter history
        bets = self.load_history(start_date, end_date)
        
        if currency:
            bets = [b for b in bets if b.currency == currency]
        
        return BetStatistics.from_bet_list(bets)
    
    def clear_session(self) -> None:
        """Clear current session bets"""
        self.current_session = []
    
    def export_to_csv(self, output_path: Path, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> None:
        """Export history to CSV file"""
        import csv
        
        bets = self.load_history(start_date, end_date)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'currency', 'amount', 'chance', 'target',
                'result', 'payout', 'profit', 'is_win', 'game_type'
            ])
            writer.writeheader()
            
            for bet in bets:
                writer.writerow({
                    'timestamp': bet.timestamp.isoformat(),
                    'currency': bet.currency,
                    'amount': str(bet.amount),
                    'chance': str(bet.chance),
                    'target': str(bet.target),
                    'result': str(bet.result),
                    'payout': str(bet.payout),
                    'profit': str(bet.profit),
                    'is_win': bet.is_win,
                    'game_type': bet.game_type,
                })
