"""
Faucet page - Enhanced with Faucet Grind strategy
Claim faucet, configure auto-claim, and run automated grinding to $20
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
    """Faucet page content - Enhanced with Faucet Grind"""
    
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
    
    ui.label('🚰 Faucet Grind').classes('text-3xl font-bold')
    ui.label('Auto-claim and grind to $20 cashout').classes('text-sm text-slate-400 mb-6')
    
    # Balance & Progress card
    with card():
        with ui.row().classes('items-start justify-between w-full'):
            # Faucet balance
            with ui.column().classes('gap-1'):
                ui.label('Faucet Balance').classes('text-sm text-slate-400')
                balance_label = ui.label(f'{store.faucet_balance:.8f} {store.currency}').classes('text-2xl font-bold').style(
                    f'color: {Theme.PRIMARY_LIGHT}'
                )
                # USD equivalent
                try:
                    from utils.currency_converter import to_usd
                    balance_usd = to_usd(store.faucet_balance, store.currency)
                    ui.label(f'≈ ${balance_usd:.4f} USD').classes('text-xs text-slate-400')
                except:
                    pass
            
            # Cashout target
            with ui.column().classes('gap-1 items-end'):
                ui.label('Cashout Target').classes('text-sm text-slate-400')
                ui.label('$20.00 USD').classes('text-2xl font-bold').style(
                    f'color: {Theme.ACCENT}'
                )
        
        # Progress bar to $20
        try:
            from utils.currency_converter import to_usd
            balance_usd = to_usd(store.faucet_balance, store.currency)
            progress = min(100, (balance_usd / 20.0) * 100)
            
            ui.separator().classes('my-4')
            
            with ui.row().classes('items-center gap-2 w-full'):
                ui.label(f'{progress:.1f}%').classes('text-sm font-semibold').style(
                    f'color: {Theme.PRIMARY}'
                )
                with ui.element('div').classes('flex-1'):
                    ui.linear_progress(value=progress / 100).props(
                        f'color="primary" size="8px" rounded'
                    ).style(f'--q-primary: {Theme.PRIMARY}')
                ui.label(f'${20.0 - balance_usd:.2f} to go').classes('text-xs text-slate-400')
        except:
            pass
    
    # Daily Claims Statistics
    with card().classes('mt-6'):
        ui.label('Daily Claims').classes('text-lg font-semibold mb-4')
        
        with ui.row().classes('gap-4'):
            # Claims today
            with ui.column().classes('gap-1'):
                ui.label('Today').classes('text-xs text-slate-400')
                ui.label('0 / 60').classes('text-xl font-bold').style(
                    f'color: {Theme.TEXT_PRIMARY}'
                )
            
            # Total claimed today
            with ui.column().classes('gap-1'):
                ui.label('Total Claimed').classes('text-xs text-slate-400')
                ui.label('$0.00').classes('text-xl font-bold').style(
                    f'color: {Theme.ACCENT}'
                )
            
            # Average per claim
            with ui.column().classes('gap-1'):
                ui.label('Avg/Claim').classes('text-xs text-slate-400')
                ui.label('$0.00').classes('text-xl font-bold').style(
                    f'color: {Theme.PRIMARY_LIGHT}'
                )
    
    # Faucet Grind Strategy
    with card().classes('mt-6'):
        ui.label('🎯 Faucet Grind Strategy').classes('text-lg font-semibold mb-2')
        ui.label('Auto-claim → Optimal all-in bet → Repeat until $20').classes(
            'text-xs text-slate-400 mb-4'
        )
        
        # Strategy explanation
        with ui.expansion('How it works', icon='help').classes('mb-4'):
            ui.markdown('''
            **Faucet Grind** is an automated strategy that:
            
            1. **Auto-claims** faucet when available (respects cooldown)
            2. **Calculates optimal chance** for $20 payout
            3. **Places all-in bet** with calculated chance
            4. **If win**: Checks for cashout ($20 threshold)
            5. **If loss**: Waits 60s, claims next faucet, repeats
            
            **Formula**: `chance = (balance × 100 × 0.97) / 20`
            
            **Example**: With $5 balance → 24.25% chance needed for $20 payout
            
            **Note**: High variance due to all-in betting. May take many attempts!
            ''').classes('text-xs')
        
        # Grind controls
        grind_running = False  # TODO: Get from backend
        
        if not grind_running:
            # Start grind button
            with ui.row().classes('gap-2 w-full'):
                start_btn = primary_button(
                    '🚀 Start Faucet Grind',
                    icon='play_arrow',
                    on_click=lambda: toast('Starting Faucet Grind...', 'info')
                ).classes('flex-1')
                
                # Settings button
                secondary_button(
                    'Settings',
                    icon='settings',
                    on_click=lambda: toast('Strategy settings', 'info')
                )
        else:
            # Grind status
            with ui.row().classes('items-center gap-2 p-3 rounded-lg mb-4').style(
                f'background-color: {Theme.ACCENT}20; border-left: 3px solid {Theme.ACCENT}'
            ):
                ui.spinner(size='sm', color=Theme.ACCENT)
                with ui.column().classes('gap-1'):
                    ui.label('Grind Active').classes('text-sm font-semibold').style(
                        f'color: {Theme.ACCENT}'
                    )
                    ui.label('Waiting for next claim...').classes('text-xs text-slate-400')
            
            # Stop button
            primary_button(
                '⏸️ Stop Grind',
                icon='stop',
                on_click=lambda: toast('Stopping...', 'info')
            ).classes('w-full')
            
            # Grind statistics
            ui.separator().classes('my-4')
            ui.label('Session Statistics').classes('text-sm font-semibold mb-2')
            
            with ui.grid(columns=3).classes('gap-2'):
                # Total bets
                with ui.column().classes('gap-1'):
                    ui.label('Bets').classes('text-xs text-slate-400')
                    ui.label('0').classes('text-lg font-bold')
                
                # Wins
                with ui.column().classes('gap-1'):
                    ui.label('Wins').classes('text-xs text-slate-400')
                    ui.label('0').classes('text-lg font-bold').style(
                        f'color: {Theme.ACCENT}'
                    )
                
                # Losses
                with ui.column().classes('gap-1'):
                    ui.label('Losses').classes('text-xs text-slate-400')
                    ui.label('0').classes('text-lg font-bold').style(
                        f'color: {Theme.ERROR}'
                    )
    
    # Manual Claim (for testing)
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
        
        # Claim button
        async def claim_faucet():
            claim_btn.props('loading')
            claim_btn.props('disable')
            
            success, message = await backend.claim_faucet()
            
            claim_btn.props(remove='loading')
            
            if success:
                toast(message, 'success')
                store.faucet_last_claim = datetime.now()
                store.faucet_next_claim = datetime.now() + timedelta(seconds=60)
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
        
        if store.faucet_last_claim:
            ui.label(
                f'Last claimed: {store.faucet_last_claim.strftime("%H:%M:%S")}'
            ).classes('text-xs text-slate-400 mt-2')
    
    # Cookie Configuration
    with card().classes('mt-6'):
        ui.label('Cookie Configuration').classes('text-lg font-semibold mb-4')
        
        if not store.faucet_cookie:
            with ui.row().classes('items-start gap-2 p-3 rounded-lg').style(
                f'background-color: {Theme.WARNING}20; border-left: 3px solid {Theme.WARNING}'
            ):
                ui.icon('warning', color=Theme.WARNING)
                ui.label('Cookie required for faucet claims. Get from browser DevTools.').classes('text-sm')
            
            secondary_button(
                'Configure in Settings',
                on_click=lambda: ui.navigate.to('/settings'),
                icon='settings'
            ).classes('mt-4')
        else:
            with ui.row().classes('items-center gap-2'):
                ui.icon('check_circle', color=Theme.ACCENT)
                ui.label('Cookie configured ✓').classes('text-sm').style(
                    f'color: {Theme.ACCENT}'
                )
