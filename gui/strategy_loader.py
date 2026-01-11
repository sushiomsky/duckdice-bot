"""
Dynamic strategy loader for NiceGUI interface.

Loads all strategies from src/betbot_strategies and provides
metadata for dynamic UI generation.
"""
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path

# Add src to path so we can import betbot_strategies
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from betbot_strategies import list_strategies, get_strategy
    from betbot_strategies.base import StrategyMetadata
    STRATEGIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import betbot_strategies: {e}")
    STRATEGIES_AVAILABLE = False


class StrategyInfo:
    """Information about a strategy for GUI display."""
    
    def __init__(self, name: str, strategy_class):
        self.name = name
        self.strategy_class = strategy_class
        
        # Get basic info
        try:
            self.display_name = strategy_class.name()
        except:
            self.display_name = name.replace("-", " ").title()
        
        try:
            self.description = strategy_class.describe()
        except:
            self.description = "No description available"
        
        # Get metadata
        try:
            self.metadata: StrategyMetadata = strategy_class.metadata()
        except:
            self.metadata = None
        
        # Get parameter schema
        try:
            self.schema: Dict[str, Any] = strategy_class.schema()
        except:
            self.schema = {}
    
    def get_display_label(self) -> str:
        """Get display label for dropdown."""
        if self.metadata:
            risk = self.metadata.risk_level
            return f"{self.display_name} ({risk} Risk)"
        return self.display_name
    
    def get_tooltip(self) -> str:
        """Get tooltip text for strategy."""
        parts = [self.description]
        
        if self.metadata:
            parts.append(f"\nRisk: {self.metadata.risk_level}")
            parts.append(f"Bankroll: {self.metadata.bankroll_required}")
            parts.append(f"Recommended for: {self.metadata.recommended_for}")
            
            if self.metadata.best_use_case:
                parts.append(f"\n{self.metadata.best_use_case}")
        
        return "\n".join(parts)
    
    def get_parameters(self) -> List[Dict[str, Any]]:
        """Get list of parameters for form generation.
        
        Returns:
            List of parameter dicts with keys:
            - name: parameter name
            - type: "str", "int", "float", "bool"
            - default: default value
            - desc: description
        """
        params = []
        for name, spec in self.schema.items():
            params.append({
                "name": name,
                "type": spec.get("type", "str"),
                "default": spec.get("default", ""),
                "desc": spec.get("desc", name.replace("_", " ").title()),
            })
        return params


class StrategyLoader:
    """Loads and manages available strategies."""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyInfo] = {}
        self._load_strategies()
    
    def _load_strategies(self):
        """Load all available strategies."""
        if not STRATEGIES_AVAILABLE:
            print("Warning: Strategies module not available, using fallback")
            self._load_fallback_strategies()
            return
        
        try:
            strategy_list = list_strategies()
            for item in strategy_list:
                name = item["name"]
                try:
                    strategy_class = get_strategy(name)
                    self.strategies[name] = StrategyInfo(name, strategy_class)
                except Exception as e:
                    print(f"Warning: Could not load strategy {name}: {e}")
            
            print(f"Loaded {len(self.strategies)} strategies")
        except Exception as e:
            print(f"Error loading strategies: {e}")
            self._load_fallback_strategies()
    
    def _load_fallback_strategies(self):
        """Fallback to basic strategies if import fails."""
        # This provides the 5 strategies currently hardcoded in the GUI
        fallback_strategies = [
            "classic-martingale",
            "anti-martingale-streak", 
            "dalembert",
            "fibonacci",
            "paroli"
        ]
        
        for name in fallback_strategies:
            # Create minimal StrategyInfo objects
            class FallbackStrategy:
                @classmethod
                def name(cls):
                    return name
                
                @classmethod
                def describe(cls):
                    return f"{name.replace('-', ' ').title()} strategy"
                
                @classmethod
                def schema(cls):
                    return {
                        "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount"},
                        "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
                        "is_high": {"type": "bool", "default": True, "desc": "Bet High/Low"},
                    }
            
            self.strategies[name] = StrategyInfo(name, FallbackStrategy)
    
    def get_strategy_names(self) -> List[str]:
        """Get list of strategy names."""
        return sorted(self.strategies.keys())
    
    def get_strategy_info(self, name: str) -> Optional[StrategyInfo]:
        """Get info about a specific strategy."""
        return self.strategies.get(name)
    
    def get_all_strategies(self) -> List[StrategyInfo]:
        """Get all strategy info objects."""
        return sorted(self.strategies.values(), key=lambda s: s.display_name)
    
    def get_strategy_class(self, name: str):
        """Get the actual strategy class."""
        info = self.strategies.get(name)
        return info.strategy_class if info else None


# Global singleton instance
_strategy_loader = None

def get_strategy_loader() -> StrategyLoader:
    """Get the global strategy loader instance."""
    global _strategy_loader
    if _strategy_loader is None:
        _strategy_loader = StrategyLoader()
    return _strategy_loader
