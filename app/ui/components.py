"""
Reusable UI components - building blocks for all pages
Every component follows UX principles: clear affordances, immediate feedback
"""

from nicegui import ui
from app.ui.theme import Theme
from typing import Optional, Callable, Any


def card(
    *args,
    **kwargs
) -> ui.card:
    """
    Premium card container with consistent styling
    Usage: with card(): ui.label('content')
    """
    return ui.card().classes(
        'bg-slate-800 rounded-xl p-4 shadow-md border-0'
    ).style(f'background-color: {Theme.BG_SECONDARY}')


def stat_card(
    label: str,
    value: Any,
    prefix: str = '',
    color: Optional[str] = None
) -> ui.card:
    """
    Statistic display card - shows label and large value
    """
    with card().classes('flex flex-col gap-2'):
        ui.label(label).classes('text-sm text-slate-400')
        
        value_color = color or Theme.TEXT_PRIMARY
        value_text = f'{prefix}{value}'
        
        ui.label(value_text).classes('text-2xl font-bold').style(
            f'color: {value_color}'
        )


def mode_badge(mode: str) -> ui.badge:
    """
    Mode indicator badge - Simulation vs Live
    """
    is_simulation = mode == 'simulation'
    bg_color = Theme.WARNING if is_simulation else Theme.ACCENT
    text = '🧪 Simulation' if is_simulation else '🔴 Live'
    
    return ui.badge(text).props(f'color={bg_color}').classes(
        'px-3 py-1 text-sm font-medium rounded-full'
    )


def betting_mode_badge(mode: str) -> ui.badge:
    """
    Betting mode badge - Main vs Faucet
    """
    is_main = mode == 'main'
    text = '💰 Main (1%)' if is_main else '🚰 Faucet (3%)'
    color = Theme.PRIMARY if is_main else Theme.PRIMARY_LIGHT
    
    return ui.badge(text).props(f'color={color}').classes(
        'px-3 py-1 text-sm font-medium rounded-full'
    )


def primary_button(
    text: str,
    on_click: Optional[Callable] = None,
    icon: Optional[str] = None,
    loading: bool = False,
    disabled: bool = False
) -> ui.button:
    """
    Primary call-to-action button
    Always shows loading state, disabled state, and has icon support
    """
    btn = ui.button(
        text,
        on_click=on_click,
        icon=icon
    ).props('unelevated')
    
    btn.classes('px-6 py-3 rounded-lg font-medium transition-all')
    btn.style(f'''
        background-color: {Theme.PRIMARY};
        color: white;
        transition: all {Theme.TRANSITION_BASE} ease;
    ''')
    
    if loading:
        btn.props('loading')
    
    if disabled:
        btn.props('disable')
        btn.style('opacity: 0.5; cursor: not-allowed')
    
    return btn


def secondary_button(
    text: str,
    on_click: Optional[Callable] = None,
    icon: Optional[str] = None
) -> ui.button:
    """Secondary button - outline style"""
    btn = ui.button(
        text,
        on_click=on_click,
        icon=icon
    ).props('outline')
    
    btn.classes('px-6 py-3 rounded-lg font-medium')
    btn.style(f'border-color: {Theme.PRIMARY}; color: {Theme.PRIMARY}')
    
    return btn


def danger_button(
    text: str,
    on_click: Optional[Callable] = None,
    icon: Optional[str] = None
) -> ui.button:
    """Danger button for destructive actions"""
    btn = ui.button(
        text,
        on_click=on_click,
        icon=icon
    ).props('unelevated')
    
    btn.classes('px-6 py-3 rounded-lg font-medium')
    btn.style(f'background-color: {Theme.ERROR}; color: white')
    
    return btn


def input_field(
    label: str,
    placeholder: str = '',
    value: str = '',
    type: str = 'text',
    validation: Optional[Callable] = None,
    on_change: Optional[Callable] = None
) -> ui.input:
    """
    Input field with label, placeholder, and optional validation
    """
    field = ui.input(
        label=label,
        placeholder=placeholder,
        value=value
    ).props(f'type={type} outlined dense')
    
    field.classes('w-full')
    field.style(f'''
        border-color: {Theme.BORDER};
        border-radius: {Theme.RADIUS_MD};
    ''')
    
    if validation:
        field.validation = validation
    
    if on_change:
        field.on_value_change(on_change)
    
    return field


def number_input(
    label: str,
    value: float = 0.0,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    step: float = 0.01,
    suffix: str = '',
    on_change: Optional[Callable] = None
) -> ui.number:
    """
    Number input with validation and suffix
    """
    field = ui.number(
        label=label,
        value=value,
        format='%.8f',
        step=step
    ).props('outlined dense')
    
    if min_value is not None:
        field.props(f'min={min_value}')
    
    if max_value is not None:
        field.props(f'max={max_value}')
    
    if suffix:
        field.props(f'suffix="{suffix}"')
    
    field.classes('w-full')
    
    if on_change:
        field.on_value_change(on_change)
    
    return field


