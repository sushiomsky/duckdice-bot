"""
Enhanced simulator page with full metrics and risk analysis.
"""

from nicegui import ui, app
from decimal import Decimal
from pathlib import Path
import asyncio
import json
from datetime import datetime

from src.simulator import (
    SimulationEngine,
    MetricsCalculator,
    RiskAnalyzer,
)
from src.script_system import ScriptLoader
from app.ui.components import card


class SimulatorController:
    """Controller for simulation page."""
    
    def __init__(self):
        """Initialize simulator controller."""
        self.engine: SimulationEngine | None = None
        self.running = False
        self.paused = False
        
        # UI elements (will be set during render)
        self.balance_label = None
        self.profit_label = None
        self.bets_label = None
        self.win_rate_label = None
        self.progress_bar = None
        self.metrics_container = None
        self.risk_container = None
        
    async def start_simulation(
        self,
        starting_balance: float,
        currency: str,
        house_edge: float,
        max_bets: int,
        strategy_name: str,
        seed: int | None,
    ):
        """Start simulation."""
        if self.running:
            ui.notify('Simulation already running', type='warning')
            return
        
        self.running = True
        self.paused = False
        
        # Create engine
        self.engine = SimulationEngine(
            starting_balance=starting_balance,
            currency=currency,
            house_edge=house_edge,
            seed=seed,
        )
        
        # Simple strategy: fixed bet at 50% chance
        # TODO: Load actual strategy from script system
        bet_amount = starting_balance * 0.01  # 1% of balance
        
        ui.notify(f'Starting simulation: {max_bets} bets', type='positive')
        
        for i in range(max_bets):
            if not self.running:
                break
            
            while self.paused:
                await asyncio.sleep(0.1)
            
            # Execute bet
            try:
                bet = self.engine.execute_bet(
                    amount=bet_amount,
                    chance=50.0,
                    roll_over=True,
                )
                
                # Update UI every 10 bets or on last bet
                if (i + 1) % 10 == 0 or i == max_bets - 1:
                    self._update_display()
                    await asyncio.sleep(0.01)  # Allow UI to update
                
            except ValueError as e:
                ui.notify(f'Simulation stopped: {e}', type='warning')
                break
        
        # Final update
        self.running = False
        self._update_display()
        self._show_final_results()
        
        ui.notify('Simulation complete', type='positive')
    
    def stop_simulation(self):
        """Stop simulation."""
        if not self.running:
            return
        self.running = False
        ui.notify('Simulation stopped', type='info')
    
    def pause_simulation(self):
        """Pause/resume simulation."""
        if not self.running:
            return
        self.paused = not self.paused
        status = 'paused' if self.paused else 'resumed'
        ui.notify(f'Simulation {status}', type='info')
    
    def reset_simulation(self):
        """Reset simulation."""
        if self.engine:
            self.engine.reset()
        self.running = False
        self.paused = False
        self._update_display()
        ui.notify('Simulation reset', type='info')
    
    def _update_display(self):
        """Update display elements."""
        if not self.engine:
            return
        
        balance = self.engine.get_balance()
        profit_loss = self.engine.get_profit_loss()
        bet_count = self.engine.get_bet_count()
        
        # Update labels
        if self.balance_label:
            self.balance_label.text = f'${balance:.4f}'
            # Color code profit/loss
            if profit_loss > 0:
                self.balance_label.classes(remove='text-red-400 text-white', add='text-green-400')
            elif profit_loss < 0:
                self.balance_label.classes(remove='text-green-400 text-white', add='text-red-400')
            else:
                self.balance_label.classes(remove='text-green-400 text-red-400', add='text-white')
        
        if self.profit_label:
            sign = '+' if profit_loss > 0 else ''
            pct = float(profit_loss / self.engine.config.starting_balance * 100)
            self.profit_label.text = f'{sign}${profit_loss:.4f} ({sign}{pct:.2f}%)'
            if profit_loss > 0:
                self.profit_label.classes(remove='text-red-400 text-slate-300', add='text-green-400')
            elif profit_loss < 0:
                self.profit_label.classes(remove='text-green-400 text-slate-300', add='text-red-400')
            else:
                self.profit_label.classes(remove='text-green-400 text-red-400', add='text-slate-300')
        
        if self.bets_label:
            history = self.engine.get_history()
            wins = sum(1 for bet in history if bet.won)
            losses = len(history) - wins
            win_rate = (wins / len(history) * 100) if history else 0
            self.bets_label.text = f'{bet_count} bets'
            if self.win_rate_label:
                self.win_rate_label.text = f'{wins}W / {losses}L ({win_rate:.1f}%)'
    
    def _show_final_results(self):
        """Show final metrics and risk analysis."""
        if not self.engine:
            return
        
        history = self.engine.get_history()
        if not history:
            return
        
        # Calculate metrics
        metrics = MetricsCalculator.calculate(
            history,
            self.engine.config.starting_balance
        )
        
        # Calculate risk
        risk = RiskAnalyzer.analyze(
            history,
            self.engine.config.starting_balance
        )
        
        # Update metrics container
        if self.metrics_container:
            self.metrics_container.clear()
            with self.metrics_container:
                self._render_metrics(metrics)
        
        # Update risk container
        if self.risk_container:
            self.risk_container.clear()
            with self.risk_container:
                self._render_risk(risk)
    
    def _render_metrics(self, metrics):
        """Render performance metrics."""
        ui.label('Performance Metrics').classes('text-lg font-semibold mb-3')
        
        with ui.grid(columns=3).classes('gap-4 w-full'):
            # Row 1
            self._metric_card('Total Bets', str(metrics.total_bets))
            self._metric_card('Wins', f'{metrics.wins} ({metrics.win_rate:.1f}%)')
            self._metric_card('Losses', str(metrics.losses))
            
            # Row 2
            self._metric_card('Total Wagered', f'${metrics.total_wagered:.2f}')
            self._metric_card('Profit/Loss', f'${metrics.profit_loss:.4f}')
            self._metric_card('ROI', f'{metrics.roi:.2f}%')
            
            # Row 3
            self._metric_card('Max Win Streak', str(metrics.max_win_streak))
            self._metric_card('Max Loss Streak', str(metrics.max_loss_streak))
            self._metric_card('Profit Factor', f'{metrics.profit_factor:.4f}')
            
            # Row 4
            self._metric_card('Avg Bet Size', f'${metrics.avg_bet_size:.4f}')
            self._metric_card('Avg Win', f'${metrics.avg_win_amount:.4f}')
            self._metric_card('Avg Loss', f'${metrics.avg_loss_amount:.4f}')
    
    def _render_risk(self, risk):
        """Render risk analysis."""
        ui.label('Risk Analysis').classes('text-lg font-semibold mb-3')
        
        with ui.grid(columns=2).classes('gap-4 w-full'):
            # Row 1
            self._metric_card('Peak Balance', f'${risk.peak_balance:.4f}')
            self._metric_card('Max Drawdown', f'${risk.max_drawdown:.4f} ({risk.max_drawdown_pct:.2f}%)')
            
            # Row 2
            self._metric_card('Current Drawdown', f'${risk.current_drawdown:.4f} ({risk.current_drawdown_pct:.2f}%)')
            self._metric_card('Variance', f'{risk.variance:.6f}')
            
            # Row 3
            self._metric_card('Std Deviation', f'{risk.std_deviation:.6f}')
            self._metric_card('Risk of Ruin', f'{risk.risk_of_ruin:.4f} ({risk.risk_of_ruin*100:.2f}%)')
            
            # Row 4 (full width)
            with ui.column().classes('col-span-2'):
                self._metric_card('Suggested Bankroll', f'${risk.suggested_bankroll:.2f}')
    
    def _metric_card(self, label: str, value: str):
        """Render a metric card."""
        with ui.card().classes('p-3 bg-slate-700'):
            ui.label(label).classes('text-xs text-slate-400 mb-1')
            ui.label(value).classes('text-sm font-mono font-semibold')
    
    def export_results(self):
        """Export simulation results."""
        if not self.engine or not self.engine.get_history():
            ui.notify('No simulation data to export', type='warning')
            return
        
        # Calculate metrics and risk
        history = self.engine.get_history()
        metrics = MetricsCalculator.calculate(history, self.engine.config.starting_balance)
        risk = RiskAnalyzer.analyze(history, self.engine.config.starting_balance)
        
        # Create export data
        export_data = {
            'simulation_config': {
                'starting_balance': str(self.engine.config.starting_balance),
                'currency': self.engine.config.currency,
                'house_edge': self.engine.config.house_edge,
                'seed': self.engine.config.seed,
            },
            'summary': {
                'total_bets': metrics.total_bets,
                'final_balance': str(self.engine.get_balance()),
                'profit_loss': str(metrics.profit_loss),
                'roi': metrics.roi,
            },
            'metrics': metrics.to_dict(),
            'risk_analysis': risk.to_dict(),
            'bets': [bet.to_dict() for bet in history],
            'exported_at': datetime.now().isoformat(),
        }
        
        # Save to file
        filename = f'simulation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        filepath = Path('bet_history') / filename
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        ui.notify(f'Results exported to {filename}', type='positive')


