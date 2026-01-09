"""
Consolidated Betting page - Quick Bet and Auto Bet in tabs
"""

import asyncio
from nicegui import ui
from app.ui.components import (
    card, primary_button, secondary_button, danger_button,
    number_input, select_field, toast, empty_state
)
from app.ui.components.common import (
    balance_display, bet_controls, loading_spinner,
    warning_banner, confirm_dialog, metric_card
)
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend


def betting_content():
    """Main betting page with Quick Bet and Auto Bet tabs"""
    
    # Connection check
    if not store.connected:
        empty_state(
            'wifi_off',
            'Not Connected',
            'Connect your API key to start betting',
            'Go to Settings',
            lambda: ui.navigate.to('/settings')
        )
        return
    
    ui.label('Betting').classes('text-3xl font-bold mb-2')
    ui.label('Place manual bets or run automated strategies').classes('text-sm text-slate-400 mb-6')
    
    # Tabs
    with ui.tabs().classes('w-full') as tabs:
        quick_tab = ui.tab('🎲 Quick Bet')
        auto_tab = ui.tab('🤖 Auto Bet')
    
    with ui.tab_panels(tabs, value=quick_tab).classes('w-full'):
        with ui.tab_panel(quick_tab):
            quick_bet_panel()
        
        with ui.tab_panel(auto_tab):
            auto_bet_panel()


