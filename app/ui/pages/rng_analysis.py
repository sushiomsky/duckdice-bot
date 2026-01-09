"""
RNG Analysis page - analyze bet patterns and generate strategies.
"""

from nicegui import ui
from pathlib import Path
import asyncio
from typing import Optional
import logging

from app.ui.components import card

logger = logging.getLogger(__name__)


class RNGAnalysisController:
    """Controller for RNG analysis page."""
    
    def __init__(self):
        """Initialize controller."""
        self.imported_data = None
        self.analysis_result = None
        self.running = False
        
        # UI elements (will be set during render)
        self.import_status_label = None
        self.progress_container = None
        self.progress_bar = None
        self.progress_label = None
        self.results_container = None
        
    async def import_file(self, file_path: str):
        """Import data from file."""
        try:
            from src.rng_analysis import FileImporter
            
            self._update_import_status("Importing file...", "info")
            
            importer = FileImporter()
            importer.set_progress_callback(self._on_import_progress)
            
            result = importer.import_file(Path(file_path))
            
            if result.success:
                self.imported_data = result.data
                self._update_import_status(
                    f"✅ {result.rows_imported} bets loaded from file",
                    "positive"
                )
                
                if result.warnings:
                    for warning in result.warnings:
                        ui.notify(warning, type='warning')
            else:
                self._update_import_status(
                    f"❌ Import failed: {result.errors[0]}",
                    "negative"
                )
                
        except Exception as e:
            logger.error(f"Import error: {e}")
            self._update_import_status(f"❌ Error: {str(e)}", "negative")
    
    def _update_import_status(self, message: str, type_: str):
        """Update import status label."""
        if self.import_status_label:
            self.import_status_label.text = message
            
            # Update color based on type
            if type_ == "positive":
                self.import_status_label.classes(
                    remove='text-slate-400 text-red-400',
                    add='text-green-400'
                )
            elif type_ == "negative":
                self.import_status_label.classes(
                    remove='text-slate-400 text-green-400',
                    add='text-red-400'
                )
            else:
                self.import_status_label.classes(
                    remove='text-green-400 text-red-400',
                    add='text-slate-400'
                )
    
    def _on_import_progress(self, message: str, progress: float):
        """Handle import progress updates."""
        # This would update a progress bar during import
        pass
    
    async def run_analysis(
        self,
        run_statistical: bool,
        run_ml: bool,
        run_deep_learning: bool,
        max_time: int,
    ):
        """Run analysis on imported data."""
        if self.imported_data is None:
            ui.notify("No data imported", type="warning")
            return
        
        if self.running:
            ui.notify("Analysis already running", type="warning")
            return
        
        self.running = True
        
        try:
            from src.rng_analysis import AnalysisEngine, AnalysisConfig
            
            # Show progress container
            if self.progress_container:
                self.progress_container.set_visibility(True)
            
            # Configure analysis
            config = AnalysisConfig(
                run_statistical=run_statistical,
                run_ml=run_ml,
                run_deep_learning=run_deep_learning,
                max_time_minutes=max_time,
            )
            
            # Create engine
            engine = AnalysisEngine()
            engine.set_progress_callback(self._on_analysis_progress)
            
            # Load data
            self._update_progress("Loading data...", 0.05)
            engine.load_data(self.imported_data)
            engine.configure(config)
            
            # Run analysis
            self._update_progress("Running analysis...", 0.1)
            
            # Run in thread pool to avoid blocking UI
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(engine.run_analysis)
                
                # Poll for completion
                while not future.done():
                    await asyncio.sleep(0.1)
                
                self.analysis_result = future.result()
            
            # Show results
            self._update_progress("Analysis complete!", 1.0)
            await asyncio.sleep(0.5)
            
            if self.progress_container:
                self.progress_container.set_visibility(False)
            
            self._show_results()
            
            ui.notify("Analysis complete!", type="positive")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            ui.notify(f"Analysis failed: {str(e)}", type="negative")
            
            if self.progress_container:
                self.progress_container.set_visibility(False)
        
        finally:
            self.running = False
    
    def _on_analysis_progress(self, message: str, progress: float):
        """Handle analysis progress updates."""
        self._update_progress(message, progress)
    
    def _update_progress(self, message: str, progress: float):
        """Update progress display."""
        if self.progress_label:
            self.progress_label.text = message
        
        if self.progress_bar:
            self.progress_bar.value = progress
    
    def _show_results(self):
        """Display analysis results."""
        if self.results_container is None or self.analysis_result is None:
            return
        
        self.results_container.clear()
        
        with self.results_container:
            if not self.analysis_result.success:
                ui.label("❌ Analysis Failed").classes("text-xl font-semibold text-red-400")
                for error in self.analysis_result.errors:
                    ui.label(f"• {error}").classes("text-sm text-red-300 ml-4")
                return
            
            # Results summary
            ui.label("Results Summary").classes("text-xl font-semibold mb-4")
            
            insights = self.analysis_result.insights
            
            with ui.grid(columns=2).classes("gap-4 w-full mb-6"):
                # Statistical results
                if 'summary' in insights:
                    summary = insights['summary']
                    
                    if 'uniformity' in summary:
                        self._result_card(
                            "📊 Uniformity Test",
                            f"{summary['uniformity']} (p={summary.get('uniformity_p_value', 0):.3f})",
                            "PASS" in summary['uniformity']
                        )
                    
                    if 'best_model' in summary:
                        self._result_card(
                            "🤖 Best ML Model",
                            f"{summary['best_model']}<br>Improvement: {summary.get('best_improvement', 0):.1f}%",
                            False
                        )
                
                # Exploitability
                self._result_card(
                    "⚠️ Exploitability",
                    insights.get('exploitability', 'UNKNOWN'),
                    insights.get('exploitability') == 'NONE'
                )
                
                # Confidence
                self._result_card(
                    "🎯 Confidence",
                    insights.get('confidence', 'LOW'),
                    insights.get('confidence') == 'HIGH'
                )
            
            # Recommendations
            if 'recommendations' in insights:
                with card().classes("bg-yellow-900 border-yellow-600"):
                    ui.label("⚠️ Important Recommendations").classes("text-lg font-semibold mb-2")
                    for rec in insights['recommendations']:
                        ui.label(f"• {rec}").classes("text-sm mb-1")
            
            # Actions
            with ui.row().classes("gap-2 mt-6"):
                ui.button(
                    "📄 View Full Report",
                    on_click=lambda: self._show_full_report()
                ).classes("bg-blue-600")
                
                ui.button(
                    "💾 Export JSON",
                    on_click=lambda: self._export_results()
                ).classes("bg-purple-600")
                
                ui.button(
                    "🚀 Generate Strategy Script",
                    on_click=lambda: self._show_generate_dialog()
                ).classes("bg-green-600")
    
    def _result_card(self, title: str, value: str, is_good: bool):
        """Render a result card."""
        color = "green" if is_good else "slate"
        
        with ui.card().classes(f"p-4 bg-{color}-800"):
            ui.label(title).classes("text-xs text-slate-400 mb-1")
            ui.html(value).classes("text-sm font-semibold")
    
    def _show_full_report(self):
        """Show detailed analysis report."""
        # TODO: Implement detailed report viewer
        ui.notify("Full report viewer - coming soon!", type="info")
    
    def _export_results(self):
        """Export results to JSON."""
        if self.analysis_result is None:
            return
        
        import json
        from datetime import datetime
        
        # Create export data
        export_data = {
            'metadata': self.analysis_result.metadata,
            'statistical_results': self.analysis_result.statistical_results,
            'ml_results': self.analysis_result.ml_results,
            'insights': self.analysis_result.insights,
            'exported_at': datetime.utcnow().isoformat(),
        }
        
        # Save to file
        filepath = Path('bet_history') / f'analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        ui.notify(f"Results exported to {filepath.name}", type="positive")
    
    def _show_generate_dialog(self):
        """Show strategy generation dialog."""
        if self.analysis_result is None:
            return
        
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label("🚀 Generate Strategy Script").classes("text-xl font-semibold mb-4")
            
            strategy_name = ui.input(
                label="Strategy Name",
                value="RNG Analysis Strategy"
            ).classes("w-full")
            
            strategy_type = ui.select(
                options=['pattern', 'ml', 'conservative'],
                label="Strategy Type",
                value='conservative'
            ).classes("w-full mt-4")
            
            ui.label("Type descriptions:").classes("text-xs text-slate-400 mt-2")
            ui.label("• Pattern: Streak-based betting").classes("text-xs ml-4")
            ui.label("• ML: ML insights (simplified)").classes("text-xs ml-4")
            ui.label("• Conservative: Fixed 1% betting").classes("text-xs ml-4")
            
            with ui.row().classes("gap-2 mt-6 w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close).classes("bg-gray-600")
                ui.button(
                    "Generate",
                    on_click=lambda: self._generate_strategy(
                        strategy_name.value,
                        strategy_type.value,
                        dialog
                    )
                ).classes("bg-green-600")
        
        dialog.open()
    
    def _generate_strategy(self, name: str, strategy_type: str, dialog):
        """Generate and save strategy script."""
        try:
            from src.rng_analysis import EnhancedScriptGenerator
            
            generator = EnhancedScriptGenerator(self.analysis_result)
            script_code, metadata = generator.generate_strategy(
                name=name,
                strategy_type=strategy_type,
                category='generated',
            )
            
            # Save to script system
            filepath = generator.save_to_script_system(
                script_code,
                metadata,
                category='generated',
            )
            
            dialog.close()
            
            ui.notify(
                f"✅ Strategy '{name}' saved to script library!",
                type="positive"
            )
            
            # Ask if user wants to view it
            with ui.dialog() as view_dialog, ui.card():
                ui.label("Strategy Generated Successfully!").classes("text-lg font-semibold mb-4")
                ui.label(f"Saved to: {filepath}").classes("text-sm text-slate-400 mb-4")
                
                with ui.row().classes("gap-2"):
                    ui.button("OK", on_click=view_dialog.close).classes("bg-blue-600")
                    ui.button(
                        "View in Script Editor",
                        on_click=lambda: (view_dialog.close(), ui.navigate.to(f'/scripts/editor?name={name}'))
                    ).classes("bg-green-600")
            
            view_dialog.open()
            
        except Exception as e:
            logger.error(f"Script generation error: {e}")
            ui.notify(f"Failed to generate script: {str(e)}", type="negative")


def rng_analysis_content() -> None:
    """Render RNG analysis page content."""
    controller = RNGAnalysisController()
    
    ui.label("🔬 RNG Analysis").classes("text-3xl font-bold")
    ui.label("Analyze bet patterns and generate strategies").classes("text-sm text-slate-400 mb-6")
    
    # Warning banner
    with card().classes("bg-yellow-900 border-yellow-600 mb-6"):
        ui.label("⚠️ Educational Use Only").classes("text-lg font-semibold mb-2")
        ui.label("Past patterns do NOT predict future outcomes. Cryptographic RNG systems are designed to be unpredictable.").classes("text-sm")
    
    # Import Data
    with card():
        ui.label("Import Data").classes("text-xl font-semibold mb-4")
        
        with ui.row().classes("gap-4 w-full items-end"):
            file_input = ui.input(
                label="File Path",
                placeholder="/path/to/bet_history.csv"
            ).classes("flex-1")
            
            ui.button(
                "📁 Choose File",
                on_click=lambda: ui.notify("File picker - coming soon!", type="info")
            )
            
            ui.button(
                "📥 Import",
                on_click=lambda: asyncio.create_task(
                    controller.import_file(file_input.value)
                )
            ).classes("bg-blue-600")
        
        controller.import_status_label = ui.label("No data loaded").classes("text-sm text-slate-400 mt-2")
    
    # Analysis Configuration
    with card().classes("mt-6"):
        ui.label("Analysis Configuration").classes("text-xl font-semibold mb-4")
        
        stat_check = ui.checkbox("Statistical Tests", value=True)
        ml_check = ui.checkbox("Machine Learning Models", value=True)
        dl_check = ui.checkbox("Deep Learning (advanced, slow)", value=False)
        
        max_time = ui.number(
            label="Max Time (minutes)",
            value=5,
            min=1,
            max=60
        ).classes("w-48 mt-4")
        
        ui.button(
            "▶ Run Analysis",
            on_click=lambda: asyncio.create_task(
                controller.run_analysis(
                    stat_check.value,
                    ml_check.value,
                    dl_check.value,
                    int(max_time.value),
                )
            )
        ).classes("bg-green-600 mt-4")
    
    # Progress
    controller.progress_container = ui.column().classes("mt-6")
    controller.progress_container.set_visibility(False)
    
    with controller.progress_container:
        with card():
            ui.label("Analysis Progress").classes("text-xl font-semibold mb-4")
            
            controller.progress_label = ui.label("Starting...").classes("text-sm text-slate-400 mb-2")
            controller.progress_bar = ui.linear_progress(value=0).classes("w-full")
    
    # Results
    with card().classes("mt-6"):
        controller.results_container = ui.column().classes("w-full")
        
        with controller.results_container:
            ui.label("Results Summary").classes("text-xl font-semibold mb-4")
            ui.label("Run an analysis to see results").classes("text-sm text-slate-400")
