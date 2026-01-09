"""
Utility functions for the GUI.
Validation, formatting, and helper functions.
"""

from typing import Any, Optional, Tuple
from decimal import Decimal, InvalidOperation


def format_balance(balance: float, currency: str = "BTC") -> str:
    """Format balance with appropriate precision"""
    if balance >= 1:
        return f"{balance:.4f} {currency.upper()}"
    else:
        return f"{balance:.8f} {currency.upper()}"


def format_profit(profit: float, percent: float = None) -> str:
    """Format profit with sign and optional percentage"""
    sign = "+" if profit >= 0 else ""
    if percent is not None:
        return f"{sign}{profit:.8f} ({sign}{percent:.2f}%)"
    else:
        return f"{sign}{profit:.8f} BTC"


def format_number(value: float, decimals: int = 2) -> str:
    """Format number with specified decimals"""
    return f"{value:.{decimals}f}"


def validate_bet_amount(amount_str: str, min_bet: float = 0.00000001, max_bet: float = 1000.0) -> Tuple[bool, str]:
    """
    Validate bet amount input.
    Returns: (is_valid, error_message)
    """
    if not amount_str:
        return False, "Amount is required"
    
    try:
        amount = float(amount_str)
    except ValueError:
        return False, "Invalid number format"
    
    if amount < min_bet:
        return False, f"Amount must be at least {min_bet}"
    
    if amount > max_bet:
        return False, f"Amount must not exceed {max_bet}"
    
    return True, ""


def validate_target_chance(chance_str: str) -> Tuple[bool, str]:
    """
    Validate target chance (0.01 - 98.99).
    Returns: (is_valid, error_message)
    """
    if not chance_str:
        return False, "Target chance is required"
    
    try:
        chance = float(chance_str)
    except ValueError:
        return False, "Invalid number format"
    
    if chance < 0.01 or chance > 98.99:
        return False, "Target chance must be between 0.01 and 98.99"
    
    return True, ""


def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate API key format.
    Returns: (is_valid, error_message)
    """
    if not api_key:
        return False, "API key is required"
    
    if len(api_key) < 10:
        return False, "API key too short"
    
    # Basic format check (alphanumeric and dashes)
    if not all(c.isalnum() or c in '-_' for c in api_key):
        return False, "API key contains invalid characters"
    
    return True, ""


def validate_percentage(value_str: str, min_val: float = -100, max_val: float = 100) -> Tuple[bool, str]:
    """
    Validate percentage input.
    Returns: (is_valid, error_message)
    """
    if not value_str:
        return False, "Value is required"
    
    try:
        value = float(value_str)
    except ValueError:
        return False, "Invalid number format"
    
    if value < min_val or value > max_val:
        return False, f"Value must be between {min_val}% and {max_val}%"
    
    return True, ""


def calculate_multiplier(target_chance: float) -> float:
    """Calculate payout multiplier from target chance"""
    if target_chance <= 0 or target_chance >= 100:
        return 0.0
    return 99.0 / target_chance


def calculate_profit(amount: float, multiplier: float, won: bool) -> float:
    """Calculate profit from bet result"""
    if won:
        return amount * (multiplier - 1)
    else:
        return -amount


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_risk_color(risk_level: str) -> str:
    """Get color for risk level"""
    risk_colors = {
        "Low": "green",
        "Medium": "yellow",
        "High": "orange",
        "Very High": "red",
        "Extreme": "red"
    }
    return risk_colors.get(risk_level, "gray")


def get_status_color(running: bool, paused: bool, error: bool = False) -> str:
    """Get status indicator color"""
    if error:
        return "red"
    if running and not paused:
        return "green"
    if paused:
        return "yellow"
    return "gray"


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def export_to_csv(data: list, filename: str) -> bool:
    """Export data to CSV file"""
    try:
        import csv
        with open(filename, 'w', newline='') as f:
            if not data:
                return True
            
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return True
    except Exception as e:
        print(f"Export failed: {e}")
        return False
