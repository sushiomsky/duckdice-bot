"""
GUI Enhancement Modules
Modular enhancements for DuckDice Modern GUI
"""

from .emergency_stop import EmergencyStopManager
from .sound_manager import SoundManager
from .chart_panel import LiveChartPanel
from .bet_history import BetHistoryViewer
from .bet_logger import BetLogger
from .enhanced_bet_history import EnhancedBetHistoryViewer
from .statistics_dashboard import StatisticsDashboard
from .strategy_config_panel import StrategyConfigPanel
from .ux_improvements import (
    AnimatedProgressBar,
    Toast,
    OnboardingWizard,
    LoadingOverlay,
    ConfirmDialog
)
from .session_recovery_dialog import (
    SessionRecoveryDialog,
    ConfirmationDialog,
    TooltipManager
)
from .settings_panel import SettingsPanel
from .export_dialog import ExportDialog, QuickExportMenu

__all__ = [
    'EmergencyStopManager',
    'SoundManager',
    'LiveChartPanel',
    'BetHistoryViewer',
    'BetLogger',
    'EnhancedBetHistoryViewer',
    'StatisticsDashboard',
    'StrategyConfigPanel',
    'AnimatedProgressBar',
    'Toast',
    'OnboardingWizard',
    'LoadingOverlay',
    'ConfirmDialog',
    'SessionRecoveryDialog',
    'ConfirmationDialog',
    'TooltipManager',
    'SettingsPanel',
    'ExportDialog',
    'QuickExportMenu'
]
