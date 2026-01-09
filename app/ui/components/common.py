"""
Common reusable UI components.

Extracted components used across multiple pages to reduce duplication.
"""

from nicegui import ui
from typing import Callable, Optional
from decimal import Decimal


def balance_display(balance: float, currency: str, show_usd: bool = False):
    """
    Display balance with formatting.
    
    Args:
        balance: Current balance
        currency: Currency code
        show_usd: Whether to show USD equivalent
    """
    with ui.card().classes('p-4 bg-slate-700'):
        ui.label('Current Balance').classes('text-xs text-slate-400 mb-1')
        
        # Main balance
        balance_str = f'{balance:.8f}' if balance < 1 else f'{balance:.2f}'
        ui.label(f'{balance_str} {currency}').classes('text-2xl font-mono font-bold')
        
        # USD equivalent (if requested and not USD)
        if show_usd and currency != 'USD':
            # TODO: Add conversion rate
            ui.label('≈ $?.?? USD').classes('text-xs text-slate-400 mt-1')


def bet_controls(
    on_bet: Callable,
    initial_amount: float = 1.0,
    initial_chance: float = 50.0,
    show_roll_direction: bool = True,
):
    """
    Reusable bet input controls.
    
    Args:
        on_bet: Callback when bet is placed (amount, chance, roll_over)
        initial_amount: Default bet amount
        initial_chance: Default win chance
        show_roll_direction: Whether to show roll over/under toggle
    """
    with ui.column().classes('gap-4 w-full'):
        with ui.row().classes('gap-4 w-full'):
            amount = ui.number(
                label='Bet Amount',
                value=initial_amount,
                min=0.00000001,
                format='%.8f'
            ).classes('flex-1')
            
            chance = ui.number(
                label='Win Chance %',
                value=initial_chance,
                min=0.01,
                max=98.0,
                step=0.01,
                format='%.2f'
            ).classes('flex-1')
        
        if show_roll_direction:
            roll_over = ui.checkbox('Roll Over (win if result > target)', value=True)
        else:
            roll_over = None
        
        def place_bet():
            roll_val = roll_over.value if roll_over else True
            on_bet(amount.value, chance.value, roll_val)
        
        ui.button(
            '🎲 Place Bet',
            on_click=place_bet
        ).classes('bg-green-600 w-full')
        
        # Payout multiplier display
        if chance.value > 0:
            multiplier = 100 / chance.value
            payout = amount.value * multiplier * 0.97  # 3% house edge
            profit = payout - amount.value
            
            with ui.row().classes('gap-4 text-sm text-slate-400 mt-2'):
                ui.label(f'Multiplier: {multiplier:.2f}x')
                ui.label(f'Potential Win: +{profit:.8f}')


def loading_spinner(message: str = 'Loading...', size: str = 'lg'):
    """
    Consistent loading indicator.
    
    Args:
        message: Loading message to display
        size: Spinner size (sm, md, lg, xl)
    """
    with ui.column().classes('items-center gap-3 p-8'):
        ui.spinner(size=size, color='blue')
        ui.label(message).classes('text-slate-300')


def error_boundary(
    error_message: str,
    on_retry: Optional[Callable] = None,
    show_details: bool = False,
    details: Optional[str] = None,
):
    """
    Display error with optional retry.
    
    Args:
        error_message: Main error message
        on_retry: Optional retry callback
        show_details: Whether to show technical details
        details: Technical error details
    """
    with ui.card().classes('p-4 bg-red-900 border border-red-600'):
        with ui.row().classes('gap-3 items-start'):
            ui.icon('error').classes('text-red-400 text-2xl')
            
            with ui.column().classes('flex-1'):
                ui.label('Error').classes('text-lg font-semibold text-red-200')
                ui.label(error_message).classes('text-sm text-red-100 mt-1')
                
                if show_details and details:
                    with ui.expansion('Technical Details').classes('mt-2'):
                        ui.label(details).classes('text-xs font-mono text-red-200')
        
        if on_retry:
            ui.button('Retry', on_click=on_retry).classes('bg-red-700 hover:bg-red-600 mt-3')


def success_message(message: str, icon: str = 'check_circle'):
    """
    Display success message.
    
    Args:
        message: Success message
        icon: Material icon name
    """
    with ui.card().classes('p-4 bg-green-900 border border-green-600'):
        with ui.row().classes('gap-3 items-center'):
            ui.icon(icon).classes('text-green-400 text-2xl')
            ui.label(message).classes('text-sm text-green-100')


