"""
Script Editor Page.

Full-featured editor for creating and editing strategy scripts.
"""

from nicegui import ui
from typing import Optional
import json
from urllib.parse import parse_qs

from src.script_system import ScriptStorage, StrategyScript, execute_strategy_script
from app.ui.components.code_editor import StrategyCodeEditor
from app.state.store import store


class ScriptEditorPage:
    """Script editor with Monaco editor and version history."""
    
    def __init__(self):
        self.storage = ScriptStorage()
        self.script: Optional[StrategyScript] = None
        self.editor: Optional[StrategyCodeEditor] = None
        self.is_modified = False
        self.script_name_input = None
        self.script_desc_input = None
        
    def render(self, query_params: dict):
        """Render the script editor page."""
        # Parse query parameters
        name = query_params.get('name', [None])[0]
        template = query_params.get('template', [None])[0]
        is_new = query_params.get('new', [None])[0] == 'true'
        
        # Load script
        if name:
            self.script = self.storage.load(name)
        elif template:
            template_script = self.storage.load(template)
            self.script = StrategyScript(
                name=f"{template_script.name}_copy",
                description=f"Copy of {template_script.description}",
                code=template_script.code,
                author="You",
                is_builtin=False,
                is_template=False
            )
            self.is_modified = True
        else:
            self.script = None
        
        with ui.column().classes('w-full h-full gap-4 p-4'):
            # Header
            with ui.row().classes('w-full items-center gap-4'):
                ui.button(
                    icon='arrow_back',
                    on_click=lambda: ui.navigate.to('/scripts')
                ).props('flat round')
                
                ui.label('Script Editor').classes('text-2xl font-bold')
                ui.space()
                
                # Status indicator
                if self.is_modified:
                    ui.badge('Modified', color='orange')
                
                ui.button(
                    'Save',
                    icon='save',
                    on_click=self._save_script
                ).props('color=primary')
                
                ui.button(
                    'Test',
                    icon='play_arrow',
                    on_click=self._test_script
                ).props('outline color=green')
            
            # Script metadata
            with ui.card().classes('w-full'):
                with ui.column().classes('gap-2'):
                    with ui.row().classes('w-full gap-4'):
                        self.script_name_input = ui.input(
                            'Script Name',
                            value=self.script.name if self.script else 'New Script',
                            on_change=lambda: setattr(self, 'is_modified', True)
                        ).props('outlined').classes('flex-1')
                        
                        if self.script:
                            ui.badge(f'v{self.script.version}', color='blue')
                    
                    self.script_desc_input = ui.input(
                        'Description',
                        value=self.script.description if self.script else '',
                        on_change=lambda: setattr(self, 'is_modified', True)
                    ).props('outlined').classes('w-full')
            
            # Code editor
            initial_code = self.script.code if self.script else ""
            self.editor = StrategyCodeEditor(
                value=initial_code,
                on_change=lambda code: setattr(self, 'is_modified', True)
            )
            
            # Version history (if editing existing script)
            if self.script and not is_new:
                self._render_version_history()
    
    def _render_version_history(self):
        """Render version history section."""
        versions = self.storage._get_version_history(self.script.name)
        
        if not versions:
            return
        
        with ui.expansion('Version History', icon='history').classes('w-full'):
            with ui.column().classes('gap-2'):
                for i, version_file in enumerate(reversed(versions)):
                    version_num = len(versions) - i
                    
                    # Load version metadata
                    meta_file = version_file.replace('.py', '.meta.json')
                    if not os.path.exists(meta_file):
                        continue
                    
                    with open(meta_file) as f:
                        meta = json.load(f)
                    
                    with ui.card().classes('w-full'):
                        with ui.row().classes('w-full items-center gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label(f'Version {version_num}').classes('font-bold')
                                ui.label(meta.get('modified_at', 'Unknown')).classes(
                                    'text-sm text-gray-500'
                                )
                            
                            ui.button(
                                'Restore',
                                icon='restore',
                                on_click=lambda vf=version_file: self._restore_version(vf)
                            ).props('flat dense')
    
    def _save_script(self):
        """Save current script."""
        if not self.editor:
            return
        
        try:
            # Validate code first
            if not self.editor.is_valid():
                ui.notify('Cannot save: Script has validation errors', type='negative')
                return
            
            # Get values
            name = self.script_name_input.value.strip()
            description = self.script_desc_input.value.strip()
            code = self.editor.get_value()
            
            if not name:
                ui.notify('Script name is required', type='warning')
                return
            
            # Create or update script
            if self.script:
                self.script.name = name
                self.script.description = description
                self.script.update_code(code)
            else:
                self.script = StrategyScript(
                    name=name,
                    description=description,
                    code=code,
                    author="You",
                    is_builtin=False
                )
            
            # Save to storage
            self.storage.save(self.script)
            
            self.is_modified = False
            ui.notify(f'Saved {name}', type='positive')
            
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', type='negative')
    
    def _test_script(self):
        """Test script execution."""
        if not self.editor:
            return
        
        try:
            code = self.editor.get_value()
            
            # Execute script
            functions = execute_strategy_script(code, 'test_script')
            
            # Test next_bet function
            ctx = {
                'balance': 10.0,
                'currency': 'DOGE',
                'base_bet': 0.01
            }
            
            bet = functions['next_bet'](ctx)
            
            # Show result
            ui.notify(
                f'✓ Test passed! Next bet: {bet}',
                type='positive',
                timeout=5000
            )
            
        except Exception as e:
            ui.notify(
                f'✗ Test failed: {str(e)}',
                type='negative',
                timeout=5000
            )
    
    def _restore_version(self, version_file: str):
        """Restore a previous version."""
        try:
            with open(version_file) as f:
                code = f.read()
            
            self.editor.set_value(code)
            self.is_modified = True
            
            ui.notify('Version restored', type='positive')
            
        except Exception as e:
            ui.notify(f'Error restoring version: {str(e)}', type='negative')


def create_script_editor_page(query_params: dict):
    """Create and render script editor page."""
    import os
    
    editor = ScriptEditorPage()
    editor.render(query_params)
