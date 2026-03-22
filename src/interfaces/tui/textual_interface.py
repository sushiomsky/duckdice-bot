"""
Textual-based TUI (Terminal User Interface) for DuckDice Bot.

A modern, interactive terminal interface using the Textual framework.
Provides real-time betting visualization, statistics, and controls.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, cast

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    Static,
)

try:
    from ...betbot_engine.events import EventType
    from ...betbot_strategies import get_strategy, list_strategies
    from .runtime_controller import RuntimeRequest, TextualRuntimeController
except ImportError:
    import os
    import sys

    # Support direct execution paths like: python src/interfaces/tui/textual_interface.py
    if __package__ in (None, ""):
        src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if src_root not in sys.path:
            sys.path.insert(0, src_root)
    from betbot_engine.events import EventType
    from betbot_strategies import get_strategy, list_strategies
    from interfaces.tui.runtime_controller import RuntimeRequest, TextualRuntimeController


class StatsPanel(Static):
    """Display session statistics."""
    
    balance = reactive(Decimal("0"))
    profit = reactive(Decimal("0"))
    bets_placed = reactive(0)
    wins = reactive(0)
    losses = reactive(0)
    currency = reactive("BTC")
    
    def compose(self) -> ComposeResult:
        yield Static("📊 Session Statistics", classes="panel-title")
        yield Static(id="balance-display")
        yield Static(id="profit-display")
        yield Static(id="bets-display")
        yield Static(id="winrate-display")
    
    def watch_balance(self, balance: Decimal) -> None:
        """Update balance display."""
        self.query_one("#balance-display", Static).update(
            f"💰 Balance: {balance:.8f} {self.currency}"
        )
    
    def watch_profit(self, profit: Decimal) -> None:
        """Update profit display."""
        color = "green" if profit >= 0 else "red"
        self.query_one("#profit-display", Static).update(
            f"[{color}]📈 Profit: {profit:+.8f} {self.currency}[/{color}]"
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


class EventLogTable(DataTable):
    """Display runtime event log."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_columns("Time", "Level", "Event", "Message")
        self.max_rows = 30

    def add_event(self, level: str, event_name: str, message: str, when: Optional[datetime] = None) -> None:
        timestamp = (when or datetime.now()).strftime("%H:%M:%S")
        level_upper = level.upper()
        level_color = {
            "ERROR": "red",
            "WARNING": "yellow",
            "INFO": "cyan",
        }.get(level_upper, "white")
        row = [
            timestamp,
            f"[{level_color}]{level_upper}[/{level_color}]",
            event_name,
            message,
        ]
        self.add_row(*row)
        if self.row_count > self.max_rows:
            self.remove_row(self.rows[0].key)


class ControlPanel(Container):
    """Betting controls and configuration."""
    
    def compose(self) -> ComposeResult:
        yield Static("🎮 Controls", classes="panel-title")
        
        with Horizontal(classes="control-row"):
            yield Label("Strategy:")
            yield Select(
                [],
                id="strategy-select",
                value=Select.BLANK,
            )
        
        with Horizontal(classes="control-row"):
            yield Label("Symbol:")
            yield Select(
                [
                    ("BTC", "BTC"),
                    ("ETH", "ETH"),
                    ("DOGE", "DOGE"),
                    ("LTC", "LTC"),
                    ("XRP", "XRP"),
                    ("TRX", "TRX"),
                    ("SOL", "SOL"),
                ],
                id="symbol-select",
                value="BTC",
            )

        with Horizontal(classes="control-row"):
            yield Label("Base Bet:")
            yield Input(placeholder="0.00000100", id="base-bet-input")
        
        with Horizontal(classes="control-row"):
            yield Label("Win Chance:")
            yield Input(placeholder="50.00", id="chance-input")

        with Horizontal(classes="control-row"):
            yield Label("Mode:")
            yield Select(
                [
                    ("Simulation", "simulation"),
                    ("Live (Main)", "live-main"),
                    ("Live (Faucet)", "live-faucet"),
                    ("Live (TLE)", "live-tle"),
                ],
                id="mode-select",
                value="simulation",
            )

        with Horizontal(classes="control-row"):
            yield Label("TLE Hash:")
            yield Input(placeholder="Required for Live (TLE)", id="tle-hash-input")

        with Horizontal(classes="control-row"):
            yield Label("Start Balance:")
            yield Input(placeholder="100.0 (simulation only)", id="start-balance-input")

        with Horizontal(classes="control-row"):
            yield Label("Max Bets:")
            yield Input(placeholder="100", id="max-bets-input")

        with Horizontal(classes="control-row"):
            yield Label("Stop Loss:")
            yield Input(placeholder="-0.02", id="stop-loss-input")

        with Horizontal(classes="control-row"):
            yield Label("Take Profit:")
            yield Input(placeholder="0.02", id="take-profit-input")

        with Horizontal(classes="control-row"):
            yield Button("▶ Start", id="start-btn", variant="success")
            yield Button("⏹ Stop", id="stop-btn", variant="error", disabled=True)


