"""
Offline simulator screen.
Run simulations without real money, visualize results.
"""

import io
import csv
from datetime import datetime
from nicegui import ui
from gui.state import app_state, BetRecord
from gui.bot_controller import bot_controller
from gui.utils import format_balance, format_profit, format_number


class Simulator:
    """Offline simulation interface"""
    
    def __init__(self):
        self.starting_balance_input = None
        self.num_rolls_input = None
        self.run_button = None
        self.stop_button = None
        self.export_button = None
        self.results_container = None
        self.chart_container = None
        
    def render(self):
        """Render simulator UI"""
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.card().classes('w-full'):
                ui.label('Offline Simulator').classes('text-2xl font-bold')
                ui.label('Test strategies safely without risking real funds').classes('text-gray-500')
            
            # Configuration
            self._render_config()
            
            # Controls
            self._render_controls()
            
            # Results
            self._render_results()
    
    def _render_config(self):
        """Render simulation configuration inputs"""
        with ui.card().classes('w-full'):
            ui.label('Simulation Settings').classes('text-lg font-semibold mb-2')
            
            with ui.row().classes('w-full gap-4'):
                self.starting_balance_input = ui.number(
                    label='Starting Balance (BTC)',
                    value=0.001,
                    min=0.00000001,
                    step=0.0001,
                    format='%.8f'
                ).classes('flex-grow')
                
                self.num_rolls_input = ui.number(
                    label='Number of Rolls',
                    value=100,
                    min=1,
                    max=10000,
                    step=10
                ).classes('flex-grow')
            
            with ui.row().classes('w-full gap-2 mt-2'):
                ui.label('Current Strategy:').classes('text-sm font-semibold')
                ui.label(app_state.strategy_name or 'None').classes('text-sm text-blue-600')
                ui.label('•').classes('text-sm text-gray-400')
                ui.label('Configure in Strategies tab').classes('text-sm text-gray-500')
    
    def _render_controls(self):
        """Render simulation control buttons"""
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full gap-2'):
                self.run_button = ui.button(
                    'Run Simulation',
                    on_click=self._run_simulation,
                    icon='play_arrow'
                ).props('color=primary')
                
                self.stop_button = ui.button(
                    'Stop',
                    on_click=self._stop_simulation,
                    icon='stop'
                ).props('color=red')
                self.stop_button.visible = False
                
                self.export_button = ui.button(
                    'Export CSV',
                    on_click=self._export_results,
                    icon='download'
                ).props('outline')
                self.export_button.visible = False
    
    def _render_results(self):
        """Render simulation results display"""
        with ui.card().classes('w-full'):
            ui.label('Results').classes('text-lg font-semibold mb-2')
            
            self.results_container = ui.column().classes('w-full gap-4')
            
            with self.results_container:
                # Stats grid
                with ui.grid(columns=4).classes('w-full gap-4'):
                    self._render_stat_card('Final Balance', '---', 'account_balance_wallet')
                    self._render_stat_card('Total Profit/Loss', '---', 'trending_up')
                    self._render_stat_card('Win Rate', '---', 'percent')
                    self._render_stat_card('Max Drawdown', '---', 'arrow_downward')
                
                # Chart placeholder
                self.chart_container = ui.column().classes('w-full mt-4')
                with self.chart_container:
                    ui.label('Run a simulation to see results').classes('text-center text-gray-500')
    
    def _render_stat_card(self, label: str, value: str, icon: str):
        """Render a single stat card"""
        with ui.card().classes('p-4'):
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.icon(icon).classes('text-gray-400')
                ui.label(label).classes('text-sm text-gray-600')
            ui.label(value).classes('text-xl font-bold')
    
    def _run_simulation(self):
        """Start offline simulation"""
        if not app_state.strategy_name:
            ui.notify('Please configure a strategy first', type='warning')
            return
        
        starting_balance = self.starting_balance_input.value
        num_rolls = int(self.num_rolls_input.value)
        
        if starting_balance <= 0:
            ui.notify('Starting balance must be positive', type='negative')
            return
        
        if num_rolls < 1 or num_rolls > 10000:
            ui.notify('Number of rolls must be 1-10000', type='negative')
            return
        
        # Update app state
        app_state.update(
            balance=starting_balance,
            starting_balance=starting_balance,
            simulation_mode=True
        )
        
        # Show stop button, hide run button
        self.run_button.visible = False
        self.stop_button.visible = True
        self.export_button.visible = False
        
        # Start simulation
        bot_controller.start(
            simulation_mode=True,
            max_bets=num_rolls,
            update_callback=self._update_results
        )
        
        ui.notify(f'Running simulation: {num_rolls} rolls', type='info')
    
    def _stop_simulation(self):
        """Stop ongoing simulation"""
        bot_controller.stop()
        
        self.run_button.visible = True
        self.stop_button.visible = False
        self.export_button.visible = True
        
        ui.notify('Simulation stopped', type='info')
    
    def _update_results(self):
        """Update results display during simulation"""
        # Check if simulation is complete
        if not bot_controller.is_running() and app_state.total_bets > 0:
            self.run_button.visible = True
            self.stop_button.visible = False
            self.export_button.visible = True
            
            self._display_final_results()
    
    def _display_final_results(self):
        """Display final simulation results"""
        self.results_container.clear()
        
        with self.results_container:
            # Calculate stats
            final_balance = app_state.balance
            starting_balance = app_state.starting_balance
            profit = final_balance - starting_balance
            profit_pct = (profit / starting_balance * 100) if starting_balance > 0 else 0
            
            total_bets = app_state.total_bets
            wins = app_state.wins
            losses = app_state.losses
            win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
            
            # Calculate max drawdown
            max_drawdown = 0
            peak_balance = starting_balance
            for bet in app_state.bet_history:
                if bet.balance > peak_balance:
                    peak_balance = bet.balance
                drawdown = (peak_balance - bet.balance) / peak_balance * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Stats grid
            with ui.grid(columns=4).classes('w-full gap-4'):
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('account_balance_wallet').classes('text-gray-400')
                        ui.label('Final Balance').classes('text-sm text-gray-600')
                    ui.label(format_balance(final_balance)).classes('text-xl font-bold')
                
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('trending_up').classes('text-gray-400')
                        ui.label('Total Profit/Loss').classes('text-sm text-gray-600')
                    profit_color = 'text-green-600' if profit >= 0 else 'text-red-600'
                    ui.label(f'{format_profit(profit)} ({profit_pct:+.2f}%)').classes(f'text-xl font-bold {profit_color}')
                
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('percent').classes('text-gray-400')
                        ui.label('Win Rate').classes('text-sm text-gray-600')
                    ui.label(f'{win_rate:.1f}%').classes('text-xl font-bold')
                
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('arrow_downward').classes('text-gray-400')
                        ui.label('Max Drawdown').classes('text-sm text-gray-600')
                    ui.label(f'{max_drawdown:.2f}%').classes('text-xl font-bold text-red-600')
            
            # Chart (simple text-based for now)
            self.chart_container.clear()
            with self.chart_container:
                with ui.card().classes('w-full p-4'):
                    ui.label('Balance History').classes('text-lg font-semibold mb-2')
                    
                    if len(app_state.bet_history) > 0:
                        # Display last 10 bets
                        ui.label('Last 10 Bets:').classes('text-sm font-semibold mb-2')
                        
                        with ui.row().classes('w-full gap-2 text-xs font-mono'):
                            ui.label('Bet #').classes('w-16')
                            ui.label('Result').classes('w-16')
                            ui.label('Balance').classes('flex-grow')
                            ui.label('Profit').classes('w-24')
                        
                        ui.separator()
                        
                        recent_bets = list(app_state.bet_history)[-10:]
                        for bet in recent_bets:
                            with ui.row().classes('w-full gap-2 text-xs font-mono'):
                                ui.label(f'#{bet.bet_number}').classes('w-16')
                                
                                result_color = 'text-green-600' if bet.won else 'text-red-600'
                                ui.label('WIN' if bet.won else 'LOSS').classes(f'w-16 {result_color}')
                                
                                ui.label(format_balance(bet.balance)).classes('flex-grow')
                                
                                profit_color = 'text-green-600' if bet.profit >= 0 else 'text-red-600'
                                ui.label(format_profit(bet.profit)).classes(f'w-24 {profit_color}')
                    else:
                        ui.label('No bet history available').classes('text-gray-500')
    
    def _export_results(self):
        """Export simulation results to CSV"""
        if len(app_state.bet_history) == 0:
            ui.notify('No results to export', type='warning')
            return
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Bet Number', 'Timestamp', 'Won', 'Bet Amount', 'Payout', 
            'Profit', 'Balance', 'Target Chance', 'Roll'
        ])
        
        # Data
        for bet in app_state.bet_history:
            writer.writerow([
                bet.bet_number,
                bet.timestamp.isoformat(),
                bet.won,
                f'{bet.bet_amount:.8f}',
                f'{bet.payout:.8f}',
                f'{bet.profit:.8f}',
                f'{bet.balance:.8f}',
                f'{bet.target_chance:.2f}',
                f'{bet.roll:.2f}'
            ])
        
        # Download
        csv_content = output.getvalue()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'simulation_{timestamp}.csv'
        
        ui.download(csv_content.encode(), filename)
        ui.notify(f'Exported {len(app_state.bet_history)} bets to {filename}', type='positive')
