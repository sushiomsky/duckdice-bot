#!/usr/bin/env python3
"""
Strategy Comparison Simulator
Runs all strategies with identical conditions and generates comprehensive HTML report
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_engine.engine import AutoBetEngine, EngineConfig
from betbot_strategies import list_strategies, get_strategy


class MockDuckDiceAPI:
    """Mock API for simulation"""
    def __init__(self, starting_balance: float = 100.0):
        self.starting_balance = starting_balance
        
    def get_user_info(self):
        return {
            'username': 'simulation_user',
            'balances': [
                {'currency': 'BTC', 'main': str(self.starting_balance), 'faucet': '10.0'},
            ]
        }


class StrategyComparator:
    """Compare all strategies under identical conditions with Monte Carlo simulation"""
    
    def __init__(self, starting_balance: float = 1.0, max_bets: int = 10000,
                 currency: str = 'btc', seed: int = 42, num_runs: int = 100):
        self.starting_balance = starting_balance
        self.max_bets = max_bets
        self.currency = currency
        self.seed = seed
        self.num_runs = num_runs  # Number of simulation runs per strategy
        self.results = []
        
    def run_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """Run a single strategy multiple times (Monte Carlo) and collect aggregate metrics"""
        print(f"Running {strategy_name}...", end=' ', flush=True)
        
        # Skip strategies that require special setup
        skip_strategies = ['custom-script', 'faucet-grind']
        if strategy_name in skip_strategies:
            print(f"⏭️  Skipped (requires special config)")
            return {
                'strategy': strategy_name,
                'skipped': True,
                'error': 'Requires special configuration'
            }
        
        # Aggregate metrics across all runs
        all_run_metrics = []
        
        for run_num in range(self.num_runs):
            # Use different seed for each run
            run_seed = self.seed + run_num
            
            # Get default params for strategy
            try:
                strategy_class = get_strategy(strategy_name)
                schema = strategy_class.get_parameters_schema()
                params = {k: v.get('default') for k, v in schema.items()}
                
                # Special handling for specific strategies
                if strategy_name == 'target-aware':
                    params['target_balance'] = self.starting_balance * 2  # Double the balance
            except:
                params = {}
            
            # Create config with unique seed for this run
            config = EngineConfig(
                symbol=self.currency,
                dry_run=True,
                faucet=False,
                stop_loss=-0.99,  # Allow 99% loss before stopping
                take_profit=10.0,  # 1000% profit
                max_bets=self.max_bets,
                max_losses=None,
                max_duration_sec=None,
                delay_ms=0,  # Fast simulation
                jitter_ms=0,
                seed=run_seed
            )
            
            # Track metrics for this single run
            run_metrics = {
                'bets_placed': 0,
                'wins': 0,
                'losses': 0,
                'ending_balance': self.starting_balance,
                'max_balance': self.starting_balance,
                'min_balance': self.starting_balance,
                'busted': False,
                'total_wagered': 0.0,
                'bet_sizes': []
            }
            
            def track_bet(bet_data: Dict[str, Any]):
                """Track bet metrics for this run"""
                # Extract result from the event structure
                result = bet_data.get('result', {})
                
                # Skip if no result (summary event)
                if not result:
                    return
                    
                run_metrics['bets_placed'] += 1
                
                win = result.get('win', False)
                if win:
                    run_metrics['wins'] += 1
                else:
                    run_metrics['losses'] += 1
                
                # Balance is at top level of event
                balance = float(bet_data.get('balance', 0))
                
                # Amount is in the bet spec
                bet_spec = bet_data.get('bet', {})
                amount = float(bet_spec.get('amount', 0))
                
                run_metrics['ending_balance'] = balance
                run_metrics['max_balance'] = max(run_metrics['max_balance'], balance)
                run_metrics['min_balance'] = min(run_metrics['min_balance'], balance)
                run_metrics['bet_sizes'].append(amount)
                
                # Check for bust
                if balance <= 0.0001:
                    run_metrics['busted'] = True
            
            try:
                api = MockDuckDiceAPI(starting_balance=self.starting_balance)
                engine = AutoBetEngine(api, config)
                
                result = engine.run(
                    strategy_name=strategy_name,
                    params=params,
                    printer=None,  # Silent
                    json_sink=track_bet,
                    stop_checker=None
                )
                
                # Calculate run metrics
                if run_metrics['bets_placed'] > 0:
                    run_metrics['win_rate'] = (run_metrics['wins'] / run_metrics['bets_placed']) * 100
                    run_metrics['profit'] = run_metrics['ending_balance'] - self.starting_balance
                    run_metrics['profit_percent'] = (run_metrics['profit'] / self.starting_balance) * 100
                else:
                    # No bets placed - set sensible defaults
                    run_metrics['win_rate'] = 0.0
                    run_metrics['profit'] = run_metrics['ending_balance'] - self.starting_balance
                    run_metrics['profit_percent'] = (run_metrics['profit'] / self.starting_balance) * 100 if self.starting_balance > 0 else 0.0
                
                if run_metrics['bet_sizes']:
                    run_metrics['total_wagered'] = sum(run_metrics['bet_sizes'])
                
                run_metrics['stop_reason'] = result.get('stop_reason', 'unknown')
                
                all_run_metrics.append(run_metrics)
                
            except Exception as e:
                # Record failed run
                all_run_metrics.append({
                    'error': str(e),
                    'busted': True,
                    'profit_percent': -100.0
                })
            
            # Progress indicator every 10 runs
            if (run_num + 1) % 10 == 0:
                print(f"{run_num + 1}", end='...', flush=True)
        
        # Aggregate results from all runs
        if not all_run_metrics:
            print("❌ No valid runs")
            return {'strategy': strategy_name, 'error': 'All runs failed'}
        
        # Calculate aggregate statistics
        profits = [r.get('profit_percent', -100) for r in all_run_metrics]
        ending_balances = [r.get('ending_balance', 0) for r in all_run_metrics]
        max_balances = [r.get('max_balance', self.starting_balance) for r in all_run_metrics]
        win_rates = [r.get('win_rate', 0) for r in all_run_metrics if 'win_rate' in r]
        busts = sum(1 for r in all_run_metrics if r.get('busted', False))
        
        # Calculate aggregated metrics
        bets_placed_list = [r.get('bets_placed', 0) for r in all_run_metrics]
        min_balances = [r.get('min_balance', self.starting_balance) for r in all_run_metrics]
        bet_sizes_all = [size for r in all_run_metrics for size in r.get('bet_sizes', [])]
        total_wagered_list = [r.get('total_wagered', 0) for r in all_run_metrics]
        
        metrics = {
            'strategy': strategy_name,
            'starting_balance': self.starting_balance,
            'max_bets': self.max_bets,
            'num_runs': self.num_runs,
            
            # Aggregate statistics
            'avg_profit_percent': sum(profits) / len(profits),
            'median_profit_percent': sorted(profits)[len(profits) // 2],
            'best_profit_percent': max(profits),
            'worst_profit_percent': min(profits),
            'std_dev_profit': (sum((p - sum(profits)/len(profits))**2 for p in profits) / len(profits)) ** 0.5,
            
            'avg_ending_balance': sum(ending_balances) / len(ending_balances),
            'avg_max_balance': sum(max_balances) / len(max_balances),
            'avg_win_rate': sum(win_rates) / len(win_rates) if win_rates else 0,
            
            'bust_count': busts,
            'bust_rate': (busts / self.num_runs) * 100,
            
            'profitable_runs': sum(1 for p in profits if p > 0),
            'profitable_rate': (sum(1 for p in profits if p > 0) / self.num_runs) * 100,
            
            # Additional aggregated metrics for HTML report
            'bets_placed': int(sum(bets_placed_list) / len(bets_placed_list)) if bets_placed_list else 0,
            'min_balance': sum(min_balances) / len(min_balances) if min_balances else self.starting_balance,
            'avg_bet_size': sum(bet_sizes_all) / len(bet_sizes_all) if bet_sizes_all else 0,
            'max_bet_size': max(bet_sizes_all) if bet_sizes_all else 0,
            'total_wagered': sum(total_wagered_list) / len(total_wagered_list) if total_wagered_list else 0,
            'duration_sec': 0.0,  # Not applicable for Monte Carlo
            'stop_reason': f"{self.num_runs} runs completed",
            
            # Legacy fields for compatibility
            'profit_percent': sum(profits) / len(profits),
            'ending_balance': sum(ending_balances) / len(ending_balances),
            'max_balance': sum(max_balances) / len(max_balances),
            'win_rate': sum(win_rates) / len(win_rates) if win_rates else 0,
            'busts': busts,
        }
        
        print(f"✅ {self.num_runs} runs, avg: {metrics['avg_profit_percent']:+.2f}%, busts: {busts}")
        
        return metrics
    
    def run_all(self) -> List[Dict[str, Any]]:
        """Run all strategies"""
        strategies = list_strategies()
        strategy_names = [s['name'] if isinstance(s, dict) else s for s in strategies]
        
        print(f"\n{'='*60}")
        print(f"Strategy Comparison Simulator")
        print(f"{'='*60}")
        print(f"Starting Balance: {self.starting_balance} {self.currency.upper()}")
        print(f"Max Bets: {self.max_bets}")
        print(f"Strategies: {len(strategy_names)}")
        print(f"Seed: {self.seed} (reproducible)")
        print(f"{'='*60}\n")
        
        results = []
        for strategy_name in strategy_names:
            metrics = self.run_strategy(strategy_name)
            results.append(metrics)
        
        self.results = results
        return results
    
    def generate_html_report(self, output_file: str = 'strategy_comparison.html'):
        """Generate comprehensive HTML report"""
        if not self.results:
            raise ValueError("No results to report. Run run_all() first.")
        
        # Filter out skipped strategies
        valid_results = [r for r in self.results if not r.get('skipped', False)]
        
        # Sort by profit
        sorted_results = sorted(valid_results, key=lambda x: x['profit_percent'], reverse=True)
        
        # Calculate summary stats
        total_strategies = len(valid_results)
        skipped_strategies = len(self.results) - len(valid_results)
        profitable = sum(1 for r in valid_results if r['avg_profit_percent'] > 0)
        busted = sum(1 for r in valid_results if r['busts'] > 0)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strategy Comparison Report - Monte Carlo Simulation</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .header .subtitle {{
            font-size: 1.3em;
            margin-top: 15px;
            font-weight: bold;
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 5px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .charts {{
            padding: 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .chart-container h2 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.3em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .positive {{ color: #28a745; font-weight: bold; }}
        .negative {{ color: #dc3545; font-weight: bold; }}
        .neutral {{ color: #6c757d; }}
        .rank {{
            display: inline-block;
            width: 30px;
            height: 30px;
            line-height: 30px;
            text-align: center;
            border-radius: 50%;
            font-weight: bold;
            color: white;
        }}
        .rank-1 {{ background: #FFD700; }}
        .rank-2 {{ background: #C0C0C0; }}
        .rank-3 {{ background: #CD7F32; }}
        .rank-other {{ background: #6c757d; }}
        .details-section {{
            padding: 40px;
        }}
        .details-section h2 {{
            margin-bottom: 20px;
            color: #333;
        }}
        .strategy-detail {{
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .strategy-detail h3 {{
            margin-bottom: 15px;
            color: #667eea;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .metric {{
            background: white;
            padding: 10px;
            border-radius: 4px;
        }}
        .metric-label {{
            font-size: 0.8em;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 1.2em;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎲 Strategy Comparison Report</h1>
            <p>Monte Carlo Simulation Analysis</p>
            <div class="subtitle">
                {self.num_runs} runs × {self.max_bets:,} bets = {self.num_runs * self.max_bets:,} total bets per strategy
            </div>
            <p style="font-size: 0.9em; margin-top: 10px;">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Tested Strategies</h3>
                <div class="value">{total_strategies}</div>
            </div>
            <div class="summary-card">
                <h3>Runs Per Strategy</h3>
                <div class="value">{self.num_runs}</div>
            </div>
            <div class="summary-card">
                <h3>Bets Per Run</h3>
                <div class="value">{self.max_bets:,}</div>
            </div>
            <div class="summary-card">
                <h3>Total Simulations</h3>
                <div class="value">{total_strategies * self.num_runs}</div>
            </div>
            <div class="summary-card">
                <h3>Starting Balance</h3>
                <div class="value">{self.starting_balance} {self.currency.upper()}</div>
            </div>
            <div class="summary-card">
                <h3>Best Strategy</h3>
                <div class="value {'positive' if sorted_results[0]['avg_profit_percent'] > 0 else 'negative'}">{sorted_results[0]['strategy']}<br><small>({sorted_results[0]['avg_profit_percent']:+.2f}%)</small></div>
            </div>
            <div class="summary-card">
                <h3>Worst Strategy</h3>
                <div class="value negative">{sorted_results[-1]['strategy']}<br><small>({sorted_results[-1]['avg_profit_percent']:+.2f}%)</small></div>
            </div>
            <div class="summary-card">
                <h3>Total Bust Rate</h3>
                <div class="value">{sum(r.get('bust_count', 0) for r in valid_results) / (total_strategies * self.num_runs) * 100:.1f}%</div>
            </div>
        </div>
        
        <div class="charts">
            <div class="chart-container">
                <h2>📊 Profit Comparison</h2>
                <canvas id="profitChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>📈 Max Balance Reached</h2>
                <canvas id="maxBalanceChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>🎯 Win Rate Comparison</h2>
                <canvas id="winRateChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>💰 Total Wagered</h2>
                <canvas id="wageredChart"></canvas>
            </div>
        </div>
        
        <div class="details-section">
            <h2>📋 Monte Carlo Results - Detailed Comparison</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Strategy</th>
                        <th>Runs</th>
                        <th>Avg Profit %</th>
                        <th>Median %</th>
                        <th>Best %</th>
                        <th>Worst %</th>
                        <th>Std Dev</th>
                        <th>Bust Rate</th>
                        <th>Win Rate</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for rank, result in enumerate(sorted_results, 1):
            rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
            profit_class = "positive" if result.get('avg_profit_percent', 0) > 0 else "negative" if result.get('avg_profit_percent', 0) < 0 else "neutral"
            
            html += f"""
                    <tr>
                        <td><span class="rank {rank_class}">{rank}</span></td>
                        <td><strong>{result['strategy']}</strong></td>
                        <td>{result.get('num_runs', 0)}</td>
                        <td class="{profit_class}">{result.get('avg_profit_percent', 0):+.2f}%</td>
                        <td>{result.get('median_profit_percent', 0):+.2f}%</td>
                        <td class="positive">{result.get('best_profit_percent', 0):+.2f}%</td>
                        <td class="negative">{result.get('worst_profit_percent', 0):+.2f}%</td>
                        <td>{result.get('std_dev_profit', 0):.2f}</td>
                        <td>{result.get('bust_rate', 0):.1f}%</td>
                        <td>{result.get('avg_win_rate', 0):.1f}%</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="details-section">
            <h2>🔍 Individual Strategy Details</h2>