class ProgressPanel(Container):
    """Display betting progress."""
    
    def compose(self) -> ComposeResult:
        yield Static("📈 Progress", classes="panel-title")
        yield ProgressBar(total=100, id="progress-bar", show_percentage=True)
        yield Static("Ready to start", id="status-display")
        yield Static("Reason: waiting", id="reason-display")
        yield Static("Risk: n/a", id="risk-display")
        yield Static("Analytics: n/a", id="analytics-display")
        yield Static("Strategy: n/a", id="strategy-display")
        yield Static("Schema: n/a", id="schema-display")
        yield Static("Summary: n/a", id="summary-display")


class DuckDiceTUI(App):
    """
    Main TUI application for DuckDice Bot.
    
    Keyboard shortcuts:
        Ctrl+S: Start betting
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
        height: 28;
        border: solid $accent;
        margin: 1;
    }
    
    ProgressPanel {
        height: 10;
        border: solid $success;
        margin: 1;
    }
    
    BetHistoryTable {
        border: solid $warning;
        margin: 1;
    }

    EventLogTable {
        height: 10;
        border: solid $secondary;
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
        Binding("ctrl+x", "stop", "Stop"),
        Binding("ctrl+q", "quit", "Quit"),
    ]
    
    TITLE = "🎲 DuckDice Bot - Terminal Interface"
    SUB_TITLE = "Automated betting with real-time monitoring"
    
    def __init__(self):
        super().__init__()
        self._controller = TextualRuntimeController()
        self._is_running = False
        self.session_data = {
            'starting_balance': Decimal("0"),
            'current_balance': Decimal("0"),
            'bets': [],
            'strategy': '',
            'strategy_desc': '',
            'base_bet': Decimal("0.00000100"),
            'win_chance': 50.0,
            'max_bets': 100,
            'symbol': 'BTC',
            'stop_loss': -0.02,
            'take_profit': 0.02,
            'current_win_streak': 0,
            'current_loss_streak': 0,
            'max_win_streak': 0,
            'max_loss_streak': 0,
            'total_bet_amount': Decimal("0"),
            'total_profit_amount': Decimal("0"),
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
            yield EventLogTable(id="event-log")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the interface."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        self.set_interval(0.15, self._process_runtime_events)
        
        # Set initial values
        stats = self.query_one("#stats-panel", StatsPanel)
        stats.balance = Decimal("100.0")
        stats.currency = "BTC"
        stats.profit = Decimal("0")
        stats.bets_placed = 0
        stats.wins = 0
        stats.losses = 0
        self.query_one("#strategy-display", Static).update("Strategy: n/a")
        self.query_one("#schema-display", Static).update("Schema: n/a")
        self.query_one("#risk-display", Static).update("Risk: stop_loss=-0.02, take_profit=0.02")
        self.query_one("#analytics-display", Static).update("Analytics: n/a")
        self.query_one("#summary-display", Static).update("Summary: n/a")
        self.query_one("#start-balance-input", Input).value = "100.0"
        self.query_one("#max-bets-input", Input).value = "100"
        self.query_one("#stop-loss-input", Input).value = "-0.02"
        self.query_one("#take-profit-input", Input).value = "0.02"
        self._load_strategies()
        self._apply_mode_field_rules()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        if button_id == "start-btn":
            self.action_start()
        elif button_id == "stop-btn":
            self.action_stop()
    
    def action_start(self) -> None:
        """Start betting."""
        if self._is_running:
            return

        try:
            request = self._build_runtime_request()
            self._controller.start(request)
            self._is_running = True
            self._set_controls_running(True)
            self._set_status("[green]🟢 Session starting...[/green]", "boot")
            self._reset_session_view()
            self._append_event_log("info", "session", "Start requested")
        except Exception as exc:
            self.notify(f"Start failed: {exc}", severity="error")
            self._set_status("[red]❌ Start failed[/red]", str(exc))
            self._append_event_log("error", "start_failed", str(exc))
    
    def action_stop(self) -> None:
        """Stop betting."""
        if not self._is_running:
            return

        self._controller.request_stop()
        self._set_status("[yellow]⏹ Stop requested...[/yellow]", "user_stop")
        self._append_event_log("warning", "session", "Stop requested by user")

    def _load_strategies(self) -> None:
        strategy_select = self.query_one("#strategy-select", Select)
        strategies = list_strategies()
        options = [(item["name"], item["name"]) for item in strategies]
        if not options:
            options = [("combined-high-roller", "combined-high-roller")]
        strategy_select.set_options(options)
        strategy_select.value = options[0][1]
        self._update_strategy_preview(options[0][1])

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "strategy-select":
            value = cast(Optional[str], event.value)
            if value and value != Select.BLANK:
                self._update_strategy_preview(value)
        elif event.select.id == "mode-select":
            self._apply_mode_field_rules()

    def _update_strategy_preview(self, strategy_name: str) -> None:
        try:
            cls = get_strategy(strategy_name)
            desc = cls.describe() if hasattr(cls, "describe") else ""
            schema = cls.schema() if hasattr(cls, "schema") else {}
            self.session_data["strategy"] = strategy_name
            self.session_data["strategy_desc"] = desc or ""
            short_desc = (desc or "").strip()
            if len(short_desc) > 110:
                short_desc = short_desc[:107] + "..."
            text = f"Strategy: {strategy_name}"
            if short_desc:
                text += f" | {short_desc}"
            self.query_one("#strategy-display", Static).update(text)
            self.query_one("#schema-display", Static).update(
                f"Schema: {self._schema_preview_text(schema)}"
            )
            self._hydrate_inputs_from_schema(schema)
        except Exception:
            self.query_one("#strategy-display", Static).update(f"Strategy: {strategy_name}")
            self.query_one("#schema-display", Static).update("Schema: n/a")

    def _schema_preview_text(self, schema: Dict[str, Any]) -> str:
        if not schema:
            return "n/a"
        keys = list(schema.keys())[:4]
        parts = []
        for key in keys:
            field = schema.get(key, {})
            parts.append(f"{key}={field.get('default')}")
        return ", ".join(parts)

    def _hydrate_inputs_from_schema(self, schema: Dict[str, Any]) -> None:
        base_input = self.query_one("#base-bet-input", Input)
        chance_input = self.query_one("#chance-input", Input)

        if not base_input.value.strip():
            for key in ("base_bet", "base_amount", "min_bet", "min_amount"):
                if key in schema:
                    default = schema[key].get("default")
                    if default not in (None, ""):
                        base_input.value = str(default)
                        break

        if not chance_input.value.strip():
            for key in ("chance", "target_chance"):
                if key in schema:
                    default = schema[key].get("default")
                    if default not in (None, ""):
                        chance_input.value = str(default)
                        break

    def _build_runtime_request(self) -> RuntimeRequest:
        strategy_select = self.query_one("#strategy-select", Select)
        mode_select = self.query_one("#mode-select", Select)
        symbol_select = self.query_one("#symbol-select", Select)
        base_input = self.query_one("#base-bet-input", Input)
        chance_input = self.query_one("#chance-input", Input)
        tle_hash_input = self.query_one("#tle-hash-input", Input)
        start_balance_input = self.query_one("#start-balance-input", Input)
        max_bets_input = self.query_one("#max-bets-input", Input)
        stop_loss_input = self.query_one("#stop-loss-input", Input)
        take_profit_input = self.query_one("#take-profit-input", Input)

        strategy_name = cast(Optional[str], strategy_select.value)
        if not strategy_name or strategy_name == Select.BLANK:
            raise ValueError("Select a strategy first")

        mode = cast(Optional[str], mode_select.value) or "simulation"
        symbol = cast(Optional[str], symbol_select.value) or "BTC"
        tle_hash = (tle_hash_input.value or "").strip() or None
        if mode == "live-tle" and not tle_hash:
            raise ValueError("TLE hash is required for Live (TLE) mode")

        start_balance = (start_balance_input.value or "").strip() or "100.0"
        try:
            Decimal(start_balance)
        except Exception as exc:
            raise ValueError("Start Balance must be a valid decimal") from exc
        if mode != "simulation":
            start_balance = "0"

        max_bets_raw = (max_bets_input.value or "").strip() or str(self.session_data["max_bets"])
        try:
            max_bets = int(max_bets_raw)
            if max_bets <= 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Max Bets must be a positive integer") from exc

        stop_loss_raw = (stop_loss_input.value or "").strip() or str(self.session_data["stop_loss"])
        take_profit_raw = (take_profit_input.value or "").strip() or str(self.session_data["take_profit"])
        try:
            stop_loss = float(stop_loss_raw)
        except ValueError as exc:
            raise ValueError("Stop Loss must be a float (e.g. -0.02)") from exc
        try:
            take_profit = float(take_profit_raw)
        except ValueError as exc:
            raise ValueError("Take Profit must be a float (e.g. 0.02)") from exc

        params = self._build_strategy_params(
            strategy_name=strategy_name,
            base_bet_text=(base_input.value or "").strip(),
            chance_text=(chance_input.value or "").strip(),
        )

        self.session_data["max_bets"] = max_bets
        self.session_data["symbol"] = symbol
        self.session_data["stop_loss"] = stop_loss
        self.session_data["take_profit"] = take_profit

        return RuntimeRequest(
            strategy_name=strategy_name,
            strategy_params=params,
            mode=mode,
            symbol=symbol,
            start_balance=start_balance,
            max_bets=max_bets,
            stop_loss=stop_loss,
            take_profit=take_profit,
            tle_hash=tle_hash,
        )

    def _build_strategy_params(
        self,
        strategy_name: str,
        base_bet_text: str,
        chance_text: str,
    ) -> Dict[str, Any]:
        strategy_cls = get_strategy(strategy_name)
        schema = strategy_cls.schema() if hasattr(strategy_cls, "schema") else {}
        params: Dict[str, Any] = {}

        for key, field in schema.items():
            params[key] = field.get("default")

        if base_bet_text:
            if "base_bet" in params:
                params["base_bet"] = base_bet_text
            elif "base_amount" in params:
                params["base_amount"] = base_bet_text
            elif "min_bet" in params:
                params["min_bet"] = base_bet_text
            elif "min_amount" in params:
                params["min_amount"] = base_bet_text
        if chance_text:
            if "chance" in params:
                params["chance"] = chance_text
            elif "target_chance" in params:
                try:
                    params["target_chance"] = float(chance_text)
                except ValueError:
                    pass

        return params

    def _reset_session_view(self) -> None:
        stats = self.query_one("#stats-panel", StatsPanel)
        history = self.query_one("#bet-history", BetHistoryTable)
        event_log = self.query_one("#event-log", EventLogTable)
        progress = self.query_one("#progress-bar", ProgressBar)

        stats.profit = Decimal("0")
        stats.bets_placed = 0
        stats.wins = 0
        stats.losses = 0
        stats.balance = Decimal("0")
        history.clear()
        event_log.clear()
        progress.update(progress=0)
        self.session_data["current_win_streak"] = 0
        self.session_data["current_loss_streak"] = 0
        self.session_data["max_win_streak"] = 0
        self.session_data["max_loss_streak"] = 0
        self.session_data["total_bet_amount"] = Decimal("0")
        self.session_data["total_profit_amount"] = Decimal("0")
        self.query_one("#analytics-display", Static).update("Analytics: n/a")
        self.query_one("#summary-display", Static).update("Summary: n/a")

    def _set_controls_running(self, running: bool) -> None:
        self.query_one("#start-btn", Button).disabled = running
        self.query_one("#stop-btn", Button).disabled = not running
        self.query_one("#strategy-select", Select).disabled = running
        self.query_one("#symbol-select", Select).disabled = running
        self.query_one("#mode-select", Select).disabled = running
        self.query_one("#base-bet-input", Input).disabled = running
        self.query_one("#chance-input", Input).disabled = running
        self.query_one("#tle-hash-input", Input).disabled = running
        self.query_one("#start-balance-input", Input).disabled = running
        self.query_one("#max-bets-input", Input).disabled = running
        self.query_one("#stop-loss-input", Input).disabled = running
        self.query_one("#take-profit-input", Input).disabled = running
        if not running:
            self._apply_mode_field_rules()

    def _apply_mode_field_rules(self) -> None:
        if self._is_running:
            return
        mode_select = self.query_one("#mode-select", Select)
        mode = cast(Optional[str], mode_select.value) or "simulation"

        tle_hash_input = self.query_one("#tle-hash-input", Input)
        start_balance_input = self.query_one("#start-balance-input", Input)

        is_tle = mode == "live-tle"
        is_sim = mode == "simulation"

        tle_hash_input.disabled = not is_tle
        if not is_tle:
            tle_hash_input.value = ""

        start_balance_input.disabled = not is_sim
        if is_sim and not start_balance_input.value.strip():
            start_balance_input.value = "100.0"

    def _set_status(self, status: str, reason: str) -> None:
        self.query_one("#status-display", Static).update(status)
        self.query_one("#reason-display", Static).update(f"Reason: {reason}")
        self._update_risk_display(self.session_data.get("current_balance", Decimal("0")))

    def _update_analytics_display(self) -> None:
        bets = int(self.query_one("#stats-panel", StatsPanel).bets_placed)
        if bets <= 0:
            self.query_one("#analytics-display", Static).update("Analytics: n/a")
            return
        total_bet_amount: Decimal = self.session_data.get("total_bet_amount", Decimal("0"))
        total_profit_amount: Decimal = self.session_data.get("total_profit_amount", Decimal("0"))
        avg_bet = total_bet_amount / Decimal(bets)
        avg_pl = total_profit_amount / Decimal(bets)
        text = (
            "Analytics: "
            f"WS={self.session_data['current_win_streak']} "
            f"LS={self.session_data['current_loss_streak']} "
            f"MaxWS={self.session_data['max_win_streak']} "
            f"MaxLS={self.session_data['max_loss_streak']} "
            f"AvgBet={avg_bet:.8f} AvgP/L={avg_pl:+.8f}"
        )
        self.query_one("#analytics-display", Static).update(text)

    def _update_risk_display(self, current_balance: Decimal) -> None:
        start = self.session_data.get("starting_balance", Decimal("0"))
        stop_loss = float(self.session_data.get("stop_loss", -0.02))
        take_profit = float(self.session_data.get("take_profit", 0.02))
        if start <= 0:
            self.query_one("#risk-display", Static).update(
                f"Risk: stop_loss={stop_loss}, take_profit={take_profit}"
            )
            return

        drawdown_pct = float((start - current_balance) / start * Decimal("100"))
        pnl_pct = float((current_balance - start) / start * Decimal("100"))
        stop_balance = start * (Decimal("1") + Decimal(str(stop_loss)))
        target_balance = start * (Decimal("1") + Decimal(str(take_profit)))
        self.query_one("#risk-display", Static).update(
            "Risk: "
            f"DD={drawdown_pct:+.2f}% PnL={pnl_pct:+.2f}% "
            f"SL@{stop_balance:.8f} TP@{target_balance:.8f}"
        )

    def _append_event_log(self, level: str, event_name: str, message: str, ts: Optional[float] = None) -> None:
        event_log = self.query_one("#event-log", EventLogTable)
        when = datetime.fromtimestamp(ts) if ts is not None else None
        event_log.add_event(level=level, event_name=event_name, message=message, when=when)

    def _render_summary(self, summary: Dict[str, Any], stop_reason: str) -> None:
        bets = summary.get("bets", 0)
        profit = summary.get("profit", "0")
        ending = summary.get("ending_balance", "0")
        text = f"Summary: bets={bets}, profit={profit}, end={ending}, reason={stop_reason}"
        self.query_one("#summary-display", Static).update(text)
        self._append_event_log("info", "summary", text)

    def _process_runtime_events(self) -> None:
        events = self._controller.poll_events()
        if not events:
            return

        stats = self.query_one("#stats-panel", StatsPanel)
        history = self.query_one("#bet-history", BetHistoryTable)
        progress = self.query_one("#progress-bar", ProgressBar)
        max_bets = self.session_data["max_bets"]

        for event in events:
            if event.event_type == EventType.SESSION_STARTED:
                starting_balance = Decimal(str(event.data.get("starting_balance", "0")))
                currency = str(event.data.get("currency", self.session_data["symbol"]))
                self.session_data["starting_balance"] = starting_balance
                self.session_data["current_balance"] = starting_balance
                stats.balance = starting_balance
                stats.currency = currency
                self.session_data["symbol"] = currency
                self._set_status("[green]🟢 Betting Active[/green]", "session_started")
                self._update_risk_display(starting_balance)
                self._append_event_log(
                    "info",
                    "session_started",
                    f"strategy={self.session_data.get('strategy','?')} symbol={currency} start={starting_balance}",
                    event.timestamp,
                )

            elif event.event_type == EventType.BET_RESULT:
                data = event.data
                result = data.get("result", {}) or {}
                profit = Decimal(str(data.get("profit", "0")))
                balance = Decimal(str(data.get("balance", "0")))
                win = bool(data.get("win", False))
                bet_number = int(data.get("bet_number", 0))

                self.session_data["current_balance"] = balance
                stats.balance = balance
                stats.profit = balance - self.session_data["starting_balance"]
                if win:
                    stats.wins += 1
                else:
                    stats.losses += 1
                stats.bets_placed = bet_number

                amount_text = result.get("api_raw", {}).get("bet", {}).get("amount")
                amount = Decimal(str(amount_text)) if amount_text is not None else abs(profit)
                chance_text = result.get("chance") or "50"
                try:
                    chance_value = float(chance_text)
                except (TypeError, ValueError):
                    chance_value = 50.0
                roll = result.get("number", 0)

                history.add_bet(
                    {
                        "time": datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S"),
                        "amount": amount,
                        "chance": chance_value,
                        "roll": roll,
                        "win": win,
                        "profit": profit,
                    }
                )

                self.session_data["total_bet_amount"] = (
                    self.session_data.get("total_bet_amount", Decimal("0")) + amount
                )
                self.session_data["total_profit_amount"] = (
                    self.session_data.get("total_profit_amount", Decimal("0")) + profit
                )
                if win:
                    self.session_data["current_win_streak"] += 1
                    self.session_data["current_loss_streak"] = 0
                    self.session_data["max_win_streak"] = max(
                        self.session_data["max_win_streak"],
                        self.session_data["current_win_streak"],
                    )
                else:
                    self.session_data["current_loss_streak"] += 1
                    self.session_data["current_win_streak"] = 0
                    self.session_data["max_loss_streak"] = max(
                        self.session_data["max_loss_streak"],
                        self.session_data["current_loss_streak"],
                    )

                progress.update(progress=min(100.0, (bet_number / max_bets) * 100))
                self._update_risk_display(balance)
                self._update_analytics_display()

            elif event.event_type == EventType.STATS_UPDATED:
                data = event.data
                stats.wins = int(data.get("wins", stats.wins))
                stats.losses = int(data.get("losses", stats.losses))
                stats.bets_placed = int(data.get("total_bets", stats.bets_placed))
                stats.balance = Decimal(str(data.get("current_balance", stats.balance)))
                stats.profit = Decimal(str(data.get("profit", stats.profit)))
                if stats.bets_placed and stats.bets_placed % 25 == 0:
                    self._append_event_log(
                        "info",
                        "stats",
                        f"bets={stats.bets_placed} wins={stats.wins} losses={stats.losses}",
                        event.timestamp,
                    )

            elif event.event_type == EventType.WARNING:
                warning_msg = str(event.data.get("message", "Warning"))
                self.notify(warning_msg, severity="warning")
                self._append_event_log("warning", "warning", warning_msg, event.timestamp)

            elif event.event_type == EventType.ERROR:
                message = str(event.data.get("message", "Error"))
                details = str(event.data.get("exception_message", ""))
                self.notify(f"{message}: {details}".strip(": "), severity="error")
                self._set_status("[red]❌ Runtime error[/red]", message)
                self._append_event_log("error", "error", f"{message}: {details}".strip(": "), event.timestamp)
                self._is_running = False
                self._set_controls_running(False)

            elif event.event_type == EventType.SESSION_ENDED:
                stop_reason = str(event.data.get("stop_reason", "completed"))
                summary = event.data.get("summary", {}) or {}
                self._is_running = False
                self._set_controls_running(False)
                self._set_status("[blue]✓ Session Complete[/blue]", stop_reason)
                progress.update(progress=100.0)
                self._render_summary(summary, stop_reason)
                self._append_event_log("info", "session_ended", f"reason={stop_reason}", event.timestamp)

            elif event.event_type == EventType.INFO:
                message = str(event.data.get("message", "info"))
                self._append_event_log("info", "info", message, event.timestamp)

        if self._is_running and not self._controller.is_running:
            self._is_running = False
            self._set_controls_running(False)
            if self._controller.summary:
                self._render_summary(self._controller.summary, "completed")
                self._set_status("[blue]✓ Session Complete[/blue]", "completed")
            else:
                self._append_event_log("warning", "runtime", "Session thread ended without summary")


def run_tui():
    """Launch the TUI application."""
    app = DuckDiceTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