def slider_input(
    label: str,
    value: float = 50.0,
    min_value: float = 0.0,
    max_value: float = 100.0,
    step: float = 0.1,
    on_change: Optional[Callable] = None
) -> ui.slider:
    """
    Slider with label and real-time value display
    """
    slider_container = ui.column().classes('w-full gap-2')
    
    with slider_container:
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(label).classes('text-sm text-slate-400')
            value_label = ui.label(f'{value:.2f}%').classes('text-sm font-medium')
        
        slider = ui.slider(
            min=min_value,
            max=max_value,
            value=value,
            step=step
        ).props('label-always')
        
        slider.classes('w-full')
        slider.style(f'color: {Theme.PRIMARY}')
        
        # Update value label on change
        slider.on_value_change(lambda e: value_label.set_text(f'{e.value:.2f}%'))
        
        if on_change:
            slider.on_value_change(on_change)
    
    return slider


def select_field(
    label: str,
    options: list,
    value: Optional[str] = None,
    on_change: Optional[Callable] = None
) -> ui.select:
    """
    Select dropdown with label
    """
    field = ui.select(
        label=label,
        options=options,
        value=value
    ).props('outlined dense')
    
    field.classes('w-full')
    
    if on_change:
        field.on_value_change(on_change)
    
    return field


def toggle_switch(
    label: str,
    value: bool = False,
    on_change: Optional[Callable] = None
) -> ui.switch:
    """
    Toggle switch with label
    """
    with ui.row().classes('items-center gap-3'):
        switch = ui.switch(value=value).style(f'color: {Theme.ACCENT}')
        ui.label(label).classes('text-sm')
        
        if on_change:
            switch.on_value_change(on_change)
    
    return switch


def loading_spinner(message: str = 'Loading...') -> ui.spinner:
    """
    Loading spinner with message
    """
    with ui.column().classes('items-center gap-2 p-4'):
        ui.spinner(size='lg', color=Theme.PRIMARY)
        ui.label(message).classes('text-sm text-slate-400')


def empty_state(
    icon: str,
    title: str,
    message: str,
    action_text: Optional[str] = None,
    action_callback: Optional[Callable] = None
):
    """
    Empty state with helpful message and optional action
    """
    with ui.column().classes('items-center justify-center gap-4 py-12'):
        ui.icon(icon, size='4rem').style(f'color: {Theme.TEXT_MUTED}')
        ui.label(title).classes('text-xl font-semibold')
        ui.label(message).classes('text-sm text-slate-400 text-center max-w-md')
        
        if action_text and action_callback:
            primary_button(action_text, on_click=action_callback)


def error_state(
    title: str,
    message: str,
    solution: Optional[str] = None,
    retry_callback: Optional[Callable] = None
):
    """
    Error state with explanation and solution
    """
    with card().classes('border-l-4').style(f'border-left-color: {Theme.ERROR}'):
        with ui.column().classes('gap-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('error', color=Theme.ERROR)
                ui.label(title).classes('font-semibold')
            
            ui.label(message).classes('text-sm text-slate-400')
            
            if solution:
                with ui.row().classes('items-start gap-2 mt-2'):
                    ui.icon('lightbulb', size='sm', color=Theme.WARNING)
                    ui.label(solution).classes('text-sm text-slate-300')
            
            if retry_callback:
                secondary_button('Retry', on_click=retry_callback, icon='refresh')


def toast(message: str, type: str = 'info'):
    """
    Toast notification - temporary message
    """
    colors = {
        'success': Theme.ACCENT,
        'error': Theme.ERROR,
        'warning': Theme.WARNING,
        'info': Theme.PRIMARY
    }
    
    icons = {
        'success': 'check_circle',
        'error': 'error',
        'warning': 'warning',
        'info': 'info'
    }
    
    ui.notify(
        message,
        type=type,
        color=colors.get(type, Theme.PRIMARY),
        icon=icons.get(type, 'info'),
        position='top',
        close_button=True
    )


def confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable,
    on_cancel: Optional[Callable] = None,
    confirm_text: str = 'Confirm',
    cancel_text: str = 'Cancel',
    danger: bool = False
):
    """
    Confirmation dialog for destructive actions
    """
    with ui.dialog() as dialog, ui.card().classes('p-6 gap-4'):
        ui.label(title).classes('text-xl font-semibold')
        ui.label(message).classes('text-sm text-slate-400')
        
        with ui.row().classes('gap-2 justify-end w-full mt-4'):
            secondary_button(cancel_text, on_click=lambda: (
                dialog.close(),
                on_cancel() if on_cancel else None
            ))
            
            if danger:
                danger_button(confirm_text, on_click=lambda: (
                    dialog.close(),
                    on_confirm()
                ))
            else:
                primary_button(confirm_text, on_click=lambda: (
                    dialog.close(),
                    on_confirm()
                ))
    
    dialog.open()
