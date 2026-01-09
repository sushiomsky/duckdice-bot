"""
Strategy Script Model

Represents a betting strategy as an editable Python script.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class StrategyScript:
    """
    Represents a betting strategy script.
    
    All strategies are Python scripts with standard structure:
    - next_bet(ctx) -> BetSpec: Calculate next bet
    - on_result(ctx, result) -> None: Handle bet result
    - Optional: init(ctx, params) -> None: Initialize strategy
    """
    
    # Core attributes
    name: str  # Unique strategy name (alphanumeric + dash/underscore)
    description: str  # Brief description
    code: str  # Python source code
    
    # Metadata
    is_builtin: bool = False  # True for pre-installed strategies
    author: str = "User"
    version: str = "1.0.0"
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    # Version control
    revision: int = 1  # Increments on each save
    
    # Configuration
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # File path (None for unsaved scripts)
    file_path: Optional[Path] = None
    
    def __post_init__(self):
        """Validate script attributes"""
        # Sanitize name (alphanumeric + dash/underscore only)
        if not self.name:
            raise ValueError("Script name cannot be empty")
        
        # Convert name to safe filename
        self.name = "".join(c for c in self.name if c.isalnum() or c in "-_")
        
        if not self.name:
            raise ValueError("Script name must contain at least one valid character")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'is_builtin': self.is_builtin,
            'author': self.author,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'revision': self.revision,
            'parameters': self.parameters,
            'file_path': str(self.file_path) if self.file_path else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyScript':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            code=data['code'],
            is_builtin=data.get('is_builtin', False),
            author=data.get('author', 'User'),
            version=data.get('version', '1.0.0'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            modified_at=datetime.fromisoformat(data['modified_at']) if 'modified_at' in data else datetime.now(),
            revision=data.get('revision', 1),
            parameters=data.get('parameters', {}),
            file_path=Path(data['file_path']) if data.get('file_path') else None
        )
    
    def get_file_name(self) -> str:
        """Get safe filename for this script"""
        return f"{self.name}.py"
    
    def get_metadata_file_name(self) -> str:
        """Get metadata filename"""
        return f"{self.name}.meta.json"
    
    def update_code(self, new_code: str) -> None:
        """Update script code and increment revision"""
        self.code = new_code
        self.modified_at = datetime.now()
        self.revision += 1
    
    def is_valid_structure(self) -> bool:
        """
        Check if script has required structure.
        Must define: next_bet()
        Optional: on_result(), init()
        """
        try:
            import ast
            tree = ast.parse(self.code)
            
            # Find all function definitions
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            
            # Must have next_bet
            if 'next_bet' not in functions:
                return False
            
            return True
        except SyntaxError:
            return False
    
    def get_summary(self) -> str:
        """Get one-line summary"""
        lines = self.code.split('\n')
        if len(lines) > 10:
            return f"{len(lines)} lines, revision {self.revision}"
        return f"{len(lines)} lines"
