# Installation Instructions - v3.9.0

Choose your platform below for installation instructions.

---

## 📦 Download Packages

### Available Downloads

- **Source Code** (All Platforms): `duckdice-bot-v3.9.0-source.tar.gz`
- **macOS (ARM64)**: `duckdice-bot-v3.9.0-macos-arm64.tar.gz`
- **Checksums**: `SHA256SUMS`

**Windows and Linux users:** Use the source code package.

---

## 🍎 macOS Installation

### Requirements
- macOS 11.0 or later
- Python 3.9+ (recommended: Python 3.11)
- Homebrew (optional, for easy Python installation)

### Quick Install

1. **Download** the macOS package:
   ```bash
   curl -L https://github.com/sushiomsky/duckdice-bot/releases/download/v3.9.0/duckdice-bot-v3.9.0-macos-arm64.tar.gz -o duckdice-bot.tar.gz
   ```

2. **Extract**:
   ```bash
   tar -xzf duckdice-bot.tar.gz
   cd duckdice-bot
   ```

3. **Install dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Run**:
   ```bash
   ./run_nicegui.sh
   ```

5. **Open browser** to http://localhost:8080

### Intel Mac
If you're on Intel Mac, use the source package instead.

---

## 🐧 Linux Installation

### Requirements
- Ubuntu 20.04+ / Debian 11+ / Fedora 35+ / Arch Linux
- Python 3.9+
- pip

### Ubuntu/Debian

1. **Install Python and dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git
   ```

2. **Download** source package:
   ```bash
   wget https://github.com/sushiomsky/duckdice-bot/releases/download/v3.9.0/duckdice-bot-v3.9.0-source.tar.gz
   tar -xzf duckdice-bot-v3.9.0-source.tar.gz
   cd duckdice-bot
   ```

3. **Create virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run**:
   ```bash
   ./run_nicegui.sh
   ```

6. **Access** at http://localhost:8080

### Fedora/RHEL

```bash
sudo dnf install python3 python3-pip
# Then follow steps 2-6 from Ubuntu instructions
```

### Arch Linux

```bash
sudo pacman -S python python-pip
# Then follow steps 2-6 from Ubuntu instructions
```

---

## 🪟 Windows Installation

### Requirements
- Windows 10/11
- Python 3.9+ from [python.org](https://www.python.org/downloads/)
- Git (optional, for cloning)

### Method 1: Using Source Package

1. **Download Python** from https://www.python.org/downloads/
   - ⚠️ During installation, check "Add Python to PATH"

2. **Download** source package:
   - Go to: https://github.com/sushiomsky/duckdice-bot/releases/tag/v3.9.0
   - Download: `duckdice-bot-v3.9.0-source.tar.gz`
   - Extract using 7-Zip or WinRAR

3. **Open PowerShell** in the extracted folder:
   - Right-click folder → "Open in Terminal" (Windows 11)
   - Or Shift+Right-click → "Open PowerShell window here"

4. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

5. **Run the bot**:
   ```powershell
   python -m app.main
   ```
   
   Or create `run.bat`:
   ```batch
   @echo off
   python -m app.main
   pause
   ```

6. **Open browser** to http://localhost:8080

### Method 2: Using Git

```powershell
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
git checkout v3.9.0
pip install -r requirements.txt
python -m app.main
```

---

## 🐳 Docker Installation (All Platforms)

### Requirements
- Docker Desktop installed

### Run with Docker

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   # Copy application
   COPY . /app
   
   # Install dependencies
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Expose port
   EXPOSE 8080
   
   # Run
   CMD ["python", "-m", "app.main"]
   ```

2. **Build and run**:
   ```bash
   docker build -t duckdice-bot .
   docker run -p 8080:8080 duckdice-bot
   ```

3. **Access** at http://localhost:8080

---

## 📱 Accessing from Other Devices

Once running, access the bot from:
- **Same computer**: http://localhost:8080
- **Other devices** on same network: http://YOUR_IP:8080
  - Find your IP:
    - Windows: `ipconfig`
    - macOS/Linux: `ifconfig` or `ip addr`

---

## ⚙️ First-Time Setup

1. **Open browser** to http://localhost:8080
2. Go to **Settings** (⚙️ icon or Ctrl+8)
3. Enter your **DuckDice API Key**
   - Get it from: https://duckdice.io → Settings → API
4. Click **Connect**
5. You're ready to start!

---

## 🚀 Enable Turbo Mode

For maximum betting speed:

1. Go to **Settings** (Ctrl+8)
2. Scroll to **Performance** section
3. Toggle **⚡ Turbo Mode (Maximum Speed)**
4. Save

⚠️ **Note**: Turbo mode is best for simulation and testing.

---

## 🔍 Verify Installation

Run this to verify everything works:

```bash
python3 -c "from app.main import ui; print('✅ Installation successful!')"
```

---

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### Port 8080 already in use
Edit `app/config.py` and change `DEFAULT_PORT = 8080` to another port.

### Permission denied on run_nicegui.sh
```bash
chmod +x run_nicegui.sh
```

### Can't access from other devices
Check firewall settings and ensure port 8080 is allowed.

---

## 📚 Documentation

- **Quick Start**: See `QUICKSTART.md`
- **Full README**: See `README.md`
- **Release Notes**: See `RELEASE_NOTES_v3.9.0.md`

---

## 💡 Tips

- Use **Ctrl+7** for quick access to Statistics
- Press **?** to see all keyboard shortcuts
- Enable **Turbo Mode** for faster simulation testing
- Check **Statistics** regularly to analyze performance

---

## 🆘 Need Help?

- **Issues**: https://github.com/sushiomsky/duckdice-bot/issues
- **Discussions**: https://github.com/sushiomsky/duckdice-bot/discussions
- **Documentation**: Full docs in repository

---

## 🎉 Enjoy!

You're all set! Start betting responsibly with the fastest DuckDice bot available.

**Version**: 3.9.0 "Turbo Edition"  
**License**: MIT
