from __future__ import annotations
"""
Comprehensive HTML report generator for Monte Carlo strategy simulation results.

Produces a single self-contained HTML file with:
  • Sortable comparison table
  • Interactive Plotly.js charts (via CDN — no server needed)
  • Per-strategy equity band, drawdown, and distribution charts
  • Final strategy comparison section
"""

import json
import math
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

from betbot_engine.strategy_simulator import StrategySimResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(v: float, decimals: int = 2) -> str:
    return f"{v:.{decimals}f}"


def _pct(v: float) -> str:
    return f"{v:.1f}%"


def _color(v: float, positive_good: bool = True) -> str:
    if positive_good:
        return "#22c55e" if v > 0 else ("#ef4444" if v < 0 else "#94a3b8")
    return "#ef4444" if v > 0 else ("#22c55e" if v < 0 else "#94a3b8")


def _grade(result: StrategySimResult) -> tuple[str, str]:
    """Return (letter_grade, bg_color)."""
    score = 0
    score += min(30, max(0, result.roi_mean))          # up to 30 pts for ROI
    score += result.profitable_run_pct * 0.3            # up to 30 pts
    score -= result.max_drawdown_mean * 50              # penalty for drawdown
    score -= result.ruin_pct * 0.3                      # penalty for ruin rate
    score += max(0, result.sharpe_mean) * 5             # bonus for Sharpe

    if score >= 25:   return "A", "#166534"
    if score >= 15:   return "B", "#1e40af"
    if score >= 5:    return "C", "#92400e"
    if score >= -5:   return "D", "#7c2d12"
    return "F", "#450a0a"


# ── Chart builders (return Plotly.js JSON) ───────────────────────────────────

def _equity_band_traces(r: StrategySimResult) -> List[Dict[str, Any]]:
    """Equity band chart: p10 fill, mean line, p90 fill."""
    x = list(range(len(r.band_mean)))
    traces = []

    # P90 upper bound (invisible line, used as fill boundary)
    traces.append({
        "x": x, "y": [round(v, 4) for v in r.band_p90],
        "mode": "lines", "line": {"width": 0}, "name": "P90",
        "showlegend": False, "hoverinfo": "skip",
    })
    # P10 lower bound with fill-to-tonexty
    traces.append({
        "x": x, "y": [round(v, 4) for v in r.band_p10],
        "mode": "lines", "line": {"width": 0},
        "fill": "tonexty", "fillcolor": "rgba(99,179,237,0.15)",
        "name": "P10–P90 band", "showlegend": True, "hoverinfo": "skip",
    })
    # Mean line
    traces.append({
        "x": x, "y": [round(v, 4) for v in r.band_mean],
        "mode": "lines", "line": {"color": "#3b82f6", "width": 2.5},
        "name": "Mean balance",
    })
    # Starting balance reference
    traces.append({
        "x": [0, len(x) - 1],
        "y": [r.starting_balance, r.starting_balance],
        "mode": "lines",
        "line": {"color": "#f59e0b", "width": 1.5, "dash": "dot"},
        "name": "Start", "showlegend": True,
    })
    return traces


def _drawdown_traces(r: StrategySimResult) -> List[Dict[str, Any]]:
    """Drawdown area chart from mean equity curve."""
    curve = r.band_mean
    if not curve:
        return []
    peak = curve[0]
    dd = []
    for v in curve:
        if v > peak:
            peak = v
        dd.append(-(peak - v) / peak * 100 if peak > 0 else 0)
    x = list(range(len(dd)))
    return [{
        "x": x, "y": [round(v, 3) for v in dd],
        "mode": "lines", "fill": "tozeroy",
        "line": {"color": "#ef4444", "width": 1.5},
        "fillcolor": "rgba(239,68,68,0.25)",
        "name": "Drawdown %",
    }]


