"""
Settings page - API connection and configuration
First page users should visit to connect
"""

from nicegui import ui
from app.ui.components import (
    card, primary_button, secondary_button, input_field,
    select_field, toggle_switch, toast, loading_spinner
)
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend


def settings_content():
    """Settings page content"""
    
    ui.label('Settings').classes('text-3xl font-bold')
    ui.label('Configure your DuckDice connection').classes('text-sm text-slate-400 mb-6')
    
    # API Settings Card
    with card():
        ui.label('API Connection').classes('text-xl font-semibold mb-4')
        
        # API Key input
        api_key_input = input_field(
            label='API Key',
            placeholder='Enter your DuckDice API key',
            value=store.api_key,
            type='password'
        )
        
        ui.label('Get your API key from DuckDice.io → Settings → API').classes(
            'text-xs text-slate-400 mt-2 mb-4'
        )
        
        # Connection status
        status_container = ui.row().classes('items-center gap-2 mb-4')
        
        def update_status():
            status_container.clear()
            with status_container:
                if store.connected:
                    ui.icon('check_circle', color=Theme.ACCENT)
                    ui.label(f'Connected as {store.username}').classes('text-sm font-medium')
                else:
                    ui.icon('error', color=Theme.ERROR)
                    ui.label('Not connected').classes('text-sm text-slate-400')
        
        update_status()
        
        # Connect/Disconnect button
        async def handle_connection():
            if store.connected:
                await backend.disconnect()
                toast('Disconnected', 'info')
                update_status()
                connect_btn.set_text('Connect')
                ui.navigate.to('/settings')
            else:
                api_key = api_key_input.value
                if not api_key:
                    toast('Please enter an API key', 'error')
                    return
                
                connect_btn.props('loading')
                success, message = await backend.connect(api_key)
                connect_btn.props(remove='loading')
                
                if success:
                    toast(message, 'success')
                    update_status()
                    connect_btn.set_text('Disconnect')
                    ui.navigate.to('/')
                else:
                    toast(message, 'error')
        
        connect_btn = primary_button(
            'Connect' if not store.connected else 'Disconnect',
            on_click=handle_connection,
            icon='wifi' if not store.connected else 'wifi_off'
        )
    
    # Betting Preferences
    with card().classes('mt-6'):
        ui.label('Betting Preferences').classes('text-xl font-semibold mb-4')
        
        # Default currency
        if store.available_currencies:
            currency_select = select_field(
                label='Default Currency',
                options=store.available_currencies,
                value=store.currency,
                on_change=lambda e: setattr(store, 'currency', e.value)
            )
        else:
            ui.label('Connect to load currencies').classes('text-sm text-slate-400')
        
        # Default mode
        mode_select = select_field(
            label='Default Mode',
            options=['simulation', 'live'],
            value=store.mode,
            on_change=lambda e: setattr(store, 'mode', e.value)
        )
        
        # Default betting mode
        betting_mode_select = select_field(
            label='Default Betting Mode',
            options=['main', 'faucet'],
            value=store.betting_mode,
            on_change=lambda e: setattr(store, 'betting_mode', e.value)
        )
    
    # Faucet Settings
    with card().classes('mt-6'):
        ui.label('Faucet Configuration').classes('text-xl font-semibold mb-4')
        
        # Cookie input
        cookie_input = input_field(
            label='Browser Cookie',
            placeholder='Paste your browser cookie here',
            value=store.faucet_cookie,
            type='password'
        )
        
        ui.label('Copy cookie from browser DevTools → Network → any request → Cookie header').classes(
            'text-xs text-slate-400 mt-2 mb-4'
        )
        
        # Save cookie button
        def save_cookie():
            cookie = cookie_input.value
            if cookie:
                backend.save_faucet_cookie(cookie)
                toast('Cookie saved', 'success')
            else:
                toast('Please enter a cookie', 'error')
        
        secondary_button('Save Cookie', on_click=save_cookie, icon='save')
        
        # Auto-claim toggle
        ui.separator().classes('my-4')
        
        auto_claim_switch = toggle_switch(
            label='Enable Auto-Claim (60s interval)',
            value=store.faucet_auto_claim,
            on_change=lambda e: setattr(store, 'faucet_auto_claim', e.value)
        )
    
    # Statistics
    with card().classes('mt-6'):
        ui.label('Session Management').classes('text-xl font-semibold mb-4')
        
        ui.label(f'Total Bets: {store.total_bets}').classes('text-sm')
        ui.label(f'Profit/Loss: {store.profit:.8f} {store.currency}').classes('text-sm')
        
        def reset_stats():
            store.reset_statistics()
            toast('Statistics reset', 'success')
            ui.navigate.to('/settings')
        
        secondary_button(
            'Reset Statistics',
            on_click=reset_stats,
            icon='refresh'
        ).classes('mt-4')
