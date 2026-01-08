"""
Application configuration constants
Centralized configuration for maintainability
"""

# Server configuration
DEFAULT_PORT = 8080
DEFAULT_HOST = "0.0.0.0"

# Auto-refresh settings
BALANCE_REFRESH_INTERVAL = 30  # seconds
FAUCET_COOLDOWN = 60  # seconds

# Limits
MAX_BET_HISTORY = 1000
MAX_CONCURRENT_BETS = 1

# Keyboard shortcuts
KEYBOARD_SHORTCUTS = {
    'b': '/quick-bet',
    'a': '/auto-bet',
    'f': '/faucet',
    'h': '/history',
    's': '/settings',
    'd': '/',
}

# House edges
HOUSE_EDGE_MAIN = 0.01  # 1%
HOUSE_EDGE_FAUCET = 0.03  # 3%

# UI settings
TOAST_DURATION = 3  # seconds
ANIMATION_DURATION = 300  # milliseconds
MOBILE_BREAKPOINT = 1024  # pixels

# Version
APP_VERSION = "3.2.0"
APP_NAME = "DuckDice Bot"
NICEGUI_VERSION = "1.0.0"

# URLs
GITHUB_REPO = "https://github.com/sushiomsky/duckdice-bot"
DUCKDICE_URL = "https://duckdice.io"

# API settings
API_TIMEOUT = 30  # seconds
API_RETRY_COUNT = 3
