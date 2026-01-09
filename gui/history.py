"""
Bet history and analytics screen.
View past bets, charts, export data.
"""

import io
import csv
from datetime import datetime
from nicegui import ui
from gui.state import app_state
from gui.utils import format_balance, format_profit, format_number


class History:
    """Bet history and analytics interface"""
    
    def __init__(self):
        self.history_table = None
        self.export_button = None
        self.clear_button = None
        self.page_size = 50
        self.current_page = 0
        
    def render(self):
        """Render history UI"""
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column():
                        ui.label('Bet History').classes('text-2xl font-bold')
                        ui.label(f'{len(app_state.bet_history)} total bets').classes('text-gray-500')
                    
                    with ui.row().classes('gap-2'):
                        self.export_button = ui.button(
                            'Export CSV',
                            on_click=self._export_csv,
                            icon='download'
                        ).props('outline')
                        
                        self.clear_button = ui.button(
                            'Clear History',
                            on_click=self._clear_history,
                            icon='delete'
                        ).props('outline color=red')
            
            # Summary stats
            self._render_summary()
            
            # Bet table
            self._render_table()
    
    def _render_summary(self):
        """Render summary statistics"""
        with ui.card().classes('w-full'):
            ui.label('Session Summary').classes('text-lg font-semibold mb-2')
            
            total_bets = app_state.total_bets
            wins = app_state.wins
            losses = app_state.losses
            win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
            
            current_balance = app_state.balance
            starting_balance = app_state.starting_balance
            total_profit = current_balance - starting_balance
            profit_pct = (total_profit / starting_balance * 100) if starting_balance > 0 else 0
            
            with ui.grid(columns=5).classes('w-full gap-4'):
                self._render_stat('Total Bets', format_number(total_bets), 'casino')
                self._render_stat('Wins', format_number(wins), 'check_circle', 'text-green-600')
                self._render_stat('Losses', format_number(losses), 'cancel', 'text-red-600')
                self._render_stat('Win Rate', f'{win_rate:.1f}%', 'percent')
                
                profit_color = 'text-green-600' if total_profit >= 0 else 'text-red-600'
                self._render_stat(
                    'Total P/L',
                    f'{format_profit(total_profit)} ({profit_pct:+.2f}%)',
                    'trending_up',
                    profit_color
                )
    
    def _render_stat(self, label: str, value: str, icon: str, value_class: str = ''):
        """Render a single stat card"""
        with ui.card().classes('p-4'):
            with ui.row().classes('items-center gap-2 mb-1'):
                ui.icon(icon).classes('text-gray-400')
                ui.label(label).classes('text-sm text-gray-600')
            ui.label(value).classes(f'text-lg font-bold {value_class}')
    
    def _render_table(self):
        """Render bet history table"""
        with ui.card().classes('w-full'):
            ui.label('Bet Details').classes('text-lg font-semibold mb-2')
            
            if len(app_state.bet_history) == 0:
                ui.label('No bets recorded yet').classes('text-center text-gray-500 py-8')
                return
            
            # Pagination controls
            total_pages = (len(app_state.bet_history) + self.page_size - 1) // self.page_size
            
            with ui.row().classes('w-full items-center justify-between mb-2'):
                ui.label(f'Page {self.current_page + 1} of {total_pages}').classes('text-sm text-gray-600')
                
                with ui.row().classes('gap-2'):
                    ui.button(
                        icon='chevron_left',
                        on_click=lambda: self._change_page(-1)
                    ).props('flat dense').set_enabled(self.current_page > 0)
                    
                    ui.button(
                        icon='chevron_right',
                        on_click=lambda: self._change_page(1)
                    ).props('flat dense').set_enabled(self.current_page < total_pages - 1)
            
            # Table
            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(app_state.bet_history))
            page_bets = list(app_state.bet_history)[start_idx:end_idx]
            
            columns = [
                {'name': 'bet_number', 'label': 'Bet #', 'field': 'bet_number', 'align': 'left'},
                {'name': 'timestamp', 'label': 'Time', 'field': 'timestamp', 'align': 'left'},
                {'name': 'result', 'label': 'Result', 'field': 'result', 'align': 'center'},
                {'name': 'bet_amount', 'label': 'Bet', 'field': 'bet_amount', 'align': 'right'},
                {'name': 'target_chance', 'label': 'Chance', 'field': 'target_chance', 'align': 'right'},
                {'name': 'roll', 'label': 'Roll', 'field': 'roll', 'align': 'right'},
                {'name': 'payout', 'label': 'Payout', 'field': 'payout', 'align': 'right'},
                {'name': 'profit', 'label': 'Profit', 'field': 'profit', 'align': 'right'},
                {'name': 'balance', 'label': 'Balance', 'field': 'balance', 'align': 'right'},
            ]
            
            rows = []
            for bet in reversed(page_bets):  # Show newest first
                rows.append({
                    'bet_number': bet.bet_number,
                    'timestamp': bet.timestamp.strftime('%H:%M:%S'),
                    'result': 'WIN' if bet.won else 'LOSS',
                    'bet_amount': f'{bet.bet_amount:.8f}',
                    'target_chance': f'{bet.target_chance:.2f}%',
                    'roll': f'{bet.roll:.2f}',
                    'payout': f'{bet.payout:.8f}',
                    'profit': f'{bet.profit:+.8f}',
                    'balance': f'{bet.balance:.8f}',
                })
            
            ui.table(
                columns=columns,
                rows=rows,
                row_key='bet_number'
            ).classes('w-full').props('flat dense')
    
    def _change_page(self, delta: int):
        """Change current page"""
        total_pages = (len(app_state.bet_history) + self.page_size - 1) // self.page_size
        new_page = self.current_page + delta
        
        if 0 <= new_page < total_pages:
            self.current_page = new_page
            # Re-render would happen here in a real reactive framework
            # For now, user needs to manually refresh
            ui.notify(f'Page {self.current_page + 1}', type='info')
    
    def _export_csv(self):
        """Export all bet history to CSV"""
        if len(app_state.bet_history) == 0:
            ui.notify('No bets to export', type='warning')
            return
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Bet Number', 'Timestamp', 'Won', 'Bet Amount', 'Target Chance', 
            'Roll', 'Payout', 'Profit', 'Balance'
        ])
        
        # Data (newest first)
        for bet in reversed(list(app_state.bet_history)):
            writer.writerow([
                bet.bet_number,
                bet.timestamp.isoformat(),
                bet.won,
                f'{bet.bet_amount:.8f}',
                f'{bet.target_chance:.2f}',
                f'{bet.roll:.2f}',
                f'{bet.payout:.8f}',
                f'{bet.profit:.8f}',
                f'{bet.balance:.8f}',
            ])
        
        # Download
        csv_content = output.getvalue()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'bet_history_{timestamp}.csv'
        
        ui.download(csv_content.encode(), filename)
        ui.notify(f'Exported {len(app_state.bet_history)} bets', type='positive')
    
    def _clear_history(self):
        """Clear all bet history (with confirmation)"""
        async def confirm_clear():
            result = await ui.run_javascript(
                'return confirm("Clear all bet history? This cannot be undone.")'
            )
            
            if result:
                app_state.bet_history.clear()
                app_state.update(
                    total_bets=0,
                    wins=0,
                    losses=0,
                    current_streak=0,
                    streak_type='none'
                )
                
                self.current_page = 0
                ui.notify('History cleared', type='info')
        
        ui.timer(0.1, confirm_clear, once=True)
