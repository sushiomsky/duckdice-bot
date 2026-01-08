"""
Lightweight logging utility for NiceGUI app
Provides structured logging with timestamp and level
"""

import logging
from datetime import datetime
from pathlib import Path

# Create logs directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logger
logger = logging.getLogger("duckdice_nicegui")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)

# File handler
log_file = LOG_DIR / f"nicegui_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(console_formatter)

# Add handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def log_info(message: str, **kwargs):
    """Log info message with optional context"""
    extra = f" - {kwargs}" if kwargs else ""
    logger.info(f"{message}{extra}")


def log_error(message: str, error: Exception = None, **kwargs):
    """Log error message with exception details"""
    extra = f" - {kwargs}" if kwargs else ""
    if error:
        logger.error(f"{message}: {str(error)}{extra}", exc_info=True)
    else:
        logger.error(f"{message}{extra}")


def log_warning(message: str, **kwargs):
    """Log warning message"""
    extra = f" - {kwargs}" if kwargs else ""
    logger.warning(f"{message}{extra}")


def log_debug(message: str, **kwargs):
    """Log debug message"""
    extra = f" - {kwargs}" if kwargs else ""
    logger.debug(f"{message}{extra}")
