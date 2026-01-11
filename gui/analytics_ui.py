"""
Analytics UI - Statistical analysis and performance metrics display.
"""
from nicegui import ui
from gui.state import app_state
from gui.analytics import get_analytics_calculator, StrategyComparison
from gui.database import get_db_manager


class AnalyticsUI:
    """Analytics dashboard with performance metrics."""
    
    def __init__(self):
        self.calculator = get_analytics_calculator()
        self.db = get_db_manager()
        self.metrics_container = None
        self.comparison_container = None
    
    def render(self):
        """Render analytics UI."""
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.card().classes('w-full'):
                ui.label('Analytics Dashboard').classes('text-2xl font-bold')
                ui.label('Statistical analysis and performance metrics').classes('text-gray-500')
            
            # Refresh button
            with ui.card().classes('w-full'):
                ui.button('Refresh Analytics', on_click=self._refresh_analytics,
                         icon='refresh', color='primary')
            
            # Current session metrics
            self._render_current_session()
            
            # Historical comparison
            self._render_historical_comparison()
    
    def _render_current_session(self):
        """Render current session analytics."""
        with ui.card().classes('w-full'):
            ui.label('Current Session Metrics').classes('text-xl font-bold mb-4')
            
            self.metrics_container = ui.column().classes('w-full gap-3')
            self._update_current_metrics()
    
    def _update_current_metrics(self):
        """Update current session metrics display."""
        if not self.metrics_container:
            return
        
        self.metrics_container.clear()
        
        # Calculate analytics from current state
        bets = app_state.bet_history
        
        if not bets:
            with self.metrics_container:
                ui.label('No bets yet. Start betting to see analytics.').classes(
                    'text-gray-500 text-center p-8'
                )
            return
        
        analytics = self.calculator.calculate_session_analytics(
            bets, 
            starting_balance=app_state.starting_balance
        )
        
        with self.metrics_container:
            # Key metrics grid
            with ui.grid(columns=3).classes('w-full gap-4'):
                # Win Rate
                self._metric_card('Win Rate', f'{analytics.win_rate:.2f}%',
                                 'trending_up', 'green' if analytics.win_rate > 50 else 'red')
                
                # ROI
                self._metric_card('ROI', f'{analytics.roi:+.2f}%',
                                 'attach_money', 'green' if analytics.roi > 0 else 'red')
                
                # Profit Factor
                self._metric_card('Profit Factor', f'{analytics.profit_factor:.2f}',
                                 'balance', 'green' if analytics.profit_factor > 1 else 'red')
                
                # Net Profit
                currency = app_state.currency.upper() if app_state.currency else 'BTC'
                self._metric_card('Net Profit', f'{analytics.net_profit:+.8f} {currency}',
                                 'show_chart', 'green' if analytics.net_profit > 0 else 'red')
                
                # Max Drawdown
                self._metric_card('Max Drawdown', f'{analytics.max_drawdown_pct:.2f}%',
                                 'trending_down', 'red')
                
                # Sharpe Ratio
                sharpe = self.calculator.calculate_sharpe_ratio([b.profit for b in bets])
                self._metric_card('Sharpe Ratio', f'{sharpe:.4f}',
                                 'assessment', 'green' if sharpe > 0 else 'gray')
            
            # Detailed statistics
            with ui.expansion('Detailed Statistics', icon='analytics').classes('w-full mt-4'):
                with ui.grid(columns=2).classes('w-full gap-3'):
                    self._stat_item('Total Bets', f'{analytics.total_bets:,}')
                    self._stat_item('Total Wagered', f'{analytics.total_wagered:.8f} {currency}')
                    self._stat_item('Wins / Losses', f'{analytics.wins} / {analytics.losses}')
                    self._stat_item('Gross Profit', f'{analytics.gross_profit:.8f} {currency}')
                    self._stat_item('Gross Loss', f'{analytics.gross_loss:.8f} {currency}')
                    self._stat_item('Avg Bet Size', f'{analytics.avg_bet_size:.8f} {currency}')
                    self._stat_item('Avg Win', f'{analytics.avg_win:.8f} {currency}')
                    self._stat_item('Avg Loss', f'{analytics.avg_loss:.8f} {currency}')
                    self._stat_item('Avg Profit/Bet', f'{analytics.avg_profit_per_bet:.8f} {currency}')
                    self._stat_item('Largest Win', f'{analytics.largest_win:.8f} {currency}')
                    self._stat_item('Largest Loss', f'{analytics.largest_loss:.8f} {currency}')
                    self._stat_item('Std Deviation', f'{analytics.std_deviation:.8f}')
                    self._stat_item('Longest Win Streak', f'{analytics.longest_win_streak}')
                    self._stat_item('Longest Loss Streak', f'{analytics.longest_loss_streak}')
    
    def _metric_card(self, label: str, value: str, icon: str, color: str = 'blue'):
        """Create a metric card."""
        with ui.card().tight().classes('p-4'):
            with ui.row().classes('items-center gap-3'):
                ui.icon(icon, size='md').classes(f'text-{color}-500')
                with ui.column().classes('gap-0'):
                    ui.label(label).classes('text-xs text-gray-500')
                    ui.label(value).classes('text-lg font-bold')
    
    def _stat_item(self, label: str, value: str):
        """Create a simple stat item."""
        with ui.row().classes('justify-between items-center'):
            ui.label(label).classes('text-sm text-gray-600')
            ui.label(value).classes('text-sm font-semibold')
    
    def _render_historical_comparison(self):
        """Render historical session comparison."""
        with ui.card().classes('w-full'):
            ui.label('Historical Session Comparison').classes('text-xl font-bold mb-4')
            ui.label('Compare performance across different sessions').classes('text-sm text-gray-500 mb-3')
            
            self.comparison_container = ui.column().classes('w-full gap-3')
            self._update_comparison()
    
    def _update_comparison(self):
        """Update session comparison display."""
        if not self.comparison_container:
            return
        
        self.comparison_container.clear()
        
        # Load recent sessions from database
        sessions = self.db.list_sessions(limit=10)
        
        if not sessions:
            with self.comparison_container:
                ui.label('No historical sessions found.').classes(
                    'text-gray-500 text-center p-8'
                )
            return
        
        with self.comparison_container:
            # Sessions table
            columns = [
                {'name': 'session', 'label': 'Session', 'field': 'session', 'align': 'left'},
                {'name': 'strategy', 'label': 'Strategy', 'field': 'strategy', 'align': 'left'},
                {'name': 'bets', 'label': 'Bets', 'field': 'bets', 'align': 'right'},
                {'name': 'win_rate', 'label': 'Win %', 'field': 'win_rate', 'align': 'right'},
                {'name': 'profit', 'label': 'Profit', 'field': 'profit', 'align': 'right'},
                {'name': 'roi', 'label': 'ROI %', 'field': 'roi', 'align': 'right'},
            ]
            
            rows = []
            for i, session in enumerate(sessions, 1):
                win_rate = (session['wins'] / session['total_bets'] * 100) if session['total_bets'] > 0 else 0
                
                rows.append({
                    'session': f"Session {i}",
                    'strategy': session['strategy_name'] or 'Unknown',
                    'bets': session['total_bets'] or 0,
                    'win_rate': f"{win_rate:.1f}%",
                    'profit': f"{session['profit'] or 0:+.6f}",
                    'roi': f"{session['profit_percent'] or 0:+.2f}%"
                })
            
            ui.table(columns=columns, rows=rows, row_key='session').classes('w-full')
            
            # Best performers summary
            if len(sessions) >= 2:
                with ui.expansion('Best Performers', icon='emoji_events').classes('w-full mt-3'):
                    # Find best by different metrics
                    best_roi = max(sessions, key=lambda s: s['profit_percent'] or -999)
                    best_profit = max(sessions, key=lambda s: s['profit'] or -999)
                    best_win_rate = max(sessions, key=lambda s: (s['wins'] / s['total_bets']) if s['total_bets'] > 0 else 0)
                    
                    with ui.column().classes('gap-2'):
                        ui.label(f"🏆 Best ROI: {best_roi['strategy_name']} ({best_roi['profit_percent'] or 0:+.2f}%)")
                        ui.label(f"💰 Most Profit: {best_profit['strategy_name']} ({best_profit['profit'] or 0:+.6f})")
                        best_wr = (best_win_rate['wins'] / best_win_rate['total_bets'] * 100) if best_win_rate['total_bets'] > 0 else 0
                        ui.label(f"🎯 Best Win Rate: {best_win_rate['strategy_name']} ({best_wr:.1f}%)")
    
    def _refresh_analytics(self):
        """Refresh all analytics displays."""
        self._update_current_metrics()
        self._update_comparison()
        ui.notify('📊 Analytics refreshed', type='positive', position='top')
