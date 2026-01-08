"""Dashboard page - first thing users see"""

from nicegui import ui
from app.ui.components import card, stat_card, primary_button, secondary_button, empty_state, toast
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend


async def handle_refresh():
    success = await backend.refresh_balances()
    toast('Balances updated' if success else 'Refresh failed', 'success' if success else 'error')


def dashboard_content():
    if not store.connected:
        empty_state('wifi_off', 'Not Connected', 'Connect your API key to start', 'Connect Now', lambda: ui.navigate.to('/settings'))
        return
    
    with ui.row().classes('w-full items-center justify-between'):
        ui.label(f'Welcome, {store.username}').classes('text-3xl font-bold')
        secondary_button('Refresh', handle_refresh, 'refresh')
    
    with ui.row().classes('w-full gap-4 mt-6'):
        with card().classes('flex-1'):
            ui.label('💰 Main Balance').classes('text-sm text-slate-400')
            ui.label(f'{store.main_balance:.8f} {store.currency}').classes('text-2xl font-bold')
        with card().classes('flex-1'):
            ui.label('🚰 Faucet Balance').classes('text-sm text-slate-400')
            ui.label(f'{store.faucet_balance:.8f} {store.currency}').classes('text-2xl font-bold')
    
    ui.label('Statistics').classes('text-xl font-semibold mt-6')
    with ui.row().classes('w-full gap-4'):
        stat_card('Bets', store.total_bets)
        stat_card('Win Rate', f'{store.win_rate:.1f}%')
        stat_card('Profit', f'{store.profit:.8f}', color=Theme.ACCENT if store.profit >= 0 else Theme.ERROR)
        stat_card('Streak', abs(store.streak), prefix='🔥 ' if store.streak > 0 else '❄️ ')
