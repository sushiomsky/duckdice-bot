"""
Settings and configuration screen.
API keys, stop conditions, preferences.
"""

from nicegui import ui
from gui.state import app_state
from gui.utils import validate_api_key, validate_bet_amount


class Settings:
    """Settings and configuration interface"""
    
    def __init__(self):
        self.api_key_input = None
        self.test_connection_button = None
        self.simulation_mode_switch = None
        self.dark_mode_switch = None
        
        # Stop conditions
        self.max_profit_input = None
        self.max_loss_input = None
        self.max_bets_input = None
        self.min_balance_input = None
        
    def render(self):
        """Render settings UI"""
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.card().classes('w-full'):
                ui.label('Settings').classes('text-2xl font-bold')
                ui.label('Configure API access and bot behavior').classes('text-gray-500')
            
            # API Configuration
            self._render_api_settings()
            
            # Stop Conditions
            self._render_stop_conditions()
            
            # Preferences
            self._render_preferences()
            
            # Advanced
            self._render_advanced()
    
    def _render_api_settings(self):
        """Render API configuration section"""
        with ui.card().classes('w-full'):
            ui.label('API Configuration').classes('text-lg font-semibold mb-2')
            
            # Warning about live mode
            with ui.row().classes('w-full items-center gap-2 p-2 bg-yellow-100 rounded'):
                ui.icon('warning').classes('text-yellow-600')
                ui.label('Live mode uses real money. Test thoroughly in simulation mode first.').classes('text-sm text-yellow-800')
            
            ui.space().classes('h-2')
            
            # API Key
            with ui.row().classes('w-full gap-2'):
                self.api_key_input = ui.input(
                    label='DuckDice API Key',
                    placeholder='Enter your API key',
                    password=True,
                    password_toggle_button=True,
                    value=app_state.api_key or '',
                    on_change=lambda e: self._on_api_key_change(e.value)
                ).classes('flex-grow')
                
                self.test_connection_button = ui.button(
                    'Test Connection',
                    on_click=self._test_connection,
                    icon='wifi'
                ).props('outline')
            
            ui.label('Get your API key from DuckDice settings').classes('text-xs text-gray-500')
            
            # Currency (hardcoded to BTC for now)
            ui.space().classes('h-2')
            with ui.row().classes('w-full items-center gap-2'):
                ui.label('Currency:').classes('text-sm font-semibold')
                ui.label('BTC (Bitcoin)').classes('text-sm')
    
    def _render_stop_conditions(self):
        """Render stop condition settings"""
        with ui.card().classes('w-full'):
            ui.label('Stop Conditions').classes('text-lg font-semibold mb-2')
            ui.label('Bot will stop automatically when any condition is met').classes('text-sm text-gray-500 mb-4')
            
            with ui.grid(columns=2).classes('w-full gap-4'):
                # Profit target
                with ui.column().classes('gap-1'):
                    ui.label('Max Profit %').classes('text-sm font-semibold')
                    self.max_profit_input = ui.number(
                        label='Stop when profit reaches (%)',
                        value=app_state.stop_profit_pct or 0,
                        min=0,
                        max=1000,
                        step=1,
                        format='%.1f',
                        on_change=lambda e: app_state.update(stop_profit_pct=e.value if e.value > 0 else None)
                    ).classes('w-full')
                    ui.label('0 = disabled').classes('text-xs text-gray-500')
                
                # Loss limit
                with ui.column().classes('gap-1'):
                    ui.label('Max Loss %').classes('text-sm font-semibold')
                    self.max_loss_input = ui.number(
                        label='Stop when loss reaches (%)',
                        value=app_state.stop_loss_pct or 0,
                        min=0,
                        max=100,
                        step=1,
                        format='%.1f',
                        on_change=lambda e: app_state.update(stop_loss_pct=e.value if e.value > 0 else None)
                    ).classes('w-full')
                    ui.label('0 = disabled').classes('text-xs text-gray-500')
                
                # Max bets
                with ui.column().classes('gap-1'):
                    ui.label('Max Bets').classes('text-sm font-semibold')
                    self.max_bets_input = ui.number(
                        label='Stop after N bets',
                        value=app_state.max_bets or 0,
                        min=0,
                        max=100000,
                        step=10,
                        on_change=lambda e: app_state.update(max_bets=int(e.value) if e.value > 0 else None)
                    ).classes('w-full')
                    ui.label('0 = unlimited').classes('text-xs text-gray-500')
                
                # Min balance
                with ui.column().classes('gap-1'):
                    ui.label('Min Balance').classes('text-sm font-semibold')
                    self.min_balance_input = ui.number(
                        label='Stop when balance falls below (BTC)',
                        value=app_state.min_balance or 0,
                        min=0,
                        step=0.0001,
                        format='%.8f',
                        on_change=lambda e: app_state.update(min_balance=e.value if e.value > 0 else None)
                    ).classes('w-full')
                    ui.label('0 = disabled').classes('text-xs text-gray-500')
    
    def _render_preferences(self):
        """Render general preferences"""
        with ui.card().classes('w-full'):
            ui.label('Preferences').classes('text-lg font-semibold mb-2')
            
            with ui.column().classes('w-full gap-3'):
                # Simulation mode toggle
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label('Simulation Mode').classes('text-sm font-semibold')
                        ui.label('Practice with fake bets (recommended for testing)').classes('text-xs text-gray-500')
                    
                    self.simulation_mode_switch = ui.switch(
                        value=app_state.simulation_mode,
                        on_change=lambda e: self._toggle_simulation_mode(e.value)
                    )
                
                ui.separator()
                
                # Dark mode toggle
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label('Dark Mode').classes('text-sm font-semibold')
                        ui.label('Use dark theme for UI').classes('text-xs text-gray-500')
                    
                    self.dark_mode_switch = ui.switch(
                        value=True,
                        on_change=lambda e: self._toggle_dark_mode(e.value)
                    )
                
                ui.separator()
                
                # Update interval
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1 flex-grow'):
                        ui.label('Update Interval').classes('text-sm font-semibold')
                        ui.label('How often to refresh UI (milliseconds)').classes('text-xs text-gray-500')
                    
                    ui.number(
                        value=250,
                        min=100,
                        max=5000,
                        step=50,
                        suffix='ms'
                    ).classes('w-32')
    
    def _render_advanced(self):
        """Render advanced settings"""
        with ui.card().classes('w-full'):
            ui.label('Advanced').classes('text-lg font-semibold mb-2')
            
            with ui.column().classes('w-full gap-3'):
                # Bet delay
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1 flex-grow'):
                        ui.label('Bet Delay').classes('text-sm font-semibold')
                        ui.label('Delay between bets to avoid rate limits').classes('text-xs text-gray-500')
                    
                    ui.number(
                        value=1.0,
                        min=0.1,
                        max=10.0,
                        step=0.1,
                        suffix='sec',
                        format='%.1f',
                        on_change=lambda e: app_state.update(bet_delay=e.value)
                    ).classes('w-32')
                
                ui.separator()
                
                # Log level
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1 flex-grow'):
                        ui.label('Log Level').classes('text-sm font-semibold')
                        ui.label('Verbosity of console logs').classes('text-xs text-gray-500')
                    
                    ui.select(
                        options=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        value='INFO'
                    ).classes('w-32')
    
    def _on_api_key_change(self, value: str):
        """Handle API key input change"""
        app_state.update(api_key=value if value else None)
    
    def _test_connection(self):
        """Test API connection"""
        if not app_state.api_key:
            ui.notify('Please enter an API key first', type='warning')
            return
        
        if not validate_api_key(app_state.api_key):
            ui.notify('API key format appears invalid', type='negative')
            return
        
        # In a real implementation, this would ping the DuckDice API
        ui.notify('API connection test not yet implemented', type='info')
        
        # TODO: Implement actual API test
        # try:
        #     client = DuckDiceClient(app_state.api_key)
        #     balance = client.get_balance()
        #     app_state.update(balance=balance)
        #     ui.notify(f'Connection successful! Balance: {format_balance(balance)}', type='positive')
        # except APIError as e:
        #     ui.notify(f'Connection failed: {str(e)}', type='negative')
    
    def _toggle_simulation_mode(self, enabled: bool):
        """Toggle simulation mode"""
        app_state.update(simulation_mode=enabled)
        
        if enabled:
            ui.notify('Simulation mode enabled - bets will be simulated', type='positive')
        else:
            ui.notify('⚠️ Live mode enabled - real money will be used!', type='warning')
    
    def _toggle_dark_mode(self, enabled: bool):
        """Toggle dark mode"""
        if enabled:
            ui.run_javascript('document.body.classList.add("dark")')
            ui.notify('Dark mode enabled', type='info')
        else:
            ui.run_javascript('document.body.classList.remove("dark")')
            ui.notify('Light mode enabled', type='info')
