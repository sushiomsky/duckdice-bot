"""
Script Validation Engine for Strategy Scripts.

Validates Python scripts for:
- Syntax errors
- Required function signatures
- Dangerous imports and operations
- Type safety and best practices
"""

import ast
import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    line: int
    column: int
    message: str
    severity: str  # 'error', 'warning', 'info'
    
    def to_dict(self) -> Dict:
        return {
            'line': self.line,
            'column': self.column,
            'message': self.message,
            'severity': self.severity
        }


@dataclass
class ValidationResult:
    """Result of script validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings]
        }


class ScriptValidator:
    """Validates strategy scripts for safety and correctness."""
    
    # Dangerous modules that should not be imported
    DANGEROUS_IMPORTS = {
        'os', 'sys', 'subprocess', 'shutil', 'glob',
        'socket', 'urllib', 'requests', 'http',
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'importlib', 'pkgutil', 'runpy'
    }
    
    # Safe modules allowed for strategies
    SAFE_IMPORTS = {
        'math', 'random', 'decimal', 'fractions',
        'statistics', 'datetime', 'time',
        'typing', 'dataclasses', 'enum',
        'collections', 'itertools', 'functools'
    }
    
    # Required function signatures
    REQUIRED_FUNCTIONS = {
        'next_bet': ['ctx']
    }
    
    # Optional function signatures
    OPTIONAL_FUNCTIONS = {
        'on_result': ['ctx', 'result'],
        'init': ['ctx', 'params']
    }
    
    def validate(self, code: str) -> ValidationResult:
        """
        Validate a strategy script.
        
        Args:
            code: Python source code to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # 1. Syntax validation
        syntax_errors = self._validate_syntax(code)
        errors.extend(syntax_errors)
        
        if syntax_errors:
            # Can't proceed with AST analysis if syntax is invalid
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Parse AST for further validation
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(ValidationError(
                line=e.lineno or 0,
                column=e.offset or 0,
                message=f"Syntax error: {e.msg}",
                severity='error'
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # 2. Import validation
        import_errors, import_warnings = self._validate_imports(tree)
        errors.extend(import_errors)
        warnings.extend(import_warnings)
        
        # 3. Function signature validation
        func_errors, func_warnings = self._validate_functions(tree)
        errors.extend(func_errors)
        warnings.extend(func_warnings)
        
        # 4. Safety validation
        safety_errors, safety_warnings = self._validate_safety(tree)
        errors.extend(safety_errors)
        warnings.extend(safety_warnings)
        
        # 5. Best practices validation
        practice_warnings = self._validate_best_practices(tree)
        warnings.extend(practice_warnings)
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
    
    def _validate_syntax(self, code: str) -> List[ValidationError]:
        """Validate Python syntax."""
        errors = []
        
        try:
            compile(code, '<script>', 'exec')
        except SyntaxError as e:
            errors.append(ValidationError(
                line=e.lineno or 0,
                column=e.offset or 0,
                message=f"Syntax error: {e.msg}",
                severity='error'
            ))
        except Exception as e:
            errors.append(ValidationError(
                line=0,
                column=0,
                message=f"Compilation error: {str(e)}",
                severity='error'
            ))
        
        return errors
    
    def _validate_imports(self, tree: ast.AST) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate imports for safety."""
        errors = []
        warnings = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.DANGEROUS_IMPORTS:
                        errors.append(ValidationError(
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Dangerous import '{alias.name}' is not allowed",
                            severity='error'
                        ))
                    elif alias.name not in self.SAFE_IMPORTS:
                        warnings.append(ValidationError(
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Import '{alias.name}' may not be available in sandbox",
                            severity='warning'
                        ))
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module in self.DANGEROUS_IMPORTS or module.split('.')[0] in self.DANGEROUS_IMPORTS:
                    errors.append(ValidationError(
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Dangerous import from '{module}' is not allowed",
                        severity='error'
                    ))
                elif module not in self.SAFE_IMPORTS and module.split('.')[0] not in self.SAFE_IMPORTS:
                    warnings.append(ValidationError(
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Import from '{module}' may not be available in sandbox",
                        severity='warning'
                    ))
        
        return errors, warnings
    
    def _validate_functions(self, tree: ast.AST) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate required function signatures."""
        errors = []
        warnings = []
        
        # Find all function definitions
        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions[node.name] = node
        
        # Check required functions
        for func_name, required_args in self.REQUIRED_FUNCTIONS.items():
            if func_name not in functions:
                errors.append(ValidationError(
                    line=0,
                    column=0,
                    message=f"Required function '{func_name}({', '.join(required_args)})' is missing",
                    severity='error'
                ))
            else:
                func_node = functions[func_name]
                args = [arg.arg for arg in func_node.args.args]
                
                if args != required_args:
                    errors.append(ValidationError(
                        line=func_node.lineno,
                        column=func_node.col_offset,
                        message=f"Function '{func_name}' must have signature: {func_name}({', '.join(required_args)})",
                        severity='error'
                    ))
        
        # Check optional functions have correct signatures
        for func_name, expected_args in self.OPTIONAL_FUNCTIONS.items():
            if func_name in functions:
                func_node = functions[func_name]
                args = [arg.arg for arg in func_node.args.args]
                
                if args != expected_args:
                    warnings.append(ValidationError(
                        line=func_node.lineno,
                        column=func_node.col_offset,
                        message=f"Function '{func_name}' should have signature: {func_name}({', '.join(expected_args)})",
                        severity='warning'
                    ))
        
        return errors, warnings
    
    def _validate_safety(self, tree: ast.AST) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate script doesn't use dangerous operations."""
        errors = []
        warnings = []
        
        for node in ast.walk(tree):
            # Check for eval/exec calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('eval', 'exec', 'compile', '__import__'):
                        errors.append(ValidationError(
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Use of '{node.func.id}()' is not allowed",
                            severity='error'
                        ))
            
            # Check for file operations
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('open', 'file'):
                        errors.append(ValidationError(
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"File operations are not allowed",
                            severity='error'
                        ))
            
            # Check for dangerous attribute access
            if isinstance(node, ast.Attribute):
                dangerous_attrs = {'__import__', '__builtins__', '__globals__', '__locals__'}
                if node.attr in dangerous_attrs:
                    errors.append(ValidationError(
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Access to '{node.attr}' is not allowed",
                        severity='error'
                    ))
        
        return errors, warnings
    
    def _validate_best_practices(self, tree: ast.AST) -> List[ValidationError]:
        """Validate best practices and code quality."""
        warnings = []
        
        # Check for global variables
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                warnings.append(ValidationError(
                    line=node.lineno,
                    column=node.col_offset,
                    message="Use of global variables may cause issues. Consider using class attributes.",
                    severity='info'
                ))
        
        return warnings


def validate_script(code: str) -> ValidationResult:
    """
    Convenience function to validate a script.
    
    Args:
        code: Python source code to validate
        
    Returns:
        ValidationResult with errors and warnings
    """
    validator = ScriptValidator()
    return validator.validate(code)