def simulator_content() -> None:
    """Render simulator page content."""
    controller = SimulatorController()
    
    ui.label('🧪 Simulator').classes('text-3xl font-bold')
    ui.label('Test strategies risk-free with virtual balance').classes('text-sm text-slate-400 mb-6')
    
    # Configuration
    with card():
        ui.label('Configuration').classes('text-xl font-semibold mb-4')
        
        with ui.row().classes('gap-4 w-full items-end'):
            starting_balance = ui.number(
                label='Starting Balance',
                value=100.0,
                min=1.0,
                format='%.2f'
            ).classes('flex-1')
            
            currency = ui.select(
                ['USD', 'BTC', 'ETH', 'LTC', 'DOGE'],
                value='USD',
                label='Currency'
            ).classes('w-32')
            
            house_edge = ui.number(
                label='House Edge %',
                value=3.0,
                min=0.0,
                max=100.0,
                step=0.1,
                format='%.1f'
            ).classes('w-32')
        
        with ui.row().classes('gap-4 w-full items-end mt-4'):
            max_bets = ui.number(
                label='Number of Bets',
                value=100,
                min=1,
                step=10
            ).classes('flex-1')
            
            strategy = ui.select(
                ['Fixed Bet (50%)', 'Martingale', 'Anti-Martingale'],
                value='Fixed Bet (50%)',
                label='Strategy'
            ).classes('flex-1')
            
            seed = ui.number(
                label='Seed (optional)',
                value=None,
                min=1
            ).classes('w-32')
        
        with ui.row().classes('gap-2 mt-4'):
            async def start_click():
                await controller.start_simulation(
                    starting_balance.value,
                    currency.value,
                    house_edge.value,
                    int(max_bets.value),
                    strategy.value,
                    int(seed.value) if seed.value else None,
                )
            
            ui.button('▶ Start', on_click=start_click).classes('bg-green-600')
            ui.button('⏸ Pause', on_click=controller.pause_simulation).classes('bg-yellow-600')
            ui.button('⏹ Stop', on_click=controller.stop_simulation).classes('bg-red-600')
            ui.button('🔄 Reset', on_click=controller.reset_simulation).classes('bg-blue-600')
            ui.button('📊 Export', on_click=controller.export_results).classes('bg-purple-600')
    
    # Current Session
    with card().classes('mt-6'):
        ui.label('Current Session').classes('text-xl font-semibold mb-4')
        
        with ui.grid(columns=4).classes('gap-4 w-full'):
            with ui.column():
                ui.label('Balance').classes('text-xs text-slate-400')
                controller.balance_label = ui.label('$100.00').classes('text-2xl font-mono font-bold')
            
            with ui.column():
                ui.label('Profit/Loss').classes('text-xs text-slate-400')
                controller.profit_label = ui.label('$0.00 (0.00%)').classes('text-lg font-mono text-slate-300')
            
            with ui.column():
                ui.label('Bets').classes('text-xs text-slate-400')
                controller.bets_label = ui.label('0 bets').classes('text-lg font-mono')
            
            with ui.column():
                ui.label('Win Rate').classes('text-xs text-slate-400')
                controller.win_rate_label = ui.label('0W / 0L (0%)').classes('text-lg font-mono')
        
        # Progress bar (placeholder for now)
        # controller.progress_bar = ui.linear_progress(value=0).classes('mt-4')
    
    # Performance Metrics
    with card().classes('mt-6'):
        controller.metrics_container = ui.column().classes('w-full')
        with controller.metrics_container:
            ui.label('Performance Metrics').classes('text-lg font-semibold mb-3')
            ui.label('Run a simulation to see metrics').classes('text-sm text-slate-400')
    
    # Risk Analysis
    with card().classes('mt-6'):
        controller.risk_container = ui.column().classes('w-full')
        with controller.risk_container:
            ui.label('Risk Analysis').classes('text-lg font-semibold mb-3')
            ui.label('Run a simulation to see risk analysis').classes('text-sm text-slate-400')