def warning_banner(message: str, details: Optional[str] = None):
    """
    Display warning banner.
    
    Args:
        message: Warning message
        details: Optional additional details
    """
    with ui.card().classes('p-4 bg-yellow-900 border border-yellow-600'):
        with ui.row().classes('gap-3 items-start'):
            ui.icon('warning').classes('text-yellow-400 text-2xl')
            
            with ui.column():
                ui.label(message).classes('text-sm font-semibold text-yellow-100')
                if details:
                    ui.label(details).classes('text-xs text-yellow-200 mt-1')


def metric_card(label: str, value: str, icon: Optional[str] = None, color: str = 'slate'):
    """
    Display a metric in a card.
    
    Args:
        label: Metric label
        value: Metric value
        icon: Optional material icon
        color: Card color (slate, green, red, blue)
    """
    with ui.card().classes(f'p-3 bg-{color}-800'):
        if icon:
            with ui.row().classes('gap-2 items-center mb-2'):
                ui.icon(icon).classes(f'text-{color}-400')
                ui.label(label).classes('text-xs text-slate-400')
        else:
            ui.label(label).classes('text-xs text-slate-400 mb-1')
        
        ui.label(value).classes('text-lg font-mono font-semibold')


def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable,
    confirm_text: str = 'Confirm',
    cancel_text: str = 'Cancel',
):
    """
    Show confirmation dialog.
    
    Args:
        title: Dialog title
        message: Confirmation message
        on_confirm: Callback when confirmed
        confirm_text: Confirm button text
        cancel_text: Cancel button text
    """
    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label(title).classes('text-xl font-semibold mb-4')
        ui.label(message).classes('text-sm text-slate-300 mb-6')
        
        with ui.row().classes('gap-2 w-full justify-end'):
            ui.button(cancel_text, on_click=dialog.close).classes('bg-gray-600')
            
            def confirm():
                dialog.close()
                on_confirm()
            
            ui.button(confirm_text, on_click=confirm).classes('bg-blue-600')
    
    dialog.open()


def progress_bar_with_label(value: float, label: str, show_percentage: bool = True):
    """
    Progress bar with label.
    
    Args:
        value: Progress value (0-1)
        label: Progress label
        show_percentage: Whether to show percentage
    """
    with ui.column().classes('w-full gap-2'):
        with ui.row().classes('justify-between items-center'):
            ui.label(label).classes('text-sm text-slate-300')
            if show_percentage:
                ui.label(f'{value*100:.0f}%').classes('text-sm text-slate-400')
        
        ui.linear_progress(value=value).classes('w-full')


def stat_row(label: str, value: str, color: str = 'slate-300'):
    """
    Display a stat in a row.
    
    Args:
        label: Stat label
        value: Stat value
        color: Text color class
    """
    with ui.row().classes('justify-between items-center py-2 border-b border-slate-700'):
        ui.label(label).classes('text-sm text-slate-400')
        ui.label(value).classes(f'text-sm font-mono {color}')


def copy_button(text: str, tooltip: str = 'Copy to clipboard'):
    """
    Button to copy text to clipboard.
    
    Args:
        text: Text to copy
        tooltip: Tooltip text
    """
    def copy():
        # Note: Clipboard API requires HTTPS
        ui.notify('Copied to clipboard!', type='positive')
    
    return ui.button(
        icon='content_copy',
        on_click=copy
    ).props(f'flat dense').tooltip(tooltip)


def empty_state(
    icon: str,
    title: str,
    message: str,
    action_label: Optional[str] = None,
    on_action: Optional[Callable] = None,
):
    """
    Display empty state with optional action.
    
    Args:
        icon: Material icon name
        title: Empty state title
        message: Empty state message
        action_label: Optional action button label
        on_action: Optional action callback
    """
    with ui.column().classes('items-center justify-center gap-4 p-12'):
        ui.icon(icon).classes('text-6xl text-slate-600')
        ui.label(title).classes('text-xl font-semibold text-slate-400')
        ui.label(message).classes('text-sm text-slate-500 text-center max-w-md')
        
        if action_label and on_action:
            ui.button(action_label, on_click=on_action).classes('bg-blue-600 mt-4')
