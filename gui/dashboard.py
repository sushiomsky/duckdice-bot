"""
Dashboard screen - Main control interface.
Live status, start/stop/pause controls, real-time stats.
"""

from nicegui import ui
from gui.state import app_state
from gui.bot_controller import bot_controller
from gui.utils import format_balance, format_profit, format_number, get_status_color


class Dashboard:
    """Main dashboard with bot controls and live stats"""
    
    def __init__(self):
        self.status_badge = None
        self.balance_label = None
        self.profit_label = None
        self.bets_label = None
        self.wins_label = None
        self.losses_label = None
        self.streak_label = None
        self.start_button = None
        self.stop_button = None
        self.pause_button = None
        self.resume_button = None
        
    def render(self):
        """Render dashboard UI"""
        with ui.column().classes('w-full gap-4'):
            # Header with status
            self._render_header()
            
            # Control buttons
            self._render_controls()
            
            # Live stats grid
            self._render_stats()
            
            # Session info
            self._render_session_info()
    
    def _render_header(self):
        """Render header with status indicator"""
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full items-center justify-between'):
                # Title
                ui.label('Dashboard').classes('text-2xl font-bold')
                
                # Status badge (most prominent)
                with ui.row().classes('items-center gap-2'):
                    self.status_badge = ui.badge('IDLE').props('outline')
                    
                    # Mode indicator
                    if app_state.simulation_mode:
                        ui.badge('SIMULATION', color='orange').props('outline')
                    else:
                        ui.badge('LIVE', color='green').props('outline')
        
        # Update status
        self._update_status_badge()
    
    def _render_controls(self):
        """Render control buttons"""
        with ui.card().classes('w-full'):
            ui.label('Bot Control').classes('text-lg font-bold mb-2')
            
            with ui.row().classes('gap-2'):
                # START button (disabled if invalid config)
                self.start_button = ui.button(
                    'START',
                    on_click=self._on_start,
                    color='green'
                ).props('size=lg icon=play_arrow')
                self.start_button.enabled = self._can_start()
                
                # PAUSE button (only visible when running)
                self.pause_button = ui.button(
                    'PAUSE',
                    on_click=self._on_pause,
                    color='yellow'
                ).props('size=lg icon=pause')
                self.pause_button.visible = False
                
                # RESUME button (only visible when paused)
                self.resume_button = ui.button(
                    'RESUME',
                    on_click=self._on_resume,
                    color='green'
                ).props('size=lg icon=play_arrow')
                self.resume_button.visible = False
                
                # STOP button (always accessible when running)
                self.stop_button = ui.button(
                    'EMERGENCY STOP',
                    on_click=self._on_stop,
                    color='red'
                ).props('size=lg icon=stop')
                self.stop_button.visible = False
    
    def _render_stats(self):
        """Render live statistics grid"""
        with ui.card().classes('w-full'):
            ui.label('Live Statistics').classes('text-lg font-bold mb-4')
            
            # Grid of stats (2 columns on desktop, 1 on mobile)
            with ui.grid(columns=2).classes('w-full gap-4'):
                # Balance
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Balance').classes('text-sm text-gray-400')
                    self.balance_label = ui.label(
                        format_balance(app_state.balance, app_state.currency)
                    ).classes('text-2xl font-bold')
                
                # Profit/Loss
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Profit / Loss').classes('text-sm text-gray-400')
                    self.profit_label = ui.label(
                        format_profit(app_state.profit, app_state.profit_percent)
                    ).classes('text-2xl font-bold')
                
                # Total Bets
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Total Bets').classes('text-sm text-gray-400')
                    self.bets_label = ui.label(str(app_state.total_bets)).classes('text-2xl font-bold')
                
                # Win Rate
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Win Rate').classes('text-sm text-gray-400')
                    win_rate = 0
                    if app_state.total_bets > 0:
                        win_rate = (app_state.wins / app_state.total_bets) * 100
                    self.wins_label = ui.label(f'{win_rate:.1f}%').classes('text-2xl font-bold')
                
                # Wins
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Wins').classes('text-sm text-gray-400')
                    ui.label(str(app_state.wins)).classes('text-2xl font-bold text-green-500')
                
                # Losses
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Losses').classes('text-sm text-gray-400')
                    ui.label(str(app_state.losses)).classes('text-2xl font-bold text-red-500')
                
                # Current Streak
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Current Streak').classes('text-sm text-gray-400')
                    streak_text = f"{app_state.current_streak} {app_state.streak_type}"
                    color = 'text-green-500' if app_state.streak_type == 'win' else 'text-red-500'
                    self.streak_label = ui.label(streak_text).classes(f'text-2xl font-bold {color}')
                
                # Strategy
                with ui.card().classes('p-4 bg-gray-800'):
                    ui.label('Strategy').classes('text-sm text-gray-400')
                    ui.label(app_state.current_strategy).classes('text-xl font-bold')
    
    def _render_session_info(self):
        """Render session information"""
        with ui.card().classes('w-full'):
            ui.label('Session Info').classes('text-lg font-bold mb-2')
            
            with ui.column().classes('gap-2'):
                # Stop conditions
                if app_state.stop_profit:
                    ui.label(f'Stop at profit: +{app_state.stop_profit * 100:.1f}%').classes('text-sm')
                
                if app_state.stop_loss:
                    ui.label(f'Stop at loss: {app_state.stop_loss * 100:.1f}%').classes('text-sm')
                
                if app_state.max_bets:
                    ui.label(f'Max bets: {app_state.max_bets}').classes('text-sm')
                
                # Error display
                if app_state.last_error:
                    ui.label(f'⚠️ Error: {app_state.last_error}').classes('text-sm text-red-500')
    
    def _can_start(self) -> bool:
        """Check if bot can be started"""
        # Must have strategy
        if not app_state.current_strategy:
            return False
        
        # Must have API key if not in simulation
        if not app_state.simulation_mode and not app_state.api_key:
            return False
        
        # Must not be running
        if bot_controller.is_running():
            return False
        
        return True
    
    def _on_start(self):
        """Handle start button click"""
        try:
            # Get strategy parameters from app_state
            params = app_state.strategy_params.copy()
            
            # Add stop conditions
            params['stop_profit'] = app_state.stop_profit
            params['stop_loss'] = app_state.stop_loss
            params['max_bets'] = app_state.max_bets
            
            # Start bot
            bot_controller.set_update_callback(self.update_display)
            bot_controller.start(app_state.current_strategy, params)
            
            # Update UI
            self.update_display()
            
            ui.notify('Bot started', type='positive')
        except Exception as e:
            ui.notify(f'Failed to start: {str(e)}', type='negative')
    
    def _on_stop(self):
        """Handle stop button click"""
        bot_controller.stop()
        self.update_display()
        ui.notify('Bot stopped', type='warning')
    
    def _on_pause(self):
        """Handle pause button click"""
        bot_controller.pause()
        self.update_display()
        ui.notify('Bot paused', type='info')
    
    def _on_resume(self):
        """Handle resume button click"""
        bot_controller.resume()
        self.update_display()
        ui.notify('Bot resumed', type='positive')
    
    def _update_status_badge(self):
        """Update status badge based on current state"""
        if not self.status_badge:
            return
        
        if bot_controller.is_running():
            if bot_controller.is_paused():
                self.status_badge.set_text('PAUSED')
                self.status_badge.props('color=yellow')
            else:
                self.status_badge.set_text('RUNNING')
                self.status_badge.props('color=green')
        else:
            self.status_badge.set_text('IDLE')
            self.status_badge.props('color=gray')
    
    def update_display(self):
        """Update all display elements (called from bot thread)"""
        # Update status badge
        self._update_status_badge()
        
        # Update balance
        if self.balance_label:
            self.balance_label.set_text(format_balance(app_state.balance, app_state.currency))
        
        # Update profit
        if self.profit_label:
            profit_text = format_profit(app_state.profit, app_state.profit_percent)
            self.profit_label.set_text(profit_text)
            # Color based on profit/loss
            if app_state.profit > 0:
                self.profit_label.classes('text-2xl font-bold text-green-500', remove='text-2xl font-bold text-red-500')
            elif app_state.profit < 0:
                self.profit_label.classes('text-2xl font-bold text-red-500', remove='text-2xl font-bold text-green-500')
        
        # Update bet count
        if self.bets_label:
            self.bets_label.set_text(str(app_state.total_bets))
        
        # Update win rate
        if self.wins_label:
            win_rate = 0
            if app_state.total_bets > 0:
                win_rate = (app_state.wins / app_state.total_bets) * 100
            self.wins_label.set_text(f'{win_rate:.1f}%')
        
        # Update streak
        if self.streak_label:
            streak_text = f"{app_state.current_streak} {app_state.streak_type}"
            self.streak_label.set_text(streak_text)
        
        # Update button visibility
        is_running = bot_controller.is_running()
        is_paused = bot_controller.is_paused()
        
        if self.start_button:
            self.start_button.visible = not is_running
            self.start_button.enabled = self._can_start()
        
        if self.stop_button:
            self.stop_button.visible = is_running
        
        if self.pause_button:
            self.pause_button.visible = is_running and not is_paused
        
        if self.resume_button:
            self.resume_button.visible = is_running and is_paused
    
    def setup_timer(self):
        """Setup periodic UI updates (call after render)"""
        ui.timer(0.25, self.update_display)  # 250ms update cycle
