"""
Event system for betting engine.

Provides a clean separation between engine logic and UI/interface layers.
All engine outputs are emitted as structured events that interfaces can subscribe to.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from decimal import Decimal
from enum import Enum


class EventType(Enum):
    """Types of events emitted by the betting engine"""
    # Session lifecycle
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    
    # Bet lifecycle
    BET_PLACED = "bet_placed"
    BET_RESULT = "bet_result"
    BET_ERROR = "bet_error"
    
    # Balance updates
    BALANCE_UPDATED = "balance_updated"
    BALANCE_WARNING = "balance_warning"
    
    # Strategy events
    STRATEGY_INITIALIZED = "strategy_initialized"
    STRATEGY_STATE_CHANGED = "strategy_state_changed"
    
    # Progress/stats
    STATS_UPDATED = "stats_updated"
    PROGRESS_UPDATED = "progress_updated"
    
    # Warnings/errors
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class BettingEvent:
    """Base event emitted by the betting engine"""
    event_type: EventType
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        return f"BettingEvent({self.event_type.value}, {self.data})"


@dataclass
class SessionStartedEvent(BettingEvent):
    """Emitted when a betting session starts"""
    def __init__(self, timestamp: float, strategy_name: str, config: Dict[str, Any], 
                 starting_balance: Decimal, currency: str):
        super().__init__(
            event_type=EventType.SESSION_STARTED,
            timestamp=timestamp,
            data={
                'strategy_name': strategy_name,
                'config': config,
                'starting_balance': str(starting_balance),
                'currency': currency,
            }
        )


@dataclass
class SessionEndedEvent(BettingEvent):
    """Emitted when a betting session ends"""
    def __init__(self, timestamp: float, stop_reason: str, summary: Dict[str, Any]):
        super().__init__(
            event_type=EventType.SESSION_ENDED,
            timestamp=timestamp,
            data={
                'stop_reason': stop_reason,
                'summary': summary,
            }
        )


@dataclass
class BetPlacedEvent(BettingEvent):
    """Emitted when a bet is placed"""
    def __init__(self, timestamp: float, bet_number: int, amount: Decimal, 
                 chance: float, payout_multiplier: float, prediction: str):
        super().__init__(
            event_type=EventType.BET_PLACED,
            timestamp=timestamp,
            data={
                'bet_number': bet_number,
                'amount': str(amount),
                'chance': chance,
                'payout_multiplier': payout_multiplier,
                'prediction': prediction,
            }
        )


@dataclass
class BetResultEvent(BettingEvent):
    """Emitted when a bet result is received"""
    def __init__(self, timestamp: float, bet_number: int, win: bool, 
                 profit: Decimal, balance: Decimal, result_data: Dict[str, Any]):
        super().__init__(
            event_type=EventType.BET_RESULT,
            timestamp=timestamp,
            data={
                'bet_number': bet_number,
                'win': win,
                'profit': str(profit),
                'balance': str(balance),
                'result': result_data,
            }
        )


@dataclass
class BalanceUpdatedEvent(BettingEvent):
    """Emitted when balance changes"""
    def __init__(self, timestamp: float, balance: Decimal, currency: str, 
                 change: Optional[Decimal] = None):
        super().__init__(
            event_type=EventType.BALANCE_UPDATED,
            timestamp=timestamp,
            data={
                'balance': str(balance),
                'currency': currency,
                'change': str(change) if change else None,
            }
        )


@dataclass
class StatsUpdatedEvent(BettingEvent):
    """Emitted periodically with session statistics"""
    def __init__(self, timestamp: float, total_bets: int, wins: int, losses: int,
                 win_rate: float, profit: Decimal, profit_percent: float, 
                 current_balance: Decimal):
        super().__init__(
            event_type=EventType.STATS_UPDATED,
            timestamp=timestamp,
            data={
                'total_bets': total_bets,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'profit': str(profit),
                'profit_percent': profit_percent,
                'current_balance': str(current_balance),
            }
        )


@dataclass
class WarningEvent(BettingEvent):
    """Emitted for warnings"""
    def __init__(self, timestamp: float, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            event_type=EventType.WARNING,
            timestamp=timestamp,
            data={
                'message': message,
                'details': details or {},
            }
        )


@dataclass
class ErrorEvent(BettingEvent):
    """Emitted for errors"""
    def __init__(self, timestamp: float, message: str, exception: Optional[Exception] = None):
        super().__init__(
            event_type=EventType.ERROR,
            timestamp=timestamp,
            data={
                'message': message,
                'exception_type': type(exception).__name__ if exception else None,
                'exception_message': str(exception) if exception else None,
            }
        )


@dataclass
class InfoEvent(BettingEvent):
    """Emitted for informational messages"""
    def __init__(self, timestamp: float, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            event_type=EventType.INFO,
            timestamp=timestamp,
            data={
                'message': message,
                **(data or {}),
            }
        )
