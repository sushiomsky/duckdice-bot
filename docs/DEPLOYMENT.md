# 🚀 DuckDice Bot - Deployment Guide

Current deployment guidance for the CLI-first DuckDice Bot architecture.

Primary interfaces:
- `duckdice_cli.py` (automation/headless)
- `duckdice_tui.py` (terminal UI: Textual or ncurses)

---

## ✅ Pre-Deployment Checklist

- Python 3.9+ installed (`python3 --version`)
- `pip` available
- virtual environment support (`python3 -m venv --help`)
- network connectivity to `duckdice.io`
- DuckDice API key for live modes
- repository cloned and dependencies installed

---

## 💻 System Requirements

Minimum:
- OS: Windows 10/11, macOS 10.15+, Linux
- CPU: Dual-core
- RAM: 2GB
- Disk: 500MB

Recommended:
- CPU: Quad-core
- RAM: 4GB+
- Low-latency internet connection

---

## 📦 Installation (Source)

```bash
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
python3 -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Optional for modern terminal UI:

```bash
pip install textual
```

---

## ⚙️ Configuration

### API Key

Set one of the following:

```bash
export DUCKDICE_API_KEY="your_api_key_here"
```

or configure through:

```bash
python3 duckdice_cli.py config
```

### Logging

```bash
export LOG_LEVEL=INFO
```

Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`.

---

## 🏃 Running the Application

### CLI (recommended for deployment/automation)

```bash
# Interactive guided setup
python3 duckdice_cli.py interactive

# Direct run example (simulation)
python3 duckdice_cli.py run \
  --mode simulation \
  --currency btc \
  --strategy classic-martingale \
  --balance 100 \
  --max-bets 100
```

### TUI (interactive terminal)

```bash
# Textual interface (default)
python3 duckdice_tui.py

# ncurses interface
python3 duckdice_tui.py --ncurses
```

### Convenience scripts

```bash
./scripts/QUICK_START.sh
./scripts/QUICK_DEPLOY.sh
```

---

## 🔁 Background/Service Deployment

For production servers, prefer CLI runs under a process manager.

### systemd (Linux) example

```ini
[Unit]
Description=DuckDice Bot CLI
After=network.target

[Service]
Type=simple
User=duckdice
WorkingDirectory=/home/duckdice/duckdice-bot
Environment="PATH=/home/duckdice/duckdice-bot/venv/bin"
Environment="DUCKDICE_API_KEY=replace_me"
Environment="LOG_LEVEL=INFO"
ExecStart=/home/duckdice/duckdice-bot/venv/bin/python duckdice_cli.py run --mode live-main --currency btc --strategy classic-martingale --max-bets 100000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### nohup example

```bash
mkdir -p data/logs
nohup python3 duckdice_cli.py run --mode live-main --currency btc --strategy classic-martingale --max-bets 100000 > data/logs/runtime.log 2>&1 &
```

---

## 🧪 Validation

Run before and after deployment updates:

```bash
python -m py_compile duckdice_cli.py duckdice_tui.py
pytest tests/ -q
```

Check runtime help/entrypoints:

```bash
python3 duckdice_cli.py --help
python3 duckdice_cli.py run --help
python3 duckdice_tui.py --help
```

---

## 📊 Monitoring

If running under redirected output/systemd:

```bash
tail -f data/logs/runtime.log
```

Use database/logging docs for deeper observability:
- `docs/DATABASE_LOGGING.md`
- `docs/INTERFACES/TUI_GUIDE.md`

---

## 🔧 Troubleshooting

### Missing dependency

```bash
pip install -r requirements.txt
```

### TUI launch fails

```bash
python3 duckdice_tui.py --ncurses
```

### API connection issues

```bash
python3 duckdice_cli.py config
python3 duckdice_cli.py run --help
```

Verify API key and network access to DuckDice.

---

## 🔒 Security Notes

- Never commit API keys.
- Prefer environment variables or local config (`~/.duckdice/`).
- Run as non-root user in production.
- Keep `LOG_LEVEL` at `INFO` unless debugging.

