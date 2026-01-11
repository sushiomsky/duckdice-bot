# 🚀 DuckDice Bot - Deployment Guide

**Version**: 4.0.0 (NiceGUI Complete Edition)  
**Date**: January 11, 2026  
**Status**: Production Ready ✅

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Production Deployment](#production-deployment)
7. [Testing & Validation](#testing--validation)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Security Best Practices](#security-best-practices)

---

## ✅ Pre-Deployment Checklist

Before deploying, ensure:

- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] pip package manager available (`pip --version`)
- [ ] Git installed (for source deployment)
- [ ] Virtual environment support (`python3 -m venv --help`)
- [ ] Sufficient disk space (500MB recommended)
- [ ] Network connectivity to duckdice.io
- [ ] DuckDice account with API key (for live mode)

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **CPU**: Dual-core 2.0 GHz
- **RAM**: 2GB
- **Disk**: 500MB free space
- **Network**: Stable internet connection

### Recommended Requirements
- **OS**: Latest versions
- **CPU**: Quad-core 2.5 GHz+
- **RAM**: 4GB+
- **Disk**: 1GB free space
- **Network**: Low-latency connection (<100ms to duckdice.io)

### Software Dependencies
```
Python >= 3.8
nicegui >= 1.4.0
matplotlib >= 3.8.0
requests >= 2.31.0
PyYAML >= 6.0.2
pynput >= 1.7.6
RestrictedPython >= 6.0
```

---

## 📦 Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Make scripts executable (macOS/Linux)
chmod +x run_nicegui.sh run_gui_web.sh run_gui.sh

# Run web interface
./run_nicegui.sh
# OR
python gui/app.py
```

### Method 2: Pre-built Packages

Download from [Releases](https://github.com/sushiomsky/duckdice-bot/releases/latest):

**Windows**:
```bash
# Download DuckDiceBot-Windows-x64.zip
# Extract and run DuckDiceBot.exe
```

**macOS**:
```bash
# Download DuckDiceBot-macOS-universal.zip
# Extract and run DuckDiceBot
# Allow in System Preferences > Security if needed
```

**Linux**:
```bash
# Download DuckDiceBot-Linux-x64.tar.gz
tar -xzf DuckDiceBot-Linux-x64.tar.gz
cd DuckDiceBot
./DuckDiceBot
```

### Method 3: Docker (Advanced)

```dockerfile
# Dockerfile (create in project root)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["python", "gui/app.py"]
```

```bash
# Build and run
docker build -t duckdice-bot .
docker run -p 8080:8080 -v $(pwd)/data:/app/data duckdice-bot
```

---

## ⚙️ Configuration

### 1. Environment Variables (Optional)

Create `.env` file:
```bash
DUCKDICE_API_KEY=your_api_key_here
DEFAULT_CURRENCY=btc
DEFAULT_BALANCE=0.001
LOG_LEVEL=INFO
```

### 2. API Key Setup

**Get API Key**:
1. Visit https://duckdice.io
2. Login → Account Settings
3. Navigate to Bot API section
4. Generate new API key
5. Copy and save securely

**Configure in App**:
1. Open web interface (http://localhost:8080)
2. Go to **Settings** tab
3. Paste API key
4. Click **Test Connection**
5. Verify "Connection successful" message

### 3. Database Setup

Database auto-creates on first run:
```bash
# Location: data/duckdice_bot.db
# Tables: bet_history, strategy_profiles, sessions
# No manual setup required
```

### 4. Strategy Configuration

17 strategies available:
- Martingale, Anti-Martingale, D'Alembert
- Fibonacci, Labouchere, Paroli
- Oscar's Grind, Pyramid, Reverse Pyramid
- Double Street, And more...

Configure in **Strategies** tab with visual form builder.

---

## 🏃 Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Run web interface
python gui/app.py

# Access at http://localhost:8080
```

### Production Mode

```bash
# Run with auto-restart (using screen/tmux)
screen -S duckdice
source venv/bin/activate
python gui/app.py --reload
# Detach: Ctrl+A, D
# Reattach: screen -r duckdice

# Or use systemd (Linux)
sudo systemctl start duckdice-bot
```

### Background Process

```bash
# Using nohup
nohup python gui/app.py > logs/app.log 2>&1 &

# Check process
ps aux | grep "gui/app.py"

# Stop process
kill <PID>
```

---

## 🌐 Production Deployment

### Nginx Reverse Proxy (Recommended)

```nginx
# /etc/nginx/sites-available/duckdice-bot
server {
    listen 80;
    server_name duckdice.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/duckdice-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Add SSL with Let's Encrypt
sudo certbot --nginx -d duckdice.yourdomain.com
```

### Systemd Service (Linux)

```ini
# /etc/systemd/system/duckdice-bot.service
[Unit]
Description=DuckDice Bot Web Interface
After=network.target

[Service]
Type=simple
User=duckdice
WorkingDirectory=/home/duckdice/duckdice-bot
Environment="PATH=/home/duckdice/duckdice-bot/venv/bin"
ExecStart=/home/duckdice/duckdice-bot/venv/bin/python gui/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable duckdice-bot
sudo systemctl start duckdice-bot
sudo systemctl status duckdice-bot

# View logs
sudo journalctl -u duckdice-bot -f
```

### Cloud Deployment

#### AWS EC2
```bash
# Launch t2.micro instance (Ubuntu 22.04)
# Open port 8080 in security group
# SSH and install
ssh ubuntu@your-ec2-ip
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
# Follow installation steps
```

#### DigitalOcean
```bash
# Create $5/month droplet (Ubuntu)
# Same as EC2 setup
```

#### Heroku
```bash
# Create Procfile
echo "web: python gui/app.py --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create duckdice-bot-app
git push heroku main
heroku open
```

---

## 🧪 Testing & Validation

### 1. Run Unit Tests

```bash
# Activate venv
source venv/bin/activate

# Run all tests
cd tests/gui
python test_gui_components.py

# Expected: 7 passed, 0 failed
```

### 2. Test Web Interface

```bash
# Start server
python gui/app.py

# Open browser: http://localhost:8080
# Check all tabs load: Dashboard, Strategies, Simulator, History, Analytics, Settings
```

### 3. Test API Connection

1. Go to **Settings** tab
2. Enter valid API key
3. Click **Test Connection**
4. Verify green success notification

### 4. Test Simulation Mode

1. Go to **Strategies** tab
2. Select "Martingale"
3. Set parameters (Base: 0.00000100, Target: 49.5)
4. Go to **Dashboard** tab
5. Click **Start Bot** (Simulation mode)
6. Observe bets in History tab
7. Click **Stop Bot**
8. Check **Analytics** tab for metrics

### 5. Test Charts

1. Run bot with 20+ bets
2. Go to **Dashboard** tab
3. Scroll to Charts section
4. Expand all 4 charts (Balance, P/L, Distribution, Streaks)
5. Click **Export All Charts** → verify PNG files saved

### 6. Test Database

```bash
# Check database exists
ls -lh data/duckdice_bot.db

# Query database
sqlite3 data/duckdice_bot.db "SELECT COUNT(*) FROM bet_history;"
sqlite3 data/duckdice_bot.db "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 5;"
```

### 7. Test Profile Management

1. Configure a strategy
2. Click **Save Profile**
3. Enter name "TestProfile1"
4. Verify success notification
5. Change parameters
6. Click **Load Profile** → select "TestProfile1"
7. Verify parameters restored
8. Click **Delete Profile**

---

## 📊 Monitoring

### Application Logs

```bash
# View real-time logs
tail -f logs/app.log

# Search for errors
grep ERROR logs/app.log

# Check warnings
grep WARN logs/app.log
```

### Database Monitoring

```bash
# Database size
ls -lh data/duckdice_bot.db

# Record counts
sqlite3 data/duckdice_bot.db <<EOF
SELECT 'Bets:', COUNT(*) FROM bet_history;
SELECT 'Profiles:', COUNT(*) FROM strategy_profiles;
SELECT 'Sessions:', COUNT(*) FROM sessions;
EOF
```

### Performance Metrics

Monitor in **Analytics** tab:
- Win Rate (target: >49%)
- ROI (target: positive)
- Max Drawdown (acceptable: <20%)
- Profit Factor (target: >1.0)
- Sharpe Ratio (good: >0.5)

### System Resources

```bash
# CPU and memory usage
top -p $(pgrep -f "gui/app.py")

# Network connections
netstat -an | grep 8080

# Disk usage
du -sh data/
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Error: Address already in use: 8080
# Solution: Kill existing process
lsof -ti:8080 | xargs kill -9
# Or use different port
python gui/app.py --port 8081
```

#### 2. Module Import Errors
```bash
# Error: No module named 'nicegui'
# Solution: Install dependencies
pip install -r requirements.txt

# Or reinstall
pip install --upgrade -r requirements.txt
```

#### 3. Database Locked
```bash
# Error: database is locked
# Solution: Close other connections
sqlite3 data/duckdice_bot.db ".quit"
# Or backup and recreate
cp data/duckdice_bot.db data/backup.db
rm data/duckdice_bot.db  # Auto-recreates on restart
```

#### 4. API Connection Failed
```bash
# Error: Connection timeout
# Check: Internet connectivity
ping duckdice.io

# Check: API key validity
# Go to Settings → Test Connection

# Check: Firewall rules
sudo ufw allow 443/tcp
```

#### 5. Charts Not Loading
```bash
# Error: No charts displayed
# Solution: Check matplotlib installation
pip install --upgrade matplotlib

# Verify Agg backend
python -c "import matplotlib; print(matplotlib.get_backend())"
# Should output: agg
```

#### 6. Permission Denied (macOS/Linux)
```bash
# Error: Permission denied: './run_nicegui.sh'
# Solution: Make executable
chmod +x run_nicegui.sh run_gui_web.sh run_gui.sh
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python gui/app.py

# Check all module imports
python -c "
import gui.app
import gui.charts
import gui.database
import gui.analytics
import gui.bot_controller
print('✓ All imports successful')
"
```

### Reset to Defaults

```bash
# Backup data
cp -r data/ data_backup/

# Clear database (keeps file)
sqlite3 data/duckdice_bot.db <<EOF
DELETE FROM bet_history;
DELETE FROM strategy_profiles;
DELETE FROM sessions;
VACUUM;
EOF

# Full reset (delete database)
rm data/duckdice_bot.db
# Auto-recreates on next run
```

---

## 🔒 Security Best Practices

### 1. API Key Security

```bash
# Never commit API keys to git
echo ".env" >> .gitignore

# Use environment variables
export DUCKDICE_API_KEY="your_key"

# Rotate keys regularly (monthly)
# DuckDice → Account Settings → Regenerate API Key
```

### 2. Network Security

```bash
# Firewall (Linux)
sudo ufw enable
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw deny 8080/tcp  # Block direct access

# Use reverse proxy (nginx) instead of direct port access
```

### 3. SSL/TLS

```bash
# Always use HTTPS in production
# Let's Encrypt (free)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
0 0 1 * * certbot renew --quiet
```

### 4. Access Control

```bash
# Run as non-root user
sudo useradd -m -s /bin/bash duckdice
sudo chown -R duckdice:duckdice /path/to/duckdice-bot

# Limit file permissions
chmod 600 .env
chmod 600 data/duckdice_bot.db
```

### 5. Rate Limiting

Configure in **Settings** tab:
- Bet delay: ≥1 second (default)
- Avoid aggressive betting patterns
- Monitor for API rate limits

### 6. Backup Strategy

```bash
# Daily database backups
crontab -e
0 2 * * * cp ~/duckdice-bot/data/duckdice_bot.db ~/backups/db_$(date +\%Y\%m\%d).db

# Keep last 30 days
find ~/backups/ -name "db_*.db" -mtime +30 -delete
```

---

## 📈 Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes (already included)
CREATE INDEX idx_bet_session ON bet_history(session_id);
CREATE INDEX idx_bet_timestamp ON bet_history(timestamp DESC);

-- Regular vacuum (weekly)
VACUUM;
ANALYZE;
```

### 2. Chart Performance

```python
# Charts auto-throttle to every 10 bets
# Adjust in gui/dashboard.py if needed
if len(app_state.bet_history) % 10 == 0:
    self._update_charts()
```

### 3. Memory Management

```bash
# Monitor memory usage
watch -n 5 'ps aux | grep python'

# Restart if memory grows
# systemd handles this automatically with Restart=always
```

---

## 📞 Support

### Documentation
- [README.md](README.md) - Main documentation
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Technical details
- [TODO_FEATURES.md](TODO_FEATURES.md) - Feature status

### Community
- GitHub Issues: https://github.com/sushiomsky/duckdice-bot/issues
- DuckDice Support: support@duckdice.io

### Reporting Bugs
```bash
# Include in bug reports:
- Python version: python3 --version
- OS version: uname -a
- Error logs: logs/app.log
- Steps to reproduce
```

---

## ✅ Deployment Checklist

Final verification before production:

- [ ] All tests passing (7/7)
- [ ] API connection successful
- [ ] Database created and accessible
- [ ] All 17 strategies load correctly
- [ ] Charts generate without errors
- [ ] Profile save/load/delete works
- [ ] Analytics calculations accurate
- [ ] SSL certificate installed (production)
- [ ] Firewall rules configured
- [ ] Systemd service enabled
- [ ] Nginx reverse proxy configured
- [ ] Backup system in place
- [ ] Monitoring setup complete
- [ ] API key secured
- [ ] Log rotation configured

---

## 🎉 Success!

Your DuckDice Bot is now deployed and ready for use!

**Next Steps**:
1. Start in **Simulation Mode**
2. Test strategies with virtual balance
3. Monitor **Analytics Dashboard**
4. Optimize based on performance data
5. Transition to **Live Mode** when confident

**Remember**: 
- Always use stop conditions
- Never bet more than you can afford
- Monitor analytics regularly
- Keep API keys secure
- Backup your database

---

**Status**: ✅ PRODUCTION READY  
**Version**: 4.0.0  
**Last Updated**: January 11, 2026

Happy betting! 🎲
