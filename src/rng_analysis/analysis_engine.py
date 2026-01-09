"""
Analysis engine wrapper for RNG analysis.

Wraps existing analysis modules with clean interface.
"""

import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Add rng_analysis directory to Python path
rng_analysis_dir = Path(__file__).parent.parent.parent / 'rng_analysis'
if str(rng_analysis_dir) not in sys.path:
    sys.path.insert(0, str(rng_analysis_dir))


@dataclass
class AnalysisConfig:
    """Configuration for analysis."""
    run_statistical: bool = True
    run_ml: bool = True
    run_deep_learning: bool = False
    max_time_minutes: int = 5
    min_data_points: int = 100
    save_results: bool = True
    save_visualizations: bool = False


@dataclass
class AnalysisResult:
    """Complete analysis results."""
    success: bool
    statistical_results: Dict[str, Any] = field(default_factory=dict)
    ml_results: Dict[str, Any] = field(default_factory=dict)
    deep_learning_results: Dict[str, Any] = field(default_factory=dict)
    insights: Dict[str, Any] = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnalysisEngine:
    """Wrapper for RNG analysis modules."""
    
    def __init__(self):
        """Initialize analysis engine."""
        self.config = AnalysisConfig()
        self.data = None
        self.progress_callback: Optional[Callable[[str, float], None]] = None
        
        # Try to import existing modules
        self._import_modules()
        
    def _import_modules(self):
        """Import existing analysis modules."""
        try:
            from pattern_analyzer import PatternAnalyzer
            self.pattern_analyzer = PatternAnalyzer
            logger.info("Loaded PatternAnalyzer")
        except ImportError as e:
            logger.warning(f"Could not import PatternAnalyzer: {e}")
            self.pattern_analyzer = None
            
        try:
            from ml_predictor import MLPredictor
            self.ml_predictor = MLPredictor
            logger.info("Loaded MLPredictor")
        except ImportError as e:
            logger.warning(f"Could not import MLPredictor: {e}")
            self.ml_predictor = None
            
        try:
            from deep_learning_predictor import DeepLearningPredictor
            self.deep_learning_predictor = DeepLearningPredictor
            logger.info("Loaded DeepLearningPredictor")
        except ImportError as e:
            logger.warning(f"Could not import DeepLearningPredictor: {e}")
            self.deep_learning_predictor = None
            
        try:
            from strategy_generator import StrategyGenerator
            self.strategy_generator = StrategyGenerator
            logger.info("Loaded StrategyGenerator")
        except ImportError as e:
            logger.warning(f"Could not import StrategyGenerator: {e}")
            self.strategy_generator = None
    
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set progress callback function."""
        self.progress_callback = callback
        
    def _report_progress(self, message: str, progress: float):
        """Report progress if callback set."""
        if self.progress_callback:
            self.progress_callback(message, progress)
            
    def configure(self, config: AnalysisConfig):
        """Configure analysis parameters."""
        self.config = config
        
    def load_data(self, data):
        """
        Load data for analysis.
        
        Args:
            data: DataFrame or filepath
        """
        import pandas as pd
        
        if isinstance(data, pd.DataFrame):
            self.data = data
        elif isinstance(data, (str, Path)):
            # Import using FileImporter
            from .file_importer import FileImporter
            importer = FileImporter()
            result = importer.import_file(Path(data))
            if result.success:
                self.data = result.data
            else:
                raise ValueError(f"Failed to load data: {result.errors}")
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")
            
        logger.info(f"Loaded {len(self.data)} data points")
        
    def run_analysis(self) -> AnalysisResult:
        """
        Run complete analysis pipeline.
        
        Returns:
            AnalysisResult with all results
        """
        if self.data is None:
            return AnalysisResult(
                success=False,
                errors=["No data loaded. Call load_data() first."]
            )
        
        # Validate minimum data points
        if len(self.data) < self.config.min_data_points:
            return AnalysisResult(
                success=False,
                errors=[f"Insufficient data: {len(self.data)} < {self.config.min_data_points}"]
            )
        
        result = AnalysisResult(
            success=True,
            metadata={
                'total_data_points': len(self.data),
                'analysis_started': datetime.utcnow().isoformat(),
                'config': self.config.__dict__,
            }
        )
        
        total_steps = sum([
            self.config.run_statistical,
            self.config.run_ml,
            self.config.run_deep_learning,
        ])
        current_step = 0
        
        # Run statistical analysis
        if self.config.run_statistical:
            self._report_progress("Running statistical analysis...", current_step / total_steps)
            try:
                result.statistical_results = self._run_statistical_analysis()
            except Exception as e:
                logger.error(f"Statistical analysis error: {e}")
                result.errors.append(f"Statistical analysis failed: {str(e)}")
            current_step += 1
        
        # Run ML analysis
        if self.config.run_ml:
            self._report_progress("Running ML models...", current_step / total_steps)
            try:
                result.ml_results = self._run_ml_analysis()
            except Exception as e:
                logger.error(f"ML analysis error: {e}")
                result.errors.append(f"ML analysis failed: {str(e)}")
            current_step += 1
        
        # Run deep learning analysis
        if self.config.run_deep_learning:
            self._report_progress("Running deep learning...", current_step / total_steps)
            try:
                result.deep_learning_results = self._run_deep_learning_analysis()
            except Exception as e:
                logger.error(f"Deep learning analysis error: {e}")
                result.errors.append(f"Deep learning failed: {str(e)}")
            current_step += 1
        
        # Generate insights
        self._report_progress("Generating insights...", 0.95)
        result.insights = self._generate_insights(result)
        
        result.metadata['analysis_completed'] = datetime.utcnow().isoformat()
        
        self._report_progress("Analysis complete", 1.0)
        
        return result
    
    def _run_statistical_analysis(self) -> Dict[str, Any]:
        """Run statistical analysis."""
        if self.pattern_analyzer is None:
            return {'error': 'PatternAnalyzer not available'}
        
        try:
            analyzer = self.pattern_analyzer(self.data['outcome'].values)
            
            results = {
                'distribution': analyzer.analyze_distribution(),
                'autocorrelation': analyzer.analyze_autocorrelation(),
                'runs_test': analyzer.runs_test(),
            }
            
            return results
        except Exception as e:
            logger.error(f"Statistical analysis error: {e}")
            return {'error': str(e)}
    
    def _run_ml_analysis(self) -> Dict[str, Any]:
        """Run ML analysis."""
        if self.ml_predictor is None:
            return {'error': 'MLPredictor not available'}
        
        try:
            predictor = self.ml_predictor(self.data)
            
            results = {
                'random_forest': predictor.train_random_forest(),
                'xgboost': predictor.train_xgboost(),
            }
            
            return results
        except Exception as e:
            logger.error(f"ML analysis error: {e}")
            return {'error': str(e)}
    
    def _run_deep_learning_analysis(self) -> Dict[str, Any]:
        """Run deep learning analysis."""
        if self.deep_learning_predictor is None:
            return {'error': 'DeepLearningPredictor not available'}
        
        try:
            predictor = self.deep_learning_predictor(self.data)
            
            results = {
                'lstm': predictor.train_lstm(),
            }
            
            return results
        except Exception as e:
            logger.error(f"Deep learning analysis error: {e}")
            return {'error': str(e)}
    
    def _generate_insights(self, result: AnalysisResult) -> Dict[str, Any]:
        """Generate insights from analysis results."""
        insights = {
            'summary': {},
            'exploitability': 'UNKNOWN',
            'confidence': 'LOW',
            'recommendations': [],
        }
        
        # Statistical insights
        if result.statistical_results and 'distribution' in result.statistical_results:
            dist = result.statistical_results['distribution']
            if 'ks_p_value' in dist:
                p_value = dist['ks_p_value']
                is_uniform = p_value > 0.05
                insights['summary']['uniformity'] = 'PASS' if is_uniform else 'FAIL'
                insights['summary']['uniformity_p_value'] = p_value
        
        # ML insights
        if result.ml_results:
            best_improvement = 0
            for model_name, model_result in result.ml_results.items():
                if isinstance(model_result, dict) and 'improvement' in model_result:
                    improvement = model_result.get('improvement', 0)
                    if improvement > best_improvement:
                        best_improvement = improvement
                        insights['summary']['best_model'] = model_name
                        insights['summary']['best_improvement'] = improvement
            
            # Assess exploitability
            if best_improvement < 5.0:
                insights['exploitability'] = 'NONE'
                insights['confidence'] = 'HIGH'
                insights['recommendations'].append('No exploitable patterns found')
            elif best_improvement < 10.0:
                insights['exploitability'] = 'VERY LOW'
                insights['confidence'] = 'MEDIUM'
                insights['recommendations'].append('Minimal improvement - not recommended')
            else:
                insights['exploitability'] = 'LOW'
                insights['confidence'] = 'LOW'
                insights['recommendations'].append('Use with extreme caution and small bets')
        
        # General recommendations
        insights['recommendations'].append('⚠️ Past patterns do NOT predict future outcomes')
        insights['recommendations'].append('Start with minimum bets if testing')
        insights['recommendations'].append('Gambling should be for entertainment only')
        
        return insights
