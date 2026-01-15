"""
Rich-based CLI interface for the betting engine.

This adapter connects the event-driven engine to the Rich terminal UI,
providing a beautiful command-line betting experience.
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich import box

# Use try/except for flexible imports
try:
    # Try relative imports first (when used as package)
    from ..base import BettingInterface
    from ...betbot_engine.events import (
        BettingEvent, EventType, SessionStartedEvent, BetResultEvent,
        StatsUpdatedEvent, SessionEndedEvent, WarningEvent, ErrorEvent
    )
    from ...betbot_engine.observers import EventObserver
except ImportError:
    # Fall back to absolute imports (when run from src/)
    from interfaces.base import BettingInterface
    from betbot_engine.events import (
        BettingEvent, EventType, SessionStartedEvent, BetResultEvent,
        StatsUpdatedEvent, SessionEndedEvent, WarningEvent, ErrorEvent
    )
    from betbot_engine.observers import EventObserver


class SessionStats:
    """Track session statistics for display"""
    
    def __init__(self):
        self.bets_placed = 0
        self.wins = 0
        self.losses = 0
        self.current_balance = Decimal(0)
        self.starting_balance = Decimal(0)
        self.profit_loss = Decimal(0)
        self.profit_loss_percent = 0.0
        self.loss_streak = 0
        self.max_loss_streak = 0
        self.last_bet_win = None
        
    def update_from_bet(self, bet_result: BetResultEvent):
        """Update stats from a bet result event"""
        self.bets_placed = bet_result.bet_number
        self.current_balance = bet_result.current_balance
        self.loss_streak = bet_result.loss_streak
        self.max_loss_streak = max(self.max_loss_streak, bet_result.loss_streak)
        
        # Track wins/losses
        if bet_result.result.get('win'):
            self.wins += 1
            self.last_bet_win = True
        else:
            self.losses += 1
            self.last_bet_win = False
            
    def update_from_stats(self, stats: StatsUpdatedEvent):
        """Update stats from a stats update event"""
        self.bets_placed = stats.bets_placed
        self.current_balance = stats.current_balance
        self.profit_loss = stats.profit_loss
        self.profit_loss_percent = stats.profit_loss_percent
        self.loss_streak = stats.loss_streak
        self.max_loss_streak = max(self.max_loss_streak, stats.loss_streak)


class RichInterface(BettingInterface, EventObserver):
    """
    Rich-based CLI interface that implements both BettingInterface and EventObserver.
    
    This class connects to the event-driven engine and provides a beautiful
    terminal UI using the Rich library.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.stats = SessionStats()
        self.strategy_name = ""
        self.symbol = ""
        self.session_start_time: Optional[datetime] = None
        self.live_display: Optional[Live] = None
        
    # ========== EventObserver Implementation ==========
    
    def on_event(self, event: BettingEvent) -> None:
        """Handle events from the engine"""
        if event.event_type == EventType.SESSION_STARTED:
            self._handle_session_started(event)
        elif event.event_type == EventType.BET_RESULT:
            self._handle_bet_result(event)
        elif event.event_type == EventType.STATS_UPDATED:
            self._handle_stats_updated(event)
        elif event.event_type == EventType.SESSION_ENDED:
            self._handle_session_ended(event)
        elif event.event_type == EventType.WARNING:
            self._handle_warning(event)
        elif event.event_type == EventType.ERROR:
            self._handle_error(event)
    
    def _handle_session_started(self, event: SessionStartedEvent) -> None:
        """Handle session start event"""
        data = event.data
        self.strategy_name = data.get('strategy_name', '')
        self.symbol = data.get('currency', '')
        starting_balance_str = data.get('starting_balance', '0')
        self.stats.starting_balance = Decimal(starting_balance_str)
        self.stats.current_balance = Decimal(starting_balance_str)
        self.session_start_time = event.timestamp
        
        self.display_session_start(
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            starting_balance=self.stats.starting_balance,
            params=data.get('config', {})
        )
    
    def _handle_bet_result(self, event: BetResultEvent) -> None:
        """Handle bet result event"""
        data = event.data
        bet_number = data.get('bet_number', 0)
        win = data.get('win', False)
        profit = Decimal(str(data.get('profit', '0')))
        balance = Decimal(str(data.get('balance', '0')))
        
        # Update stats
        self.stats.bets_placed = bet_number
        self.stats.current_balance = balance
        
        if win:
            self.stats.wins += 1
            self.last_bet_win = True
        else:
            self.stats.losses += 1
            self.last_bet_win = False
        
        # Display result
        result = data.get('result', {})
        self.display_bet_result(
            bet_number=bet_number,
            win=win,
            profit=profit,
            balance=balance
        )
    
    def _handle_stats_updated(self, event: StatsUpdatedEvent) -> None:
        """Handle stats update event"""
        data = event.data
        self.stats.bets_placed = data.get('total_bets', 0)
        self.stats.wins = data.get('wins', 0)
        self.stats.losses = data.get('losses', 0)
        self.stats.current_balance = Decimal(str(data.get('current_balance', '0')))
        self.stats.profit_loss = Decimal(str(data.get('profit', '0')))
        self.stats.profit_loss_percent = data.get('profit_percent', 0.0)
        
        # Update live display if active
        if self.live_display:
            self.display_stats(data)
    
    def _handle_session_ended(self, event: SessionEndedEvent) -> None:
        """Handle session end event"""
        data = event.data
        self.display_session_end(
            reason=data.get('stop_reason', 'completed'),
            summary=data.get('summary', {})
        )
    
    def _handle_warning(self, event: WarningEvent) -> None:
        """Handle warning event"""
        data = event.data
        message = data.get('message', 'Unknown warning')
        self.console.print(f"[yellow]⚠️  Warning: {message}[/yellow]")
    
    def _handle_error(self, event: ErrorEvent) -> None:
        """Handle error event"""
        data = event.data
        message = data.get('message', 'Unknown error')
        details = data.get('details', {})
        self.console.print(f"[red]❌ Error: {message}[/red]")
        if details:
            self.console.print(f"[dim]Details: {details}[/dim]")
    
    # ========== BettingInterface Implementation ==========
    
    def initialize(self) -> None:
        """Initialize the interface"""
        pass  # Rich console doesn't need explicit initialization
    
    def shutdown(self) -> None:
        """Clean up the interface"""
        if self.live_display:
            self.live_display.stop()
    
    def display_session_start(
        self,
        strategy_name: str = None,
        symbol: str = None,
        starting_balance: Decimal = None,
        params: Dict[str, Any] = None,
        **kwargs
    ) -> None:
        """Display session start information"""
        # Handle both old and new signatures
        if strategy_name is None:
            strategy_name = kwargs.get('strategy', 'Unknown')
        if symbol is None:
            symbol = kwargs.get('currency', 'Unknown')
        if starting_balance is None:
            starting_balance = kwargs.get('starting_balance', Decimal(0))
        if params is None:
            params = kwargs.get('config', {})
        
        # Create a nice panel with session info
        info_table = Table(show_header=False, box=box.SIMPLE)
        info_table.add_column("Key", style="cyan")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Strategy", strategy_name)
        info_table.add_row("Symbol", symbol)
        info_table.add_row("Starting Balance", f"{starting_balance:,.8f}")
        
        # Add key parameters
        if params:
            info_table.add_row("", "")  # Spacer
            for key, value in params.items():
                info_table.add_row(f"  {key}", str(value))
        
        panel = Panel(
            info_table,
            title="[bold green]🎲 Session Started[/bold green]",
            border_style="green"
        )
        self.console.print(panel)
        self.console.print()
    
    def display_bet_placed(self, bet_number: int, amount: Decimal, chance: float) -> None:
        """Display information about a placed bet"""
        self.console.print(
            f"[dim]Placing bet #{bet_number}: {amount} @ {chance}%[/dim]"
        )
    
    def display_bet_result(
        self,
        bet_number: int = None,
        bet_spec: Dict[str, Any] = None,
        result: Dict[str, Any] = None,
        balance: Decimal = None,
        **kwargs
    ) -> None:
        """Display individual bet result"""
        # Handle both old and new signatures
        if bet_number is None:
            bet_number = kwargs.get('bet_number', 0)
        if result is None:
            # Old signature
            win = kwargs.get('win', False)
            profit = kwargs.get('profit', Decimal(0))
            balance = kwargs.get('balance', Decimal(0))
        else:
            # New signature
            win = result.get('win', False)
            profit = Decimal(str(result.get('profit', '0')))
            if balance is None:
                balance = Decimal(str(result.get('balance', '0')))
        
        if bet_spec is None:
            amount = kwargs.get('amount', '0')
        else:
            amount = bet_spec.get('amount', '0')
        
        # Color based on win/loss
        if win:
            status = "[green]WIN[/green]"
            profit_str = f"[green]+{profit:,.8f}[/green]"
        else:
            status = "[red]LOSS[/red]"
            profit_str = f"[red]{profit:,.8f}[/red]"
        
        # Build output line
        output = (
            f"Bet #{bet_number:<4} {status} "
            f"Amount: {amount:<12} "
            f"Profit: {profit_str:<20} "
            f"Balance: {balance:,.8f}"
        )
        
        self.console.print(output)
    
    def display_stats(self, stats: Dict[str, Any]) -> None:
        """Display current session statistics"""
        # Create stats table
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Metric", style="cyan bold")
        table.add_column("Value", style="white")
        
        # Calculate win rate
        win_rate = (self.stats.wins / self.stats.bets_placed * 100) if self.stats.bets_placed > 0 else 0
        
        table.add_row("Bets Placed", str(self.stats.bets_placed))
        table.add_row("Wins / Losses", f"{self.stats.wins} / {self.stats.losses}")
        table.add_row("Win Rate", f"{win_rate:.2f}%")
        table.add_row("Current Balance", f"{self.stats.current_balance:,.8f}")
        table.add_row("Profit/Loss", f"{self.stats.profit_loss:+,.8f}")
        table.add_row("P/L %", f"{self.stats.profit_loss_percent:+.2f}%")
        table.add_row("Current Streak", str(self.stats.loss_streak))
        table.add_row("Max Streak", str(self.stats.max_loss_streak))
        
        # Show in panel
        panel = Panel(
            table,
            title=f"[bold cyan]📊 {self.strategy_name} - {self.symbol}[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(panel)
    
    def display_session_end(
        self,
        reason: str = None,
        summary: Dict[str, Any] = None
    ) -> None:
        """Display session end summary"""
        if summary is None:
            summary = {}
        if reason is None:
            reason = summary.get('stop_reason', 'completed')
            
        # Create summary table
        table = Table(show_header=False, box=box.DOUBLE)
        table.add_column("Item", style="cyan bold")
        table.add_column("Value", style="white bold")
        
        table.add_row("Stop Reason", reason.replace('_', ' ').title())
        table.add_row("Total Bets", str(summary.get('bets', 0)))
        table.add_row("Duration", f"{summary.get('duration_sec', 0):.2f}s")
        table.add_row("Starting Balance", summary.get('starting_balance', '0'))
        table.add_row("Ending Balance", summary.get('ending_balance', '0'))
        
        profit = Decimal(summary.get('profit', '0'))
        if profit >= 0:
            profit_style = "green bold"
            profit_str = f"+{profit}"
        else:
            profit_style = "red bold"
            profit_str = str(profit)
        
        table.add_row("Profit/Loss", Text(profit_str, style=profit_style))
        
        # Determine panel color based on profit
        border_style = "green" if profit >= 0 else "red"
        title = "[bold green]✅ Session Complete - Profit![/bold green]" if profit >= 0 else "[bold red]❌ Session Complete - Loss[/bold red]"
        
        panel = Panel(
            table,
            title=title,
            border_style=border_style
        )
        self.console.print()
        self.console.print(panel)
    
    def display_warning(self, message: str) -> None:
        """Display a warning message"""
        self.console.print(f"[yellow]⚠️  {message}[/yellow]")
    
    def display_error(self, message: str, details: Optional[str] = None) -> None:
        """Display an error message"""
        self.console.print(f"[red]❌ {message}[/red]")
        if details:
            self.console.print(f"[dim]{details}[/dim]")
    
    def display_info(self, message: str) -> None:
        """Display an informational message"""
        self.console.print(f"[cyan]ℹ️  {message}[/cyan]")
    
    def get_user_input(self, prompt: str, default: Optional[str] = None, options: Optional[list] = None) -> str:
        """Get input from user (blocking)"""
        # This is a blocking operation - not ideal for event-driven architecture
        # But sometimes necessary for interactive CLI
        if options:
            self.console.print(f"\n[cyan]{prompt}[/cyan]")
            for i, option in enumerate(options, 1):
                self.console.print(f"  {i}. {option}")
            result = input("> ")
        else:
            if default:
                result = input(f"{prompt} [{default}]: ") or default
            else:
                result = input(f"{prompt}: ")
        return result
    
    def get_choice(self, prompt: str, choices: list) -> str:
        """Get user choice from a list"""
        self.console.print(f"\n[cyan]{prompt}[/cyan]")
        for i, choice in enumerate(choices, 1):
            self.console.print(f"  {i}. {choice}")
        
        while True:
            try:
                idx = int(input("> ")) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
                else:
                    self.console.print(f"[red]Please enter a number between 1 and {len(choices)}[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number[/red]")
    
    def check_stop_requested(self) -> bool:
        """Check if user has requested to stop"""
        # In a real implementation, this would check for Ctrl+C or other signals
        # For now, just return False (no stop requested)
        return False
    
    def update_progress(self, current: int, total: Optional[int] = None, message: Optional[str] = None) -> None:
        """Update progress indicator"""
        if total:
            pct = (current / total * 100) if total > 0 else 0
            progress_str = f"[{current}/{total}] {pct:.1f}%"
        else:
            progress_str = f"[{current}]"
        
        if message:
            self.console.print(f"[dim]{progress_str} {message}[/dim]")
        else:
            self.console.print(f"[dim]{progress_str}[/dim]")
    
    def clear_screen(self) -> None:
        """Clear the terminal screen"""
        self.console.clear()
    
    def start_live_display(self) -> None:
        """Start a live updating display"""
        # Could implement Rich Live display here for real-time updates
        pass
    
    def stop_live_display(self) -> None:
        """Stop the live updating display"""
        if self.live_display:
            self.live_display.stop()
            self.live_display = None
