"""
Textual-based TUI (Terminal User Interface) for DuckDice Bot.

A modern, interactive terminal interface using the Textual framework.
Provides real-time betting visualization, statistics, and controls.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, Button, Label, 
    DataTable, ProgressBar, Select, Input
)
from textual.reactive import reactive
from textual.binding import Binding
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio


class StatsPanel(Static):
    """Display session statistics."""
    
    balance = reactive(Decimal("0"))
    profit = reactive(Decimal("0"))
    bets_placed = reactive(0)
    wins = reactive(0)
    losses = reactive(0)
    
    def compose(self) -> ComposeResult:
        yield Static("📊 Session Statistics", classes="panel-title")
        yield Static(id="balance-display")
        yield Static(id="profit-display")
        yield Static(id="bets-display")
        yield Static(id="winrate-display")
    
    def watch_balance(self, balance: Decimal) -> None:
        """Update balance display."""
        self.query_one("#balance-display", Static).update(
            f"💰 Balance: {balance:.8f} BTC"
        )
    
    def watch_profit(self, profit: Decimal) -> None:
        """Update profit display."""
        color = "green" if profit >= 0 else "red"
        self.query_one("#profit-display", Static).update(
            f"[{color}]📈 Profit: {profit:+.8f} BTC[/{color}]"
        )
    
    def watch_bets_placed(self, count: int) -> None:
        """Update bets count."""
        self.query_one("#bets-display", Static).update(
            f"🎲 Bets: {count} (W: {self.wins}, L: {self.losses})"
        )
        
        # Update winrate
        if count > 0:
            winrate = (self.wins / count) * 100
            self.query_one("#winrate-display", Static).update(
                f"📊 Win Rate: {winrate:.2f}%"
            )


class BetHistoryTable(DataTable):
    """Display recent bet history."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_columns("Time", "Amount", "Chance", "Roll", "Result", "Profit")
        self.max_rows = 20
    
    def add_bet(self, bet_data: Dict[str, Any]) -> None:
        """Add a bet to the history."""
        result_color = "green" if bet_data['win'] else "red"
        result_text = "✓ WIN" if bet_data['win'] else "✗ LOSS"
        
        row = [
            bet_data.get('time', datetime.now().strftime("%H:%M:%S")),
            f"{bet_data['amount']:.8f}",
            f"{bet_data['chance']:.2f}%",
            f"{bet_data.get('roll', 0):.2f}",
            f"[{result_color}]{result_text}[/{result_color}]",
            f"[{result_color}]{bet_data['profit']:+.8f}[/{result_color}]"
        ]
        
        self.add_row(*row)
        
        # Keep only recent bets
        if self.row_count > self.max_rows:
            self.remove_row(self.rows[0].key)


class ControlPanel(Container):
    """Betting controls and configuration."""
    
    def compose(self) -> ComposeResult:
        yield Static("🎮 Controls", classes="panel-title")
        
        with Horizontal(classes="control-row"):
            yield Label("Strategy:")
            yield Select(
                [
                    ("Martingale", "martingale"),
                    ("Anti-Martingale", "anti_martingale"),
                    ("D'Alembert", "dalembert"),
                    ("Fibonacci", "fibonacci"),
                    ("Flat Betting", "flat"),
                ],
                id="strategy-select",
                value="flat"
            )
        
        with Horizontal(classes="control-row"):
            yield Label("Base Bet:")
            yield Input(placeholder="0.00000100", id="base-bet-input")
        
        with Horizontal(classes="control-row"):
            yield Label("Win Chance:")
            yield Input(placeholder="50.00", id="chance-input")
        
        with Horizontal(classes="control-row"):
            yield Button("▶ Start", id="start-btn", variant="success")
            yield Button("⏸ Pause", id="pause-btn", variant="warning", disabled=True)
            yield Button("⏹ Stop", id="stop-btn", variant="error", disabled=True)


class ProgressPanel(Container):
    """Display betting progress."""
    
    def compose(self) -> ComposeResult:
        yield Static("📈 Progress", classes="panel-title")
        yield ProgressBar(total=100, id="progress-bar", show_percentage=True)
        yield Static("Ready to start", id="status-display")


