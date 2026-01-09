# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for DuckDice Bot Ultimate GUI
Builds standalone executable with all dependencies
"""

import sys
from pathlib import Path

block_cipher = None

# Detect platform
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'
is_linux = sys.platform.startswith('linux')

# All hidden imports for strategies
hidden_imports = [
    'betbot_strategies.target_aware',
    'betbot_strategies.classic_martingale',
    'betbot_strategies.fibonacci',
    'betbot_strategies.dalembert',
    'betbot_strategies.labouchere',
    'betbot_strategies.paroli',
    'betbot_strategies.oscars_grind',
    'betbot_strategies.one_three_two_six',
    'betbot_strategies.kelly_capped',
    'betbot_strategies.anti_martingale_streak',
    'betbot_strategies.fib_loss_cluster',
    'betbot_strategies.max_wager_flow',
    'betbot_strategies.faucet_cashout',
    'betbot_strategies.rng_analysis_strategy',
    'betbot_strategies.range50_random',
    'betbot_strategies.custom_script',
    'simulation_engine',
    'gui_enhancements.ux_improvements',
    'gui_enhancements.keyboard_shortcuts',
    'gui_enhancements.tkinter_chart',
]

# Data files to include
datas = [
    ('src', 'src'),
    ('COMPLETE_FEATURES.md', '.'),
    ('DATABASE_AND_CHARTS.md', '.'),
    ('UX_ENHANCEMENTS.md', '.'),
    ('QUICK_START_GUIDE.md', '.'),
    ('LICENSE', '.'),
]

# Analysis
a = Analysis(
    ['duckdice_gui_ultimate.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Optional - we have Tkinter fallback
        'numpy',       # Not needed
        'pandas',      # Not needed
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific options
exe_name = 'DuckDiceBot'
if is_windows:
    exe_name += '.exe'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if is_windows and Path('assets/icon.ico').exists() else None,
)

# macOS specific - create .app bundle
if is_macos:
    app = BUNDLE(
        exe,
        name='DuckDiceBot.app',
        icon='assets/icon.icns' if Path('assets/icon.icns').exists() else None,
        bundle_identifier='io.duckdice.bot',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleName': 'DuckDice Bot',
            'CFBundleDisplayName': 'DuckDice Bot',
            'CFBundleShortVersionString': '3.1.0',
            'CFBundleVersion': '3.1.0',
        },
    )
