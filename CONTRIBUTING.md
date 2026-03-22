# Contributing to DuckDice Bot

Thank you for your interest in contributing to DuckDice Bot! This document provides guidelines and best practices for contributing.

## 🚀 Quick Start for Contributors

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/duckdice-bot.git
cd duckdice-bot
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt  # For building executables

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

### 3. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

## 📋 Development Guidelines

### Code Style

- **Python**: Follow PEP 8 style guide
- **Formatting**: Use Black formatter (already in requirements)
- **Line Length**: 100 characters maximum
- **Type Hints**: Use type hints where possible

Format your code:
```bash
black duckdice_cli.py duckdice_tui.py
black src/
```

### Code Organization

```
duckdice-bot/
├── src/                       # Core library code
│   ├── betbot_engine/         # Runtime engine and orchestration
│   ├── betbot_strategies/     # Built-in strategy implementations
│   └── duckdice_api/          # DuckDice API client
├── duckdice_cli.py            # Primary CLI entrypoint
├── duckdice_tui.py            # Terminal UI launcher (Textual/ncurses)
├── tests/                 # Test files
└── docs/                      # Documentation
```

### Testing

Run tests before submitting:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_strategies.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_martingale_doubles_on_loss()`
- Mock external API calls

Example:
```python
def test_strategy_calculation():
    """Test that strategy calculates next bet correctly."""
    strategy = MartingaleStrategy()
    next_bet = strategy.calculate(last_bet=1.0, won=False)
    assert next_bet == 2.0
```

## 🎯 What to Contribute

### High Priority

- **Bug Fixes**: Always welcome!
- **Strategy Improvements**: Enhance existing strategies
- **Documentation**: Improve guides, add examples
- **Test Coverage**: Add tests for untested code

### Medium Priority

- **New Strategies**: Add new betting strategies
- **UI Improvements**: Enhance CLI/TUI workflows and terminal UX
- **Performance**: Optimize slow operations
- **Error Handling**: Better error messages

### Ideas Welcome

- **New Features**: Propose new features via Issues
- **Refactoring**: Improve code structure
- **Accessibility**: Make UI more accessible
- **Localization**: Add translations

## 📝 Pull Request Process

### 1. Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass (`python -m pytest`)
- [ ] Code is formatted with Black
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated (under "Unreleased")
- [ ] Commit messages are clear and descriptive

### 2. Commit Messages

Use conventional commit format:

```
feat: Add Fibonacci betting strategy
fix: Correct balance calculation in simulator
docs: Update installation guide for Windows
test: Add tests for API error handling
refactor: Simplify bet logging logic
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding/updating tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `chore`: Maintenance tasks

### 3. Submit PR

1. Push your branch to your fork
2. Create Pull Request on GitHub
3. Fill out the PR template
4. Wait for review
5. Address review comments
6. Merge when approved!

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing [Issues](https://github.com/sushiomsky/duckdice-bot/issues)
2. Try latest version from `main` branch
3. Collect debug information

### Bug Report Template

```markdown
**Describe the bug**
Clear description of what happened

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should have happened

**Environment:**
- OS: [e.g., macOS 14.1]
- Python version: [e.g., 3.11.5]
- DuckDice Bot version: [e.g., 3.9.0]

**Logs/Screenshots**
Paste relevant logs or attach screenshots
```

## 💡 Suggesting Features

### Feature Request Template

```markdown
**Problem**
Describe the problem this feature would solve

**Solution**
Describe your proposed solution

**Alternatives**
Any alternative solutions you've considered

**Additional Context**
Any other context, mockups, or examples
```

## 🏗️ Building and Testing

### Build Desktop Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build for your platform
./build_release.sh      # Linux/macOS
build_windows.bat       # Windows

# Output in dist/
```

### Test the Build

```bash
# Run the executable
./dist/DuckDiceBot        # Linux/macOS
dist\DuckDiceBot.exe      # Windows
```

### Run Terminal Interfaces

```bash
# Start guided interactive CLI
python3 duckdice_cli.py interactive

# Launch modern Textual TUI
python3 duckdice_tui.py

# Launch lightweight ncurses TUI
python3 duckdice_tui.py --ncurses
```

## 📚 Documentation Standards

### Code Documentation

```python
def calculate_next_bet(last_bet: float, won: bool, balance: float) -> float:
    """
    Calculate the next bet amount based on previous result.
    
    Args:
        last_bet: The amount of the previous bet
        won: Whether the previous bet won
        balance: Current account balance
        
    Returns:
        The calculated next bet amount
        
    Raises:
        ValueError: If last_bet or balance is negative
        
    Example:
        >>> calculate_next_bet(1.0, False, 100.0)
        2.0
    """
    pass
```

### Markdown Documentation

- Use clear headings
- Add code examples
- Include screenshots for UI changes
- Update table of contents
- Check links work

## 🤝 Code Review

### What Reviewers Look For

- **Correctness**: Does it work?
- **Tests**: Are there tests? Do they pass?
- **Style**: Follows guidelines?
- **Documentation**: Is it documented?
- **Impact**: Could it break existing features?

### As a Reviewer

- Be respectful and constructive
- Explain *why* changes are needed
- Approve if looks good!
- Test the changes locally if possible

## 🎓 Learning Resources

### Python
- [PEP 8 Style Guide](https://pep8.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)

### Terminal UI (Textual)
- [Textual Documentation](https://textual.textualize.io/)
- [Textual Guide](https://textual.textualize.io/guide/)

### CLI
- [argparse Documentation](https://docs.python.org/3/library/argparse.html)

### DuckDice API
- [DuckDice Bot API](https://duckdice.io/bot-api)
- [API Documentation](https://duckdice.io/api-docs)

## 📞 Getting Help

- **Questions**: Open a [Discussion](https://github.com/sushiomsky/duckdice-bot/discussions)
- **Bugs**: Open an [Issue](https://github.com/sushiomsky/duckdice-bot/issues)
- **Chat**: Join community discussions

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- Listed in CHANGELOG.md for their contributions
- Mentioned in release notes
- Added to a CONTRIBUTORS.md file (coming soon!)

---

Thank you for contributing to DuckDice Bot! 🎲✨