"""
        
        for rank, result in enumerate(sorted_results, 1):
            profit_class = "positive" if result['avg_profit_percent'] > 0 else "negative"
            html += f"""
            <div class="strategy-detail">
                <h3>#{rank}. {result['strategy']}</h3>
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-label">Bets Placed</div>
                        <div class="metric-value">{result['bets_placed']:,}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value">{result['win_rate']:.2f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Ending Balance</div>
                        <div class="metric-value">{result['ending_balance']:.6f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Profit</div>
                        <div class="metric-value {profit_class}">{result['profit_percent']:+.2f}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Max Balance</div>
                        <div class="metric-value">{result['max_balance']:.6f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Min Balance</div>
                        <div class="metric-value">{result['min_balance']:.6f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Avg Bet Size</div>
                        <div class="metric-value">{result['avg_bet_size']:.6f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Max Bet Size</div>
                        <div class="metric-value">{result['max_bet_size']:.6f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Wagered</div>
                        <div class="metric-value">{result['total_wagered']:.6f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Duration</div>
                        <div class="metric-value">{result['duration_sec']:.2f}s</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Busts</div>
                        <div class="metric-value">{result['busts']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Stop Reason</div>
                        <div class="metric-value" style="font-size: 0.9em;">{result['stop_reason']}</div>
                    </div>
                </div>
            </div>
"""
        
        # Add chart data
        strategy_names = [r['strategy'] for r in sorted_results]
        profit_percents = [r['profit_percent'] for r in sorted_results]
        max_balances = [r['max_balance'] for r in sorted_results]
        win_rates = [r['win_rate'] for r in sorted_results]
        total_wagered = [r['total_wagered'] for r in sorted_results]
        
        # Color code: green if positive, red if negative
        bar_colors = ['rgba(40, 167, 69, 0.7)' if p > 0 else 'rgba(220, 53, 69, 0.7)' for p in profit_percents]
        
        html += f"""
        </div>
    </div>
    
    <script>
        // Profit Chart
        new Chart(document.getElementById('profitChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(strategy_names)},
                datasets: [{{
                    label: 'Profit %',
                    data: {json.dumps(profit_percents)},
                    backgroundColor: {json.dumps(bar_colors)},
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: (context) => context.parsed.y.toFixed(2) + '%'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: (value) => value + '%'
                        }}
                    }}
                }}
            }}
        }});
        
        // Max Balance Chart
        new Chart(document.getElementById('maxBalanceChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(strategy_names)},
                datasets: [{{
                    label: 'Max Balance',
                    data: {json.dumps(max_balances)},
                    backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        
        // Win Rate Chart
        new Chart(document.getElementById('winRateChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(strategy_names)},
                datasets: [{{
                    label: 'Win Rate %',
                    data: {json.dumps(win_rates)},
                    backgroundColor: 'rgba(40, 167, 69, 0.7)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{
                            callback: (value) => value + '%'
                        }}
                    }}
                }}
            }}
        }});
        
        // Total Wagered Chart
        new Chart(document.getElementById('wageredChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(strategy_names)},
                datasets: [{{
                    label: 'Total Wagered',
                    data: {json.dumps(total_wagered)},
                    backgroundColor: 'rgba(255, 193, 7, 0.7)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        # Write to file
        output_path = Path(output_file)
        output_path.write_text(html)
        print(f"\n✅ HTML report generated: {output_path.absolute()}")
        return str(output_path.absolute())


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare all betting strategies with Monte Carlo simulation')
    parser.add_argument('-b', '--balance', type=float, default=10.0,
                       help='Starting balance (default: 10.0)')
    parser.add_argument('-n', '--max-bets', type=int, default=10000,
                       help='Maximum bets per run (default: 10000)')
    parser.add_argument('-r', '--runs', type=int, default=100,
                       help='Number of simulation runs per strategy (default: 100)')
    parser.add_argument('-c', '--currency', type=str, default='btc',
                       help='Currency symbol (default: btc)')
    parser.add_argument('-s', '--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    parser.add_argument('-o', '--output', type=str, default='strategy_comparison.html',
                       help='Output HTML file (default: strategy_comparison.html)')
    
    args = parser.parse_args()
    
    comparator = StrategyComparator(
        starting_balance=args.balance,
        max_bets=args.max_bets,
        currency=args.currency,
        seed=args.seed,
        num_runs=args.runs
    )
    
    # Run all strategies
    comparator.run_all()
    
    # Generate report
    output_file = comparator.generate_html_report(args.output)
    
    print(f"\n{'='*60}")
    print(f"Comparison complete!")
    print(f"Open the report: file://{output_file}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
