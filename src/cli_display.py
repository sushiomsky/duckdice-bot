"""
Enhanced CLI Display Module using Rich

Provides beautiful terminal output with:
- Colors for win/loss/info
- Progress bars for sessions
- Tables for statistics
- Live updating displays
- ASCII art for branding
"""

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from typing import Dict, Any, Optional
import time

# Global console instance
console = Console()


class CLIDisplay:
    """Enhanced CLI display manager"""
    
    def __init__(self):
        self.console = console
        self.current_session = None
        
    def print_banner(self):
        """Print DuckDice Bot banner"""
        banner_text = """
[bold cyan]╔══════════════════════════════════════════════════════════╗
║                  🎲 DuckDice Bot 4.9.2                   ║
║           Monte Carlo Strategy Comparison                ║
╚══════════════════════════════════════════════════════════╝[/bold cyan]
        """
        self.console.print(banner_text)
    
    def print_section(self, title: str, style: str = "bold yellow"):
        """Print a section header"""
        self.console.print(f"\n[{style}]{'='*60}[/{style}]")
        self.console.print(f"[{style}]{title.center(60)}[/{style}]")
        self.console.print(f"[{style}]{'='*60}[/{style}]\n")
    
    def print_step(self, step_num: int, title: str, total_steps: Optional[int] = None):
        """Print a step header"""
        if total_steps:
            step_text = f"Step {step_num}/{total_steps}: {title}"
        else:
            step_text = f"Step {step_num}: {title}"
        
        self.console.print(f"\n[bold cyan]{step_text}[/bold cyan]")
        self.console.print("[cyan]" + "-" * 60 + "[/cyan]")
    
    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"[bold green]✓[/bold green] {message}")
    
    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"[bold red]✗[/bold red] {message}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")
    
    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"[bold blue]ℹ[/bold blue] {message}")
    
    def print_bet_result(self, bet_num: int, win: bool, profit: float, balance: float, 
                        bet_amount: float = None, multiplier: float = None):
        """Print a bet result with color coding"""
        if win:
            icon = "[bold green]✓ WIN [/bold green]"
            profit_str = f"[green]+{profit:.8f}[/green]"
        else:
            icon = "[bold red]✗ LOSE[/bold red]"
            profit_str = f"[red]{profit:.8f}[/red]"
        
        bet_info = f"Bet #{bet_num}: {icon}"
        if bet_amount:
            bet_info += f" | Amount: {bet_amount:.8f}"
        if multiplier:
            bet_info += f" | {multiplier:.2f}x"
        
        bet_info += f" | Profit: {profit_str} | Balance: [cyan]{balance:.8f}[/cyan]"
        
        self.console.print(bet_info)
    
    def print_strategy_list(self, strategies: list):
        """Print strategies grouped by risk level"""
        
        # Group strategies
        conservative = ['dalembert', 'oscars-grind', 'one-three-two-six']
        moderate = ['fibonacci', 'labouchere', 'paroli', 'fib-loss-cluster']
        aggressive = ['classic-martingale', 'anti-martingale-streak', 'streak-hunter']
        
        self.console.print("\n[bold green]🟢 Conservative (Low Risk):[/bold green]")
        for s in [s for s in strategies if s in conservative]:
            self.console.print(f"  • {s}")
        
        self.console.print("\n[bold yellow]🟡 Moderate (Medium Risk):[/bold yellow]")
        for s in [s for s in strategies if s in moderate]:
            self.console.print(f"  • {s}")
        
        self.console.print("\n[bold red]🔴 Aggressive (High Risk):[/bold red]")
        for s in [s for s in strategies if s in aggressive]:
            self.console.print(f"  • {s}")
        
        self.console.print("\n[bold blue]🔵 Specialized:[/bold blue]")
        specialized = [s for s in strategies if s not in conservative + moderate + aggressive]
        for s in specialized:
            self.console.print(f"  • {s}")
    
    def print_session_summary(self, data: Dict[str, Any]):
        """Print session summary in a nice table"""
        
        table = Table(title="Session Summary", box=box.ROUNDED, show_header=False)
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        # Add rows
        for key, value in data.items():
            table.add_row(key, str(value))
        
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")
    
    def print_statistics_table(self, stats: Dict[str, Any]):
        """Print statistics in a formatted table"""
        
        table = Table(title="📊 Betting Statistics", box=box.DOUBLE_EDGE)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green", justify="right")
        
        # Add rows with color coding
        for key, value in stats.items():
            if isinstance(value, float):
                if 'profit' in key.lower() or 'balance' in key.lower():
                    if value >= 0:
                        formatted = f"[green]{value:.8f}[/green]"
                    else:
                        formatted = f"[red]{value:.8f}[/red]"
                elif '%' in str(value) or 'rate' in key.lower():
                    formatted = f"{value:.2f}%"
                else:
                    formatted = f"{value:.8f}"
            else:
                formatted = str(value)
            
            table.add_row(key, formatted)
        
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")
    
    def create_progress_bar(self, total: int, description: str = "Processing"):
        """Create a progress bar for tracking session"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan] bets"),
            TimeElapsedColumn(),
            console=self.console
        )
    
    def print_live_stats(self, bets: int, wins: int, losses: int, 
                        profit: float, balance: float, win_rate: float):
        """Print live statistics during session"""
        
        # Create a panel with current stats
        stats_text = f"""
