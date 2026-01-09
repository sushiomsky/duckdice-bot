# 🎯 Phase 2: Unified Script System - Implementation Plan

## Overview
Merge scripts and strategies into a single unified system where all strategies are editable Python scripts. Users can create, edit, and run custom strategies with a professional code editor featuring syntax highlighting, error detection, and code formatting.

---

## 📋 Detailed Task Breakdown

### ✅ Task 2.1: Unified Strategy Script Model (2 hours) - COMPLETE

**Status**: ✅ Complete

**Completed**:
1. ✅ Created `StrategyScript` model with full versioning
2. ✅ Created `ScriptStorage` with file-based storage in ~/.duckdice/strategies/
3. ✅ Created `ScriptLoader` with validation and caching
4. ✅ Implemented version history (keeps last 10 versions)

**Files Created**:
- ✅ `src/script_system/strategy_script.py` (4,516 bytes)
- ✅ `src/script_system/script_storage.py` (6,741 bytes)
- ✅ `src/script_system/script_loader.py` (5,104 bytes)

---

### ✅ Task 2.3: Script Validation Engine (1.5 hours) - COMPLETE

**Status**: ✅ Complete

**Completed**:
1. ✅ Created AST-based syntax validator
2. ✅ Implemented dangerous import detection (os, sys, subprocess, etc.)
3. ✅ Added required function signature validation
4. ✅ Safety checks for eval, exec, file operations
5. ✅ Best practices warnings (global variables, etc.)

**Files Created**:
- ✅ `src/script_system/validator.py` (11,611 bytes)

**Features**:
- Line-by-line error reporting with severity levels
- Validates required functions: next_bet(ctx)
- Validates optional functions: on_result(ctx, result), init(ctx, params)
- Blocks all dangerous operations

---

### ✅ Task 2.4: Safe Execution Sandbox (2.5 hours) - COMPLETE

**Status**: ✅ Complete

**Completed**:
1. ✅ Integrated RestrictedPython for safe execution
2. ✅ Implemented timeout protection (5s default)
3. ✅ Created restricted globals with safe builtins only
4. ✅ Added StrategyExecutor with betting-specific validation
5. ✅ Function caching for performance

**Files Created**:
- ✅ `src/script_system/executor.py` (11,258 bytes)

**Features**:
- Safe import handler (only allows math, random, decimal, etc.)
- Blocks os, sys, subprocess, file, eval, exec
- Timeout protection prevents infinite loops
- Validates bet parameters (amount > 0, 0 < chance < 100)
- Full error context in exceptions

---

### ✅ Task 2.5: Template Library (1 hour) - COMPLETE

**Status**: ✅ Complete

**Completed**:
1. ✅ Created 4 professional strategy templates
2. ✅ Each template has metadata JSON with parameters
3. ✅ Templates stored in ~/.duckdice/strategies/templates/

**Templates Created**:
- ✅ Simple Martingale (double on loss)
- ✅ Anti-Martingale (double on win)  
- ✅ Fixed Percentage (Kelly Criterion inspired)
- ✅ Target Profit (auto-stop at goal)

**Files Created**:
- ✅ `~/.duckdice/strategies/templates/simple_martingale.py` + .meta.json
- ✅ `~/.duckdice/strategies/templates/anti_martingale.py` + .meta.json
- ✅ `~/.duckdice/strategies/templates/fixed_percentage.py` + .meta.json
- ✅ `~/.duckdice/strategies/templates/target_profit.py` + .meta.json

---

### Task 2.2: Advanced Code Editor (3 hours) - NOT STARTED

**Goal**: Create a model where all strategies are Python scripts

**Subtasks**:
1. Create `StrategyScript` model:
   ```python
   class StrategyScript:
       name: str
       description: str
       code: str  # Python code
       is_builtin: bool  # True for pre-installed, False for custom
       created_at: datetime
       modified_at: datetime
       version: int
   ```

2. Create script storage system:
   - Directory: `~/.duckdice/strategies/`
   - Format: Python files (.py)
   - Metadata: JSON sidecar files

3. Convert existing strategies to script format:
   - Extract strategy logic to standalone Python
   - Add standard header/imports
   - Save as template scripts

4. Create strategy loader:
   - Scan strategy directory
   - Load both built-in and custom
   - Validate script structure
   - Import and register

