"""
Faucet page - claim faucet and configure auto-claim
"""

from nicegui import ui
from app.ui.components import (
    card, primary_button, secondary_button, input_field,
    toggle_switch, toast, empty_state
)
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend
from datetime import datetime, timedelta
import asyncio


async def update_countdown(label, next_claim_time):
    """Update countdown timer"""
    while True:
        if not next_claim_time:
            label.set_text('Ready to claim!')
            break
        
        now = datetime.now()
        if now >= next_claim_time:
            label.set_text('Ready to claim!')
            break
        
        remaining = int((next_claim_time - now).total_seconds())
        label.set_text(f'⏳ Next claim in {remaining}s')
        await asyncio.sleep(1)


def faucet_content():
    """Faucet page content"""
    
    # Connection check
    if not store.connected:
        empty_state(
            'wifi_off',
            'Not Connected',
            'Connect your API key first',
            'Go to Settings',
            lambda: ui.navigate.to('/settings')
        )
        return
    
    ui.label('🚰 Faucet').classes('text-3xl font-bold')
    ui.label('Claim free coins every 60 seconds').classes('text-sm text-slate-400 mb-6')
    
    # Balance card
    with card():
        ui.label('Faucet Balance').classes('text-lg font-semibold mb-2')
        ui.label(f'{store.faucet_balance:.8f} {store.currency}').classes('text-3xl font-bold').style(
            f'color: {Theme.PRIMARY_LIGHT}'
        )
    
    # Claim section
    with card().classes('mt-6'):
        ui.label('Manual Claim').classes('text-lg font-semibold mb-4')
        
        # Check if on cooldown
        can_claim = True
        if store.faucet_next_claim:
            can_claim = datetime.now() >= store.faucet_next_claim
        
        # Countdown label
        countdown_label = ui.label('Ready to claim!').classes('text-sm text-slate-400 mb-3')
        
        # Start countdown if needed
        if not can_claim and store.faucet_next_claim:
            asyncio.create_task(update_countdown(countdown_label, store.faucet_next_claim))
        
        # Claim button with countdown
        async def claim_faucet():
            claim_btn.props('loading')
            claim_btn.props('disable')
            
            success, message = await backend.claim_faucet()
            
            claim_btn.props(remove='loading')
            
            if success:
                toast(message, 'success')
                # Set cooldown
                store.faucet_last_claim = datetime.now()
                store.faucet_next_claim = datetime.now() + timedelta(seconds=60)
                # Restart countdown
                asyncio.create_task(update_countdown(countdown_label, store.faucet_next_claim))
                claim_btn.props('disable')
            else:
                toast(message, 'error')
                claim_btn.props(remove='disable')
        
        claim_btn = primary_button(
            '💧 Claim Faucet',
            on_click=claim_faucet,
            icon='water_drop',
            disabled=not can_claim
        ).classes('w-full')
        
        # Cooldown info
        if store.faucet_last_claim:
            ui.label(
                f'Last claimed: {store.faucet_last_claim.strftime("%H:%M:%S")}'
            ).classes('text-xs text-slate-400 mt-2')
    
    # Auto-claim configuration
    with card().classes('mt-6'):
        ui.label('Auto-Claim Configuration').classes('text-lg font-semibold mb-4')
        
        # Cookie input
        if not store.faucet_cookie:
            with ui.row().classes('items-start gap-2 p-3 rounded-lg').style(
                f'background-color: {Theme.WARNING}20; border-left: 3px solid {Theme.WARNING}'
            ):
                ui.icon('warning', color=Theme.WARNING)
                ui.label('Cookie required for auto-claim. Configure in Settings.').classes('text-sm')
            
            secondary_button(
                'Go to Settings',
                on_click=lambda: ui.navigate.to('/settings'),
                icon='settings'
            ).classes('mt-4')
        else:
            # Cookie configured
            with ui.row().classes('items-center gap-2 mb-4'):
                ui.icon('check_circle', color=Theme.ACCENT)
                ui.label('Cookie configured').classes('text-sm text-slate-400')
            
            # Auto-claim toggle
            auto_claim_switch = toggle_switch(
                label='Enable Auto-Claim (60s interval)',
                value=store.faucet_auto_claim,
                on_change=lambda e: handle_auto_claim_toggle(e.value)
            )
            
            def handle_auto_claim_toggle(enabled):
                store.faucet_auto_claim = enabled
                if enabled:
                    toast('Auto-claim enabled', 'success')
                    # Start auto-claim in backend
                    if backend.faucet_manager:
                        backend.faucet_manager.start_auto_claim()
                else:
                    toast('Auto-claim disabled', 'info')
                    # Stop auto-claim in backend
                    if backend.faucet_manager:
                        backend.faucet_manager.stop_auto_claim()
            
            # Status
            if store.faucet_auto_claim:
                with ui.row().classes('items-center gap-2 mt-4 p-3 rounded-lg').style(
                    f'background-color: {Theme.ACCENT}20'
                ):
                    ui.icon('schedule', color=Theme.ACCENT)
                    ui.label('Auto-claim is running in background').classes('text-sm')
    
    # Claim history
    if store.bet_history:
        faucet_bets = [bet for bet in store.bet_history if bet.mode == 'faucet']
        
        if faucet_bets:
            with card().classes('mt-6'):
                ui.label('Claim History').classes('text-lg font-semibold mb-4')
                
                for bet in faucet_bets[:10]:
                    with ui.row().classes('items-center justify-between p-2 rounded').style(
                        f'background-color: {Theme.BG_TERTIARY}'
                    ):
                        ui.label(bet.timestamp.strftime('%H:%M:%S')).classes('text-sm')
                        
                        profit_color = Theme.ACCENT if bet.is_win else Theme.ERROR
                        icon = '✓' if bet.is_win else '✗'
                        ui.label(f'{icon} {bet.profit:.8f}').classes('text-sm').style(
                            f'color: {profit_color}'
                        )
    
    # Tips
    with card().classes('mt-6'):
        ui.label('💡 Tips').classes('text-lg font-semibold mb-3')
        
        tips = [
            'Faucet has 3% house edge (vs 1% for main)',
            'Claims reset every 60 seconds',
            'Auto-claim requires browser cookie',
            'Use faucet mode for risk-free testing',
        ]
        
        for tip in tips:
            with ui.row().classes('items-start gap-2 mb-2'):
                ui.icon('lightbulb', size='sm', color=Theme.WARNING)
                ui.label(tip).classes('text-sm text-slate-300')
