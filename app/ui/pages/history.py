"""
History page - view bet history with filtering
"""

from nicegui import ui
from app.ui.components import card, secondary_button, empty_state, select_field
from app.ui.theme import Theme
from app.state.store import store


def history_content():
    """History page content"""
    
    ui.label('📊 Bet History').classes('text-3xl font-bold')
    ui.label('View all your betting activity').classes('text-sm text-slate-400 mb-6')
    
    # Check if any history exists
    if not store.bet_history:
        empty_state(
            'casino',
            'No Bets Yet',
            'Your betting history will appear here',
            'Place Your First Bet',
            lambda: ui.navigate.to('/quick-bet')
        )
        return
    
    # Filters
    with card():
        ui.label('Filters').classes('text-sm font-medium mb-3')
        
        with ui.row().classes('gap-4 items-end'):
            # Mode filter
            mode_filter = select_field(
                label='Mode',
                options=['all', 'main', 'faucet'],
                value='all'
            )
            
            # Result filter
            result_filter = select_field(
                label='Result',
                options=['all', 'wins', 'losses'],
                value='all'
            )
            
            # Export button
            def export_history():
                # Simple CSV export
                import csv
                from io import StringIO
                
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['Time', 'Currency', 'Amount', 'Chance', 'Result', 'Profit', 'Win'])
                
                for bet in store.bet_history:
                    writer.writerow([
                        bet.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        bet.currency,
                        bet.amount,
                        bet.chance,
                        bet.result,
                        bet.profit,
                        'Yes' if bet.is_win else 'No'
                    ])
                
                # Trigger download
                ui.download(output.getvalue().encode(), 'bet_history.csv')
                toast('History exported', 'success')
            
            secondary_button('Export CSV', on_click=export_history, icon='download')
    
    # Statistics summary
    total_wagered = sum(bet.amount for bet in store.bet_history)
    total_profit = sum(bet.profit for bet in store.bet_history)
    
    with ui.row().classes('w-full gap-4 mt-6'):
        with card().classes('flex-1'):
            ui.label('Total Bets').classes('text-sm text-slate-400')
            ui.label(str(len(store.bet_history))).classes('text-2xl font-bold')
        
        with card().classes('flex-1'):
            ui.label('Total Wagered').classes('text-sm text-slate-400')
            ui.label(f'{total_wagered:.8f}').classes('text-2xl font-bold')
        
        with card().classes('flex-1'):
            ui.label('Total Profit').classes('text-sm text-slate-400')
            profit_color = Theme.ACCENT if total_profit >= 0 else Theme.ERROR
            ui.label(f'{total_profit:.8f}').classes('text-2xl font-bold').style(
                f'color: {profit_color}'
            )
        
        with card().classes('flex-1'):
            ui.label('Win Rate').classes('text-sm text-slate-400')
            ui.label(f'{store.win_rate:.1f}%').classes('text-2xl font-bold')
    
    # Bet table
    history_container = ui.column().classes('w-full mt-6')
    
    def render_history():
        history_container.clear()
        
        with history_container:
            with card():
                # Filter bets
                filtered_bets = store.bet_history
                
                if mode_filter.value != 'all':
                    filtered_bets = [b for b in filtered_bets if b.mode == mode_filter.value]
                
                if result_filter.value == 'wins':
                    filtered_bets = [b for b in filtered_bets if b.is_win]
                elif result_filter.value == 'losses':
                    filtered_bets = [b for b in filtered_bets if not b.is_win]
                
                if not filtered_bets:
                    empty_state(
                        'filter_alt',
                        'No Bets Match Filter',
                        'Try adjusting your filters',
                        None,
                        None
                    )
                    return
                
                # Table header
                with ui.row().classes('w-full items-center gap-2 p-3 border-b').style(
                    f'border-color: {Theme.BORDER}; background-color: {Theme.BG_TERTIARY}'
                ):
                    ui.label('Time').classes('text-xs font-medium text-slate-400 w-32')
                    ui.label('Mode').classes('text-xs font-medium text-slate-400 w-20')
                    ui.label('Amount').classes('text-xs font-medium text-slate-400 w-32')
                    ui.label('Chance').classes('text-xs font-medium text-slate-400 w-24')
                    ui.label('Target').classes('text-xs font-medium text-slate-400 w-24')
                    ui.label('Result').classes('text-xs font-medium text-slate-400 w-24')
                    ui.label('Profit').classes('text-xs font-medium text-slate-400 flex-1')
                
                # Table rows (paginate to first 100)
                for bet in filtered_bets[:100]:
                    with ui.row().classes('w-full items-center gap-2 p-3 border-b hover:bg-slate-700 transition-colors').style(
                        f'border-color: {Theme.BORDER}'
                    ):
                        ui.label(bet.timestamp.strftime('%H:%M:%S')).classes('text-sm w-32')
                        
                        mode_icon = '💰' if bet.mode == 'main' else '🚰'
                        ui.label(mode_icon).classes('text-sm w-20')
                        
                        ui.label(f'{bet.amount:.8f}').classes('text-sm w-32')
                        ui.label(f'{bet.chance:.2f}%').classes('text-sm w-24')
                        ui.label(f'{bet.target:.2f}').classes('text-sm w-24')
                        ui.label(f'{bet.result:.2f}').classes('text-sm w-24')
                        
                        profit_color = Theme.ACCENT if bet.is_win else Theme.ERROR
                        icon = '✓' if bet.is_win else '✗'
                        ui.label(f'{icon} {bet.profit:.8f}').classes('text-sm font-medium flex-1').style(
                            f'color: {profit_color}'
                        )
                
                # Pagination info
                if len(filtered_bets) > 100:
                    ui.label(f'Showing first 100 of {len(filtered_bets)} bets').classes(
                        'text-xs text-slate-400 mt-4'
                    )
    
    # Initial render
    render_history()
    
    # Re-render on filter changes
    mode_filter.on_value_change(lambda: render_history())
    result_filter.on_value_change(lambda: render_history())


from app.ui.components import toast
