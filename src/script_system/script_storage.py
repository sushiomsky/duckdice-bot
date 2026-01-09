"""
Script Storage

Manages loading and saving strategy scripts to filesystem.
Scripts stored in: ~/.duckdice/strategies/
Metadata stored alongside as .meta.json files
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import os

from .strategy_script import StrategyScript


class ScriptStorage:
    """Manage strategy script storage on filesystem"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize storage.
        
        Args:
            base_dir: Base directory for scripts (default: ~/.duckdice/strategies/)
        """
        if base_dir is None:
            self.base_dir = Path.home() / ".duckdice" / "strategies"
        else:
            self.base_dir = Path(base_dir)
        
        # Create directories if they don't exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        self.custom_dir = self.base_dir / "custom"
        self.builtin_dir = self.base_dir / "builtin"
        self.templates_dir = self.base_dir / "templates"
        
        self.custom_dir.mkdir(exist_ok=True)
        self.builtin_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
    
    def save(self, script: StrategyScript, is_template: bool = False) -> Path:
        """
        Save script to filesystem.
        
        Args:
            script: Script to save
            is_template: Save as template instead of regular script
            
        Returns:
            Path to saved file
        """
        # Determine directory
        if is_template:
            directory = self.templates_dir
        elif script.is_builtin:
            directory = self.builtin_dir
        else:
            directory = self.custom_dir
        
        # Save Python file
        script_path = directory / script.get_file_name()
        script_path.write_text(script.code, encoding='utf-8')
        
        # Save metadata
        metadata_path = directory / script.get_metadata_file_name()
        metadata = script.to_dict()
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        
        # Update script's file path
        script.file_path = script_path
        
        return script_path
    
    def load(self, name: str, is_builtin: bool = False, is_template: bool = False) -> Optional[StrategyScript]:
        """
        Load script from filesystem.
        
        Args:
            name: Script name
            is_builtin: Load from builtin directory
            is_template: Load from templates directory
            
        Returns:
            Loaded script or None if not found
        """
        # Determine directory
        if is_template:
            directory = self.templates_dir
        elif is_builtin:
            directory = self.builtin_dir
        else:
            directory = self.custom_dir
        
        # Load Python file
        script_path = directory / f"{name}.py"
        if not script_path.exists():
            return None
        
        code = script_path.read_text(encoding='utf-8')
        
        # Load metadata if exists
        metadata_path = directory / f"{name}.meta.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            metadata['code'] = code
            metadata['file_path'] = str(script_path)
            script = StrategyScript.from_dict(metadata)
        else:
            # Create minimal script
            script = StrategyScript(
                name=name,
                description="",
                code=code,
                is_builtin=is_builtin,
                file_path=script_path
            )
        
        return script
    
    def list_all(self) -> List[StrategyScript]:
        """List all scripts (builtin + custom)"""
        scripts = []
        
        # Load builtin scripts
        for path in self.builtin_dir.glob("*.py"):
            name = path.stem
            script = self.load(name, is_builtin=True)
            if script:
                scripts.append(script)
        
        # Load custom scripts
        for path in self.custom_dir.glob("*.py"):
            name = path.stem
            script = self.load(name, is_builtin=False)
            if script:
                scripts.append(script)
        
        return scripts
    
    def list_templates(self) -> List[StrategyScript]:
        """List all template scripts"""
        templates = []
        
        for path in self.templates_dir.glob("*.py"):
            name = path.stem
            script = self.load(name, is_template=True)
            if script:
                templates.append(script)
        
        return templates
    
    def delete(self, name: str, is_builtin: bool = False) -> bool:
        """
        Delete script from filesystem.
        
        Args:
            name: Script name
            is_builtin: Delete from builtin directory (not recommended)
            
        Returns:
            True if deleted successfully
        """
        if is_builtin:
            # Prevent deleting builtin scripts
            return False
        
        directory = self.custom_dir
        
        # Delete Python file
        script_path = directory / f"{name}.py"
        if script_path.exists():
            script_path.unlink()
        
        # Delete metadata
        metadata_path = directory / f"{name}.meta.json"
        if metadata_path.exists():
            metadata_path.unlink()
        
        return True
    
    def exists(self, name: str, is_builtin: bool = False) -> bool:
        """Check if script exists"""
        directory = self.builtin_dir if is_builtin else self.custom_dir
        return (directory / f"{name}.py").exists()
    
    def get_version_history_dir(self, name: str) -> Path:
        """Get version history directory for script"""
        directory = self.custom_dir / ".versions" / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    def save_version(self, script: StrategyScript) -> None:
        """Save current version to history"""
        if script.is_builtin:
            return  # Don't version builtin scripts
        
        version_dir = self.get_version_history_dir(script.name)
        
        # Save with revision number
        version_file = version_dir / f"rev_{script.revision}.py"
        version_file.write_text(script.code, encoding='utf-8')
        
        # Keep only last 10 versions
        versions = sorted(version_dir.glob("rev_*.py"), key=lambda p: p.stat().st_mtime)
        if len(versions) > 10:
            for old_version in versions[:-10]:
                old_version.unlink()
