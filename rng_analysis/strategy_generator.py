#!/usr/bin/env python3
"""
Strategy Generator for RNG Analysis Results
Exports analysis results in a format usable by betting strategies
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class StrategyGenerator:
    """Generate betting strategy configurations from RNG analysis results"""
    
    def __init__(self, analysis_results: Optional[Dict[str, Any]] = None):
        """
        Initialize with analysis results dictionary
        
        Args:
            analysis_results: Dictionary containing results from RNG analysis
        """
        self.analysis_results = analysis_results or {}
        
    def extract_insights(self, df: pd.DataFrame, 
                         stat_results: Dict[str, Any],
                         ml_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract actionable insights from analysis results
        
        Args:
            df: DataFrame with bet history
            stat_results: Statistical analysis results
            ml_results: Machine learning model results
            
        Returns:
            Dictionary of insights for strategy configuration
        """
        insights = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'total_bets_analyzed': len(df),
                'analysis_version': '1.0.0',
            },
            'statistical_summary': {},
            'ml_summary': {},
            'pattern_insights': {},
            'risk_assessment': {},
            'strategy_recommendations': {}
        }
        
        # Extract statistical insights
        if 'distribution' in stat_results:
            dist = stat_results['distribution']
            insights['statistical_summary'] = {
                'mean': float(dist.get('mean', 5000)),
                'std': float(dist.get('std', 2887)),
                'is_uniform': bool(dist.get('ks_p_value', 0) > 0.05),
                'ks_p_value': float(dist.get('ks_p_value', 0)),
            }
        
        if 'autocorrelation' in stat_results:
            auto = stat_results['autocorrelation']
            insights['statistical_summary']['has_autocorrelation'] = bool(auto.get('significant_lags', []))
            insights['statistical_summary']['significant_lags'] = auto.get('significant_lags', [])[:5]
        
        # Extract ML insights
        if ml_results:
            best_model = max(ml_results.items(), 
                           key=lambda x: x[1].get('improvement', -float('inf')) 
                           if 'error' not in x[1] else -float('inf'))
            
            insights['ml_summary'] = {
                'best_model': best_model[0],
                'mae': float(best_model[1].get('mae', 0)),
                'improvement_over_baseline': float(best_model[1].get('improvement', 0)),
                'r2_score': float(best_model[1].get('r2', 0)),
                'predictive_power': 'low' if best_model[1].get('improvement', 0) < 5 else 
                                   'moderate' if best_model[1].get('improvement', 0) < 10 else 'high',
            }
        
        # Pattern insights from data
        if 'Number' in df.columns and 'Result_Binary' in df.columns:
            win_rate = df['Result_Binary'].mean()
            numbers = df['Number'].values
            
            # Simple pattern detection
            high_numbers = (numbers > 5000).mean()
            low_numbers = (numbers < 5000).mean()
            
            insights['pattern_insights'] = {
                'overall_win_rate': float(win_rate),
                'high_number_frequency': float(high_numbers),
                'low_number_frequency': float(low_numbers),
                'number_volatility': float(df['Number'].std()),
            }
        
        # Risk assessment
        max_improvement = insights['ml_summary'].get('improvement_over_baseline', 0)
        
        insights['risk_assessment'] = {
            'exploitability': 'none' if max_improvement < 5 else 
                             'very_low' if max_improvement < 10 else 'low',
            'confidence_level': 'low' if max_improvement < 5 else 'moderate',
            'recommended_action': 'Do not use for real betting' if max_improvement < 10 else 
                                 'Educational only - high overfitting risk',
            'warnings': [
                'Cryptographic RNG is designed to be unpredictable',
                'Past patterns do not predict future outcomes',
                'Any apparent improvements are likely due to overfitting',
                'The house edge ensures long-term losses',
                'This is for educational purposes only'
            ]
        }
        
        # Strategy recommendations
        insights['strategy_recommendations'] = self._generate_strategy_recommendations(insights)
        
        return insights
    
    def _generate_strategy_recommendations(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate strategy configuration recommendations based on insights
        
        Args:
            insights: Extracted insights dictionary
            
        Returns:
            Strategy configuration recommendations
        """
        recommendations = {
            'recommended_strategies': [],
            'parameters': {}
        }
        
        # Conservative recommendation (always include this)
        recommendations['recommended_strategies'].append({
            'name': 'conservative',
            'reason': 'Safest approach given house edge and RNG unpredictability',
            'base_strategy': 'fib-loss-cluster',
            'parameters': {
                'base_amount': '0.000001',
                'chance': '50',
                'is_high': False,
                'loss_threshold': 5,
                'fib_max_index': 8,
                'scale': 1.0
            }
        })
        
        # Pattern-based recommendation (if any patterns detected)
        improvement = insights.get('ml_summary', {}).get('improvement_over_baseline', 0)
        
        if improvement > 5:
            # If moderate improvement detected (likely overfitting)
            win_rate = insights.get('pattern_insights', {}).get('overall_win_rate', 0.5)
            high_freq = insights.get('pattern_insights', {}).get('high_number_frequency', 0.5)
            
            recommendations['recommended_strategies'].append({
                'name': 'pattern_adapted',
                'reason': f'Based on {improvement:.2f}% improvement in analysis (likely overfitting)',
                'base_strategy': 'rng-analysis-strategy',
                'parameters': {
                    'base_amount': '0.000001',
                    'chance': '50',
                    'is_high': high_freq > 0.5,
                    'win_threshold': 0.5,
                    'loss_multiplier': 1.5,
                    'use_patterns': True
                },
                'warning': 'This may not work in practice due to overfitting'
            })
        
        # Kelly criterion recommendation
        recommendations['recommended_strategies'].append({
            'name': 'kelly_conservative',
            'reason': 'Kelly criterion with conservative cap for bankroll management',
            'base_strategy': 'kelly-capped',
            'parameters': {
                'chance': '50',
                'is_high': True,
                'kelly_cap': 0.05,  # Very conservative 5% of Kelly
                'house_edge': 0.01,
                'ewma_alpha': 0.1,
                'min_amount': '0.000001',
                'max_amount': '0.0001',
                'bankroll_hint': '0.001'
            }
        })
        
        # Parameter guidelines
        recommendations['parameters'] = {
            'base_amount': {
                'recommended': '0.000001',
                'explanation': 'Very small base to minimize risk'
            },
            'chance': {
                'recommended': '50',
                'explanation': 'Balanced odds for demonstration'
            },
            'max_loss': {
                'recommended': 0.02,
                'explanation': 'Stop after losing 2% of bankroll'
            },
            'max_profit': {
                'recommended': 0.01,
                'explanation': 'Stop after gaining 1% (take profit)'
            }
        }
        
        return recommendations
    
    def export_to_json(self, insights: Dict[str, Any], output_path: str = 'rng_strategy_config.json'):
        """
        Export insights and recommendations to JSON file
        
        Args:
            insights: Insights dictionary to export
            output_path: Path to output JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(insights, f, indent=2)
        
        print(f"\n✅ Strategy configuration exported to: {output_file}")
        return output_file
    
    def export_to_python_config(self, insights: Dict[str, Any], 
                                output_path: str = 'rng_strategy_params.py'):
        """
        Export recommendations as Python configuration file
        
        Args:
            insights: Insights dictionary to export
            output_path: Path to output Python file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        strategies = insights.get('strategy_recommendations', {}).get('recommended_strategies', [])
        
        content = f'''#!/usr/bin/env python3
"""
Auto-generated strategy configuration from RNG analysis
Generated at: {insights.get('metadata', {}).get('generated_at', 'unknown')}

⚠️ WARNING: This is for EDUCATIONAL PURPOSES ONLY
- Past patterns do not predict future outcomes
- Cryptographic RNG is unpredictable
- The house edge ensures long-term losses
- Only use with amounts you can afford to lose
"""

# Analysis Summary
ANALYSIS_INFO = {{
    'total_bets_analyzed': {insights.get('metadata', {}).get('total_bets_analyzed', 0)},
    'ml_improvement': {insights.get('ml_summary', {}).get('improvement_over_baseline', 0):.2f},
    'predictive_power': '{insights.get('ml_summary', {}).get('predictive_power', 'none')}',
    'exploitability': '{insights.get('risk_assessment', {}).get('exploitability', 'none')}',
}}

# Recommended Strategies
STRATEGIES = [
'''
        
        for strategy in strategies:
            content += f'''
    {{
        'name': '{strategy.get('name', '')}',
        'reason': '{strategy.get('reason', '')}',
        'base_strategy': '{strategy.get('base_strategy', '')}',
        'parameters': {json.dumps(strategy.get('parameters', {}), indent=8)},
'''
            if 'warning' in strategy:
                content += f"        'warning': '{strategy.get('warning', '')}',\n"
            content += '    },\n'
        
        content += ''']

# Risk Warnings
WARNINGS = [
'''
        
        for warning in insights.get('risk_assessment', {}).get('warnings', []):
            content += f"    '{warning}',\n"
        
        content += ''']

# Usage Example
"""
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_engine.engine import AutoBetEngine, EngineConfig

# Initialize API
api = DuckDiceAPI(DuckDiceConfig(api_key="YOUR_API_KEY"))

# Create engine config
engine_config = EngineConfig(
    symbol="XLM",
    faucet=True,  # Use faucet for testing
    dry_run=False,
    stop_loss=-0.02,
    take_profit=0.01,
    max_bets=100,
)

# Create engine
engine = AutoBetEngine(api, engine_config)

# Use recommended strategy
strategy = STRATEGIES[0]  # Conservative strategy
result = engine.run(
    strategy_name=strategy['base_strategy'],
    params=strategy['parameters']
)

print(f"Session complete: {result}")
"""
'''
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Python strategy configuration exported to: {output_file}")
        return output_file
    
    def print_summary(self, insights: Dict[str, Any]):
        """
        Print a human-readable summary of insights and recommendations
        
        Args:
            insights: Insights dictionary to summarize
        """
        print("\n" + "="*70)
        print("STRATEGY GENERATION SUMMARY".center(70))
        print("="*70 + "\n")
        
        # Metadata
        meta = insights.get('metadata', {})
        print(f"Generated: {meta.get('generated_at', 'N/A')}")
        print(f"Bets analyzed: {meta.get('total_bets_analyzed', 0):,}")
        print()
        
        # Statistical summary
        print("STATISTICAL ANALYSIS:")
        stat = insights.get('statistical_summary', {})
        print(f"  Distribution: {'Uniform ✅' if stat.get('is_uniform') else 'Non-uniform ⚠️'}")
        print(f"  Mean: {stat.get('mean', 0):.2f} (Expected: 5000)")
        print(f"  KS Test p-value: {stat.get('ks_p_value', 0):.6f}")
        if stat.get('has_autocorrelation'):
            print(f"  ⚠️  Autocorrelation detected at lags: {stat.get('significant_lags', [])}")
        print()
        
        # ML summary
        print("MACHINE LEARNING ANALYSIS:")
        ml = insights.get('ml_summary', {})
        print(f"  Best Model: {ml.get('best_model', 'N/A')}")
        print(f"  Improvement: {ml.get('improvement_over_baseline', 0):.2f}%")
        print(f"  Predictive Power: {ml.get('predictive_power', 'unknown').upper()}")
        print(f"  R² Score: {ml.get('r2_score', 0):.4f}")
        print()
        
        # Risk assessment
        print("RISK ASSESSMENT:")
        risk = insights.get('risk_assessment', {})
        print(f"  Exploitability: {risk.get('exploitability', 'unknown').upper()}")
        print(f"  Confidence: {risk.get('confidence_level', 'unknown').upper()}")
        print(f"  Recommendation: {risk.get('recommended_action', 'N/A')}")
        print()
        
        # Warnings
        print("⚠️  WARNINGS:")
        for warning in risk.get('warnings', [])[:3]:
            print(f"  - {warning}")
        print()
        
        # Strategy recommendations
        print("RECOMMENDED STRATEGIES:")
        strategies = insights.get('strategy_recommendations', {}).get('recommended_strategies', [])
        for i, strat in enumerate(strategies, 1):
            print(f"\n  {i}. {strat.get('name', '').upper()}")
            print(f"     Base: {strat.get('base_strategy', '')}")
            print(f"     Reason: {strat.get('reason', '')}")
            if 'warning' in strat:
                print(f"     ⚠️  {strat.get('warning', '')}")
        print()
        
        print("="*70)
        print()


def generate_strategy_from_analysis(data_dir: str = "../bet_history",
                                    output_json: str = "rng_strategy_config.json",
                                    output_python: str = "rng_strategy_params.py") -> Dict[str, Any]:
    """
    Convenience function to generate strategy from bet history
    
    Args:
        data_dir: Directory containing bet history CSV files
        output_json: Output path for JSON configuration
        output_python: Output path for Python configuration
        
    Returns:
        Dictionary of insights and recommendations
    """
    print("\n" + "="*70)
    print("GENERATING STRATEGY FROM RNG ANALYSIS".center(70))
    print("="*70 + "\n")
    
    try:
        # Import analysis modules
        from data_loader import BetHistoryLoader
        from pattern_analyzer import RNGPatternAnalyzer
        from ml_predictor import RNGMLPredictor
        
        # Load data
        print("Loading bet history data...")
        loader = BetHistoryLoader(data_dir)
        df = loader.load_all_files()
        df = loader.preprocess_data()
        
        # Run statistical analysis
        print("\nRunning statistical analysis...")
        analyzer = RNGPatternAnalyzer(df)
        stat_results = {
            'distribution': analyzer.analyze_distribution(),
            'autocorrelation': analyzer.analyze_autocorrelation(max_lag=20),
        }
        
        # Run ML analysis
        print("\nRunning machine learning analysis...")
        predictor = RNGMLPredictor(df)
        X, y = predictor.prepare_features()
        ml_results = predictor.train_models(X, y, test_size=0.2)
        
        # Generate insights
        print("\nExtracting insights...")
        generator = StrategyGenerator()
        insights = generator.extract_insights(df, stat_results, ml_results)
        
        # Print summary
        generator.print_summary(insights)
        
        # Export to files
        generator.export_to_json(insights, output_json)
        generator.export_to_python_config(insights, output_python)
        
        print("\n✅ Strategy generation complete!")
        print(f"\nNext steps:")
        print(f"  1. Review the generated configurations")
        print(f"  2. Import the Python config: from rng_strategy_params import STRATEGIES")
        print(f"  3. Use with the auto-bet engine")
        print(f"  4. ⚠️  Remember: This is educational only!")
        print()
        
        return insights
        
    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies")
        print(f"   {e}")
        print(f"\nInstall with: pip install -r requirements_analysis.txt")
        raise
    except Exception as e:
        print(f"\n❌ Error generating strategy: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate betting strategy from RNG analysis results'
    )
    parser.add_argument('--data-dir', default='../bet_history',
                       help='Directory containing bet history CSV files')
    parser.add_argument('--output-json', default='rng_strategy_config.json',
                       help='Output JSON configuration file')
    parser.add_argument('--output-python', default='rng_strategy_params.py',
                       help='Output Python configuration file')
    
    args = parser.parse_args()
    
    try:
        insights = generate_strategy_from_analysis(
            data_dir=args.data_dir,
            output_json=args.output_json,
            output_python=args.output_python
        )
    except Exception as e:
        import sys
        sys.exit(1)
