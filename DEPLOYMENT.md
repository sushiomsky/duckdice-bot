# 🚀 Deployment Guide - DuckDice Bot NiceGUI

Complete guide for deploying the NiceGUI web interface in various environments.

## 📋 Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- 2GB RAM minimum
- Network access for remote clients

## 🏠 Local Deployment (Development)

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run server
./run_nicegui.sh
```

Server starts at: `http://localhost:8080`

### Manual Start

```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Run directly
python3 app/main.py
```

## 🌐 Network Deployment (LAN Access)

To allow access from other devices on your network:

### Option 1: Edit run_nicegui.sh

```bash
# Modify app/main.py line ~180
ui.run(
    title='DuckDice Bot',
    host='0.0.0.0',  # Listen on all interfaces
    port=8080,
    reload=False,
    show=False,  # Don't auto-open browser
    dark=True,
    favicon='🎲'
)
```

### Option 2: Use Environment Variable

```bash
export NICEGUI_HOST=0.0.0.0
./run_nicegui.sh
```

Access from other devices: `http://YOUR_IP:8080`

Find your IP:
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

## 🐳 Docker Deployment (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "app/main.py"]
```

Build and run:

```bash
# Build image
docker build -t duckdice-bot .

# Run container
docker run -d -p 8080:8080 --name duckdice-bot duckdice-bot

# View logs
docker logs -f duckdice-bot
```

## ☁️ Cloud Deployment

### Heroku

1. Create `Procfile`:
```
web: python app/main.py
```

2. Deploy:
```bash
heroku create duckdice-bot
git push heroku main
```

### Railway.app

1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app/main.py`
4. Deploy automatically on push

### DigitalOcean / AWS / GCP

1. Create VM instance
2. SSH into instance
3. Follow "Network Deployment" steps above
4. Configure firewall to allow port 8080
5. (Optional) Set up reverse proxy with nginx

## 🔒 Security Considerations

### Production Deployment

1. **Use HTTPS**: Set up reverse proxy (nginx/caddy) with SSL
2. **Authentication**: Add login system (not included)
3. **Firewall**: Restrict access to known IPs
4. **Environment Variables**: Store API keys securely

Example nginx config:

```nginx
server {
    listen 443 ssl;
    server_name duckdice.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### API Key Protection

Never commit API keys! Use environment variables:

```bash
# .env file (add to .gitignore)
DUCKDICE_API_KEY=your_key_here
```

Load in app:
```python
import os
api_key = os.getenv('DUCKDICE_API_KEY')
```

## 📊 Monitoring

### Application Logs

Logs are written to: `logs/nicegui_YYYYMMDD.log`

Monitor in real-time:
```bash
tail -f logs/nicegui_*.log
```

### System Monitoring

```bash
# Check if server is running
ps aux | grep "python app/main.py"

# Monitor resource usage
top -p $(pgrep -f "python app/main.py")

# Check port 8080
netstat -tulpn | grep 8080
```

## 🔄 Auto-Restart on Crash

### Using systemd (Linux)

Create `/etc/systemd/system/duckdice-bot.service`:

```ini
[Unit]
Description=DuckDice Bot NiceGUI
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/duckdice-bot
ExecStart=/usr/bin/python3 app/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable duckdice-bot
sudo systemctl start duckdice-bot
sudo systemctl status duckdice-bot
```

### Using PM2 (All Platforms)

```bash
# Install PM2
npm install -g pm2

# Start application
pm2 start app/main.py --name duckdice-bot --interpreter python3

# Auto-restart on system reboot
pm2 startup
pm2 save

# Monitor
pm2 status
pm2 logs duckdice-bot
```

## 🧪 Testing Deployment

### Health Check

```bash
# Test server is responding
curl http://localhost:8080

# Test from another machine
curl http://YOUR_IP:8080
```

### Load Testing (Optional)

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Run load test (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8080/
```

## 📱 Mobile Access

### Local Network

1. Ensure firewall allows port 8080
2. Find server IP address
3. Open `http://SERVER_IP:8080` on mobile browser
4. Add to home screen for app-like experience

### QR Code for Easy Access

```bash
# Install qrencode
sudo apt install qrencode

# Generate QR code for URL
qrencode -t ANSIUTF8 "http://YOUR_IP:8080"
```

Scan with mobile device to access instantly!

## 🛠️ Troubleshooting

### Port Already in Use

```bash
# Find process using port 8080
lsof -i :8080

# Kill process (replace PID)
kill -9 PID
```

### Permission Denied

```bash
# Run on unprivileged port (>1024)
# Edit DEFAULT_PORT in app/config.py
DEFAULT_PORT = 8888
```

### Can't Access from Network

1. Check firewall:
```bash
# Linux
sudo ufw allow 8080

# macOS
# System Preferences → Security → Firewall → Options
```

2. Verify server is listening on all interfaces:
```bash
netstat -an | grep 8080
# Should show 0.0.0.0:8080, not 127.0.0.1:8080
```

## 📚 Additional Resources

- [NiceGUI Documentation](https://nicegui.io)
- [DuckDice API Docs](https://duckdice.io/bot-api)
- [Project README](README.md)
- [NICEGUI_README](NICEGUI_README.md)

## 🆘 Support

- **Issues**: https://github.com/sushiomsky/duckdice-bot/issues
- **Discussions**: https://github.com/sushiomsky/duckdice-bot/discussions
- **Email**: Open an issue for support

---

**Note**: This application manages real cryptocurrency bets. Deploy securely and use responsibly!
