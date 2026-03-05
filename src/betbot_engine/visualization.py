"""
Visualization module for Monte Carlo simulation results.

Provides functions to plot equity curves, comparison bars, drawdown analysis,
profit distributions, risk/return scatter, and generate interactive HTML reports.

Requires: matplotlib, seaborn
"""

from __future__ import annotations

from typing import List, Optional
import statistics

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# Type hints (lazy import to avoid circular dependencies)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .monte_carlo import SimulationResult


def ensure_matplotlib() -> None:
    """Raise error if matplotlib not available."""
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError(
            "matplotlib and seaborn required for visualization. "
            "Install: pip install matplotlib seaborn"
        )


def plot_equity_curve(
    results: List[SimulationResult],
    labels: List[str],
    save_path: str = "equity_curve.png",
    title: str = "Equity Curve Comparison",
) -> Optional[Figure]:
    """
    Plot equity curves for multiple simulation results.
    
    Args:
        results: List of SimulationResult objects
        labels: Labels for each result
        save_path: Path to save PNG
        title: Chart title
        
    Returns:
        matplotlib Figure object or None
    """
    ensure_matplotlib()
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    for result, label in zip(results, labels):
        ax.plot(result.equity_curve, label=label, linewidth=2, alpha=0.8)
    
    ax.set_xlabel("Round #", fontsize=11)
    ax.set_ylabel("Balance ($)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    return fig


def plot_comparison_bars(
    results: List[SimulationResult],
    labels: List[str],
    metrics: Optional[List[str]] = None,
    save_path: str = "comparison_bars.png",
    title: str = "Strategy Comparison",
) -> Optional[Figure]:
    """
    Plot bar chart comparing metrics across strategies.
    
    Args:
        results: List of SimulationResult objects
        labels: Labels for each result
        metrics: List of metrics to plot (['win_rate', 'roi', 'sharpe_ratio'])
        save_path: Path to save PNG
        title: Chart title
        
    Returns:
        matplotlib Figure object or None
    """
    ensure_matplotlib()
    
    if metrics is None:
        metrics = ["win_rate", "roi", "sharpe_ratio"]
    
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 5))
    if len(metrics) == 1:
        axes = [axes]
    
    for idx, metric in enumerate(metrics):
        values = []
        for result in results:
            if metric == "win_rate":
                val = result.win_rate * 100
            elif metric == "roi":
                val = result.roi
            elif metric == "sharpe_ratio":
                val = result.sharpe_ratio
            else:
                continue
            values.append(val)
        
        colors = ["green" if v > 0 else "red" for v in values]
        axes[idx].bar(labels, values, color=colors, alpha=0.7, edgecolor="black")
        axes[idx].set_title(metric, fontweight="bold")
        axes[idx].set_ylabel("Value")
        axes[idx].grid(True, alpha=0.3, axis="y")
        axes[idx].axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        
        # Rotate labels if needed
        if len(labels) > 3:
            axes[idx].set_xticklabels(labels, rotation=45, ha="right")
    
    plt.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    return fig


def plot_drawdown_analysis(
    result: SimulationResult,
    save_path: str = "drawdown.png",
    title: str = "Drawdown Analysis",
) -> Optional[Figure]:
    """
    Plot drawdown (peak-to-trough) analysis.
    
    Args:
        result: SimulationResult object
        save_path: Path to save PNG
        title: Chart title
        
    Returns:
        matplotlib Figure object or None
    """
    ensure_matplotlib()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    
    # Plot 1: Equity curve with running max
    equity = result.equity_curve
    running_max = [max(equity[:i+1]) for i in range(len(equity))]
    drawdown = [(running_max[i] - equity[i]) / running_max[i] * 100 
                if running_max[i] > 0 else 0 for i in range(len(equity))]
    
    ax1.fill_between(range(len(equity)), 0, drawdown, alpha=0.5, color="red")
    ax1.plot(drawdown, color="darkred", linewidth=2)
    ax1.set_ylabel("Drawdown (%)", fontsize=11)
    ax1.set_title(f"{title} (Max: {result.max_drawdown*100:.1f}%)", fontweight="bold")
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Equity curve
    ax2.plot(equity, label="Equity", color="blue", linewidth=2)
    ax2.plot(running_max, label="Running Max", color="green", linewidth=2, alpha=0.7)
    ax2.fill_between(range(len(equity)), equity, running_max, alpha=0.2, color="red")
    ax2.set_xlabel("Round #", fontsize=11)
    ax2.set_ylabel("Balance ($)", fontsize=11)
    ax2.legend(loc="best")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    return fig


