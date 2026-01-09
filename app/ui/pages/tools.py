"""
Consolidated Tools page - Simulator, RNG Analysis, and Verify in tabs
"""

import asyncio
from nicegui import ui
from app.ui.components import card, primary_button, secondary_button, number_input, toast
from app.ui.components.common import (
    warning_banner, loading_spinner, metric_card,
    progress_bar_with_label, error_boundary
)
from app.ui.theme import Theme
from app.state.store import store

# Import the actual page content functions
from app.ui.pages.simulator import simulator_content as render_simulator
from app.ui.pages.rng_analysis import rng_analysis_content as render_rng_analysis


def tools_content():
    """Main tools page with Simulator, RNG Analysis, and Verify tabs"""
    
    ui.label('Tools').classes('text-3xl font-bold mb-2')
    ui.label('Advanced tools for analysis and verification').classes('text-sm text-slate-400 mb-6')
    
    # Tabs
    with ui.tabs().classes('w-full') as tabs:
        simulator_tab = ui.tab('🧪 Simulator')
        rng_tab = ui.tab('📊 RNG Analysis')
        verify_tab = ui.tab('✓ Verify')
    
    with ui.tab_panels(tabs, value=simulator_tab).classes('w-full'):
        with ui.tab_panel(simulator_tab):
            simulator_panel()
        
        with ui.tab_panel(rng_tab):
            rng_analysis_panel()
        
        with ui.tab_panel(verify_tab):
            verify_panel()


def simulator_panel():
    """Simulator panel - calls simulator_content without header"""
    # Call the simulator content but it includes its own header
    # This is not ideal but works for now - can be refactored later
    render_simulator()


def rng_analysis_panel():
    """RNG Analysis panel - calls rng_analysis_content without header"""
    # Call the RNG analysis content but it includes its own header
    # This is not ideal but works for now - can be refactored later
    render_rng_analysis()


