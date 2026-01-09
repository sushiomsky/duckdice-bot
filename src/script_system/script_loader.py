"""
Script Loader

Loads and validates strategy scripts for execution.
"""

from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import sys

from .strategy_script import StrategyScript
from .script_storage import ScriptStorage


class ScriptLoader:
    """Load and prepare scripts for execution"""
    
    def __init__(self, storage: Optional[ScriptStorage] = None):
        """
        Initialize loader.
        
        Args:
            storage: Script storage instance (creates default if None)
        """
        self.storage = storage or ScriptStorage()
        self._loaded_scripts: Dict[str, StrategyScript] = {}
    
    def load_script(self, name: str, is_builtin: bool = False) -> Optional[StrategyScript]:
        """
        Load script from storage.
        
        Args:
            name: Script name
            is_builtin: Load from builtin directory
            
        Returns:
            Loaded script or None
        """
        # Check cache first
        cache_key = f"{'builtin' if is_builtin else 'custom'}:{name}"
        if cache_key in self._loaded_scripts:
            return self._loaded_scripts[cache_key]
        
        # Load from storage
        script = self.storage.load(name, is_builtin=is_builtin)
        if script:
            self._loaded_scripts[cache_key] = script
        
        return script
    
    def load_all(self) -> List[StrategyScript]:
        """Load all available scripts"""
        scripts = self.storage.list_all()
        
        # Update cache
        for script in scripts:
            cache_key = f"{'builtin' if script.is_builtin else 'custom'}:{script.name}"
            self._loaded_scripts[cache_key] = script
        
        return scripts
    
    def reload_script(self, name: str, is_builtin: bool = False) -> Optional[StrategyScript]:
        """Force reload script from disk"""
        # Remove from cache
        cache_key = f"{'builtin' if is_builtin else 'custom'}:{name}"
        if cache_key in self._loaded_scripts:
            del self._loaded_scripts[cache_key]
        
        # Reload
        return self.load_script(name, is_builtin)
    
    def get_script_functions(self, script: StrategyScript) -> Dict[str, Callable]:
        """
        Extract callable functions from script.
        
        Returns dict with: next_bet, on_result, init (if defined)
        """
        # Create isolated namespace for script execution
        namespace = {
            '__name__': f'strategy_{script.name}',
            '__builtins__': __builtins__,
        }
        
        try:
            # Execute script in namespace
            exec(script.code, namespace)
            
            # Extract functions
            functions = {}
            
            if 'next_bet' in namespace and callable(namespace['next_bet']):
                functions['next_bet'] = namespace['next_bet']
            
            if 'on_result' in namespace and callable(namespace['on_result']):
                functions['on_result'] = namespace['on_result']
            
            if 'init' in namespace and callable(namespace['init']):
                functions['init'] = namespace['init']
            
            return functions
            
        except Exception as e:
            print(f"Error loading script functions: {e}")
            return {}
    
    def validate_script(self, script: StrategyScript) -> tuple[bool, List[str]]:
        """
        Validate script structure and syntax.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if code exists
        if not script.code or not script.code.strip():
            errors.append("Script code is empty")
            return False, errors
        
        # Check syntax
        try:
            compile(script.code, f"<script:{script.name}>", 'exec')
        except SyntaxError as e:
            errors.append(f"Syntax error on line {e.lineno}: {e.msg}")
            return False, errors
        
        # Check structure
        if not script.is_valid_structure():
            errors.append("Script must define next_bet() function")
            return False, errors
        
        return True, errors
    
    def create_from_template(self, template_name: str, new_name: str, description: str = "") -> Optional[StrategyScript]:
        """
        Create new script from template.
        
        Args:
            template_name: Name of template to use
            new_name: Name for new script
            description: Optional description
            
        Returns:
            New script instance (not yet saved)
        """
        template = self.storage.load(template_name, is_template=True)
        if not template:
            return None
        
        # Create new script from template
        new_script = StrategyScript(
            name=new_name,
            description=description or template.description,
            code=template.code,
            is_builtin=False,
            author="User"
        )
        
        return new_script