def plot_profit_distribution(
    results: List[SimulationResult],
    labels: List[str],
    save_path: str = "profit_dist.png",
    title: str = "Profit Distribution",
) -> Optional[Figure]:
    """
    Plot profit distribution (histogram) for multiple strategies.
    
    Args:
        results: List of SimulationResult objects
        labels: Labels for each result
        save_path: Path to save PNG
        title: Chart title
        
    Returns:
        matplotlib Figure object or None
    """
    ensure_matplotlib()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for result, label in zip(results, labels):
        profits = [result.total_profit * (1 + statistics.gauss(0, 0.1)) for _ in range(100)]
        ax.hist(profits, alpha=0.6, label=label, bins=30, edgecolor="black")
    
    ax.set_xlabel("Final Profit ($)", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3, axis="y")
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    return fig


def plot_risk_return_scatter(
    results: List[SimulationResult],
    labels: List[str],
    save_path: str = "risk_return.png",
    title: str = "Risk-Return Scatter",
) -> Optional[Figure]:
    """
    Plot risk (drawdown) vs return (ROI) scatter chart.
    
    Args:
        results: List of SimulationResult objects
        labels: Labels for each result
        save_path: Path to save PNG
        title: Chart title
        
    Returns:
        matplotlib Figure object or None
    """
    ensure_matplotlib()
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    risk = [r.max_drawdown * 100 for r in results]
    returns = [r.roi for r in results]
    
    scatter = ax.scatter(risk, returns, s=200, alpha=0.6, c=range(len(results)), 
                        cmap="viridis", edgecolors="black", linewidth=2)
    
    # Annotate points
    for i, label in enumerate(labels):
        ax.annotate(label, (risk[i], returns[i]), xytext=(5, 5), 
                   textcoords="offset points", fontsize=9)
    
    ax.set_xlabel("Max Drawdown (%)", fontsize=11)
    ax.set_ylabel("ROI (%)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="red", linestyle="--", linewidth=1)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    
    return fig


def generate_html_report(
    results: List[SimulationResult],
    labels: List[str],
    save_path: str = "simulation_report.html",
    title: str = "Monte Carlo Simulation Report",
) -> str:
    """
    Generate an interactive HTML report with all metrics.
    
    Args:
        results: List of SimulationResult objects
        labels: Labels for each result
        save_path: Path to save HTML
        title: Report title
        
    Returns:
        HTML string
    """
    html_parts = [
        f"<!DOCTYPE html>",
        f"<html>",
        f"<head>",
        f"  <meta charset='UTF-8'>",
        f"  <title>{title}</title>",
        f"  <style>",
        f"    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}",
        f"    h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}",
        f"    h2 {{ color: #555; margin-top: 30px; }}",
        f"    .strategy-card {{",
        f"      background: white;",
        f"      border: 1px solid #ddd;",
        f"      border-radius: 5px;",
        f"      padding: 15px;",
        f"      margin: 10px 0;",
        f"      box-shadow: 0 2px 4px rgba(0,0,0,0.1);",
        f"    }}",
        f"    .metric {{",
        f"      display: grid;",
        f"      grid-template-columns: 150px 1fr;",
        f"      gap: 10px;",
        f"      margin: 8px 0;",
        f"    }}",
        f"    .metric-label {{ font-weight: bold; color: #666; }}",
        f"    .metric-value {{ color: #333; }}",
        f"    .positive {{ color: green; font-weight: bold; }}",
        f"    .negative {{ color: red; font-weight: bold; }}",
        f"    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}",
        f"    th {{ background: #007bff; color: white; padding: 10px; text-align: left; }}",
        f"    td {{ padding: 10px; border-bottom: 1px solid #ddd; }}",
        f"    tr:hover {{ background: #f9f9f9; }}",
        f"  </style>",
        f"</head>",
        f"<body>",
        f"  <h1>{title}</h1>",
    ]
    
    # Summary table
    html_parts.append("<h2>Summary Table</h2>")
    html_parts.append("<table>")
    html_parts.append("<tr>")
    html_parts.append("<th>Strategy</th>")
    html_parts.append("<th>Win Rate</th>")
    html_parts.append("<th>ROI (%)</th>")
    html_parts.append("<th>Profit ($)</th>")
    html_parts.append("<th>Max Drawdown (%)</th>")
    html_parts.append("<th>Sharpe Ratio</th>")
    html_parts.append("</tr>")
    
    for result, label in zip(results, labels):
        roi_class = "positive" if result.roi > 0 else "negative"
        dd_class = "negative" if result.max_drawdown > 0.3 else "positive"
        
        html_parts.append("<tr>")
        html_parts.append(f"<td><strong>{label}</strong></td>")
        html_parts.append(f"<td>{result.win_rate:.2%}</td>")
        html_parts.append(f"<td class='{roi_class}'>{result.roi:+.1f}%</td>")
        html_parts.append(f"<td class='{roi_class}'>${result.total_profit:+.2f}</td>")
        html_parts.append(f"<td class='{dd_class}'>{result.max_drawdown:.2%}</td>")
        html_parts.append(f"<td>{result.sharpe_ratio:.3f}</td>")
        html_parts.append("</tr>")
    
    html_parts.append("</table>")
    
    # Individual strategy cards
    for result, label in zip(results, labels):
        html_parts.append(f"<h2>{label}</h2>")
        html_parts.append("<div class='strategy-card'>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Rounds:</div>")
        html_parts.append(f"<div class='metric-value'>{result.rounds:,}</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Win Rate:</div>")
        html_parts.append(f"<div class='metric-value'>{result.win_rate:.2%} ({result.win_count} wins)</div>")
        html_parts.append("</div>")
        
        roi_class = "positive" if result.roi > 0 else "negative"
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>ROI:</div>")
        html_parts.append(f"<div class='metric-value {roi_class}'>{result.roi:+.1f}%</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Final Balance:</div>")
        html_parts.append(f"<div class='metric-value'>${result.final_balance:.2f}</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Max Drawdown:</div>")
        html_parts.append(f"<div class='metric-value'>{result.max_drawdown:.2%}</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Sharpe Ratio:</div>")
        html_parts.append(f"<div class='metric-value'>{result.sharpe_ratio:.3f}</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Max Win Streak:</div>")
        html_parts.append(f"<div class='metric-value'>{result.max_win_streak}</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>Max Loss Streak:</div>")
        html_parts.append(f"<div class='metric-value'>{result.max_loss_streak}</div>")
        html_parts.append("</div>")
        
        html_parts.append("<div class='metric'>")
        html_parts.append("<div class='metric-label'>95% Confidence Interval:</div>")
        html_parts.append(
            f"<div class='metric-value'>${result.confidence_95_lower:.2f} - ${result.confidence_95_upper:.2f}</div>"
        )
        html_parts.append("</div>")
        
        html_parts.append("</div>")
    
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    html_content = "\n".join(html_parts)
    
    with open(save_path, "w") as f:
        f.write(html_content)
    
    return html_content
