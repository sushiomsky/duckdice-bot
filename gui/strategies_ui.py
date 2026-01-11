"""
Strategy selection and configuration screen.
Load strategies dynamically, display parameters, validate inputs.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from nicegui import ui
from gui.state import app_state
from gui.utils import validate_bet_amount, validate_target_chance
from gui.strategy_loader import get_strategy_loader, StrategyInfo
from gui.database import get_db_manager


class StrategiesUI:
    """Strategy selection and configuration interface"""
    
    def __init__(self):
        self.strategy_dropdown = None
        self.params_container = None
        self.save_button = None
        self.load_button = None
        self.param_inputs: Dict[str, Any] = {}
        self.description_label = None
        self.metadata_card = None
        
        # Load strategies dynamically
        self.loader = get_strategy_loader()
        self.current_strategy_info: Optional[StrategyInfo] = None
        
        # Database for profiles
        self.db = get_db_manager()
        
        # Profile management UI elements
        self.profile_name_input = None
        self.profile_desc_input = None
        self.profile_list_select = None
    
    def render(self):
        """Render strategy selection UI"""
        with ui.column().classes('w-full gap-4'):
            # Header
            with ui.card().classes('w-full'):
                ui.label('Strategy Configuration').classes('text-2xl font-bold')
                ui.label(f'Select from {len(self.loader.strategies)} available strategies').classes('text-gray-500')
            
            # Strategy selector
            self._render_strategy_selector()
            
            # Strategy metadata (risk, description, tips)
            self._render_metadata()
            
            # Parameters form
            self._render_parameters()
            
            # Save/Load profiles
            self._render_profiles()
    
    def _render_strategy_selector(self):
        """Render strategy dropdown with all available strategies"""
        with ui.card().classes('w-full'):
            ui.label('Select Strategy').classes('text-lg font-semibold mb-2')
            
            # Build options dictionary
            strategy_options = {}
            for info in self.loader.get_all_strategies():
                strategy_options[info.name] = info.get_display_label()
            
            # Get current or default strategy
            current = app_state.strategy_name or 'classic-martingale'
            
            self.strategy_dropdown = ui.select(
                options=strategy_options,
                value=current if current in strategy_options else list(strategy_options.keys())[0],
                label='Strategy',
                on_change=self._on_strategy_change
            ).classes('w-full')
            
            # Description
            self.description_label = ui.label().classes('text-sm text-gray-600 mt-2')
            self._update_description()
    
    def _render_metadata(self):
        """Render strategy metadata (risk, tips, etc.)"""
        self.metadata_card = ui.card().classes('w-full')
        self._update_metadata()
    
    def _update_metadata(self):
        """Update metadata display for current strategy"""
        if not self.metadata_card:
            return
        
        self.metadata_card.clear()
        
        current = app_state.strategy_name or 'classic-martingale'
        info = self.loader.get_strategy_info(current)
        
        if not info or not info.metadata:
            return
        
        with self.metadata_card:
            ui.label('Strategy Information').classes('text-lg font-semibold mb-2')
            
            meta = info.metadata
            
            # Risk and other key info
            with ui.row().classes('w-full gap-4 flex-wrap'):
                with ui.card().tight().classes('p-3'):
                    ui.label('Risk Level').classes('text-xs text-gray-500')
                    risk_color = {
                        'Low': 'text-green-600',
                        'Medium': 'text-yellow-600', 
                        'High': 'text-orange-600',
                        'Very High': 'text-red-600'
                    }.get(meta.risk_level, 'text-gray-600')
                    ui.label(meta.risk_level).classes(f'font-bold {risk_color}')
                
                with ui.card().tight().classes('p-3'):
                    ui.label('Bankroll').classes('text-xs text-gray-500')
                    ui.label(meta.bankroll_required).classes('font-bold')
                
                with ui.card().tight().classes('p-3'):
                    ui.label('Volatility').classes('text-xs text-gray-500')
                    ui.label(meta.volatility).classes('font-bold')
                
                with ui.card().tight().classes('p-3'):
                    ui.label('Recommended For').classes('text-xs text-gray-500')
                    ui.label(meta.recommended_for).classes('font-bold')
            
            # Best use case
            if meta.best_use_case:
                ui.label('Best Use Case').classes('text-sm font-semibold mt-3')
                ui.label(meta.best_use_case).classes('text-sm text-gray-700')
            
            # Pros and cons in expandable section
            with ui.expansion('Pros & Cons', icon='info').classes('w-full mt-2'):
                with ui.row().classes('w-full gap-4'):
                    with ui.column().classes('flex-1'):
                        ui.label('✓ Pros').classes('font-semibold text-green-600')
                        for pro in meta.pros[:3]:  # Limit to 3
                            ui.label(f'• {pro}').classes('text-sm')
                    
                    with ui.column().classes('flex-1'):
                        ui.label('✗ Cons').classes('font-semibold text-red-600')
                        for con in meta.cons[:3]:  # Limit to 3
                            ui.label(f'• {con}').classes('text-sm')
            
            # Tips in expandable section
            if meta.tips:
                with ui.expansion('Expert Tips', icon='lightbulb').classes('w-full'):
                    for tip in meta.tips:
                        ui.label(f'💡 {tip}').classes('text-sm text-gray-700 mb-1')
    
    def _update_description(self):
        """Update description for current strategy"""
        if not self.description_label:
            return
        
        current = app_state.strategy_name or 'classic-martingale'
        info = self.loader.get_strategy_info(current)
        
        if info:
            self.description_label.set_text(info.description)
    
    def _render_parameters(self):
        """Render parameter input form for current strategy"""
        with ui.card().classes('w-full'):
            ui.label('Parameters').classes('text-lg font-semibold mb-2')
            
            self.params_container = ui.column().classes('w-full gap-2')
            
            with self.params_container:
                self._render_param_inputs()
    
    def _render_param_inputs(self):
        """Render input fields for current strategy parameters"""
        self.param_inputs.clear()
        
        current = app_state.strategy_name or 'classic-martingale'
        info = self.loader.get_strategy_info(current)
        
        if not info:
            ui.label('Strategy not found').classes('text-red-500')
            return
        
        self.current_strategy_info = info
        params = info.get_parameters()
        
        if not params:
            ui.label('No parameters required').classes('text-gray-500')
            return
        
        for param in params:
            param_name = param['name']
            param_type = param['type']
            default = param['default']
            desc = param['desc']
            
            with ui.row().classes('w-full items-center gap-4'):
                if param_type == 'bool':
                    # Boolean checkbox
                    input_field = ui.checkbox(
                        text=desc,
                        value=app_state.strategy_params.get(param_name, default),
                        on_change=lambda e, p=param_name: self._on_param_change(p, e.value)
                    )
                    self.param_inputs[param_name] = input_field
                
                elif param_type in ['int', 'float']:
                    # Numeric input
                    current_value = app_state.strategy_params.get(param_name, default)
                    
                    # Determine format and step
                    if param_type == 'int':
                        format_str = '%.0f'
                        step = 1
                    else:
                        # For amounts use high precision
                        if 'amount' in param_name.lower() or 'bet' in param_name.lower():
                            format_str = '%.8f'
                            step = 0.00000001
                        else:
                            format_str = '%.4f'
                            step = 0.1
                    
                    input_field = ui.number(
                        label=desc,
                        value=float(current_value) if current_value else default,
                        step=step,
                        format=format_str,
                        on_change=lambda e, p=param_name: self._on_param_change(p, e.value)
                    ).classes('flex-grow')
                    
                    self.param_inputs[param_name] = input_field
                    
                    # Add unit label
                    if 'amount' in param_name.lower() or 'bet' in param_name.lower():
                        ui.label('BTC').classes('text-xs text-gray-500')
                    elif 'chance' in param_name.lower():
                        ui.label('%').classes('text-xs text-gray-500')
                
                else:
                    # String input
                    input_field = ui.input(
                        label=desc,
                        value=str(app_state.strategy_params.get(param_name, default)),
                        on_change=lambda e, p=param_name: self._on_param_change(p, e.value)
                    ).classes('flex-grow')
                    
                    self.param_inputs[param_name] = input_field
    
    def _render_profiles(self):
        """Render save/load profile buttons and profile management UI"""
        with ui.card().classes('w-full'):
            ui.label('Strategy Profiles').classes('text-lg font-semibold mb-2')
            ui.label('Save and load your favorite strategy configurations').classes('text-sm text-gray-500 mb-3')
            
            # Profile list
            profiles = self.db.list_strategy_profiles()
            profile_options = {p['name']: f"{p['name']} ({p['strategy_name']})" 
                             for p in profiles}
            
            if profile_options:
                self.profile_list_select = ui.select(
                    options=profile_options,
                    label='Saved Profiles',
                    on_change=self._on_profile_select
                ).classes('w-full mb-2')
            else:
                ui.label('No saved profiles yet').classes('text-sm text-gray-500 mb-2')
            
            # Save new profile section
            with ui.expansion('Save Current Configuration', icon='save').classes('w-full mb-2'):
                self.profile_name_input = ui.input(
                    label='Profile Name',
                    placeholder='My Martingale Config'
                ).classes('w-full')
                
                self.profile_desc_input = ui.input(
                    label='Description (optional)',
                    placeholder='Low risk martingale for BTC'
                ).classes('w-full')
                
                ui.button('Save Profile', on_click=self._save_profile, 
                         icon='save', color='primary').classes('mt-2')
            
            # Action buttons
            with ui.row().classes('w-full gap-2 mt-3'):
                ui.button('Load Selected', on_click=self._load_profile, 
                         icon='folder_open').props('outline')
                ui.button('Delete Selected', on_click=self._delete_profile, 
                         icon='delete', color='negative').props('outline')
                ui.button('Apply to Bot', on_click=self._apply_to_bot, 
                         icon='check', color='primary')
    
    def _on_strategy_change(self, e):
        """Handle strategy selection change"""
        strategy_name = e.value
        app_state.update(strategy_name=strategy_name, strategy_params={})
        
        # Update description
        self._update_description()
        
        # Update metadata
        self._update_metadata()
        
        # Re-render parameters
        self.params_container.clear()
        with self.params_container:
            self._render_param_inputs()
    
    def _on_param_change(self, param_name: str, value: Any):
        """Handle parameter value change"""
        params = app_state.strategy_params.copy()
        params[param_name] = value
        app_state.update(strategy_params=params)
    
    def _on_profile_select(self, e):
        """Handle profile selection from dropdown"""
        # Just store the selected profile name, actual loading happens on button click
        pass
    
    def _save_profile(self):
        """Save current configuration to database"""
        if not self.profile_name_input or not self.profile_name_input.value:
            ui.notify('Please enter a profile name', type='warning')
            return
        
        profile_name = self.profile_name_input.value.strip()
        description = self.profile_desc_input.value.strip() if self.profile_desc_input else ""
        
        try:
            self.db.save_strategy_profile(
                name=profile_name,
                strategy_name=app_state.strategy_name,
                parameters=app_state.strategy_params,
                description=description
            )
            
            ui.notify(f'✅ Profile saved: {profile_name}', type='positive', position='top')
            
            # Clear inputs
            self.profile_name_input.value = ""
            if self.profile_desc_input:
                self.profile_desc_input.value = ""
            
            # Refresh profile list
            # NOTE: In a full implementation, we'd re-render the profile select
            
        except Exception as e:
            ui.notify(f'❌ Failed to save profile: {e}', type='negative')
    
    def _load_profile(self):
        """Load selected profile from database"""
        if not self.profile_list_select or not self.profile_list_select.value:
            ui.notify('Please select a profile to load', type='warning')
            return
        
        profile_name = self.profile_list_select.value
        
        try:
            profile = self.db.load_strategy_profile(profile_name)
            
            if not profile:
                ui.notify(f'Profile not found: {profile_name}', type='warning')
                return
            
            # Update state
            app_state.update(
                strategy_name=profile['strategy_name'],
                strategy_params=profile['parameters']
            )
            
            # Update UI
            self.strategy_dropdown.set_value(profile['strategy_name'])
            self._update_description()
            self._update_metadata()
            
            # Re-render parameters
            self.params_container.clear()
            with self.params_container:
                self._render_param_inputs()
            
            ui.notify(f'✅ Profile loaded: {profile_name}', type='positive', position='top')
            
        except Exception as e:
            ui.notify(f'❌ Failed to load profile: {e}', type='negative')
    
    def _delete_profile(self):
        """Delete selected profile from database"""
        if not self.profile_list_select or not self.profile_list_select.value:
            ui.notify('Please select a profile to delete', type='warning')
            return
        
        profile_name = self.profile_list_select.value
        
        try:
            self.db.delete_strategy_profile(profile_name)
            ui.notify(f'🗑️ Profile deleted: {profile_name}', type='info', position='top')
            
            # NOTE: In a full implementation, we'd re-render the profile select
            
        except Exception as e:
            ui.notify(f'❌ Failed to delete profile: {e}', type='negative')
    
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
