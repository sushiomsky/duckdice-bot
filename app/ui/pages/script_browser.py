"""
Script Browser Page.

Browse, search, and manage strategy scripts.
"""

from nicegui import ui
from typing import Optional, List
import os
from pathlib import Path

from src.script_system import ScriptStorage, StrategyScript
from app.state.store import store


class ScriptBrowserPage:
    """Script browser with list, search, and management features."""
    
    def __init__(self):
        self.storage = ScriptStorage()
        self.search_query = ""
        self.filter_type = "all"  # all, builtin, custom, templates
        self.scripts: List[StrategyScript] = []
        self.scripts_container = None
        
    def render(self):
        """Render the script browser page."""
        with ui.column().classes('w-full h-full gap-4 p-4'):
            # Header
            with ui.row().classes('w-full items-center gap-4'):
                ui.label('Strategy Scripts').classes('text-2xl font-bold')
                ui.space()
                
                ui.button(
                    'New Script',
                    icon='add',
                    on_click=self._new_script
                ).props('color=primary')
            
            # Search and filters
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full items-center gap-4'):
                    # Search
                    search_input = ui.input(
                        'Search scripts...',
                        on_change=lambda e: self._on_search(e.value)
                    ).props('outlined dense').classes('flex-1')
                    search_input.props('prepend-icon=search')
                    
                    # Filter dropdown
                    ui.select(
                        ['all', 'builtin', 'custom', 'templates'],
                        value='all',
                        label='Filter',
                        on_change=lambda e: self._on_filter(e.value)
                    ).props('outlined dense').classes('w-48')
                    
                    # Refresh button
                    ui.button(
                        icon='refresh',
                        on_click=self._load_scripts
                    ).props('flat round')
            
            # Scripts grid
            self.scripts_container = ui.column().classes('w-full gap-4')
            
            # Load initial scripts
            self._load_scripts()
    
    def _load_scripts(self):
        """Load and display scripts."""
        # Load all scripts
        self.scripts = []
        
        # Load builtin scripts
        builtin_scripts = self.storage.list_all(builtin_only=True)
        self.scripts.extend(builtin_scripts)
        
        # Load custom scripts
        custom_scripts = self.storage.list_all(custom_only=True)
        self.scripts.extend(custom_scripts)
        
        # Load templates
        templates = self.storage.list_templates()
        self.scripts.extend(templates)
        
        # Apply filters
        filtered = self._filter_scripts(self.scripts)
        
        # Display
        self._display_scripts(filtered)
    
    def _filter_scripts(self, scripts: List[StrategyScript]) -> List[StrategyScript]:
        """Filter scripts by search query and type."""
        filtered = scripts
        
        # Apply search filter
        if self.search_query:
            query = self.search_query.lower()
            filtered = [
                s for s in filtered
                if query in s.name.lower() or query in s.description.lower()
            ]
        
        # Apply type filter
        if self.filter_type == 'builtin':
            filtered = [s for s in filtered if s.is_builtin]
        elif self.filter_type == 'custom':
            filtered = [s for s in filtered if not s.is_builtin and not s.is_template]
        elif self.filter_type == 'templates':
            filtered = [s for s in filtered if s.is_template]
        
        return filtered
    
    def _display_scripts(self, scripts: List[StrategyScript]):
        """Display scripts in grid."""
        self.scripts_container.clear()
        
        with self.scripts_container:
            if not scripts:
                ui.label('No scripts found').classes('text-gray-500 text-center p-8')
                return
            
            # Group scripts in rows of 3
            for i in range(0, len(scripts), 3):
                with ui.row().classes('w-full gap-4'):
                    for script in scripts[i:i+3]:
                        self._create_script_card(script)
    
    def _create_script_card(self, script: StrategyScript):
        """Create a card for a script."""
        with ui.card().classes('flex-1 min-w-80'):
            with ui.column().classes('gap-2'):
                # Header
                with ui.row().classes('w-full items-start gap-2'):
                    with ui.column().classes('flex-1'):
                        ui.label(script.name).classes('text-lg font-bold')
                        ui.label(script.description).classes('text-sm text-gray-600')
                    
                    # Badge
                    if script.is_template:
                        ui.badge('Template', color='purple')
                    elif script.is_builtin:
                        ui.badge('Built-in', color='blue')
                    else:
                        ui.badge('Custom', color='green')
                
                # Metadata
                with ui.row().classes('w-full items-center gap-4 text-sm text-gray-500'):
                    ui.label(f'v{script.version}')
                    ui.label(f'by {script.author}')
                
                ui.separator()
                
                # Actions
                with ui.row().classes('w-full gap-2'):
                    ui.button(
                        'Edit',
                        icon='edit',
                        on_click=lambda s=script: self._edit_script(s)
                    ).props('flat dense').classes('flex-1')
                    
                    if not script.is_builtin:
                        ui.button(
                            'Delete',
                            icon='delete',
                            on_click=lambda s=script: self._delete_script(s)
                        ).props('flat dense color=red')
                    
                    if script.is_template:
                        ui.button(
                            'Use',
                            icon='file_copy',
                            on_click=lambda s=script: self._use_template(s)
                        ).props('flat dense color=primary')
    
    def _on_search(self, query: str):
        """Handle search input."""
        self.search_query = query
        self._load_scripts()
    
    def _on_filter(self, filter_type: str):
        """Handle filter change."""
        self.filter_type = filter_type
        self._load_scripts()
    
    def _new_script(self):
        """Create new script."""
        ui.navigate.to('/scripts/editor?new=true')
    
    def _edit_script(self, script: StrategyScript):
        """Edit existing script."""
        ui.navigate.to(f'/scripts/editor?name={script.name}')
    
    def _delete_script(self, script: StrategyScript):
        """Delete a script."""
        async def confirm_delete():
            result = await ui.run_javascript(
                f'confirm("Delete {script.name}? This cannot be undone.")',
                timeout=10.0
            )
            
            if result:
                try:
                    self.storage.delete(script.name)
                    ui.notify(f'Deleted {script.name}', type='positive')
                    self._load_scripts()
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')
        
        confirm_delete()
    
    def _use_template(self, template: StrategyScript):
        """Create new script from template."""
        ui.navigate.to(f'/scripts/editor?template={template.name}')


def create_script_browser_page():
    """Create and render script browser page."""
    browser = ScriptBrowserPage()
    browser.render()