def _roi_dist_traces(r: StrategySimResult) -> List[Dict[str, Any]]:
    """ROI distribution histogram."""
    return [{
        "x": [round(v, 2) for v in r.roi_values],
        "type": "histogram",
        "nbinsx": min(20, max(5, len(r.roi_values) // 3)),
        "marker": {"color": "#3b82f6", "opacity": 0.75,
                   "line": {"color": "#1e40af", "width": 1}},
        "name": "ROI distribution",
    }]


# ── Comparison chart builders ─────────────────────────────────────────────────

def _bar_chart(
    labels: List[str],
    values: List[float],
    title: str,
    unit: str = "",
    positive_good: bool = True,
) -> Dict[str, Any]:
    colors = [_color(v, positive_good) for v in values]
    return {
        "data": [{
            "x": labels,
            "y": [round(v, 3) for v in values],
            "type": "bar",
            "marker": {"color": colors, "opacity": 0.85,
                       "line": {"color": "#1e293b", "width": 1}},
            "text": [f"{v:.2f}{unit}" for v in values],
            "textposition": "outside",
            "hovertemplate": f"%{{x}}<br>%{{y:.2f}}{unit}<extra></extra>",
        }],
        "layout": {
            "title": {"text": title, "font": {"size": 14}},
            "margin": {"t": 40, "b": 80, "l": 50, "r": 20},
            "paper_bgcolor": "#1e293b",
            "plot_bgcolor": "#0f172a",
            "font": {"color": "#e2e8f0"},
            "xaxis": {"tickangle": -35, "tickfont": {"size": 10}},
            "yaxis": {"gridcolor": "#334155", "zerolinecolor": "#64748b"},
            "showlegend": False,
        },
    }


def _scatter_chart(results: List[StrategySimResult]) -> Dict[str, Any]:
    labels = [r.strategy_name for r in results]
    x = [round(r.max_drawdown_mean * 100, 2) for r in results]
    y = [round(r.roi_mean, 2) for r in results]
    sizes = [max(8, min(30, r.win_rate_mean * 80)) for r in results]
    colors = [_color(v) for v in y]
    return {
        "data": [{
            "x": x, "y": y,
            "mode": "markers+text",
            "text": labels,
            "textposition": "top center",
            "textfont": {"size": 9},
            "marker": {"size": sizes, "color": colors, "opacity": 0.8,
                       "line": {"color": "#e2e8f0", "width": 1}},
            "hovertemplate": (
                "<b>%{text}</b><br>Drawdown: %{x:.1f}%<br>"
                "ROI: %{y:.2f}%<extra></extra>"
            ),
        }],
        "layout": {
            "title": {"text": "Risk vs Return (bubble = win rate)", "font": {"size": 14}},
            "margin": {"t": 40, "b": 50, "l": 60, "r": 20},
            "paper_bgcolor": "#1e293b",
            "plot_bgcolor": "#0f172a",
            "font": {"color": "#e2e8f0"},
            "xaxis": {"title": "Max Drawdown (%)", "gridcolor": "#334155"},
            "yaxis": {"title": "ROI (%)", "gridcolor": "#334155",
                      "zerolinecolor": "#64748b"},
            "shapes": [{
                "type": "line", "x0": 0, "x1": 1, "y0": 0, "y1": 0,
                "xref": "paper", "yref": "y",
                "line": {"color": "#f59e0b", "width": 1.5, "dash": "dot"},
            }],
        },
    }


# ── HTML assembly ─────────────────────────────────────────────────────────────

_CHART_ID = 0


def _next_id(prefix: str = "chart") -> str:
    global _CHART_ID
    _CHART_ID += 1
    return f"{prefix}_{_CHART_ID}"


def _plotly_div(chart_def: Dict[str, Any], height: int = 300) -> str:
    cid = _next_id()
    data_json = json.dumps(chart_def["data"])
    layout_json = json.dumps(chart_def.get("layout", {}))
    return (
        f'<div id="{cid}" style="height:{height}px"></div>\n'
        f'<script>Plotly.newPlot("{cid}",{data_json},{layout_json},'
        f'{{"responsive":true,"displayModeBar":false}});</script>\n'
    )


_DARK_LAYOUT = {
    "paper_bgcolor": "#1e293b",
    "plot_bgcolor": "#0f172a",
    "font": {"color": "#e2e8f0"},
    "margin": {"t": 40, "b": 40, "l": 50, "r": 20},
    "xaxis": {"gridcolor": "#334155", "zerolinecolor": "#64748b"},
    "yaxis": {"gridcolor": "#334155", "zerolinecolor": "#64748b"},
    "legend": {"bgcolor": "#1e293b", "bordercolor": "#334155"},
}


def _strategy_section(r: StrategySimResult) -> str:
    grade, grade_color = _grade(r)
    roi_color = _color(r.roi_mean)
    dd_color = _color(r.max_drawdown_mean * 100, positive_good=False)

    def _stat(label: str, value: str, color: str = "#e2e8f0") -> str:
        return (
            f'<div class="stat-card">'
            f'<div class="stat-label">{label}</div>'
            f'<div class="stat-value" style="color:{color}">{value}</div>'
            f'</div>'
        )

    stats_html = "".join([
        _stat("ROI (mean)", f"{r.roi_mean:+.2f}%", roi_color),
        _stat("ROI (median)", f"{r.roi_median:+.2f}%", _color(r.roi_median)),
        _stat("ROI σ", f"±{r.roi_std:.2f}%"),
        _stat("Win Rate", f"{r.win_rate_mean:.1%}"),
        _stat("Max Drawdown", f"{r.max_drawdown_mean:.1%}", dd_color),
        _stat("Worst DD", f"{r.max_drawdown_worst:.1%}", "#ef4444"),
        _stat("Sharpe", f"{r.sharpe_mean:.3f}", _color(r.sharpe_mean)),
        _stat("Profitable runs", f"{r.profitable_run_pct:.1f}%",
              _color(r.profitable_run_pct - 50)),
        _stat("Ruin rate", f"{r.ruin_pct:.1f}%",
              _color(r.ruin_pct, positive_good=False)),
        _stat("Avg loss streak", f"{r.avg_loss_streak:.1f}"),
        _stat("Runs / Bets", f"{r.n_runs} × {r.bets_per_run}"),
        _stat("Start balance", f"${r.starting_balance:.2f}"),
    ])

    # Equity band chart
    eq_traces = _equity_band_traces(r)
    eq_layout = {**_DARK_LAYOUT, "title": {"text": "Equity (P10–mean–P90)", "font": {"size": 13}},
                 "yaxis": {**_DARK_LAYOUT["yaxis"], "title": "Balance ($)"}}
    eq_chart = {"data": eq_traces, "layout": eq_layout}

    # Drawdown chart
    dd_traces = _drawdown_traces(r)
    dd_layout = {**_DARK_LAYOUT, "title": {"text": "Mean Drawdown", "font": {"size": 13}},
                 "yaxis": {**_DARK_LAYOUT["yaxis"], "title": "Drawdown (%)"}}
    dd_chart = {"data": dd_traces, "layout": dd_layout}

    # ROI histogram
    roi_traces = _roi_dist_traces(r)
    roi_layout = {
        **_DARK_LAYOUT,
        "title": {"text": "ROI Distribution Across Runs", "font": {"size": 13}},
        "xaxis": {**_DARK_LAYOUT["xaxis"], "title": "ROI (%)"},
        "yaxis": {**_DARK_LAYOUT["yaxis"], "title": "Count"},
        "shapes": [{
            "type": "line", "x0": 0, "x1": 0,
            "y0": 0, "y1": 1, "yref": "paper",
            "line": {"color": "#f59e0b", "width": 2, "dash": "dot"},
        }],
    }
    roi_chart = {"data": roi_traces, "layout": roi_layout}

    slug = r.strategy_name.replace(" ", "-").replace("/", "-")

    return f"""
<section class="strategy-section" id="strat-{slug}">
  <div class="strategy-header">
    <h2 class="strategy-name">🎲 {r.strategy_name}</h2>
    <span class="grade-badge" style="background:{grade_color}">{grade}</span>
  </div>
  <div class="stat-grid">{stats_html}</div>
  <div class="charts-row">
    <div class="chart-wrap chart-wide">{_plotly_div(eq_chart, 280)}</div>
    <div class="chart-wrap">{_plotly_div(dd_chart, 280)}</div>
    <div class="chart-wrap">{_plotly_div(roi_chart, 280)}</div>
  </div>
</section>
"""


def _comparison_section(results: List[StrategySimResult]) -> str:
    sorted_by_roi = sorted(results, key=lambda r: r.roi_mean, reverse=True)
    labels = [r.strategy_name for r in sorted_by_roi]

    roi_chart = _bar_chart(labels, [r.roi_mean for r in sorted_by_roi],
                           "Mean ROI (%)", "%")
    wr_chart = _bar_chart(labels, [r.win_rate_mean * 100 for r in sorted_by_roi],
                          "Win Rate (%)", "%")
    dd_chart = _bar_chart(labels, [r.max_drawdown_mean * 100 for r in sorted_by_roi],
                          "Avg Max Drawdown (%)", "%", positive_good=False)
    sh_chart = _bar_chart(labels, [r.sharpe_mean for r in sorted_by_roi],
                          "Sharpe Ratio")
    pft_chart = _bar_chart(labels, [r.profitable_run_pct for r in sorted_by_roi],
                           "Profitable Runs (%)", "%")
    ruin_chart = _bar_chart(labels, [r.ruin_pct for r in sorted_by_roi],
                            "Ruin Rate (%)", "%", positive_good=False)
    scatter = _scatter_chart(results)

    # Sortable summary table
    rows = ""
    for rank, r in enumerate(sorted_by_roi, 1):
        grade, gc = _grade(r)
        roi_c = _color(r.roi_mean)
        ruin_c = _color(r.ruin_pct, positive_good=False)
        slug = r.strategy_name.replace(" ", "-").replace("/", "-")
        rows += f"""
        <tr>
          <td class="rank">#{rank}</td>
          <td><a href="#strat-{slug}" class="strat-link">{r.strategy_name}</a></td>
          <td style="color:{roi_c};font-weight:600">{r.roi_mean:+.2f}%</td>
          <td>{r.roi_median:+.2f}%</td>
          <td>±{r.roi_std:.2f}%</td>
          <td>{r.win_rate_mean:.1%}</td>
          <td>{r.max_drawdown_mean:.1%}</td>
          <td>{r.sharpe_mean:.3f}</td>
          <td>{r.profitable_run_pct:.1f}%</td>
          <td style="color:{ruin_c}">{r.ruin_pct:.1f}%</td>
          <td><span class="grade-badge-sm" style="background:{gc}">{grade}</span></td>
        </tr>"""

    return f"""
<section class="comparison-section" id="comparison">
  <h2>📊 Strategy Comparison</h2>
  <p class="subtitle">All strategies ranked by mean ROI across {results[0].n_runs} Monte Carlo runs 
     of {results[0].bets_per_run} bets each (starting ${results[0].starting_balance:.0f})</p>

  <div class="table-wrap">
    <table id="comp-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">Rank ↕</th>
          <th onclick="sortTable(1)">Strategy ↕</th>
          <th onclick="sortTable(2)">ROI Mean ↕</th>
          <th onclick="sortTable(3)">ROI Median ↕</th>
          <th onclick="sortTable(4)">ROI σ ↕</th>
          <th onclick="sortTable(5)">Win Rate ↕</th>
          <th onclick="sortTable(6)">Max DD ↕</th>
          <th onclick="sortTable(7)">Sharpe ↕</th>
          <th onclick="sortTable(8)">Profitable % ↕</th>
          <th onclick="sortTable(9)">Ruin % ↕</th>
          <th>Grade</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <div class="charts-row">
    <div class="chart-wrap chart-wide">{_plotly_div(roi_chart, 320)}</div>
    <div class="chart-wrap chart-wide">{_plotly_div(wr_chart, 320)}</div>
  </div>
  <div class="charts-row">
    <div class="chart-wrap chart-wide">{_plotly_div(dd_chart, 320)}</div>
    <div class="chart-wrap chart-wide">{_plotly_div(sh_chart, 320)}</div>
  </div>
  <div class="charts-row">
    <div class="chart-wrap chart-wide">{_plotly_div(pft_chart, 320)}</div>
    <div class="chart-wrap chart-wide">{_plotly_div(ruin_chart, 320)}</div>
  </div>
  <div class="charts-row">
    <div class="chart-wrap chart-full">{_plotly_div(scatter, 420)}</div>
  </div>
</section>
"""


_CSS = """
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface2: #253347;
  --border: #334155;
  --text: #e2e8f0;
  --text-dim: #94a3b8;
  --accent: #3b82f6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Nav */
nav {
  position: sticky; top: 0; z-index: 100;
  background: #0a1120;
  border-bottom: 1px solid var(--border);
  padding: 0 20px;
  display: flex; align-items: center; gap: 16px; height: 48px;
  overflow-x: auto; white-space: nowrap;
}
nav .nav-brand { font-weight: 700; font-size: 15px; color: var(--text); }
nav a { color: var(--text-dim); font-size: 12px; }
nav a:hover { color: var(--text); text-decoration: none; }

/* Layout */
.container { max-width: 1400px; margin: 0 auto; padding: 24px 20px; }
h1 { font-size: 26px; font-weight: 700; margin-bottom: 4px; }
.meta { color: var(--text-dim); font-size: 12px; margin-bottom: 32px; }

/* Strategy sections */
.strategy-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}
.strategy-header {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
}
.strategy-name { font-size: 18px; font-weight: 600; }

/* Grade badges */
.grade-badge {
  padding: 4px 12px; border-radius: 20px; font-size: 18px;
  font-weight: 800; color: #fff; min-width: 40px; text-align: center;
}
.grade-badge-sm {
  padding: 2px 8px; border-radius: 12px; font-size: 11px;
  font-weight: 700; color: #fff; display: inline-block;
}

/* Stats grid */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px; margin-bottom: 16px;
}
.stat-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 10px;
}
.stat-label { font-size: 10px; color: var(--text-dim); text-transform: uppercase; }
.stat-value { font-size: 16px; font-weight: 600; margin-top: 2px; }

/* Charts */
.charts-row {
  display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px;
}
.chart-wrap {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px; flex: 1; min-width: 280px;
}
.chart-wide { flex: 2; min-width: 400px; }
.chart-full { flex: 1 1 100%; }

/* Comparison */
.comparison-section {
  background: var(--surface);
  border: 2px solid var(--accent);
  border-radius: 12px; padding: 24px; margin-bottom: 32px;
}
.comparison-section h2 { font-size: 22px; margin-bottom: 6px; }
.subtitle { color: var(--text-dim); font-size: 12px; margin-bottom: 20px; }

/* Table */
.table-wrap { overflow-x: auto; margin-bottom: 24px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
thead th {
  background: #1d3461; color: var(--text); padding: 10px 8px;
  text-align: left; cursor: pointer; white-space: nowrap;
  border-bottom: 2px solid var(--accent);
}
thead th:hover { background: #253e6b; }
tbody td { padding: 8px; border-bottom: 1px solid var(--border); }
tbody tr:hover { background: var(--surface2); }
.rank { color: var(--text-dim); font-size: 11px; }
.strat-link { font-weight: 500; }

/* Responsive */
@media (max-width: 768px) {
  .chart-wide, .chart-full { min-width: 100%; }
  .stat-grid { grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); }
}
"""

_SORT_JS = """
let _sortDir = {};
function sortTable(col) {
  const tbl = document.getElementById('comp-table');
  const tbody = tbl.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc = !_sortDir[col];
  _sortDir[col] = asc;
  rows.sort((a, b) => {
    const ta = a.cells[col].textContent.trim().replace(/[%$+,#]/g,'');
    const tb = b.cells[col].textContent.trim().replace(/[%$+,#]/g,'');
    const na = parseFloat(ta), nb = parseFloat(tb);
    const va = isNaN(na) ? ta : na;
    const vb = isNaN(nb) ? tb : nb;
    return asc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });
  rows.forEach(r => tbody.appendChild(r));
}
"""


def build_report(
    results: List[StrategySimResult],
    output_path: str = "simulation_report.html",
    title: str = "DuckDice Bot — Monte Carlo Strategy Report",
) -> str:
    """
    Build a self-contained HTML report.

    Args:
        results:     List of StrategySimResult (one per strategy)
        output_path: Where to save the HTML file
        title:       Page title

    Returns:
        Path to saved file
    """
    global _CHART_ID
    _CHART_ID = 0  # reset so IDs are deterministic per report

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_strats = len(results)

    # Build nav links
    nav_links = "\n".join(
        f'<a href="#strat-{r.strategy_name.replace(" ", "-").replace("/", "-")}">'
        f'{r.strategy_name}</a>'
        for r in sorted(results, key=lambda x: x.strategy_name)
    )

    # Per-strategy sections
    strategy_sections = "\n".join(
        _strategy_section(r)
        for r in sorted(results, key=lambda x: x.roi_mean, reverse=True)
    )

    # Comparison section
    comp_section = _comparison_section(results)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" crossorigin="anonymous"></script>
<style>
{_CSS}
</style>
</head>
<body>
<nav>
  <span class="nav-brand">🦆 DuckDice Monte Carlo</span>
  <a href="#comparison">📊 Comparison</a>
  {nav_links}
</nav>
<div class="container">
  <h1>{title}</h1>
  <p class="meta">Generated: {now} &nbsp;|&nbsp; {n_strats} strategies &nbsp;|&nbsp;
     {results[0].n_runs} runs × {results[0].bets_per_run} bets &nbsp;|&nbsp;
     Starting balance: ${results[0].starting_balance:.2f}</p>

  {comp_section}

  <h2 style="margin:32px 0 16px;font-size:20px">📋 Individual Strategy Reports</h2>
  <p class="meta" style="margin-bottom:20px">Strategies sorted by mean ROI (best first)</p>

  {strategy_sections}

</div>
<script>
{_SORT_JS}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
