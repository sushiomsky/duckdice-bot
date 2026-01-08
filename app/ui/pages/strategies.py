"""
Strategies page - browse and learn about 16 betting strategies
"""

from nicegui import ui
from app.ui.components import card, primary_button, secondary_button, empty_state
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend


def get_risk_color(risk_level: str) -> str:
    """Get color for risk level badge"""
    return {
        'low': Theme.ACCENT,
        'medium': Theme.WARNING,
        'high': Theme.ERROR,
        'very_high': Theme.ERROR,
    }.get(risk_level, Theme.TEXT_MUTED)


def strategy_card_component(strategy):
    """Single strategy card"""
    with card().classes('cursor-pointer hover:shadow-lg transition-all'):
        # Header with risk badge
        with ui.row().classes('items-center justify-between mb-3'):
            ui.label(strategy['name']).classes('text-lg font-semibold')
            
            risk_color = get_risk_color(strategy.get('risk_level', 'medium'))
            ui.badge(strategy.get('risk_level', 'medium').upper()).style(
                f'background-color: {risk_color}'
            )
        
        # Description
        ui.label(strategy.get('description', 'No description')).classes(
            'text-sm text-slate-400 mb-4'
        )
        
        # Pros
        if strategy.get('pros'):
            ui.label('✓ Pros:').classes('text-sm font-medium text-green-400 mb-1')
            for pro in strategy['pros'][:2]:  # Show first 2
                ui.label(f'• {pro}').classes('text-xs text-slate-400 ml-4')
        
        # Cons
        if strategy.get('cons'):
            ui.label('✗ Cons:').classes('text-sm font-medium text-red-400 mb-1 mt-2')
            for con in strategy['cons'][:2]:  # Show first 2
                ui.label(f'• {con}').classes('text-xs text-slate-400 ml-4')
        
        # Action button
        secondary_button(
            'Use Strategy',
            on_click=lambda s=strategy: use_strategy(s),
            icon='arrow_forward'
        ).classes('mt-4 w-full')


def use_strategy(strategy):
    """Navigate to auto-bet with selected strategy"""
    store.current_strategy = strategy['id']
    toast(f'Selected: {strategy["name"]}', 'success')
    ui.navigate.to('/auto-bet')


def strategies_content():
    """Strategies page content"""
    
    ui.label('📚 Betting Strategies').classes('text-3xl font-bold')
    ui.label('16 professional strategies to automate your betting').classes(
        'text-sm text-slate-400 mb-6'
    )
    
    # Filter by risk level
    with card():
        ui.label('Filter by Risk Level').classes('text-sm font-medium mb-2')
        
        risk_filter = ui.radio(
            ['all', 'low', 'medium', 'high', 'very_high'],
            value='all'
        ).props('inline').classes('gap-4')
    
    # Get strategies from backend
    strategies = backend.get_strategies()
    
    if not strategies:
        empty_state(
            'strategy',
            'No Strategies Available',
            'Strategies could not be loaded',
            'Refresh Page',
            lambda: ui.navigate.to('/strategies')
        )
        return
    
    # Strategy grid - 3 columns
    strategies_container = ui.column().classes('w-full gap-4 mt-6')
    
    def render_strategies():
        strategies_container.clear()
        
        with strategies_container:
            # Filter strategies
            filtered = strategies
            if risk_filter.value != 'all':
                filtered = [
                    s for s in strategies
                    if s.get('risk_level') == risk_filter.value
                ]
            
            # Group by category
            classic = [s for s in filtered if s['id'] in [
                'classic_martingale', 'anti_martingale_streak', 'dalembert',
                'fibonacci', 'paroli', 'labouchere', 'oscars_grind', 'one_three_two_six'
            ]]
            
            advanced = [s for s in filtered if s['id'] in [
                'kelly_capped', 'faucet_cashout', 'target_aware', 'max_wager_flow'
            ]]
            
            experimental = [s for s in filtered if s['id'] in [
                'rng_analysis_strategy', 'range50_random', 'fib_loss_cluster', 'custom_script'
            ]]
            
            # Classic strategies
            if classic:
                ui.label('⚡ Classic Strategies').classes('text-xl font-semibold mt-4')
                with ui.grid(columns=3).classes('w-full gap-4'):
                    for strategy in classic:
                        strategy_card_component(strategy)
            
            # Advanced strategies
            if advanced:
                ui.label('🎯 Advanced Strategies').classes('text-xl font-semibold mt-6')
                with ui.grid(columns=3).classes('w-full gap-4'):
                    for strategy in advanced:
                        strategy_card_component(strategy)
            
            # Experimental
            if experimental:
                ui.label('🧪 Experimental').classes('text-xl font-semibold mt-6')
                with ui.grid(columns=3).classes('w-full gap-4'):
                    for strategy in experimental:
                        strategy_card_component(strategy)
            
            # Empty state if filtered out everything
            if not filtered:
                empty_state(
                    'filter_alt',
                    'No Strategies Match Filter',
                    'Try selecting a different risk level',
                    'Show All',
                    lambda: (risk_filter.set_value('all'), render_strategies())
                )
    
    # Initial render
    render_strategies()
    
    # Re-render on filter change
    risk_filter.on_value_change(lambda: render_strategies())
    
    # Info card
    with card().classes('mt-6'):
        ui.label('ℹ️ How to Use').classes('text-lg font-semibold mb-3')
        
        steps = [
            'Select a strategy that matches your risk tolerance',
            'Click "Use Strategy" to configure it',
            'Go to Auto Bet page to start automation',
            'Set stop-loss and take-profit limits',
            'Monitor progress in real-time',
        ]
        
        for i, step in enumerate(steps, 1):
            with ui.row().classes('items-start gap-2 mb-2'):
                ui.label(f'{i}.').classes('text-sm font-bold').style(f'color: {Theme.PRIMARY}')
                ui.label(step).classes('text-sm text-slate-300')


from app.ui.components import toast