**Files to Create**:
- `src/script_system/strategy_script.py`
- `src/script_system/script_storage.py`
- `src/script_system/script_loader.py`

---

### Task 2.2: Advanced Code Editor (3 hours)

**Goal**: Professional Python editor with all modern features

**Subtasks**:
1. NiceGUI Monaco Editor integration:
   ```python
   # Use Monaco Editor (VSCode editor)
   from nicegui import ui
   
   editor = ui.monaco_editor(
       language='python',
       theme='vs-dark',
       options={
           'lineNumbers': True,
           'minimap': {'enabled': True},
           'fontSize': 14,
           'formatOnPaste': True,
           'formatOnType': True,
       }
   )
   ```

2. Add syntax validation:
   - Real-time AST parsing
   - Show errors inline
   - Highlight problematic lines

3. Add code formatting:
   - Use `black` or `autopep8`
   - Format button
   - Auto-format on save

4. Add auto-completion:
   - Strategy API methods
   - Common variables
   - DuckDice API functions

5. Add line folding:
   - Fold functions
   - Fold classes
   - Fold comments

**Files to Create**:
- `app/ui/components/code_editor.py`

**Dependencies**:
```bash
pip install black autopep8
# Monaco editor already in NiceGUI
```

---

### Task 2.3: Script Validation Engine (1 hour)

**Goal**: Validate scripts before execution

**Subtasks**:
1. Create `ScriptValidator` class:
   ```python
   class ScriptValidator:
       def validate_syntax(code: str) -> List[Error]
       def validate_structure(code: str) -> List[Error]
       def validate_safety(code: str) -> List[Warning]
   ```

2. Syntax validation:
   - Parse with Python AST
   - Check for syntax errors
   - Return line numbers + messages

3. Structure validation:
   - Check for required functions (next_bet, on_result)
   - Verify function signatures
   - Ensure proper returns

4. Safety validation:
   - No dangerous imports (os, sys, subprocess)
   - No file operations
   - No network operations
   - Warn on infinite loops

**Files to Create**:
- `src/script_system/validator.py`

---

### Task 2.4: Safe Execution Sandbox (2 hours)

**Goal**: Execute user scripts safely

**Subtasks**:
1. Create execution sandbox:
   - Use RestrictedPython for safe exec
   - Limited globals/builtins
   - No dangerous operations

2. Create safe execution environment:
   ```python
   class SafeExecutor:
       def execute_script(
           code: str,
           globals_dict: Dict,
           timeout: int = 10
       ) -> Tuple[bool, Any, str]
   ```

3. Add timeout protection:
   - Max execution time per bet
   - Kill runaway scripts
   - Return timeout error

4. Add error handling:
   - Catch all exceptions
   - Return useful error messages
   - Don't crash main app

**Files to Create**:
- `src/script_system/executor.py`

**Dependencies**:
```bash
pip install RestrictedPython
```

---

### Task 2.5: Template Library (1 hour)

**Goal**: Pre-made script templates for users

**Subtasks**:
1. Create template directory: `~/.duckdice/templates/`

2. Create template scripts:
   - Simple Martingale
   - Anti-Martingale
   - Fixed Percentage
   - Target Profit
   - Stop Loss
   - Faucet Grind (script version)

3. Template metadata:
   - Name, description
   - Author, license
   - Difficulty level
   - Risk level

4. Template manager:
   - List templates
   - Create from template
   - Copy to custom scripts

**Files to Create**:
- `src/script_system/templates/`
- `src/script_system/template_manager.py`

---

### Task 2.6: Script Management UI (2 hours)

**Goal**: Full CRUD for scripts in NiceGUI

**Subtasks**:
1. Create script browser page:
   - List all scripts (built-in + custom)
   - Filter by type
   - Search by name
   - Sort by date/name

2. Create script editor page:
   - Monaco editor integration
   - Save/Save As buttons
   - Format code button
   - Run/Test button
   - Delete button (custom only)

3. Create new script wizard:
   - Name input
   - Description input
   - Template selection
   - Create from blank

4. Add version history:
   - Auto-save on edit
   - Keep last 10 versions
   - Restore from history
   - Compare versions

**Files to Create**:
- `app/ui/pages/script_editor.py`
- `app/ui/pages/script_browser.py`

---

### Task 2.7: Integration & Migration (1 hour)