def quick_bet_panel():
    """Quick bet panel content"""
    
    # Mode toggles
    with card():
        ui.label('Betting Mode').classes('text-lg font-semibold mb-4')
        
        # Responsive layout: stack on mobile, row on desktop
        with ui.column().classes('gap-4 sm:flex-row'):
            # Simulation/Live toggle
            mode_group = ui.radio(
                ['simulation', 'live'],
                value=store.mode,
                on_change=lambda e: setattr(store, 'mode', e.value)
            ).props('inline')
            
            mode_group.classes('gap-4')
            
            # Main/Faucet toggle
            betting_mode_group = ui.radio(
                ['main', 'faucet'],
                value=store.betting_mode,
                on_change=lambda e: setattr(store, 'betting_mode', e.value)
            ).props('inline')
            
            betting_mode_group.classes('gap-4')
        
        # Warning for live mode
        if store.mode == 'live':
            warning_banner('⚠️ Live mode will use real funds!')
        
        # House edge display
        house_edge = store.get_house_edge() * 100
        ui.label(f'House Edge: {house_edge:.0f}%').classes('text-sm text-slate-400 mt-2')
    
    # Bet configuration
    with card().classes('mt-6'):
        ui.label('Bet Configuration').classes('text-lg font-semibold mb-4')
        
        # Currency selector
        currency_select = select_field(
            label='Currency',
            options=store.available_currencies,
            value=store.currency,
            on_change=lambda e: setattr(store, 'currency', e.value)
        )
        
        # Balance display
        current_balance = store.get_current_balance()
        balance_text = f'Available: {current_balance:.8f} {store.currency}'
        ui.label(balance_text).classes('text-sm text-slate-400 mb-4').bind_text_from(
            store, 'main_balance' if store.betting_mode == 'main' else 'faucet_balance',
            lambda b: f'Available: {b:.8f} {store.currency}'
        )
        
        # Bet amount
        bet_amount = number_input(
            label='Bet Amount',
            value=0.00000001,
            min_value=0.00000001,
            max_value=current_balance,
            step=0.00000001,
            suffix=store.currency
        )
        
        # Quick amount buttons - responsive flex wrap
        with ui.row().classes('gap-2 mt-2 flex-wrap'):
            for pct, label in [(0.1, '10%'), (0.25, '25%'), (0.5, '50%'), (1.0, 'All')]:
                ui.button(
                    label,
                    on_click=lambda p=pct: bet_amount.set_value(current_balance * p)
                ).props('flat dense').classes('text-xs min-h-[44px] min-w-[60px]')  # Touch-friendly size
        
        # Win chance slider
        with ui.column().classes('w-full gap-2 mt-6'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Win Chance').classes('text-sm font-medium')
                chance_label = ui.label('50.00%').classes('text-sm font-bold').style(
                    f'color: {Theme.PRIMARY}'
                )
            
            chance_slider = ui.slider(
                min=0.01,
                max=98.0,
                value=50.0,
                step=0.01
            ).props('label-always').classes('w-full').style(f'color: {Theme.PRIMARY}')
            
            # Update label on change
            chance_slider.on_value_change(
                lambda e: chance_label.set_text(f'{e.value:.2f}%')
            )
        
        # Target (over/under)
        target_select = ui.radio(
            ['over', 'under'],
            value='over'
        ).props('inline').classes('mt-4')
        
        # Potential payout calculation
        with ui.row().classes('items-center gap-2 mt-6 p-3 rounded-lg').style(
            f'background-color: {Theme.BG_TERTIARY}'
        ):
            ui.label('Potential Payout:').classes('text-sm text-slate-400')
            
            def calc_payout():
                amount = bet_amount.value or 0
                chance = chance_slider.value or 50
                house_edge = store.get_house_edge()
                payout = (amount * (100 - house_edge * 100)) / chance if chance > 0 else 0
                return f'{payout:.8f} {store.currency}'
            
            payout_label = ui.label(calc_payout()).classes('text-sm font-bold').style(
                f'color: {Theme.ACCENT}'
            )
            
            # Update on changes
            bet_amount.on_value_change(lambda: payout_label.set_text(calc_payout()))
            chance_slider.on_value_change(lambda: payout_label.set_text(calc_payout()))
    
    # Place bet button
    async def place_bet():
        amount = bet_amount.value
        chance = chance_slider.value
        target = 100 - chance if target_select.value == 'over' else chance
        
        if amount <= 0:
            toast('Please enter a valid bet amount', 'error')
            return
        
        if amount > current_balance:
            toast('Insufficient balance', 'error')
            return
        
        # Disable button and show loading
        roll_btn.props('loading')
        roll_btn.props('disable')
        
        success, message, result = await backend.place_bet(
            amount=amount,
            chance=chance,
            target=target
        )
        
        # Re-enable button
        roll_btn.props(remove='loading')
        roll_btn.props(remove='disable')
        
        if success and result:
            # Show animated result
            with ui.dialog() as result_dialog, ui.card().classes('p-6 text-center'):
                # Result icon
                if result.is_win:
                    ui.icon('celebration', size='4rem', color=Theme.ACCENT).classes('mb-4')
                    ui.label('🎉 WIN!').classes('text-3xl font-bold mb-2').style(f'color: {Theme.ACCENT}')
                    ui.label(f'+{result.profit:.8f} {store.currency}').classes('text-2xl font-bold')
                else:
                    ui.icon('sentiment_dissatisfied', size='4rem', color=Theme.ERROR).classes('mb-4')
                    ui.label('Better Luck Next Time').classes('text-2xl font-bold mb-2').style(f'color: {Theme.ERROR}')
                    ui.label(f'{result.profit:.8f} {store.currency}').classes('text-xl font-bold')
                
                ui.separator().classes('my-4')
                
                # Bet details
                with ui.column().classes('gap-1 text-left w-full'):
                    ui.label(f'Roll: {result.result:.2f}').classes('text-sm text-slate-400')
                    ui.label(f'Target: {result.target:.2f} ({target_select.value})').classes('text-sm text-slate-400')
                    ui.label(f'Chance: {result.chance:.2f}%').classes('text-sm text-slate-400')
                
                secondary_button('Close', on_click=lambda: result_dialog.close(), icon='close').classes('mt-4 w-full')
            
            result_dialog.open()
            
            # Also show toast
            if result.is_win:
                toast(f'🎉 WIN! +{result.profit:.8f} {store.currency}', 'success')
            else:
                toast(f'❌ Loss: {result.profit:.8f} {store.currency}', 'error')
            
            # Refresh balances
            await backend.refresh_balances()
        else:
            toast(message, 'error')
    
    roll_btn = primary_button(
        '🎲 Roll Dice',
        on_click=place_bet,
        icon='casino'
    ).classes('mt-6 w-full').style('font-size: 1.25rem; padding: 1rem')
    
    # Recent results
    if store.bet_history:
        with card().classes('mt-6'):
            ui.label('Recent Results').classes('text-lg font-semibold mb-4')
            
            for bet in store.bet_history[:5]:
                with ui.row().classes('items-center justify-between p-2 rounded').style(
                    f'background-color: {Theme.BG_TERTIARY}'
                ):
                    with ui.column().classes('gap-1'):
                        ui.label(f'{bet.amount:.8f} @ {bet.chance:.2f}%').classes('text-sm')
                        ui.label(bet.timestamp.strftime('%H:%M:%S')).classes('text-xs text-slate-400')
                    
                    profit_color = Theme.ACCENT if bet.is_win else Theme.ERROR
                    icon = '✓' if bet.is_win else '✗'
                    ui.label(f'{icon} {bet.profit:.8f}').classes('text-sm font-bold').style(
                        f'color: {profit_color}'
                    )


def auto_bet_panel():
    """Auto bet panel content"""
    
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
            on_click=lambda: ui.navigate.to('/library'),
            icon='library_books'
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
        warning_banner('Always set stop-loss limits to protect your balance')
    
    # Start/Stop buttons
    with ui.row().classes('gap-4 mt-6'):
        async def start_auto_bet():
            # Get selected strategy ID
            selected_name = strategy_select.value
            if not selected_name:
                toast('Please select a strategy', 'error')
                return
            
            strategy = next((s for s in strategies if s['name'] == selected_name), None)
            if not strategy:
                toast('Strategy not found', 'error')
                return
            
            # Validate inputs
            if base_bet.value <= 0:
                toast('Base bet must be greater than 0', 'error')
                return
            
            # Confirmation for live mode
            if store.mode == 'live':
                def do_start():
                    asyncio.create_task(_start_auto_bet_task())
                
                confirm_dialog(
                    title='Start Live Auto-Bet?',
                    message=f'This will use REAL funds with {strategy["name"]} strategy. Continue?',
                    on_confirm=do_start,
                    confirm_text='Start',
                    danger=True
                )
            else:
                await _start_auto_bet_task()
        
        async def _start_auto_bet_task():
            selected_name = strategy_select.value
            strategy = next((s for s in strategies if s['name'] == selected_name), None)
            
            success, message = await backend.start_auto_bet(
                strategy_id=strategy['id'],
                base_bet=base_bet.value,
                max_bets=int(max_bets.value),
                stop_loss=stop_loss.value,
                take_profit=take_profit.value
            )
            
            if success:
                toast(message, 'success')
                ui.navigate.to('/betting')  # Refresh page
            else:
                toast(message, 'error')
        
        async def stop_auto_bet():
            await backend.stop_auto_bet()
            toast('Auto-bet stopped', 'info')
            ui.navigate.to('/betting')
        
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
                metric_card('Bets Placed', str(store.auto_bet_count), 'casino')
                metric_card('Profit', f'{store.profit:.8f}', 'trending_up')
                metric_card('Win Rate', f'{store.win_rate:.1f}%', 'percent')
    
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
