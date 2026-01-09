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

# Keyboard shortcuts (Ctrl/Cmd + key)
KEYBOARD_SHORTCUTS = {
    # Navigation shortcuts (Ctrl+1 through Ctrl+8)
    '1': '/',  # Dashboard
    '2': '/betting',  # Betting
    '3': '/faucet',  # Faucet
    '4': '/library',  # Library
    '5': '/tools',  # Tools
    '6': '/history',  # History
    '7': '/statistics',  # Statistics
    '8': '/settings',  # Settings
    
    # Legacy letter shortcuts (for backwards compatibility)
    'b': '/betting',  # Betting (was Quick Bet)
    'f': '/faucet',  # Faucet
    'h': '/history',  # History
    's': '/settings',  # Settings
    'd': '/',  # Dashboard
    'l': '/library',  # Library
    't': '/tools',  # Tools
}

# House edges
HOUSE_EDGE_MAIN = 0.01  # 1%
HOUSE_EDGE_FAUCET = 0.03  # 3%

# UI settings
TOAST_DURATION = 3  # seconds
ANIMATION_DURATION = 300  # milliseconds

# Responsive breakpoints (Tailwind CSS standard)
MOBILE_BREAKPOINT = 640  # pixels (sm)
TABLET_BREAKPOINT = 768  # pixels (md)
DESKTOP_BREAKPOINT = 1024  # pixels (lg)
WIDE_BREAKPOINT = 1280  # pixels (xl)

# Touch-friendly sizes (WCAG AAA guidelines)
MIN_TOUCH_TARGET = 44  # pixels (minimum for touch)
RECOMMENDED_TOUCH_TARGET = 48  # pixels (recommended)

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