def verify_panel():
    """Quick bet verification tool"""
    
    ui.label('Verify Bet Results').classes('text-2xl font-bold mb-2')
    ui.label('Verify the fairness of any bet using server seed, client seed, and nonce').classes(
        'text-sm text-slate-400 mb-6'
    )
    
    # Info banner
    with card():
        ui.label('ℹ️ How It Works').classes('text-lg font-semibold mb-3')
        ui.label(
            'DuckDice uses provably fair technology. Each bet outcome is generated from:\n'
            '• Server Seed (hashed before bet)\n'
            '• Client Seed (your random input)\n'
            '• Nonce (bet counter)\n\n'
            'You can verify any bet result by entering these values below.'
        ).classes('text-sm text-slate-300 whitespace-pre-line')
    
    # Input form
    with card().classes('mt-6'):
        ui.label('Bet Information').classes('text-lg font-semibold mb-4')
        
        # Server seed
        server_seed = ui.input(
            'Server Seed (unhashed)',
            placeholder='Enter server seed after it\'s revealed'
        ).props('outlined').classes('w-full mb-4')
        
        # Client seed
        client_seed = ui.input(
            'Client Seed',
            placeholder='Enter your client seed'
        ).props('outlined').classes('w-full mb-4')
        
        # Nonce
        nonce_input = number_input(
            label='Nonce',
            value=0,
            min_value=0,
            step=1
        )
        
        # Server seed hash (for comparison)
        server_hash = ui.input(
            'Server Seed Hash (SHA256)',
            placeholder='Compare with hash shown before bet'
        ).props('outlined').classes('w-full mt-4')
    
    # Verify button
    result_container = ui.column().classes('w-full mt-6')
    
    async def verify_bet():
        """Verify bet calculation"""
        if not server_seed.value or not client_seed.value:
            toast('Please enter server seed and client seed', 'error')
            return
        
        result_container.clear()
        
        try:
            # Import verification logic
            from src.utils.provably_fair import calculate_result, hash_server_seed
            
            # Calculate hash
            calculated_hash = hash_server_seed(server_seed.value)
            
            # Calculate result
            roll_result = calculate_result(
                server_seed.value,
                client_seed.value,
                int(nonce_input.value)
            )
            
            # Display results
            with result_container:
                with card():
                    ui.label('✅ Verification Results').classes('text-xl font-semibold mb-4').style(
                        f'color: {Theme.ACCENT}'
                    )
                    
                    # Result
                    with ui.row().classes('items-center gap-4 mb-4'):
                        ui.label('Roll Result:').classes('text-sm text-slate-400')
                        ui.label(f'{roll_result:.2f}').classes('text-3xl font-bold').style(
                            f'color: {Theme.ACCENT}'
                        )
                    
                    ui.separator().classes('my-4')
                    
                    # Hash verification
                    with ui.column().classes('gap-2'):
                        ui.label('Hash Verification').classes('text-lg font-semibold mb-2')
                        
                        ui.label('Calculated Hash:').classes('text-xs text-slate-400')
                        ui.label(calculated_hash).classes('text-xs font-mono text-slate-300 break-all')
                        
                        if server_hash.value:
                            ui.label('Expected Hash:').classes('text-xs text-slate-400 mt-2')
                            ui.label(server_hash.value).classes('text-xs font-mono text-slate-300 break-all')
                            
                            if calculated_hash.lower() == server_hash.value.lower():
                                with ui.row().classes('items-center gap-2 mt-3 p-3 rounded-lg').style(
                                    f'background-color: {Theme.ACCENT}20; border-left: 3px solid {Theme.ACCENT}'
                                ):
                                    ui.icon('check_circle', color=Theme.ACCENT)
                                    ui.label('✓ Hash matches! Bet is provably fair.').classes('text-sm font-medium')
                            else:
                                with ui.row().classes('items-center gap-2 mt-3 p-3 rounded-lg').style(
                                    f'background-color: {Theme.ERROR}20; border-left: 3px solid {Theme.ERROR}'
                                ):
                                    ui.icon('error', color=Theme.ERROR)
                                    ui.label('⚠️ Hash mismatch! Seeds may be incorrect.').classes('text-sm font-medium')
                    
                    # Details
                    ui.separator().classes('my-4')
                    
                    ui.label('Inputs').classes('text-lg font-semibold mb-2')
                    with ui.column().classes('gap-1 text-xs text-slate-400'):
                        ui.label(f'Server Seed: {server_seed.value[:32]}...')
                        ui.label(f'Client Seed: {client_seed.value}')
                        ui.label(f'Nonce: {nonce_input.value}')
        
        except ImportError:
            # Fallback if provably_fair module doesn't exist
            with result_container:
                error_boundary(
                    'Verification module not available',
                    None,
                    False,
                    'The provably fair verification module is not installed. '
                    'This feature requires the cryptographic utilities.'
                )
        
        except Exception as e:
            with result_container:
                error_boundary(
                    'Verification failed',
                    None,
                    True,
                    str(e)
                )
    
    primary_button(
        '✓ Verify Bet',
        on_click=verify_bet,
        icon='verified'
    ).classes('mt-6 w-full').style('font-size: 1.1rem; padding: 1rem')
    
    # Example
    with card().classes('mt-6'):
        ui.label('📝 Example').classes('text-lg font-semibold mb-3')
        
        ui.label('Try these example values:').classes('text-sm text-slate-400 mb-2')
        
        example_data = {
            'Server Seed': 'abc123def456',
            'Client Seed': 'my-random-seed',
            'Nonce': '42'
        }
        
        for key, value in example_data.items():
            with ui.row().classes('items-center gap-2 mb-1'):
                ui.label(f'{key}:').classes('text-xs font-medium text-slate-400 w-32')
                ui.label(value).classes('text-xs font-mono text-slate-300')
        
        def use_example():
            server_seed.value = example_data['Server Seed']
            client_seed.value = example_data['Client Seed']
            nonce_input.value = int(example_data['Nonce'])
            toast('Example values loaded', 'success')
        
        secondary_button(
            'Use Example',
            on_click=use_example,
            icon='content_copy'
        ).classes('mt-3')
    
    # Additional resources
    with card().classes('mt-6'):
        ui.label('📚 Learn More').classes('text-lg font-semibold mb-3')
        
        resources = [
            ('DuckDice Fairness Documentation', 'https://duckdice.io/fairness'),
            ('What is Provably Fair?', 'https://en.wikipedia.org/wiki/Provably_fair'),
            ('SHA-256 Hashing', 'https://en.wikipedia.org/wiki/SHA-2'),
        ]
        
        for title, url in resources:
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.icon('open_in_new', size='sm', color=Theme.PRIMARY)
                ui.link(title, url, new_tab=True).classes('text-sm text-blue-400 hover:underline')
