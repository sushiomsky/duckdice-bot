"""
Verification Dialog Component.

Shows detailed bet verification with step-by-step calculation breakdown.
"""

from nicegui import ui
from typing import Optional
from src.verification import BetVerifier, VerificationResult


def show_verification_dialog(
    server_seed: str,
    client_seed: str,
    nonce: int,
    actual_roll: float,
    bet_amount: Optional[float] = None,
    currency: Optional[str] = None
):
    """
    Show bet verification dialog with detailed breakdown.
    
    Args:
        server_seed: Server's revealed seed
        client_seed: Client seed
        nonce: Bet nonce
        actual_roll: Actual roll result
        bet_amount: Optional bet amount for display
        currency: Optional currency for display
    """
    
    # Perform verification
    verifier = BetVerifier()
    result = verifier.verify_bet(server_seed, client_seed, nonce, actual_roll)
    steps = verifier.get_calculation_steps(server_seed, client_seed, nonce)
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
        # Header
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label('Bet Verification').classes('text-2xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense')
        
        # Status banner
        status_color = 'green' if result.is_valid else 'red' if result.error is None else 'orange'
        status_icon = result.get_status_icon()
        status_text = result.get_status_text()
        
        with ui.card().classes(f'w-full border-l-4 border-{status_color}'):
            with ui.row().classes('items-center gap-3'):
                ui.label(status_icon).classes('text-3xl')
                ui.label(status_text).classes('text-lg font-semibold')
        
        ui.separator()
        
        # Bet Details
        if bet_amount and currency:
            with ui.card().classes('w-full'):
                ui.label('Bet Details').classes('text-sm font-semibold mb-2')
                with ui.column().classes('gap-1'):
                    ui.label(f'Amount: {bet_amount:.8f} {currency}').classes('text-sm')
                    ui.label(f'Roll: {actual_roll:.3f}').classes('text-sm')
                    ui.label(f'Nonce: {nonce}').classes('text-sm')
        
        # Seeds
        with ui.card().classes('w-full'):
            ui.label('Seeds').classes('text-sm font-semibold mb-2')
            
            with ui.column().classes('gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.label('Server Seed:').classes('text-sm text-gray-400 w-32')
                    ui.input(value=server_seed).props('outlined dense readonly').classes('flex-1 font-mono text-xs')
                
                with ui.row().classes('items-center gap-2'):
                    ui.label('Client Seed:').classes('text-sm text-gray-400 w-32')
                    ui.input(value=client_seed).props('outlined dense readonly').classes('flex-1 font-mono text-xs')
                
                with ui.row().classes('items-center gap-2'):
                    ui.label('Nonce:').classes('text-sm text-gray-400 w-32')
                    ui.input(value=str(nonce)).props('outlined dense readonly').classes('flex-1 font-mono text-xs')
        
        # Calculation Steps
        with ui.card().classes('w-full'):
            ui.label('Calculation Steps').classes('text-sm font-semibold mb-2')
            
            with ui.column().classes('gap-3'):
                # Step 1: Concatenate
                with ui.expansion('Step 1: Concatenate Seeds + Nonce', icon='link').classes('w-full'):
                    ui.code(steps['step1_message']).classes('text-xs')
                
                # Step 2: SHA-256 Hash
                with ui.expansion('Step 2: SHA-256 Hash', icon='tag').classes('w-full'):
                    ui.code(steps['step2_hash']).classes('text-xs break-all')
                
                # Step 3: Extract First 5 Hex
                with ui.expansion('Step 3: Extract First 5 Hex Characters', icon='filter_1').classes('w-full'):
                    ui.label(f"First 5 characters: {steps['step3_first_5_hex']}").classes('text-sm')
                
                # Step 4: Convert to Decimal
                with ui.expansion('Step 4: Convert to Decimal', icon='calculate').classes('w-full'):
                    ui.label(f"Hex '{steps['step3_first_5_hex']}' = Decimal {steps['step4_decimal']}").classes('text-sm')
                
                # Step 5: Calculate Roll
                with ui.expansion('Step 5: Calculate Roll', icon='casino').classes('w-full'):
                    ui.label(steps['formula']).classes('text-sm font-mono')
                    ui.label(f"Result: {steps['step6_roll']:.3f}").classes('text-lg font-bold mt-2')
        
        # Comparison
        with ui.card().classes('w-full'):
            ui.label('Verification Result').classes('text-sm font-semibold mb-2')
            
            with ui.row().classes('w-full gap-4'):
                with ui.column().classes('flex-1'):
                    ui.label('Calculated Roll').classes('text-xs text-gray-400')
                    ui.label(f'{result.calculated_roll:.3f}').classes('text-2xl font-bold')
                
                ui.icon('compare_arrows').classes('text-3xl text-gray-500')
                
                with ui.column().classes('flex-1'):
                    ui.label('Actual Roll').classes('text-xs text-gray-400')
                    ui.label(f'{result.actual_roll:.3f}').classes('text-2xl font-bold')
            
            # Delta
            delta = abs(result.calculated_roll - result.actual_roll)
            delta_color = 'green' if delta < 0.001 else 'red'
            ui.label(f'Difference: {delta:.6f}').classes(f'text-sm text-{delta_color} mt-2')
        
        # Actions
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Close', on_click=dialog.close).props('outline')
            
            def export_report():
                # Export as text file
                report = f"""
Bet Verification Report
========================

Status: {status_text}

Seeds:
  Server Seed: {server_seed}
  Client Seed: {client_seed}
  Nonce: {nonce}

Calculation:
  Message: {steps['step1_message']}
  SHA-256: {steps['step2_hash']}
  First 5 Hex: {steps['step3_first_5_hex']}
  Decimal: {steps['step4_decimal']}
  Formula: {steps['formula']}

Results:
  Calculated Roll: {result.calculated_roll:.3f}
  Actual Roll: {result.actual_roll:.3f}
  Difference: {delta:.6f}
  
Verification: {'✅ PASS' if result.is_valid else '❌ FAIL'}
"""
                ui.download(report.encode(), f'verification_nonce_{nonce}.txt')
                ui.notify('Report exported', type='positive')
            
            ui.button('Export Report', icon='download', on_click=export_report)
    
    dialog.open()


def show_batch_verification_dialog(results):
    """
    Show batch verification results.
    
    Args:
        results: List of VerificationResult objects
    """
    
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-3xl'):
        # Header
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label('Batch Verification Results').classes('text-2xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense')
        
        # Summary
        total = len(results)
        verified = sum(1 for r in results if r.is_valid)
        failed = total - verified
        pass_rate = (verified / total * 100) if total > 0 else 0
        
        with ui.row().classes('w-full gap-4 mb-4'):
            with ui.card().classes('flex-1 text-center'):
                ui.label(str(total)).classes('text-3xl font-bold')
                ui.label('Total Bets').classes('text-sm text-gray-400')
            
            with ui.card().classes('flex-1 text-center border-l-4 border-green'):
                ui.label(str(verified)).classes('text-3xl font-bold text-green')
                ui.label('Verified').classes('text-sm text-gray-400')
            
            with ui.card().classes('flex-1 text-center border-l-4 border-red'):
                ui.label(str(failed)).classes('text-3xl font-bold text-red')
                ui.label('Failed').classes('text-sm text-gray-400')
            
            with ui.card().classes('flex-1 text-center'):
                ui.label(f'{pass_rate:.1f}%').classes('text-3xl font-bold')
                ui.label('Pass Rate').classes('text-sm text-gray-400')
        
        ui.separator()
        
        # Results table
        with ui.card().classes('w-full max-h-96 overflow-y-auto'):
            ui.label('Individual Results').classes('text-sm font-semibold mb-2')
            
            for result in results:
                status_icon = result.get_status_icon()
                status_color = 'green' if result.is_valid else 'red'
                
                with ui.row().classes('w-full items-center gap-3 p-2 border-b'):
                    ui.label(status_icon).classes('text-xl')
                    
                    with ui.column().classes('flex-1'):
                        ui.label(f'Nonce: {result.nonce}').classes('text-sm font-semibold')
                        ui.label(f'Roll: {result.actual_roll:.3f} → {result.calculated_roll:.3f}').classes('text-xs text-gray-400')
                    
                    ui.label(result.get_status_text()).classes(f'text-xs text-{status_color}')
        
        # Actions
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Close', on_click=dialog.close).props('outline')
    
    dialog.open()