class DuckDiceTUI(App):
    """
    Main TUI application for DuckDice Bot.
    
    Keyboard shortcuts:
        Ctrl+S: Start/Resume betting
        Ctrl+P: Pause betting
        Ctrl+X: Stop betting
        Ctrl+Q: Quit application
    """
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .panel-title {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }
    
    StatsPanel {
        height: 10;
        border: solid $primary;
        margin: 1;
    }
    
    ControlPanel {
        height: 12;
        border: solid $accent;
        margin: 1;
    }
    
    ProgressPanel {
        height: 7;
        border: solid $success;
        margin: 1;
    }
    
    BetHistoryTable {
        border: solid $warning;
        margin: 1;
    }
    
    .control-row {
        height: 3;
        padding: 1;
    }
    
    Label {
        width: 15;
        content-align: right middle;
    }
    
    Input {
        width: 1fr;
    }
    
    Select {
        width: 1fr;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+s", "start", "Start"),
        Binding("ctrl+p", "pause", "Pause"),
        Binding("ctrl+x", "stop", "Stop"),
        Binding("ctrl+q", "quit", "Quit"),
    ]
    
    TITLE = "🎲 DuckDice Bot - Terminal Interface"
    SUB_TITLE = "Automated betting with real-time monitoring"
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._is_paused = False
        self.session_data = {
            'starting_balance': Decimal("0"),
            'current_balance': Decimal("0"),
            'bets': [],
            'strategy': 'flat',
            'base_bet': Decimal("0.00000100"),
            'win_chance': 50.0,
        }
    
    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()
        
        with Container(id="main-container"):
            # Top row: Stats and Controls
            with Horizontal(id="top-row"):
                yield StatsPanel(id="stats-panel")
                yield ControlPanel(id="control-panel")
            
            # Progress panel
            yield ProgressPanel(id="progress-panel")
            
            # Bet history table
            yield BetHistoryTable(id="bet-history")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the interface."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        
        # Set initial values
        stats = self.query_one("#stats-panel", StatsPanel)
        stats.balance = Decimal("0.01")  # Demo balance
        stats.profit = Decimal("0")
        stats.bets_placed = 0
        stats.wins = 0
        stats.losses = 0
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        if button_id == "start-btn":
            self.action_start()
        elif button_id == "pause-btn":
            self.action_pause()
        elif button_id == "stop-btn":
            self.action_stop()
    
    def action_start(self) -> None:
        """Start or resume betting."""
        if not self._is_running:
            self._is_running = True
            self._is_paused = False
            
            # Update button states
            self.query_one("#start-btn", Button).disabled = True
            self.query_one("#pause-btn", Button).disabled = False
            self.query_one("#stop-btn", Button).disabled = False
            
            # Update status
            self.query_one("#status-display", Static).update(
                "[green]🟢 Betting Active[/green]"
            )
            
            # Start betting simulation (in real app, start actual betting)
            self.run_worker(self.betting_simulation(), exclusive=True)
        elif self._is_paused:
            self._is_paused = False
            self.query_one("#status-display", Static).update(
                "[green]🟢 Betting Resumed[/green]"
            )
    
    def action_pause(self) -> None:
        """Pause betting."""
        if self._is_running and not self._is_paused:
            self._is_paused = True
            self.query_one("#status-display", Static).update(
                "[yellow]⏸ Paused[/yellow]"
            )
    
    def action_stop(self) -> None:
        """Stop betting."""
        if self._is_running:
            self._is_running = False
            self._is_paused = False
            
            # Update button states
            self.query_one("#start-btn", Button).disabled = False
            self.query_one("#pause-btn", Button).disabled = True
            self.query_one("#stop-btn", Button).disabled = True
            
            # Update status
            self.query_one("#status-display", Static).update(
                "[red]⏹ Stopped[/red]"
            )
    
    async def betting_simulation(self) -> None:
        """
        Simulate betting activity for demo purposes.
        In production, this would call the actual betting engine.
        """
        import random
        
        stats = self.query_one("#stats-panel", StatsPanel)
        history = self.query_one("#bet-history", BetHistoryTable)
        progress = self.query_one("#progress-bar", ProgressBar)
        
        bet_count = 0
        max_bets = 100
        
        while self._is_running and bet_count < max_bets:
            if self._is_paused:
                await asyncio.sleep(0.1)
                continue
            
            # Simulate a bet
            bet_amount = Decimal("0.00000100")
            win_chance = 50.0
            roll = random.uniform(0, 100)
            won = roll < win_chance
            profit = bet_amount if won else -bet_amount
            
            # Update stats
            stats.balance += profit
            stats.profit += profit
            stats.bets_placed += 1
            if won:
                stats.wins += 1
            else:
                stats.losses += 1
            
            # Add to history
            history.add_bet({
                'time': datetime.now().strftime("%H:%M:%S"),
                'amount': bet_amount,
                'chance': win_chance,
                'roll': roll,
                'win': won,
                'profit': profit
            })
            
            # Update progress
            bet_count += 1
            progress.update(progress=(bet_count / max_bets) * 100)
            
            # Wait between bets
            await asyncio.sleep(0.5)
        
        # Auto-stop when complete
        if bet_count >= max_bets:
            self.action_stop()
            self.query_one("#status-display", Static).update(
                "[blue]✓ Session Complete[/blue]"
            )


def run_tui():
    """Launch the TUI application."""
    app = DuckDiceTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
