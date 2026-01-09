"""UI components for NiceGUI interface."""

from nicegui import ui
from app.state.store import store
from app.ui.theme import Theme


def mode_badge():
    """Display simulation/live mode badge."""
    def update_badge():
        is_simulation = store.get('simulation_mode', False)
        if is_simulation:
            return ui.badge('SIMULATION', color='orange').props('outline')
        else:
            return ui.badge('LIVE', color='green').props('outline')
    
    badge = ui.element('div')
    with badge:
        update_badge()
    return badge


def betting_mode_badge():
    """Display betting status badge."""
    def update_badge():
        is_betting = store.get('is_betting', False)
        if is_betting:
            return ui.badge('BETTING', color='red').props('outline')
        else:
            return ui.badge('IDLE', color='gray').props('outline')
    
    badge = ui.element('div')
    with badge:
        update_badge()
    return badge


__all__ = ['mode_badge', 'betting_mode_badge']