**Goal**: Integrate with existing system

**Subtasks**:
1. Update strategy selector:
   - Show all scripts (built-in + custom)
   - Indicate custom vs built-in
   - Preview script before selection

2. Migrate existing strategies:
   - Convert all 17 strategies to script format
   - Keep backward compatibility
   - Add script versions to repo

3. Update auto-bet engine:
   - Load script instead of class
   - Execute with safe executor
   - Handle script errors gracefully

4. Update documentation:
   - Script API reference
   - How to create custom scripts
   - Best practices

**Files to Modify**:
- `app/ui/pages/auto_bet.py`
- `src/betbot_engine/engine.py`

---

## 📊 Implementation Timeline

| Task | Duration | Dependencies | Status |
|------|----------|--------------|--------|
| 2.1 Strategy Script Model | 2h | None | ⬜ TODO |
| 2.2 Advanced Code Editor | 3h | None | ⬜ TODO |
| 2.3 Script Validation | 1h | 2.1 | ⬜ TODO |
| 2.4 Safe Execution Sandbox | 2h | 2.1 | ⬜ TODO |
| 2.5 Template Library | 1h | 2.1 | ⬜ TODO |
| 2.6 Script Management UI | 2h | 2.2, 2.3 | ⬜ TODO |
| 2.7 Integration & Migration | 1h | All | ⬜ TODO |

**Total**: 12 hours (adjusted from initial 6-8h estimate)

---

## 🧪 Testing Strategy

### Unit Tests
- Script validation logic
- Safe execution sandbox
- Template loading
- Version history

### Integration Tests
- Script loading → execution
- Editor → save → load
- Template → customize → save

### Manual Tests
1. Create new script from blank
2. Create script from template
3. Edit existing built-in (should create custom copy)
4. Run script in simulation
5. Format code
6. Verify syntax errors shown
7. Test timeout protection
8. Test dangerous code blocked

---

## 📈 Success Metrics

Phase 2 is complete when:
- ✅ All 17 strategies available as editable scripts
- ✅ Monaco editor working with Python syntax
- ✅ Real-time syntax validation functional
- ✅ Code formatting working (black/autopep8)
- ✅ Script execution sandbox secure
- ✅ Template library with 6+ templates
- ✅ Full CRUD operations in UI
- ✅ Version history working
- ✅ No breaking changes to existing features

---

## 🔧 Technical Decisions

### Code Editor Choice
**Decision**: Use Monaco Editor (built into NiceGUI)
**Reasoning**: 
- Professional VSCode editor
- Full Python support
- Syntax highlighting built-in
- Minimap, folding, etc.
- No additional dependencies

### Script Storage
**Decision**: Python files in ~/.duckdice/strategies/
**Reasoning**:
- Easy to edit externally
- Git-friendly
- Standard Python format
- Easy backup/sharing

### Execution Sandbox
**Decision**: RestrictedPython
**Reasoning**:
- Industry standard for safe Python
- Allows most normal operations
- Blocks dangerous operations
- Good error messages

### Code Formatting
**Decision**: black (with autopep8 fallback)
**Reasoning**:
- Opinionated = consistent
- Used by Python community
- Fast and reliable
- Easy integration

---

## ⚠️ Risk & Challenges

### High Risk
1. **Script Security**: Malicious scripts could harm system
   - Mitigation: RestrictedPython + timeout
   - Test extensively

2. **Performance**: Real-time syntax checking could lag
   - Mitigation: Debounce validation (500ms delay)
   - Run in background thread

### Medium Risk
1. **Backward Compatibility**: Existing strategies must still work
   - Mitigation: Keep class-based system alongside
   - Gradual migration

2. **User Experience**: Editor must be intuitive
   - Mitigation: Tooltips, examples, documentation

### Low Risk
1. **Storage**: Many scripts could use disk space
   - Mitigation: Limit versions to 10 per script

---

## 📝 Next Steps

1. **Approve plan** and adjust timeline if needed
2. **Install dependencies**: RestrictedPython, black
3. **Start Task 2.1**: Create unified script model
4. **Iterate** with testing and feedback

---

**Document Version**: 1.0  
**Created**: 2026-01-09  
**Phase**: 2 - Unified Script System  
**Status**: Ready to implement  
**Estimated Completion**: 12 hours
