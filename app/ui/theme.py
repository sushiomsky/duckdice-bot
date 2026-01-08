"""
DuckDice Bot - NiceGUI Edition
Premium web interface for automated dice betting
"""

# Design system: colors, spacing, typography
# Dark mode first, minimal and clean

class Theme:
    """Central design system - all visual constants in one place"""
    
    # Color palette - muted and professional
    PRIMARY = "#3b82f6"      # Blue - for CTAs and active states
    PRIMARY_HOVER = "#2563eb"
    PRIMARY_LIGHT = "#93c5fd"
    
    ACCENT = "#10b981"       # Green - for success and wins
    ACCENT_HOVER = "#059669"
    
    ERROR = "#ef4444"        # Red - for losses and errors
    ERROR_HOVER = "#dc2626"
    
    WARNING = "#f59e0b"      # Amber - for warnings
    
    # Neutrals - dark mode first
    BG_PRIMARY = "#0f172a"    # Main background (slate-900)
    BG_SECONDARY = "#1e293b"  # Card backgrounds (slate-800)
    BG_TERTIARY = "#334155"   # Hover states (slate-700)
    
    TEXT_PRIMARY = "#f1f5f9"   # Main text (slate-100)
    TEXT_SECONDARY = "#cbd5e1" # Secondary text (slate-300)
    TEXT_MUTED = "#94a3b8"     # Muted text (slate-400)
    
    BORDER = "#475569"         # Borders (slate-600)
    
    # Spacing system - consistent gaps
    SPACE_XS = "0.5rem"   # 8px
    SPACE_SM = "0.75rem"  # 12px
    SPACE_MD = "1rem"     # 16px
    SPACE_LG = "1.5rem"   # 24px
    SPACE_XL = "2rem"     # 32px
    SPACE_2XL = "3rem"    # 48px
    
    # Border radius
    RADIUS_SM = "0.375rem"  # 6px
    RADIUS_MD = "0.5rem"    # 8px
    RADIUS_LG = "0.75rem"   # 12px
    RADIUS_XL = "1rem"      # 16px
    
    # Typography
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    FONT_SIZE_SM = "0.875rem"  # 14px
    FONT_SIZE_BASE = "1rem"    # 16px
    FONT_SIZE_LG = "1.125rem"  # 18px
    FONT_SIZE_XL = "1.25rem"   # 20px
    FONT_SIZE_2XL = "1.5rem"   # 24px
    
    # Shadows - subtle depth
    SHADOW_SM = "0 1px 2px 0 rgba(0, 0, 0, 0.3)"
    SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.4)"
    SHADOW_LG = "0 10px 15px -3px rgba(0, 0, 0, 0.5)"
    
    # Transitions
    TRANSITION_FAST = "150ms"
    TRANSITION_BASE = "250ms"
    TRANSITION_SLOW = "350ms"
    
    @staticmethod
    def get_mode_color(mode: str) -> str:
        """Get color for betting mode"""
        return {
            'simulation': Theme.WARNING,
            'live': Theme.ACCENT,
            'main': Theme.PRIMARY,
            'faucet': Theme.PRIMARY_LIGHT
        }.get(mode, Theme.TEXT_MUTED)
