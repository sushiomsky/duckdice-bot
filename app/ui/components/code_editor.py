"""
Code Editor Component.

Professional Python code editor using Monaco Editor (VSCode engine).
Features syntax highlighting, validation, formatting, and error markers.
"""

from typing import Optional, Callable, Dict, List
from nicegui import ui
import black
from src.script_system import validate_script, ValidationError


class CodeEditor:
    """
    Professional code editor component with validation and formatting.
    
    Uses Monaco Editor for VSCode-quality editing experience.
    """
    
    def __init__(
        self,
        value: str = "",
        language: str = "python",
        theme: str = "vs-dark",
        on_change: Optional[Callable] = None,
        height: str = "500px"
    ):
        """
        Initialize code editor.
        
        Args:
            value: Initial code content
            language: Programming language (default: python)
            theme: Editor theme (vs-dark, vs-light, hc-black)
            on_change: Callback when code changes
            height: Editor height
        """
        self.on_change_callback = on_change
        self.validation_errors: List[ValidationError] = []
        self.validation_warnings: List[ValidationError] = []
        
        # Create container
        with ui.column().classes('w-full gap-2'):
            # Toolbar
            with ui.row().classes('w-full items-center gap-2'):
                ui.label('Code Editor').classes('text-lg font-bold')
                ui.space()
                
                self.error_badge = ui.badge('0', color='red').props('floating')
                self.error_badge.visible = False
                
                self.warning_badge = ui.badge('0', color='orange').props('floating')
                self.warning_badge.visible = False
                
                ui.button(
                    'Validate',
                    icon='check_circle',
                    on_click=self._validate
                ).props('outline').classes('text-blue')
                
                ui.button(
                    'Format',
                    icon='auto_fix_high',
                    on_click=self._format_code
                ).props('outline').classes('text-purple')
            
            # Monaco Editor
            self.editor = ui.editor(
                value=value,
                language=language,
                theme=theme,
                on_change=self._on_change
            ).style(f'height: {height}')
            
            # Validation messages panel
            self.validation_panel = ui.expansion(
                'Validation Messages',
                icon='error'
            ).classes('w-full')
            self.validation_panel.visible = False
            
            with self.validation_panel:
                self.messages_container = ui.column().classes('w-full gap-1')
    
    def _on_change(self, e):
        """Handle code change event."""
        if self.on_change_callback:
            self.on_change_callback(e.value)
    
    def _validate(self):
        """Validate current code."""
        code = self.editor.value
        
        # Clear previous messages
        self.messages_container.clear()
        self.validation_errors = []
        self.validation_warnings = []
        
        # Run validation
        result = validate_script(code)
        
        self.validation_errors = result.errors
        self.validation_warnings = result.warnings
        
        # Update badges
        if self.validation_errors:
            self.error_badge.set_text(str(len(self.validation_errors)))
            self.error_badge.visible = True
        else:
            self.error_badge.visible = False
        
        if self.validation_warnings:
            self.warning_badge.set_text(str(len(self.validation_warnings)))
            self.warning_badge.visible = True
        else:
            self.warning_badge.visible = False
        
        # Show messages
        if self.validation_errors or self.validation_warnings:
            self.validation_panel.visible = True
            self.validation_panel.open()
            
            with self.messages_container:
                # Show errors
                for error in self.validation_errors:
                    self._create_message(error, 'error')
                
                # Show warnings
                for warning in self.validation_warnings:
                    self._create_message(warning, 'warning')
        else:
            self.validation_panel.visible = False
            
            # Show success notification
            ui.notify(
                'Validation passed! No errors found.',
                type='positive',
                position='top',
                timeout=2000
            )
    
    def _create_message(self, error: ValidationError, msg_type: str):
        """Create validation message UI."""
        color = 'red' if msg_type == 'error' else 'orange'
        icon = 'error' if msg_type == 'error' else 'warning'
        
        with ui.card().classes(f'w-full border-l-4 border-{color}'):
            with ui.row().classes('items-start gap-2'):
                ui.icon(icon).classes(f'text-{color}')
                
                with ui.column().classes('flex-1 gap-1'):
                    ui.label(error.message).classes('font-bold')
                    
                    if error.line > 0:
                        ui.label(f'Line {error.line}, Column {error.column}').classes(
                            'text-sm text-gray-500'
                        )
    
    def _format_code(self):
        """Format code using Black."""
        code = self.editor.value
        
        if not code.strip():
            ui.notify('No code to format', type='warning')
            return
        
        try:
            # Format with Black
            formatted = black.format_str(code, mode=black.Mode())
            
            # Update editor
            self.editor.set_value(formatted)
            
            ui.notify(
                'Code formatted successfully',
                type='positive',
                position='top',
                timeout=2000
            )
        except Exception as e:
            ui.notify(
                f'Format error: {str(e)}',
                type='negative',
                position='top',
                timeout=3000
            )
    
    def get_value(self) -> str:
        """Get current editor content."""
        return self.editor.value
    
    def set_value(self, code: str):
        """Set editor content."""
        self.editor.set_value(code)
    
    def is_valid(self) -> bool:
        """Check if current code is valid."""
        code = self.editor.value
        result = validate_script(code)
        return result.is_valid
    
    def get_errors(self) -> List[ValidationError]:
        """Get validation errors."""
        return self.validation_errors
    
    def get_warnings(self) -> List[ValidationError]:
        """Get validation warnings."""
        return self.validation_warnings


