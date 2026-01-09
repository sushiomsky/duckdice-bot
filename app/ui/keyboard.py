"""
Keyboard shortcuts handler for DuckDice Bot
Provides global keyboard shortcuts for navigation and actions
"""

from nicegui import ui
from typing import Dict, Callable, Optional
from app.config import KEYBOARD_SHORTCUTS


class KeyboardShortcutManager:
    """Manages global keyboard shortcuts"""
    
    def __init__(self):
        self.shortcuts: Dict[str, Callable] = {}
        self.help_visible = False
        
    def setup(self):
        """Setup keyboard event handler"""
        ui.keyboard(on_key=self._handle_keyboard_event)
    
    def _handle_keyboard_event(self, e):
        """
        Handle keyboard events.
        
        Args:
            e: Keyboard event with key, modifiers (ctrl, shift, alt, meta)
        """
        key = e.key
        ctrl = e.modifiers.get('ctrl', False) or e.modifiers.get('meta', False)  # meta for Mac Cmd
        shift = e.modifiers.get('shift', False)
        
        # Help dialog (? key without modifiers)
        if key == '?' and not ctrl and not shift:
            self._show_help_dialog()
            return
        
        # Navigation shortcuts (Ctrl + number/letter)
        if ctrl and not shift:
            if key in KEYBOARD_SHORTCUTS:
                ui.navigate.to(KEYBOARD_SHORTCUTS[key])
                return
            
            # Additional action shortcuts
            if key == 'r':
                # Refresh current page
                ui.navigate.reload()
                return
            
            if key == ' ':  # Ctrl+Space
                # Start/Stop auto-bet (if on betting page)
                self._toggle_auto_bet()
                return
    
    def _toggle_auto_bet(self):
        """Toggle auto-bet (placeholder - would need store integration)"""
        from app.state.store import store
        from app.ui.components import toast
        
        if store.auto_bet_running:
            toast('Use the Stop button on the Betting page', 'info')
        else:
            toast('Use the Start button on the Betting page', 'info')
    
    def _show_help_dialog(self):
        """Show keyboard shortcuts help dialog"""
        if self.help_visible:
            return
        
        self.help_visible = True
        
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('⌨️ Keyboard Shortcuts').classes('text-2xl font-bold')
                ui.button(icon='close', on_click=lambda: self._close_help(dialog)).props('flat round')
            
            # Shortcuts list
            with ui.column().classes('gap-6 w-full'):
                # Navigation
                self._shortcut_section(
                    'Navigation',
                    [
                        ('Ctrl+1', 'Go to Dashboard'),
                        ('Ctrl+2', 'Go to Betting'),
                        ('Ctrl+3', 'Go to Faucet'),
                        ('Ctrl+4', 'Go to Library'),
                        ('Ctrl+5', 'Go to Tools'),
                        ('Ctrl+6', 'Go to History'),
                        ('Ctrl+7', 'Go to Settings'),
                    ]
                )
                
                # Quick actions
                self._shortcut_section(
                    'Quick Actions',
                    [
                        ('Ctrl+B', 'Go to Betting'),
                        ('Ctrl+F', 'Go to Faucet'),
                        ('Ctrl+L', 'Go to Library'),
                        ('Ctrl+T', 'Go to Tools'),
                        ('Ctrl+H', 'Go to History'),
                        ('Ctrl+R', 'Refresh page'),
                        ('?', 'Show this help'),
                    ]
                )
                
                # Tips
                ui.separator()
                with ui.card().classes('p-4 bg-blue-900 border border-blue-600'):
                    ui.label('💡 Pro Tips').classes('text-lg font-semibold mb-2')
                    tips = [
                        'On Mac, use Cmd instead of Ctrl',
                        'Number shortcuts (1-7) match navigation order',
                        'Letter shortcuts work on any page',
                    ]
                    for tip in tips:
                        with ui.row().classes('items-start gap-2 mb-1'):
                            ui.icon('lightbulb', size='sm').classes('text-yellow-400')
                            ui.label(tip).classes('text-sm')
        
        dialog.on('close', lambda: setattr(self, 'help_visible', False))
        dialog.open()
    
    def _close_help(self, dialog):
        """Close help dialog"""
        self.help_visible = False
        dialog.close()
    
    def _shortcut_section(self, title: str, shortcuts: list):
        """
        Render a section of shortcuts.
        
        Args:
            title: Section title
            shortcuts: List of (key, description) tuples
        """
        ui.label(title).classes('text-lg font-semibold mb-2')
        
        with ui.column().classes('gap-1 ml-4'):
            for key, description in shortcuts:
                with ui.row().classes('items-center gap-3'):
                    # Key badge
                    ui.badge(key).classes('font-mono').style(
                        'background-color: #475569; padding: 0.25rem 0.5rem; min-width: 80px;'
                    )
                    # Description
                    ui.label(description).classes('text-sm text-slate-300')


# Global instance
keyboard_manager = KeyboardShortcutManager()


def setup_keyboard_shortcuts():
    """Setup global keyboard shortcuts - call this on app initialization"""
    keyboard_manager.setup()
