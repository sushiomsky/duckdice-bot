"""
Strategy selection and configuration screen.
Load strategies dynamically, display parameters, validate inputs.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from nicegui import ui
from gui.state import app_state
from gui.utils import validate_bet_amount, validate_target_chance


class StrategiesUI:
    """Strategy selection and configuration interface"""
    
    def __init__(self):
        self.strategy_dropdown = None
        self.params_container = None
        self.save_button = None
        self.load_button = None
        self.param_inputs: Dict[str, Any] = {}
        
        # Available strategies (hardcoded for now - could be dynamic)
        self.strategies = {
            'martingale': {
                'name': 'Martingale',
                'description': 'Double bet after loss, reset on win',
                'params': {
                    'base_bet': {'type': 'float', 'label': 'Base Bet', 'default': 0.00000001, 'min': 0.00000001},
                    'target_chance': {'type': 'float', 'label': 'Win Chance %', 'default': 49.5, 'min': 0.01, 'max': 98.0},
                    'multiplier': {'type': 'float', 'label': 'Loss Multiplier', 'default': 2.0, 'min': 1.1, 'max': 10.0},
                    'max_bet': {'type': 'float', 'label': 'Max Bet', 'default': 0.001, 'min': 0.00000001},
                }
            },
            'reverse_martingale': {
                'name': 'Reverse Martingale',
                'description': 'Double bet after win, reset on loss',
                'params': {
                    'base_bet': {'type': 'float', 'label': 'Base Bet', 'default': 0.00000001, 'min': 0.00000001},
                    'target_chance': {'type': 'float', 'label': 'Win Chance %', 'default': 49.5, 'min': 0.01, 'max': 98.0},
                    'multiplier': {'type': 'float', 'label': 'Win Multiplier', 'default': 2.0, 'min': 1.1, 'max': 10.0},
                    'max_bet': {'type': 'float', 'label': 'Max Bet', 'default': 0.001, 'min': 0.00000001},
                }
            },
            'dalembert': {
                'name': "D'Alembert",
                'description': 'Increase bet by fixed amount on loss, decrease on win',
                'params': {
                    'base_bet': {'type': 'float', 'label': 'Base Bet', 'default': 0.00000001, 'min': 0.00000001},
                    'target_chance': {'type': 'float', 'label': 'Win Chance %', 'default': 49.5, 'min': 0.01, 'max': 98.0},
                    'step': {'type': 'float', 'label': 'Step Amount', 'default': 0.00000001, 'min': 0.00000001},
                    'max_bet': {'type': 'float', 'label': 'Max Bet', 'default': 0.001, 'min': 0.00000001},
                }
            },
            'fibonacci': {
                'name': 'Fibonacci',
                'description': 'Follow Fibonacci sequence on losses',
                'params': {
                    'base_bet': {'type': 'float', 'label': 'Base Bet', 'default': 0.00000001, 'min': 0.00000001},
                    'target_chance': {'type': 'float', 'label': 'Win Chance %', 'default': 49.5, 'min': 0.01, 'max': 98.0},
                    'max_bet': {'type': 'float', 'label': 'Max Bet', 'default': 0.001, 'min': 0.00000001},
                }
            },
            'fixed': {
                'name': 'Fixed Bet',
                'description': 'Constant bet amount every roll',
                'params': {
                    'bet_amount': {'type': 'float', 'label': 'Bet Amount', 'default': 0.00000001, 'min': 0.00000001},
                    'target_chance': {'type': 'float', 'label': 'Win Chance %', 'default': 49.5, 'min': 0.01, 'max': 98.0},
                }
            },
        }
    
    def render(self):
        """Render strategy selection UI"""
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.card().classes('w-full'):
                ui.label('Strategy Configuration').classes('text-2xl font-bold')
                ui.label('Select and configure your betting strategy').classes('text-gray-500')
            
            # Strategy selector
            self._render_strategy_selector()
            
            # Parameters form
            self._render_parameters()
            
            # Save/Load profiles
            self._render_profiles()
    
    def _render_strategy_selector(self):
        """Render strategy dropdown"""
        with ui.card().classes('w-full'):
            ui.label('Select Strategy').classes('text-lg font-semibold mb-2')
            
            strategy_options = {k: v['name'] for k, v in self.strategies.items()}
            
            self.strategy_dropdown = ui.select(
                options=strategy_options,
                value=app_state.strategy_name or 'martingale',
                label='Strategy',
                on_change=self._on_strategy_change
            ).classes('w-full')
            
            # Description
            current_strategy = app_state.strategy_name or 'martingale'
            ui.label(self.strategies[current_strategy]['description']).classes('text-sm text-gray-600 mt-2')
    
    def _render_parameters(self):
        """Render parameter input form"""
        with ui.card().classes('w-full'):
            ui.label('Parameters').classes('text-lg font-semibold mb-2')
            
            self.params_container = ui.column().classes('w-full gap-2')
            
            with self.params_container:
                self._render_param_inputs()
    
    def _render_param_inputs(self):
        """Render input fields for current strategy parameters"""
        self.param_inputs.clear()
        
        current_strategy = app_state.strategy_name or 'martingale'
        params = self.strategies[current_strategy]['params']
        
        for param_name, param_config in params.items():
            with ui.row().classes('w-full items-center gap-4'):
                label = param_config['label']
                default = param_config['default']
                param_type = param_config['type']
                
                if param_type == 'float':
                    input_field = ui.number(
                        label=label,
                        value=app_state.strategy_params.get(param_name, default),
                        min=param_config.get('min'),
                        max=param_config.get('max'),
                        step=0.00000001 if 'bet' in param_name.lower() else 0.1,
                        format='%.8f' if 'bet' in param_name.lower() else '%.2f',
                        on_change=lambda e, p=param_name: self._on_param_change(p, e.value)
                    ).classes('flex-grow')
                    
                    self.param_inputs[param_name] = input_field
                
                # Help text
                if param_name == 'target_chance':
                    ui.label('0.01-98.0%').classes('text-xs text-gray-500')
                elif 'bet' in param_name.lower():
                    ui.label('BTC').classes('text-xs text-gray-500')
    
    def _render_profiles(self):
        """Render save/load profile buttons"""
        with ui.card().classes('w-full'):
            ui.label('Strategy Profiles').classes('text-lg font-semibold mb-2')
            
            with ui.row().classes('w-full gap-2'):
                ui.button('Save Profile', on_click=self._save_profile, icon='save').props('outline')
                ui.button('Load Profile', on_click=self._load_profile, icon='folder_open').props('outline')
                ui.button('Apply to Bot', on_click=self._apply_to_bot, icon='check').props('color=primary')
    
    def _on_strategy_change(self, e):
        """Handle strategy selection change"""
        strategy_name = e.value
        app_state.update(strategy_name=strategy_name, strategy_params={})
        
        # Re-render parameters
        self.params_container.clear()
        with self.params_container:
            self._render_param_inputs()
    
    def _on_param_change(self, param_name: str, value: Any):
        """Handle parameter value change"""
        params = app_state.strategy_params.copy()
        params[param_name] = value
        app_state.update(strategy_params=params)
    
    def _save_profile(self):
        """Save current configuration to JSON file"""
        profile_dir = Path('gui/profiles')
        profile_dir.mkdir(exist_ok=True)
        
        profile_data = {
            'strategy_name': app_state.strategy_name,
            'strategy_params': app_state.strategy_params,
        }
        
        profile_path = profile_dir / f'{app_state.strategy_name}_profile.json'
        
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        ui.notify(f'Profile saved: {profile_path.name}', type='positive')
    
    def _load_profile(self):
        """Load configuration from JSON file"""
        profile_dir = Path('gui/profiles')
        if not profile_dir.exists():
            ui.notify('No profiles found', type='warning')
            return
        
        profiles = list(profile_dir.glob('*.json'))
        if not profiles:
            ui.notify('No profiles found', type='warning')
            return
        
        # For simplicity, load the first matching profile
        profile_path = profile_dir / f'{app_state.strategy_name}_profile.json'
        
        if not profile_path.exists():
            ui.notify(f'No profile found for {app_state.strategy_name}', type='warning')
            return
        
        with open(profile_path, 'r') as f:
            profile_data = json.load(f)
        
        app_state.update(
            strategy_name=profile_data['strategy_name'],
            strategy_params=profile_data['strategy_params']
        )
        
        # Re-render UI
        self.strategy_dropdown.set_value(profile_data['strategy_name'])
        self.params_container.clear()
        with self.params_container:
            self._render_param_inputs()
        
        ui.notify(f'Profile loaded: {profile_path.name}', type='positive')
    
    def _apply_to_bot(self):
        """Apply current configuration to bot state"""
        # Validation
        current_strategy = app_state.strategy_name or 'martingale'
        params = self.strategies[current_strategy]['params']
        
        for param_name, param_config in params.items():
            value = app_state.strategy_params.get(param_name, param_config['default'])
            
            # Validate based on parameter type
            if 'bet' in param_name.lower():
                if not validate_bet_amount(value):
                    ui.notify(f'Invalid {param_config["label"]}: must be >= 0.00000001 BTC', type='negative')
                    return
            
            if param_name == 'target_chance':
                if not validate_target_chance(value):
                    ui.notify('Invalid Win Chance: must be 0.01-98.0%', type='negative')
                    return
        
        ui.notify('Strategy applied successfully', type='positive')