class StrategyCodeEditor(CodeEditor):
    """
    Specialized code editor for betting strategies.
    
    Includes strategy-specific templates and help.
    """
    
    STRATEGY_TEMPLATE = '''"""
Custom Betting Strategy

Describe your strategy here.
"""

def init(ctx, params):
    """
    Initialize strategy with parameters.
    
    Args:
        ctx: Strategy context (mutable state)
        params: User-provided parameters
    """
    # Initialize your strategy state here
    ctx['base_bet'] = params.get('base_bet', 0.01)
    ctx['win_chance'] = params.get('win_chance', 50.0)


def next_bet(ctx):
    """
    Calculate next bet (REQUIRED).
    
    Args:
        ctx: Strategy context with:
            - balance: Current balance
            - currency: Currency code
            - (plus any state from init/on_result)
    
    Returns:
        Dict with 'amount', 'chance', and 'target'
    """
    return {
        'amount': ctx.get('base_bet', 0.01),
        'chance': ctx.get('win_chance', 50.0),
        'target': 'over'  # or 'under'
    }


def on_result(ctx, result):
    """
    Handle bet result (OPTIONAL).
    
    Args:
        ctx: Strategy context (mutable)
        result: Bet result with:
            - won: True/False
            - profit: Profit/loss amount
            - roll: Dice roll value
    """
    # Update strategy state based on result
    if result.get('won'):
        # Win logic
        pass
    else:
        # Loss logic
        pass
'''
    
    def __init__(self, value: str = "", on_change: Optional[Callable] = None):
        """Initialize strategy code editor."""
        super().__init__(
            value=value or self.STRATEGY_TEMPLATE,
            language='python',
            theme='vs-dark',
            on_change=on_change,
            height='600px'
        )
        
        # Add help section
        self._add_help_section()
    
    def _add_help_section(self):
        """Add strategy help documentation."""
        with ui.expansion('Strategy Help', icon='help').classes('w-full mt-2'):
            with ui.column().classes('gap-2'):
                ui.markdown('''
### Required Functions

**`next_bet(ctx)`** - REQUIRED
- Must return dict with: `amount`, `chance`, `target`
- Called before each bet to determine bet parameters

### Optional Functions

**`init(ctx, params)`** - Initialize strategy state
**`on_result(ctx, result)`** - Handle bet results

### Context (ctx)

Available in all functions:
- `ctx['balance']` - Current balance
- `ctx['currency']` - Currency code (e.g., 'DOGE')
- Plus any state you set in init/on_result

### Allowed Imports

Safe modules only:
- `math` - Mathematical functions
- `random` - Random number generation
- `decimal` - Decimal arithmetic

### Blocked Operations

For security, these are NOT allowed:
- File operations (open, read, write)
- Network access (socket, urllib, requests)
- System calls (os, sys, subprocess)
- Dangerous functions (eval, exec, __import__)

### Example: Simple Martingale

```python
def init(ctx, params):
    ctx['base_bet'] = params.get('base_bet', 0.01)
    ctx['current_bet'] = ctx['base_bet']

def next_bet(ctx):
    return {
        'amount': ctx.get('current_bet', 0.01),
        'chance': 50.0,
        'target': 'over'
    }

def on_result(ctx, result):
    if result.get('won'):
        ctx['current_bet'] = ctx['base_bet']
    else:
        ctx['current_bet'] *= 2
```
                ''')


def create_code_editor(
    value: str = "",
    on_change: Optional[Callable] = None,
    height: str = "500px"
) -> CodeEditor:
    """
    Create a code editor component.
    
    Args:
        value: Initial code
        on_change: Change callback
        height: Editor height
    
    Returns:
        CodeEditor instance
    """
    return CodeEditor(value=value, on_change=on_change, height=height)


def create_strategy_editor(
    value: str = "",
    on_change: Optional[Callable] = None
) -> StrategyCodeEditor:
    """
    Create a strategy code editor with templates and help.
    
    Args:
        value: Initial code
        on_change: Change callback
    
    Returns:
        StrategyCodeEditor instance
    """
    return StrategyCodeEditor(value=value, on_change=on_change)