[cyan]Bets:[/cyan] {bets}  [green]Wins:[/green] {wins}  [red]Losses:[/red] {losses}  [yellow]Win Rate:[/yellow] {win_rate:.1f}%
[cyan]Profit:[/cyan] {'[green]' if profit >= 0 else '[red]'}{profit:+.8f}{'[/green]' if profit >= 0 else '[/red]'}  [cyan]Balance:[/cyan] {balance:.8f}
        """
        
        panel = Panel(
            stats_text.strip(),
            title="[bold cyan]Live Statistics[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        # Clear previous line and print
        self.console.print("\n", end="")
        self.console.print(panel)
    
    def print_choice_menu(self, options: list, title: str = "Select an option"):
        """Print a choice menu with numbers"""
        self.console.print(f"\n[bold cyan]{title}:[/bold cyan]\n")
        
        for i, option in enumerate(options, 1):
            if isinstance(option, dict):
                name = option.get('name', str(option))
                desc = option.get('description', '')
                if desc:
                    self.console.print(f"  [cyan]{i}.[/cyan] [white]{name}[/white] - {desc}")
                else:
                    self.console.print(f"  [cyan]{i}.[/cyan] [white]{name}[/white]")
            else:
                self.console.print(f"  [cyan]{i}.[/cyan] [white]{option}[/white]")
        
        self.console.print()
    
    def print_parameter_prompt(self, name: str, description: str, default: Any, param_type: str):
        """Print a parameter prompt with type info"""
        type_color = {
            'int': 'yellow',
            'float': 'green',
            'bool': 'blue',
            'str': 'magenta'
        }.get(param_type, 'white')
        
        self.console.print(
            f"  [cyan]{name}[/cyan] [{type_color}]({param_type})[/{type_color}]: {description}"
        )
        self.console.print(f"    [dim]Default: {default}[/dim]")


# Global display instance
display = CLIDisplay()


def demo():
    """Demo of enhanced CLI features"""
    display.print_banner()
    
    display.print_section("Strategy Selection")
    
    strategies = [
        'dalembert', 'fibonacci', 'classic-martingale', 
        'streak-hunter', 'rng-analysis-strategy', 'faucet-grind'
    ]
    display.print_strategy_list(strategies)
    
    display.print_section("Session Summary")
    
    summary = {
        'Mode': 'simulation',
        'Currency': 'BTC',
        'Balance': '100.0',
        'Strategy': 'streak-hunter',
        'Stop-loss': '-30.0%',
        'Take-profit': '50.0%'
    }
    display.print_session_summary(summary)
    
    display.print_section("Betting Session")
    
    # Simulate some bets
    with display.create_progress_bar(10, "Running simulation") as progress:
        task = progress.add_task("Placing bets...", total=10)
        
        for i in range(10):
            time.sleep(0.3)
            win = i % 3 != 0
            profit = 0.5 if win else -0.2
            balance = 100 + (i * profit)
            
            display.print_bet_result(i+1, win, profit, balance, 0.2, 2.0)
            progress.update(task, advance=1)
    
    display.print_section("Final Statistics")
    
    stats = {
        'Total Bets': 10,
        'Wins': 7,
        'Losses': 3,
        'Win Rate': 70.0,
        'Starting Balance': 100.0,
        'Ending Balance': 103.5,
        'Profit': 3.5,
        'Profit %': 3.5
    }
    display.print_statistics_table(stats)
    
    display.print_success("Session completed successfully!")


if __name__ == "__main__":
    demo()
