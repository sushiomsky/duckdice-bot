"""
DuckDice Bot - NiceGUI Edition
Main entry point with routing
"""

from typing import Dict
from nicegui import ui, app
from app.ui.layout import create_layout
from app.ui.pages.dashboard import dashboard_content
from app.ui.pages.settings import settings_content
from app.ui.pages.quick_bet import quick_bet_content
from app.ui.pages.auto_bet import auto_bet_content
from app.ui.pages.faucet import faucet_content
from app.ui.pages.strategies import strategies_content
from app.ui.pages.history import history_content
from app.ui.pages.script_browser import create_script_browser_page
from app.ui.pages.script_editor import create_script_editor_page
from app.ui.pages.simulator import simulator_content
from app.ui.theme import Theme
from app.config import KEYBOARD_SHORTCUTS, DEFAULT_PORT
from app.utils.logger import log_info


# Configure app
app.add_static_files('/assets', 'app/assets')


# Keyboard shortcuts handler
def setup_keyboard_shortcuts() -> None:
    """Setup global keyboard shortcuts"""
    ui.keyboard(
        on_key=lambda e: handle_keyboard_event(e.key, e.modifiers)
    )


def handle_keyboard_event(key: str, modifiers: Dict) -> None:
    """Handle keyboard shortcuts"""
    ctrl = modifiers.get('ctrl', False) or modifiers.get('meta', False)
    
    if not ctrl:
        return
    
    if key in KEYBOARD_SHORTCUTS:
        ui.navigate.to(KEYBOARD_SHORTCUTS[key])


@ui.page('/')
def index_page() -> None:
    """Dashboard - main page"""
    setup_keyboard_shortcuts()
    create_layout(dashboard_content)


@ui.page('/quick-bet')
def quick_bet_page() -> None:
    """Quick bet page"""
    create_layout(quick_bet_content)


@ui.page('/auto-bet')
def auto_bet_page() -> None:
    """Auto bet page"""
    create_layout(auto_bet_content)


@ui.page('/faucet')
def faucet_page() -> None:
    """Faucet page"""
    create_layout(faucet_content)


@ui.page('/strategies')
def strategies_page() -> None:
    """Strategies browser"""
    create_layout(strategies_content)


@ui.page('/history')
def history_page() -> None:
    """Bet history"""
    create_layout(history_content)


@ui.page('/settings')
def settings_page() -> None:
    """Settings and configuration"""
    create_layout(settings_content)


@ui.page('/scripts')
def scripts_browser_page() -> None:
    """Script browser"""
    def scripts_content() -> None:
        create_script_browser_page()
    
    create_layout(scripts_content)


@ui.page('/scripts/editor')
def scripts_editor_page(name: str = None, template: str = None, new: str = None) -> None:
    """Script editor"""
    def editor_content() -> None:
        # Build query params dict
        query_params = {}
        if name:
            query_params['name'] = [name]
        if template:
            query_params['template'] = [template]
        if new:
            query_params['new'] = [new]
        
        create_script_editor_page(query_params)
    
    create_layout(editor_content)


@ui.page('/simulator')
def simulator_page() -> None:
    """Simulator page"""
    create_layout(simulator_content)


@ui.page('/help')
def help_page() -> None:
    """Help page"""
    def help_content() -> None:
        from app.ui.components import card
        
        ui.label('❓ Help').classes('text-3xl font-bold')
        ui.label('Getting started with DuckDice Bot').classes('text-sm text-slate-400 mb-6')
        
        with card():
            ui.label('Quick Start Guide').classes('text-xl font-semibold mb-4')
            
            steps = [
                ('1️⃣', 'Go to Settings and enter your DuckDice API key'),
                ('2️⃣', 'Click Connect to establish connection'),
                ('3️⃣', 'Choose between Simulation (safe testing) or Live (real bets)'),
                ('4️⃣', 'Use Quick Bet for manual betting or Auto Bet for automation'),
                ('5️⃣', 'Monitor your progress on the Dashboard'),
            ]
            
            for emoji, text in steps:
                with ui.row().classes('items-start gap-3 mb-3'):
                    ui.label(emoji).classes('text-2xl')
                    ui.label(text).classes('text-sm text-slate-300')
        
        with card().classes('mt-6'):
            ui.label('Keyboard Shortcuts').classes('text-xl font-semibold mb-4')
            
            shortcuts = [
                ('Ctrl+B', 'Quick Bet'),
                ('Ctrl+A', 'Auto Bet'),
                ('Ctrl+F', 'Faucet'),
                ('Ctrl+H', 'History'),
                ('Ctrl+S', 'Settings'),
            ]
            
            for keys, action in shortcuts:
                with ui.row().classes('items-center justify-between mb-2'):
                    ui.label(keys).classes('text-sm font-mono px-2 py-1 rounded').style(
                        f'background-color: {Theme.BG_TERTIARY}'
                    )
                    ui.label(action).classes('text-sm text-slate-400')
    
    create_layout(help_content)


@ui.page('/about')
def about_page() -> None:
    """About page"""
    def about_content() -> None:
        from app.ui.components import card
        
        ui.label('ℹ️ About').classes('text-3xl font-bold')
        ui.label('DuckDice Bot v3.2.0').classes('text-sm text-slate-400 mb-6')
        
        with card():
            ui.label('DuckDice Bot - NiceGUI Edition').classes('text-xl font-semibold mb-4')
            
            ui.label(
                'Advanced betting automation for DuckDice.io with modern web interface'
            ).classes('text-sm text-slate-300 mb-4')
            
            features = [
                '🎲 Manual and automated betting',
                '📊 16 professional strategies',
                '🚰 Faucet mode with auto-claim',
                '📈 Real-time statistics tracking',
                '🎨 Modern dark-mode interface',
                '📱 Mobile-responsive design',
            ]
            
            for feature in features:
                ui.label(feature).classes('text-sm text-slate-300 mb-2')
            
            ui.separator().classes('my-4')
            
            ui.label('MIT License © 2025').classes('text-xs text-slate-500')
            ui.label('https://github.com/sushiomsky/duckdice-bot').classes('text-xs text-slate-500')
    
    create_layout(about_content)


# Run the application
if __name__ in {'__main__', '__mp_main__'}:
    log_info("Starting DuckDice Bot NiceGUI server", port=DEFAULT_PORT)
    ui.run(
        title='DuckDice Bot',
        port=DEFAULT_PORT,
        reload=False,
        show=True,
        dark=True,
        favicon='🎲'
    )
