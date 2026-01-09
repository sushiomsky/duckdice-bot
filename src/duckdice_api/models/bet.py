"""
Data models for bet history and results.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class BetResult:
    """Single bet result from API"""
    bet_id: Optional[str]
    timestamp: datetime
    currency: str
    amount: Decimal
    chance: Decimal
    target: Decimal
    result: Decimal
    payout: Decimal
    profit: Decimal
    is_win: bool
    game_type: str = 'dice'  # 'dice' or 'range'
    server_seed: Optional[str] = None
    client_seed: Optional[str] = None
    nonce: Optional[int] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'BetResult':
        """Create BetResult from API response"""
        return cls(
            bet_id=data.get('betId') or data.get('id'),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            currency=data.get('currency') or data.get('symbol', 'BTC'),
            amount=Decimal(str(data.get('amount', 0))),
            chance=Decimal(str(data.get('chance', 0))),
            target=Decimal(str(data.get('target', 0))),
            result=Decimal(str(data.get('result', 0))),
            payout=Decimal(str(data.get('payout', 0))),
            profit=Decimal(str(data.get('profit', 0))),
            is_win=bool(data.get('isWin') or data.get('win', False)),
            game_type=data.get('gameType', 'dice'),
            server_seed=data.get('serverSeed'),
            client_seed=data.get('clientSeed'),
            nonce=data.get('nonce')
        )


@dataclass
class BetHistoryPage:
    """Paginated bet history response"""
    bets: list[BetResult]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
    
    @property
    def total_pages(self) -> int:
        """Calculate total pages"""
        return (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 1


@dataclass
class BetStatistics:
    """Aggregated bet statistics"""
    total_bets: int
    total_wagered: Decimal
    total_profit: Decimal
    total_wins: int
    total_losses: int
    win_rate: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    average_bet: Decimal
    average_profit: Decimal
    
    @classmethod
    def from_bet_list(cls, bets: list[BetResult]) -> 'BetStatistics':
        """Calculate statistics from bet list"""
        if not bets:
            return cls(
                total_bets=0,
                total_wagered=Decimal('0'),
                total_profit=Decimal('0'),
                total_wins=0,
                total_losses=0,
                win_rate=Decimal('0'),
                largest_win=Decimal('0'),
                largest_loss=Decimal('0'),
                average_bet=Decimal('0'),
                average_profit=Decimal('0')
            )
        
        total_bets = len(bets)
        total_wagered = sum(bet.amount for bet in bets)
        total_profit = sum(bet.profit for bet in bets)
        total_wins = sum(1 for bet in bets if bet.is_win)
        total_losses = total_bets - total_wins
        win_rate = Decimal(total_wins) / Decimal(total_bets) if total_bets > 0 else Decimal('0')
        
        wins = [bet.profit for bet in bets if bet.is_win]
        losses = [bet.profit for bet in bets if not bet.is_win]
        
        largest_win = max(wins) if wins else Decimal('0')
        largest_loss = min(losses) if losses else Decimal('0')
        average_bet = total_wagered / Decimal(total_bets) if total_bets > 0 else Decimal('0')
        average_profit = total_profit / Decimal(total_bets) if total_bets > 0 else Decimal('0')
        
        return cls(
            total_bets=total_bets,
            total_wagered=total_wagered,
            total_profit=total_profit,
            total_wins=total_wins,
            total_losses=total_losses,
            win_rate=win_rate,
            largest_win=largest_win,
            largest_loss=largest_loss,
            average_bet=average_bet,
            average_profit=average_profit
        )
