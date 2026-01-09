"""
App layout - header, sidebar, content shell
Responsive design with mobile collapse
"""

from nicegui import ui
from app.ui.theme import Theme
from app.ui.components import mode_badge, betting_mode_badge
from app.state.store import store


def create_header():
    """
    Sticky header - always visible with connection status
    Responsive: collapses on mobile
    """
    with ui.header().classes('shadow-md').style(f'''
        background-color: {Theme.BG_SECONDARY};
        border-bottom: 1px solid {Theme.BORDER};
    '''):
        with ui.row().classes('w-full max-w-7xl mx-auto px-4 py-3 items-center justify-between'):
            # Logo and title
            with ui.row().classes('items-center gap-3'):
                ui.icon('casino', size='lg', color=Theme.PRIMARY)
                ui.label('DuckDice Bot').classes('text-xl font-bold hidden sm:block')
                ui.label('DDB').classes('text-xl font-bold sm:hidden')
            
            # Mode indicators - stack on mobile
            with ui.row().classes('items-center gap-2 sm:gap-3 flex-wrap'):
                # Simulation/Live badge
                mode_badge(store.mode)
                
                # Main/Faucet badge
                betting_mode_badge(store.betting_mode)
                
                # Connection status
                connection_indicator()


def connection_indicator():
    """
    Connection status with username
    """
    with ui.row().classes('items-center gap-2 px-3 py-1 rounded-lg').style(
        f'background-color: {Theme.BG_TERTIARY}'
    ):
        if store.connected:
            ui.icon('wifi', size='sm', color=Theme.ACCENT)
            ui.label(store.username).classes('text-sm font-medium')
        else:
            ui.icon('wifi_off', size='sm', color=Theme.ERROR)
            ui.label('Disconnected').classes('text-sm text-slate-400')


def create_sidebar():
    """
    Left sidebar navigation - collapses on mobile with toggle button
    """
    # Mobile menu toggle
    drawer = ui.left_drawer(
        value=True,
        bordered=True,
        elevated=False
    ).classes('p-4').style(f'background-color: {Theme.BG_PRIMARY}')
    
    # Make drawer collapse on mobile by default
    drawer.props('breakpoint=1024')  # Collapse below 1024px (lg breakpoint)
    
    with drawer:
        # Navigation items
        nav_items = [
            ('dashboard', 'Dashboard', '/'),
            ('casino', 'Betting', '/betting'),
            ('water_drop', 'Faucet', '/faucet'),
            ('library_books', 'Library', '/library'),
            ('build', 'Tools', '/tools'),
            ('history', 'History', '/history'),
            ('settings', 'Settings', '/settings'),
        ]
        
        with ui.column().classes('gap-2 w-full'):
            for icon, label, path in nav_items:
                create_nav_item(icon, label, path)
        
        # Spacer
        ui.space()
        
        # Bottom actions
        with ui.column().classes('gap-2 w-full mt-auto'):
            ui.separator()
            
            # Keyboard shortcuts button
            def show_shortcuts():
                from app.ui.keyboard import keyboard_manager
                keyboard_manager._show_help_dialog()
            
            create_nav_item('keyboard', 'Shortcuts (?)', None, on_click=show_shortcuts)
            create_nav_item('help', 'Help', '/help')
            create_nav_item('info', 'About', '/about')
    
    return drawer


def create_nav_item(icon: str, label: str, path: str = None, on_click = None):
    """
    Single navigation item with hover effect
    
    Args:
        icon: Material icon name
        label: Display label
        path: Navigation path (optional if on_click provided)
        on_click: Optional click handler (overrides path navigation)
    """
    # Check if current page
    is_active = path and ui.context.client.page.path == path
    
    # Determine click handler
    click_handler = on_click if on_click else (lambda: ui.navigate.to(path) if path else None)
    
    with ui.button(
        on_click=click_handler
    ).props('flat no-caps').classes('w-full justify-start px-4 py-3 rounded-lg'):
        
        # Active state styling
        if is_active:
            ui.element().style(f'background-color: {Theme.BG_TERTIARY}')
        
        with ui.row().classes('items-center gap-3'):
            ui.icon(icon, size='sm', color=Theme.PRIMARY if is_active else Theme.TEXT_SECONDARY)
            ui.label(label).classes(
                'font-medium' if is_active else 'text-slate-400'
            )


def create_layout(content_fn):
    """
    Main layout wrapper - header + sidebar + content
    
    Usage:
        @ui.page('/')
        def index():
            with create_layout(dashboard_content):
                pass
    """
    # Global dark theme styling
    ui.colors(
        primary=Theme.PRIMARY,
        secondary=Theme.ACCENT,
        accent=Theme.WARNING,
        dark=Theme.BG_PRIMARY,
        positive=Theme.ACCENT,
        negative=Theme.ERROR,
        info=Theme.PRIMARY,
        warning=Theme.WARNING
    )
    
    # Add dark mode class to body
    ui.query('body').classes('bg-slate-900 text-slate-100')
    
    # Custom CSS for scrollbar and general polish
    ui.add_head_html(f'''
        <style>
            * {{
                font-family: {Theme.FONT_FAMILY};
            }}
            
            /* Custom scrollbar */
            ::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            
            ::-webkit-scrollbar-track {{
                background: {Theme.BG_PRIMARY};
            }}
            
            ::-webkit-scrollbar-thumb {{
                background: {Theme.BG_TERTIARY};
                border-radius: 4px;
            }}
            
            ::-webkit-scrollbar-thumb:hover {{
                background: {Theme.BORDER};
            }}
            
            /* Smooth transitions */
            * {{
                transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
            }}
            
            /* Button hover effects */
            button:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }}
            
            /* Mobile responsive */
            @media (max-width: 640px) {{
                .max-w-5xl {{
                    padding-left: 1rem;
                    padding-right: 1rem;
                }}
            }}
            
            /* Card animations */
            .q-card {{
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            
            .q-card:hover {{
                transform: translateY(-2px);
            }}
            
            /* Smooth transitions */
            button, a, input, select {{
                transition: all {Theme.TRANSITION_BASE} ease;
            }}
            
            /* Focus styles */
            *:focus {{
                outline: 2px solid {Theme.PRIMARY};
                outline-offset: 2px;
            }}
        </style>
    ''')
    
    # Header
    create_header()
    
    # Sidebar
    create_sidebar()
    
    # Main content area
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
        content_fn()
