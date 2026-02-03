# Installation Guide

Complete installation instructions for all platforms.

---

## 📦 Installation Methods

Choose the method that best suits your needs:

| Method | Best For | Python Required | Internet Required |
|--------|----------|-----------------|-------------------|
| **PyPI** | Most users | ✅ Yes (3.9+) | ✅ Yes |
| **Executable** | No Python setup | ❌ No | ✅ Download only |
| **From Source** | Developers | ✅ Yes (3.9+) | ✅ Yes |

---

## Method 1: Install from PyPI (Recommended)

### Prerequisites
- Python 3.9 or higher
- pip (comes with Python)
- Internet connection

### Installation

```bash
# Install package
pip install duckdice-betbot

# Verify installation
duckdice --version

# Optional: Install with TUI support
pip install duckdice-betbot[tui]
```

### Upgrade

```bash
# Upgrade to latest version
pip install --upgrade duckdice-betbot
```

### Uninstall

```bash
pip uninstall duckdice-betbot
```

---

## Method 2: Download Executable

**No Python installation required!**

### Windows

1. Download `duckdice-bot-windows-x64.zip` from [Releases](https://github.com/sushiomsky/duckdice-bot/releases/latest)
2. Extract ZIP file
3. Open PowerShell/CMD in extracted folder
4. Run:
   ```powershell
   .\duckdice.exe --help
   ```

**Optional**: Add to PATH
```powershell
# Add current directory to PATH (temporary)
$env:PATH += ";$PWD"

# Now run from anywhere
duckdice --help
```

### macOS

1. Download `duckdice-bot-macos-universal.tar.gz` from [Releases](https://github.com/sushiomsky/duckdice-bot/releases/latest)
2. Extract:
   ```bash
   tar -xzf duckdice-bot-macos-universal.tar.gz
   cd duckdice-bot-macos-universal
   ```
3. Make executable:
   ```bash
   chmod +x duckdice
   ```
4. Run:
   ```bash
   ./duckdice --help
   ```

**If you see "unidentified developer" warning:**
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine duckdice

# Or allow in System Preferences > Security & Privacy
```

**Optional**: Install to `/usr/local/bin`
```bash
sudo cp duckdice /usr/local/bin/
duckdice --help  # Now available globally
```

### Linux

1. Download `duckdice-bot-linux-x64.tar.gz` from [Releases](https://github.com/sushiomsky/duckdice-bot/releases/latest)
2. Extract:
   ```bash
   tar -xzf duckdice-bot-linux-x64.tar.gz
   cd duckdice-bot-linux-x64
   ```
3. Make executable:
   ```bash
   chmod +x duckdice
   ```
4. Run:
   ```bash
   ./duckdice --help
   ```

**Optional**: Install to `/usr/local/bin`
```bash
sudo cp duckdice /usr/local/bin/
duckdice --help  # Now available globally
```

---

## Method 3: Install from Source

### Prerequisites
- Python 3.9+
- git
- pip

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# 2. (Optional) Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python duckdice_cli.py --help
```

### Running from Source

```bash
# CLI
python duckdice_cli.py run --strategy martingale

# TUI (requires rich)
pip install rich
python duckdice_tui.py

# Or create alias
alias duckdice='python /path/to/duckdice_cli.py'
```

---

## 🔧 Post-Installation Setup

### 1. Get API Key

1. Create account at [DuckDice.io](https://duckdice.io)
2. Go to Settings → API
3. Generate new API key
4. Copy the key

### 2. Configure API Key

**Option A: Environment Variable (Recommended)**

```bash
# Linux/macOS (add to ~/.bashrc or ~/.zshrc)
export DUCKDICE_API_KEY="your-api-key-here"

# Windows PowerShell (add to profile)
$env:DUCKDICE_API_KEY="your-api-key-here"

# Windows CMD
set DUCKDICE_API_KEY=your-api-key-here
```

**Option B: .env File**

```bash
# Create .env file in current directory
echo "DUCKDICE_API_KEY=your-api-key" > .env
```

**Option C: Command Line (Least Secure)**

```bash
duckdice run --strategy martingale --api-key "your-api-key"
```

### 3. Test Installation

```bash
# List strategies
duckdice list-strategies

# Run simulation (no API key needed)
duckdice run --strategy dalembert --bets 10 --simulate

# Run live (requires API key)
duckdice run --strategy martingale --bets 5
```

---

## 🐍 Python Version Requirements

| Python Version | Supported | Notes |
|----------------|-----------|-------|
| 3.9 | ✅ Yes | Minimum version |
| 3.10 | ✅ Yes | Fully supported |
| 3.11 | ✅ Yes | Recommended |
| 3.12 | ✅ Yes | Latest supported |
| 3.8 | ❌ No | Too old |
| 3.13+ | ⚠️ Untested | May work |

**Check your Python version:**
```bash
python --version
# or
python3 --version
```

---

## 🔍 Troubleshooting

### "command not found: duckdice"

**If installed via pip:**
```bash
# Check if pip bin directory is in PATH
python -m pip show duckdice-betbot

# Or run directly
python -m duckdice_cli --help
```

**If using executable:**
```bash
# Use full path
./duckdice --help

# Or add to PATH (see platform-specific instructions above)
```

### "No module named 'duckdice_api'"

You're running from source without installing dependencies:
```bash
pip install -r requirements.txt
```

### "ImportError: No module named 'rich'"

TUI requires the `rich` library:
```bash
pip install rich
# or
pip install duckdice-betbot[tui]
```

### Windows: "Cannot be loaded because running scripts is disabled"

PowerShell execution policy issue:
```powershell
# Check current policy
Get-ExecutionPolicy

# Set to allow scripts (requires admin)
Set-ExecutionPolicy RemoteSigned

# Or run without changing policy
powershell -ExecutionPolicy Bypass -File script.ps1
```

### macOS: "duckdice cannot be opened"

Gatekeeper blocking unsigned binary:
```bash
# Remove quarantine
xattr -d com.apple.quarantine duckdice

# Or: System Preferences > Security & Privacy > Allow
```

### Linux: "Permission denied"

Executable not marked as executable:
```bash
chmod +x duckdice
```

### API Connection Issues

If getting connection errors:

1. **Check internet connection**
2. **Try different domain**:
   ```bash
   # API client automatically tries:
   # duckdice.io → duckdice.live → duckdice.net
   ```
3. **Check API key**:
   ```bash
   # Test API key
   duckdice balance
   ```
4. **Check firewall**:
   - Ensure outbound HTTPS (port 443) allowed
   - Some corporate firewalls block gambling sites

---

## 📦 Dependencies

### Core Dependencies (Automatic)
- `requests` - HTTP client
- `python-dotenv` - Environment variable management

### Optional Dependencies
- `rich` - TUI interface (install with `[tui]` extra)
- `pytest` - Testing (dev only)
- `pyinstaller` - Building executables (dev only)

### Full Dependency Tree

```bash
# View all dependencies
pip show duckdice-betbot

# Or check requirements.txt
cat requirements.txt
```

---

## 🔄 Upgrading

### From PyPI

```bash
# Upgrade to latest
pip install --upgrade duckdice-betbot

# Check version
duckdice --version
```

### From Source

```bash
cd duckdice-bot
git pull origin main
pip install -r requirements.txt
```

### From Executable

Download latest release and replace old executable.

---

## 🗑️ Uninstallation

### PyPI Installation

```bash
pip uninstall duckdice-betbot
```

### Source Installation

```bash
# If you created virtual environment
rm -rf venv

# Remove repository
rm -rf duckdice-bot
```

### Executable Installation

Just delete the executable and extracted folder.

### Clean Up Data

```bash
# Remove bet history database (optional)
rm -rf data/

# Remove config files (optional)
rm .env
```

---

## 🌐 Platform-Specific Notes

### Windows

- Use PowerShell or CMD (not Git Bash for executables)
- Antivirus may flag executable - whitelist if needed
- Windows Defender SmartScreen may block - click "More info" → "Run anyway"

### macOS

- Universal binary works on Intel and Apple Silicon
- May need to allow in Security & Privacy settings
- Python from python.org recommended over system Python

### Linux

- Works on most distributions (Ubuntu, Debian, Fedora, Arch, etc.)
- May need to install `python3-venv` on some distros:
  ```bash
  sudo apt install python3-venv  # Ubuntu/Debian
  sudo dnf install python3-venv  # Fedora
  ```

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/sushiomsky/duckdice-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sushiomsky/duckdice-bot/discussions)
- **Documentation**: [Full Docs](../docs/)

---

**Next Steps**:
- [Getting Started Guide](../GETTING_STARTED.md)
- [CLI Guide](INTERFACES/CLI_GUIDE.md)
- [Strategy Guide](STRATEGIES/README.md)
