"""
Enhanced script generator for RNG analysis results.

Generates executable Python strategy scripts compatible with Phase 2 script system.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from textwrap import dedent
import logging

logger = logging.getLogger(__name__)


class EnhancedScriptGenerator:
    """Generate executable strategy scripts from analysis results."""
    
    PATTERN_STRATEGY_TEMPLATE = dedent('''
    """
    {name}
    
    Auto-generated from RNG analysis on {date}.
    
    Analysis Summary:
    - Bets analyzed: {total_bets}
    - Best model: {best_model}
    - Improvement: {improvement}%
    - Exploitability: {exploitability}
    
    ⚠️ WARNING: Past patterns do not guarantee future outcomes.
    Use at your own risk. Start with small bets.
    """
    
    # Analysis insights
    INSIGHTS = {insights_json}
    
    def next_bet(state):
        """
        Calculate next bet based on RNG analysis insights.
        
        Args:
            state: Current strategy state
        
        Returns:
            (amount, chance, roll_over)
        """
        balance = state['balance']
        base_bet = state.get('base_bet', 1.0)
        target_chance = state.get('target_chance', 50.0)
        
        # Calculate bet amount (1% of balance by default)
        bet_amount = max(base_bet, float(balance) * 0.01)
        
        {strategy_logic}
        
        return bet_amount, target_chance, True
    
    def on_result(state, won, profit):
        """Update state after bet result."""
        state['total_bets'] = state.get('total_bets', 0) + 1
        state['total_profit'] = state.get('total_profit', 0) + profit
        
        if won:
            state['wins'] = state.get('wins', 0) + 1
            state['current_streak'] = state.get('current_streak', 0) + 1
        else:
            state['losses'] = state.get('losses', 0) + 1
            state['current_streak'] = 0
        
        {state_update_logic}
    
    def init(params):
        """Initialize strategy state."""
        return {{
            'base_bet': params.get('base_bet', 1.0),
            'target_chance': params.get('target_chance', 50.0),
            'total_bets': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0,
            'current_streak': 0,
            {initial_state}
        }}
    ''')
    
    def __init__(self, analysis_result=None):
        """
        Initialize script generator.
        
        Args:
            analysis_result: AnalysisResult object from analysis engine
        """
        self.analysis_result = analysis_result
        
    def generate_strategy(
        self,
        name: str,
        strategy_type: str = 'pattern',
        category: str = 'generated',
    ) -> tuple[str, dict]:
        """
        Generate strategy script and metadata.
        
        Args:
            name: Strategy name
            strategy_type: Type of strategy (pattern, ml, conservative)
            category: Script category
            
        Returns:
            Tuple of (script_code, metadata_dict)
        """
        # Extract insights
        insights = self._extract_insights()
        
        # Generate strategy logic based on type
        if strategy_type == 'pattern':
            logic, state_update, initial_state = self._generate_pattern_logic(insights)
        elif strategy_type == 'ml':
            logic, state_update, initial_state = self._generate_ml_logic(insights)
        elif strategy_type == 'conservative':
            logic, state_update, initial_state = self._generate_conservative_logic(insights)
        else:
            logic, state_update, initial_state = self._generate_default_logic()
        
        # Generate script code
        script_code = self.PATTERN_STRATEGY_TEMPLATE.format(
            name=name,
            date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            total_bets=insights.get('total_bets', 0),
            best_model=insights.get('best_model', 'N/A'),
            improvement=insights.get('improvement', 0),
            exploitability=insights.get('exploitability', 'UNKNOWN'),
            insights_json=json.dumps(insights, indent=4),
            strategy_logic=logic,
            state_update_logic=state_update,
            initial_state=initial_state,
        )
        
        # Generate metadata
        metadata = {
            'name': name,
            'description': f'Auto-generated from RNG analysis ({insights.get("total_bets", 0)} bets)',
            'version': '1.0.0',
            'category': category,
            'author': 'RNG Analysis Engine',
            'created_at': datetime.utcnow().isoformat(),
            'analysis_metadata': {
                'total_bets': insights.get('total_bets', 0),
                'best_model': insights.get('best_model', 'N/A'),
                'improvement': insights.get('improvement', 0),
                'exploitability': insights.get('exploitability', 'UNKNOWN'),
                'confidence': insights.get('confidence', 'LOW'),
            },
            'parameters': [
                {
                    'name': 'base_bet',
                    'type': 'float',
                    'default': 1.0,
                    'min': 0.00000001,
                    'description': 'Base bet amount',
                },
                {
                    'name': 'target_chance',
                    'type': 'float',
                    'default': 50.0,
                    'min': 0.01,
                    'max': 98.0,
                    'description': 'Target win chance %',
                },
            ],
        }
        
        return script_code, metadata
    
    def _extract_insights(self) -> Dict[str, Any]:
        """Extract insights from analysis result."""
        if self.analysis_result is None:
            return {
                'total_bets': 0,
                'best_model': 'N/A',
                'improvement': 0,
                'exploitability': 'UNKNOWN',
                'confidence': 'LOW',
            }
        
        insights = {}
        
        # Get metadata
        if hasattr(self.analysis_result, 'metadata'):
            insights['total_bets'] = self.analysis_result.metadata.get('total_data_points', 0)
        
        # Get ML results
        if hasattr(self.analysis_result, 'insights'):
            summary = self.analysis_result.insights.get('summary', {})
            insights['best_model'] = summary.get('best_model', 'N/A')
            insights['improvement'] = summary.get('best_improvement', 0)
            insights['exploitability'] = self.analysis_result.insights.get('exploitability', 'UNKNOWN')
            insights['confidence'] = self.analysis_result.insights.get('confidence', 'LOW')
        
        return insights
    
    def _generate_pattern_logic(self, insights: Dict[str, Any]) -> tuple[str, str, str]:
        """Generate pattern-based strategy logic."""
        logic = dedent('''
        # Pattern-based betting
        # Adjust bet based on streak
        if state.get('current_streak', 0) >= 3:
            # On a win streak, be conservative
            bet_amount = base_bet
        elif state.get('losses', 0) > state.get('wins', 0):
            # More losses, increase slightly
            bet_amount = min(bet_amount * 1.5, float(balance) * 0.05)
        ''').strip()
        
        state_update = dedent('''
        # Track patterns
        state['last_result'] = 'win' if won else 'loss'
        ''').strip()
        
        initial_state = "'last_result': None,"
        
        return logic, state_update, initial_state
    
    def _generate_ml_logic(self, insights: Dict[str, Any]) -> tuple[str, str, str]:
        """Generate ML-based strategy logic."""
        logic = dedent('''
        # ML-based betting (simplified)
        # Real ML would require model inference
        
        # Use conservative fixed percentage
        bet_amount = max(base_bet, float(balance) * 0.01)
        
        # Adjust chance based on confidence
        if state.get('wins', 0) > state.get('losses', 0):
            target_chance = 55.0  # Slightly higher chance
        else:
            target_chance = 50.0  # Default
        ''').strip()
        
        state_update = "# ML state updates would go here"
        initial_state = ""
        
        return logic, state_update, initial_state
    
    def _generate_conservative_logic(self, insights: Dict[str, Any]) -> tuple[str, str, str]:
        """Generate conservative strategy logic."""
        logic = dedent('''
        # Conservative fixed betting
        # Always bet 1% of balance with 50% chance
        bet_amount = max(base_bet, float(balance) * 0.01)
        target_chance = 50.0
        ''').strip()
        
        state_update = "# Conservative - no state changes needed"
        initial_state = ""
        
        return logic, state_update, initial_state
    
    def _generate_default_logic(self) -> tuple[str, str, str]:
        """Generate default strategy logic."""
        logic = "# Default: 1% of balance, 50% chance"
        state_update = ""
        initial_state = ""
        
        return logic, state_update, initial_state
    
    def save_to_script_system(
        self,
        script_code: str,
        metadata: dict,
        category: str = 'generated',
    ) -> Path:
        """
        Save generated script to Phase 2 script system.
        
        Args:
            script_code: Python script code
            metadata: Script metadata dictionary
            category: Script category (generated, custom, etc.)
            
        Returns:
            Path to saved script
        """
        from src.script_system import ScriptStorage
        
        storage = ScriptStorage()
        
        # Create StrategyScript object
        from src.script_system import StrategyScript
        
        script = StrategyScript(
            name=metadata['name'],
            description=metadata['description'],
            code=script_code,
            category=category,
            version=metadata['version'],
            author=metadata['author'],
        )
        
        # Save to storage
        filepath = storage.save(script, category=category)
        
        # Save metadata
        metadata_path = filepath.with_suffix('.meta.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved generated strategy to {filepath}")
        
        return filepath
