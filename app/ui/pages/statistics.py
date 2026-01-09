"""
Statistics page - comprehensive bet analytics and statistics
"""

from nicegui import ui
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.ui.components import card, primary_button, secondary_button, empty_state
from app.ui.components.common import metric_card, loading_spinner
from app.ui.theme import Theme
from app.state.store import store


def statistics_content():
    """Statistics page with comprehensive analytics"""
    
    ui.label('📊 Statistics').classes('text-3xl font-bold mb-2')
    ui.label('Comprehensive betting analytics and insights').classes('text-sm text-slate-400 mb-6')
    
    # Time period selector
    with card():
        ui.label('Time Period').classes('text-lg font-semibold mb-4')
        
        with ui.row().classes('gap-2 flex-wrap'):
            period_buttons = []
            periods = [
                ('24h', '24 Hours', 1),
                ('7d', '7 Days', 7),
                ('30d', '30 Days', 30),
                ('90d', '90 Days', 90),
                ('all', 'All Time', None),
            ]
            
            selected_period = {'value': '7d'}
            
            for period_id, label, days in periods:
                btn = ui.button(
                    label,
                    on_click=lambda p=period_id: select_period(p)
                ).props('outline' if period_id != '7d' else '').classes('min-w-[100px]')
                period_buttons.append((period_id, btn))
            
            def select_period(period_id: str):
                selected_period['value'] = period_id
                # Update button styles
                for pid, btn in period_buttons:
                    if pid == period_id:
                        btn.props(remove='outline')
                    else:
                        btn.props('outline')
                # Reload statistics
                load_statistics(period_id)
    
    # Statistics container
    stats_container = ui.column().classes('w-full gap-6 mt-6')
    
    def load_statistics(period: str = '7d'):
        """Load and display statistics"""
        stats_container.clear()
        
        with stats_container:
            # Check if we have bet history
            if not store.bet_history:
                empty_state(
                    'bar_chart',
                    'No Data Available',
                    'Start betting to see statistics',
                    'Go to Betting',
                    lambda: ui.navigate.to('/betting')
                )
                return
            
            # Filter bets by period
            bets = store.bet_history
            if period != 'all':
                days = {'24h': 1, '7d': 7, '30d': 30, '90d': 90}.get(period, 7)
                cutoff = datetime.now() - timedelta(days=days)
                bets = [b for b in bets if b.timestamp >= cutoff]
            
            if not bets:
                empty_state(
                    'bar_chart',
                    'No Data for Period',
                    f'No bets found for {period}',
                    'Show All Time',
                    lambda: select_period('all')
                )
                return
            
            # Calculate statistics
            total_bets = len(bets)
            total_wagered = sum(b.amount for b in bets)
            total_profit = sum(b.profit for b in bets)
            wins = [b for b in bets if b.is_win]
            losses = [b for b in bets if not b.is_win]
            win_rate = (len(wins) / total_bets * 100) if total_bets > 0 else 0
            
            largest_win = max([b.profit for b in wins]) if wins else Decimal('0')
            largest_loss = min([b.profit for b in losses]) if losses else Decimal('0')
            avg_bet = total_wagered / total_bets if total_bets > 0 else Decimal('0')
            avg_profit = total_profit / total_bets if total_bets > 0 else Decimal('0')
            
            # Overview metrics
            with card():
                ui.label('Overview').classes('text-xl font-semibold mb-4')
                
                with ui.grid(columns=4).classes('w-full gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'):
                    metric_card('Total Bets', str(total_bets), 'casino')
                    metric_card('Total Wagered', f'{total_wagered:.8f}', 'trending_up')
                    metric_card('Total Profit', f'{total_profit:.8f}', 'account_balance')
                    metric_card('Win Rate', f'{win_rate:.1f}%', 'percent')
            
            # Win/Loss breakdown
            with card().classes('mt-6'):
                ui.label('Win/Loss Analysis').classes('text-xl font-semibold mb-4')
                
                with ui.grid(columns=2).classes('w-full gap-4 grid-cols-1 md:grid-cols-2'):
                    # Wins column
                    with ui.column().classes('gap-2'):
                        ui.label('Wins').classes('text-lg font-semibold text-green-400')
                        ui.label(f'Count: {len(wins)}').classes('text-sm text-slate-300')
                        ui.label(f'Largest: {largest_win:.8f}').classes('text-sm text-slate-300')
                        
                        # Win rate bar
                        with ui.column().classes('w-full mt-2'):
                            ui.label(f'{win_rate:.1f}%').classes('text-sm')
                            ui.linear_progress(win_rate / 100).props(f'color=positive').classes('w-full')
                    
                    # Losses column
                    with ui.column().classes('gap-2'):
                        ui.label('Losses').classes('text-lg font-semibold text-red-400')
                        ui.label(f'Count: {len(losses)}').classes('text-sm text-slate-300')
                        ui.label(f'Largest: {largest_loss:.8f}').classes('text-sm text-slate-300')
                        
                        # Loss rate bar
                        loss_rate = 100 - win_rate
                        with ui.column().classes('w-full mt-2'):
                            ui.label(f'{loss_rate:.1f}%').classes('text-sm')
                            ui.linear_progress(loss_rate / 100).props(f'color=negative').classes('w-full')
            
            # Averages
            with card().classes('mt-6'):
                ui.label('Averages').classes('text-xl font-semibold mb-4')
                
                with ui.grid(columns=2).classes('w-full gap-4 grid-cols-1 md:grid-cols-2'):
                    metric_card('Average Bet', f'{avg_bet:.8f}', 'casino')
                    metric_card('Average Profit', f'{avg_profit:.8f}', 'account_balance')
            
            # Currency breakdown
            currencies = {}
            for bet in bets:
                if bet.currency not in currencies:
                    currencies[bet.currency] = {
                        'bets': 0,
                        'wagered': Decimal('0'),
                        'profit': Decimal('0'),
                        'wins': 0
                    }
                currencies[bet.currency]['bets'] += 1
                currencies[bet.currency]['wagered'] += bet.amount
                currencies[bet.currency]['profit'] += bet.profit
                if bet.is_win:
                    currencies[bet.currency]['wins'] += 1
            
            if len(currencies) > 1:
                with card().classes('mt-6'):
                    ui.label('By Currency').classes('text-xl font-semibold mb-4')
                    
                    for currency, stats in currencies.items():
                        currency_win_rate = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
                        
                        with ui.row().classes('items-center justify-between p-3 mb-2 rounded-lg').style(
                            f'background-color: {Theme.BG_TERTIARY}'
                        ):
                            with ui.column().classes('gap-1'):
                                ui.label(currency).classes('text-lg font-bold')
                                ui.label(f"{stats['bets']} bets · {stats['wagered']:.8f} wagered").classes('text-xs text-slate-400')
                            
                            with ui.column().classes('gap-1 items-end'):
                                profit_color = Theme.ACCENT if stats['profit'] >= 0 else Theme.ERROR
                                ui.label(f"{stats['profit']:.8f}").classes('text-lg font-bold').style(
                                    f'color: {profit_color}'
                                )
                                ui.label(f"{currency_win_rate:.1f}% win rate").classes('text-xs text-slate-400')
            
            # Recent streaks
            current_streak = 0
            best_win_streak = 0
            best_loss_streak = 0
            temp_win_streak = 0
            temp_loss_streak = 0
            
            for bet in reversed(bets):  # Most recent first
                if bet.is_win:
                    temp_win_streak += 1
                    temp_loss_streak = 0
                    if current_streak == 0:
                        current_streak = temp_win_streak
                else:
                    temp_loss_streak += 1
                    temp_win_streak = 0
                    if current_streak == 0:
                        current_streak = -temp_loss_streak
                
                best_win_streak = max(best_win_streak, temp_win_streak)
                best_loss_streak = max(best_loss_streak, temp_loss_streak)
            
            with card().classes('mt-6'):
                ui.label('Streaks').classes('text-xl font-semibold mb-4')
                
                with ui.grid(columns=3).classes('w-full gap-4 grid-cols-1 md:grid-cols-3'):
                    # Current streak
                    with ui.column().classes('gap-1'):
                        ui.label('Current Streak').classes('text-sm text-slate-400')
                        if current_streak > 0:
                            ui.label(f'{current_streak} wins').classes('text-2xl font-bold text-green-400')
                        elif current_streak < 0:
                            ui.label(f'{abs(current_streak)} losses').classes('text-2xl font-bold text-red-400')
                        else:
                            ui.label('N/A').classes('text-2xl font-bold text-slate-400')
                    
                    # Best win streak
                    metric_card('Best Win Streak', str(best_win_streak), 'trending_up')
                    
                    # Worst loss streak
                    metric_card('Worst Loss Streak', str(best_loss_streak), 'trending_down')
            
            # Export button
            with ui.row().classes('gap-2 mt-6'):
                secondary_button(
                    'Export CSV',
                    on_click=lambda: export_statistics(period),
                    icon='download'
                )
                
                secondary_button(
                    'View Full History',
                    on_click=lambda: ui.navigate.to('/history'),
                    icon='history'
                )
    
    def export_statistics(period: str):
        """Export statistics to CSV"""
        # TODO: Implement CSV export using BetHistoryManager
        ui.notify('Export functionality coming soon!', type='info')
    
    # Initial load
    load_statistics('7d')
