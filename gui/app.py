"""
NiceGUI Web Interface for DuckDice Bot
Main entry point - run with: python gui/app.py
"""

import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nicegui import ui
from gui.dashboard import Dashboard
from gui.strategies_ui import StrategiesUI
from gui.simulator import Simulator
from gui.history import History
from gui.settings import Settings
from gui.analytics_ui import AnalyticsUI
from gui.state import app_state
from gui.bot_controller import bot_controller


def main():
    """Initialize and run NiceGUI application"""
    
    # Initialize UI components
    dashboard = Dashboard()
    strategies_ui = StrategiesUI()
    simulator = Simulator()
    history = History()
    analytics_ui = AnalyticsUI()
    settings = Settings()
    
    # Main page
    @ui.page('/')
    def index():
        # Set dark mode by default
        ui.dark_mode().enable()
        
        # Header
        with ui.header().classes('items-center justify-between px-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('casino').classes('text-2xl')
                ui.label('DuckDice Bot').classes('text-xl font-bold')
            
            with ui.row().classes('items-center gap-2'):
                # Mode indicator
                mode_color = 'green' if app_state.simulation_mode else 'red'
                mode_text = 'SIMULATION' if app_state.simulation_mode else 'LIVE'
                ui.badge(mode_text).props(f'color={mode_color}')
                
                # Balance indicator
                ui.label(f'Balance: {app_state.balance:.8f} BTC').classes('text-sm')
        
        # Main content with tabs
        with ui.tabs().classes('w-full') as tabs:
            tab_dashboard = ui.tab('Dashboard', icon='dashboard')
            tab_strategies = ui.tab('Strategies', icon='psychology')
            tab_simulator = ui.tab('Simulator', icon='science')
            tab_history = ui.tab('History', icon='history')
            tab_analytics = ui.tab('Analytics', icon='analytics')
            tab_settings = ui.tab('Settings', icon='settings')
        
        with ui.tab_panels(tabs, value=tab_dashboard).classes('w-full'):
            # Dashboard tab
            with ui.tab_panel(tab_dashboard):
                dashboard.render()
                dashboard.setup_timer()
            
            # Strategies tab
            with ui.tab_panel(tab_strategies):
                strategies_ui.render()
            
            # Simulator tab
            with ui.tab_panel(tab_simulator):
                simulator.render()
            
            # History tab
            with ui.tab_panel(tab_history):
                history.render()
            
            # Analytics tab
            with ui.tab_panel(tab_analytics):
                analytics_ui.render()
            
            # Settings tab
            with ui.tab_panel(tab_settings):
                settings.render()
        
        # Footer
        with ui.footer().classes('justify-center'):
            ui.label('DuckDice Bot v3.9.0 | Built with NiceGUI').classes('text-xs text-gray-500')
    
    # Run the app
    ui.run(
        title='DuckDice Bot',
        favicon='🎲',
        host='127.0.0.1',
        port=8080,
        reload=False,
        show=True,  # Auto-open browser
        dark=True
    )


if __name__ == '__main__':
    main()
