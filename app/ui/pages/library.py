"""
Consolidated Library page - Strategies and Scripts in tabs
"""

from nicegui import ui
from typing import List
from pathlib import Path

from app.ui.components import card, primary_button, secondary_button, empty_state, toast
from app.ui.components.common import metric_card, warning_banner
from app.ui.theme import Theme
from app.state.store import store
from app.services.backend import backend
from src.script_system import ScriptStorage, StrategyScript
from app.utils.performance import Debouncer


def library_content():
    """Main library page with Strategies and Scripts tabs"""
    
    ui.label('Library').classes('text-3xl font-bold mb-2')
    ui.label('Browse strategies and manage custom scripts').classes('text-sm text-slate-400 mb-6')
    
    # Tabs
    with ui.tabs().classes('w-full') as tabs:
        strategies_tab = ui.tab('📚 Strategies')
        scripts_tab = ui.tab('💻 Scripts')
    
    with ui.tab_panels(tabs, value=strategies_tab).classes('w-full'):
        with ui.tab_panel(strategies_tab):
            strategies_panel()
        
        with ui.tab_panel(scripts_tab):
            scripts_panel()


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
    """Navigate to betting page with selected strategy"""
    store.current_strategy = strategy['id']
    toast(f'Selected: {strategy["name"]}', 'success')
    ui.navigate.to('/betting')


def strategies_panel():
    """Strategies panel content"""
    
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
            lambda: ui.navigate.to('/library')
        )
        return
    
    # Strategy grid
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
                # Responsive grid: 1 col mobile, 2 col tablet, 3 col desktop
                with ui.grid(columns=1).classes('w-full gap-4 sm:grid-cols-2 lg:grid-cols-3'):
                    for strategy in classic:
                        strategy_card_component(strategy)
            
            # Advanced strategies
            if advanced:
                ui.label('🎯 Advanced Strategies').classes('text-xl font-semibold mt-6')
                with ui.grid(columns=1).classes('w-full gap-4 sm:grid-cols-2 lg:grid-cols-3'):
                    for strategy in advanced:
                        strategy_card_component(strategy)
            
            # Experimental
            if experimental:
                ui.label('🧪 Experimental').classes('text-xl font-semibold mt-6')
                with ui.grid(columns=1).classes('w-full gap-4 sm:grid-cols-2 lg:grid-cols-3'):
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
            'Go to Betting page to start automation',
            'Set stop-loss and take-profit limits',
            'Monitor progress in real-time',
        ]
        
        for i, step in enumerate(steps, 1):
            with ui.row().classes('items-start gap-2 mb-2'):
                ui.label(f'{i}.').classes('text-sm font-bold').style(f'color: {Theme.PRIMARY}')
                ui.label(step).classes('text-sm text-slate-300')


