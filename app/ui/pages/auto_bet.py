"""
Auto Bet page - automated betting with strategies
"""

from nicegui import ui
from app.ui.components import (
    card, primary_button, danger_button, secondary_button,
    select_field, number_input, empty_state, toast
)
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend


def auto_bet_content():
    """Auto bet page content"""
    
    # Connection check
    if not store.connected:
        empty_state(
            'wifi_off',
            'Not Connected',
            'Connect your API key to use auto-betting',
            'Go to Settings',
            lambda: ui.navigate.to('/settings')
        )
        return
    
    ui.label('🤖 Auto Bet').classes('text-3xl font-bold')
    ui.label('Automated betting with professional strategies').classes('text-sm text-slate-400 mb-6')
    
    # Strategy selection
    with card():
        ui.label('Select Strategy').classes('text-lg font-semibold mb-4')
        
        strategies = backend.get_strategies()
        strategy_options = {s['name']: s['id'] for s in strategies}
        
        strategy_select = select_field(
            label='Betting Strategy',
            options=list(strategy_options.keys()),
            value=list(strategy_options.keys())[0] if strategy_options else None
        )
        
        # Strategy info
        def show_strategy_info():
            selected_name = strategy_select.value
            if selected_name:
                strategy = next((s for s in strategies if s['name'] == selected_name), None)
                if strategy:
                    with ui.row().classes('items-center gap-2 mt-3 p-3 rounded-lg').style(
                        f'background-color: {Theme.BG_TERTIARY}'
                    ):
                        ui.label(strategy.get('description', 'No description')).classes('text-sm')
        
        show_strategy_info()
        strategy_select.on_value_change(lambda: show_strategy_info())
        
        # Browse strategies button
        secondary_button(
            'Browse All Strategies',
            on_click=lambda: ui.navigate.to('/strategies'),
            icon='strategy'
        ).classes('mt-4')
    
    # Betting configuration
    with card().classes('mt-6'):
        ui.label('Betting Configuration').classes('text-lg font-semibold mb-4')
        
        # Base bet
        base_bet = number_input(
            label='Base Bet Amount',
            value=0.00000001,
            min_value=0.00000001,
            suffix=store.currency
        )
        
        # Number of bets
        max_bets = number_input(
            label='Maximum Bets (0 = unlimited)',
            value=100,
            min_value=0,
            step=1
        )
    
    # Risk management
    with card().classes('mt-6'):
        ui.label('Risk Management').classes('text-lg font-semibold mb-4')
        
        # Stop loss
        stop_loss = number_input(
            label='Stop Loss (0 = disabled)',
            value=0.0,
            min_value=0.0,
            suffix=store.currency
        )
        
        # Take profit
        take_profit = number_input(
            label='Take Profit (0 = disabled)',
            value=0.0,
            min_value=0.0,
            suffix=store.currency
        )
        
        # Warning
        with ui.row().classes('items-center gap-2 mt-4 p-3 rounded-lg').style(
            f'background-color: {Theme.WARNING}20; border-left: 3px solid {Theme.WARNING}'
        ):
            ui.icon('warning', color=Theme.WARNING)
            ui.label('Always set stop-loss limits to protect your balance').classes('text-sm')
    
    # Start/Stop buttons
    with ui.row().classes('gap-4 mt-6'):
        async def start_auto_bet():
            if store.mode == 'live':
                # Show confirmation for live mode
                toast('Auto-bet not fully implemented yet', 'warning')
                # In full implementation, this would start the betting loop
            else:
                toast('Simulation mode auto-bet coming soon', 'info')
        
        def stop_auto_bet():
            store.auto_bet_running = False
            toast('Auto-bet stopped', 'info')
        
        if not store.auto_bet_running:
            primary_button(
                '▶️ Start Auto-Bet',
                on_click=start_auto_bet,
                icon='play_arrow'
            ).style('font-size: 1.1rem; padding: 1rem 2rem')
        else:
            danger_button(
                '⏸️ Stop Auto-Bet',
                on_click=stop_auto_bet,
                icon='stop'
            ).style('font-size: 1.1rem; padding: 1rem 2rem')
    
    # Progress (if running)
    if store.auto_bet_running:
        with card().classes('mt-6'):
            ui.label('Auto-Bet Progress').classes('text-lg font-semibold mb-4')
            
            with ui.row().classes('w-full gap-4'):
                ui.label(f'Bets Placed: {store.auto_bet_count}').classes('text-sm')
                ui.label(f'Profit: {store.profit:.8f}').classes('text-sm')
                ui.label(f'Win Rate: {store.win_rate:.1f}%').classes('text-sm')
    
    # Tips
    with card().classes('mt-6'):
        ui.label('💡 Tips').classes('text-lg font-semibold mb-3')
        
        tips = [
            'Test strategies in simulation mode first',
            'Always set realistic stop-loss limits',
            'Monitor progress regularly',
            'Different strategies work better in different conditions',
            'Consider using lower-risk strategies for longer sessions',
        ]
        
        for tip in tips:
            with ui.row().classes('items-start gap-2 mb-2'):
                ui.icon('lightbulb', size='sm', color=Theme.WARNING)
                ui.label(tip).classes('text-sm text-slate-300')