def scripts_panel():
    """Scripts panel content"""
    
    storage = ScriptStorage()
    
    # Header with new script button
    with ui.row().classes('w-full items-center justify-between mb-4'):
        ui.label('Your custom strategy scripts').classes('text-sm text-slate-400')
        
        primary_button(
            'New Script',
            on_click=lambda: ui.navigate.to('/scripts/editor?new=true'),
            icon='add'
        )
    
    # Scripts container
    scripts_container = ui.column().classes('w-full gap-4 mt-6')
    
    # Debouncer for search to avoid excessive reloads
    search_debouncer = Debouncer(delay=0.5)
    
    def load_scripts(search_value='', filter_value='all'):
        """Load and display scripts with search and filter"""
        scripts_container.clear()
        
        # Load all scripts based on filter
        all_scripts = []
        search_lower = search_value.lower()
        
        try:
            if filter_value in ['all', 'builtin']:
                builtin_scripts = storage.list_all(builtin_only=True)
                all_scripts.extend(builtin_scripts)
            
            if filter_value in ['all', 'custom']:
                custom_scripts = storage.list_all(custom_only=True)
                all_scripts.extend(custom_scripts)
            
            if filter_value in ['all', 'templates']:
                template_scripts = storage.list_templates()
                all_scripts.extend(template_scripts)
        except Exception as e:
            with scripts_container:
                empty_state(
                    'error',
                    'Error Loading Scripts',
                    str(e),
                    'Retry',
                    lambda: load_scripts(search_value, filter_value)
                )
            return
        
        # Filter by search
        if search_lower:
            all_scripts = [
                s for s in all_scripts
                if search_lower in s.name.lower() or 
                   (s.description and search_lower in s.description.lower())
            ]
        
        # Display scripts
        with scripts_container:
            if not all_scripts:
                empty_state(
                    'code',
                    'No Scripts Found',
                    'Create your first custom strategy script' if not search_lower else 'No scripts match your search',
                    'New Script' if not search_lower else 'Clear Search',
                    lambda: ui.navigate.to('/scripts/editor?new=true') if not search_lower else load_scripts('', filter_value)
                )
                return
            
            # Group by type
            builtin = [s for s in all_scripts if getattr(s, 'builtin', False)]
            custom = [s for s in all_scripts if not getattr(s, 'builtin', False)]
            
            # Builtin scripts
            if builtin:
                ui.label('📦 Built-in Scripts').classes('text-xl font-semibold mt-4')
                # Responsive grid: 1 col mobile, 2 col tablet+
                with ui.grid(columns=1).classes('w-full gap-4 md:grid-cols-2'):
                    for script in builtin:
                        script_card(script, storage, lambda: load_scripts(search_value, filter_value), is_builtin=True)
            
            # Custom scripts
            if custom:
                ui.label('🎨 Custom Scripts').classes('text-xl font-semibold mt-6')
                with ui.grid(columns=1).classes('w-full gap-4 md:grid-cols-2'):
                    for script in custom:
                        script_card(script, storage, lambda: load_scripts(search_value, filter_value), is_builtin=False)
    
    # Search and filters with debouncing
    with card():
        with ui.row().classes('w-full items-center gap-4'):
            # Search with debounced handler
            search_input = ui.input(
                'Search scripts...'
            ).props('outlined dense').classes('flex-1')
            search_input.props('prepend-icon=search')
            
            # Filter dropdown
            filter_select = ui.select(
                ['all', 'builtin', 'custom', 'templates'],
                value='all',
                label='Filter'
            ).props('outlined dense').classes('w-48')
    
    # Load initial scripts
    load_scripts()
    
    # Reload with debouncing on search (waits 0.5s after user stops typing)
    async def debounced_search(e):
        await search_debouncer.debounce(lambda: load_scripts(
            search_input.value if search_input.value else '',
            filter_select.value if filter_select.value else 'all'
        ))()
    
    search_input.on_value_change(debounced_search)
    
    # Reload immediately on filter change
    filter_select.on_value_change(lambda: load_scripts(
        search_input.value if search_input.value else '',
        filter_select.value if filter_select.value else 'all'
    ))
    
    # Info card
    with card().classes('mt-6'):
        ui.label('💡 About Scripts').classes('text-lg font-semibold mb-3')
        
        tips = [
            'Scripts are Python-based custom strategies with full control',
            'Use templates to get started quickly',
            'All scripts run in a secure sandbox environment',
            'Test scripts in simulation mode before going live',
            'Share your best scripts with the community',
        ]
        
        for tip in tips:
            with ui.row().classes('items-start gap-2 mb-2'):
                ui.icon('lightbulb', size='sm', color=Theme.WARNING)
                ui.label(tip).classes('text-sm text-slate-300')


def script_card(script: StrategyScript, storage: ScriptStorage, reload_callback, is_builtin: bool = False):
    """Single script card component"""
    with card().classes('hover:shadow-lg transition-all'):
        # Header
        with ui.row().classes('items-center justify-between mb-3'):
            ui.label(script.name).classes('text-lg font-semibold')
            
            if is_builtin:
                ui.badge('BUILT-IN').style(f'background-color: {Theme.PRIMARY}')
            else:
                ui.badge('CUSTOM').style(f'background-color: {Theme.ACCENT}')
        
        # Description
        if script.description:
            ui.label(script.description).classes('text-sm text-slate-400 mb-4')
        
        # Metadata
        with ui.row().classes('items-center gap-4 text-xs text-slate-500'):
            if hasattr(script, 'version'):
                ui.label(f'v{script.version}')
            if hasattr(script, 'author'):
                ui.label(f'by {script.author}')
        
        # Actions
        with ui.row().classes('gap-2 mt-4 w-full'):
            secondary_button(
                'Edit',
                on_click=lambda: ui.navigate.to(f'/scripts/editor?name={script.name}'),
                icon='edit'
            ).classes('flex-1')
            
            if not is_builtin:
                ui.button(
                    icon='delete',
                    on_click=lambda: delete_script(script, storage, reload_callback)
                ).props('flat color=red')
            
            primary_button(
                'Use',
                on_click=lambda: use_script(script),
                icon='play_arrow'
            ).classes('flex-1')


def use_script(script: StrategyScript):
    """Use a script in auto-bet"""
    toast(f'Selected script: {script.name}', 'success')
    ui.navigate.to('/betting')


def delete_script(script: StrategyScript, storage: ScriptStorage, reload_callback):
    """Delete a custom script"""
    async def confirm_delete():
        result = await ui.run_javascript(
            f'confirm("Delete {script.name}? This cannot be undone.")',
            timeout=10.0
        )
        
        if result:
            try:
                storage.delete(script.name)
                toast(f'Deleted {script.name}', 'success')
                reload_callback()
            except Exception as e:
                toast(f'Error: {str(e)}', 'error')
    
    confirm_delete()
