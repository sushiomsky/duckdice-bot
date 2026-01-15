"""
Classic ncurses-based TUI interface.

A traditional ncurses terminal interface for systems without Textual.
Lightweight and compatible with standard Python curses library.
"""

import curses
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque


class NCursesInterface:
    """
    Classic ncurses-based terminal interface.
    
    Keyboard controls:
        s: Start betting
        p: Pause betting
        x: Stop betting
        q: Quit
    """
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.is_running = False
        self.is_paused = False
        
        # Session data
        self.balance = Decimal("0.01")
        self.starting_balance = Decimal("0.01")
        self.profit = Decimal("0")
        self.bets_placed = 0
        self.wins = 0
        self.losses = 0
        
        # Bet history (keep last 15 bets)
        self.bet_history = deque(maxlen=15)
        
        # Colors
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)
        
        # Non-blocking input
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        curses.curs_set(0)  # Hide cursor
    
    def draw_border(self, y, x, height, width, title=""):
        """Draw a border with optional title."""
        # Top border
        self.stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐")
        if title:
            title_text = f" {title} "
            title_x = x + (width - len(title_text)) // 2
            self.stdscr.addstr(y, title_x, title_text, curses.A_BOLD)
        
        # Sides
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "│")
            self.stdscr.addstr(y + i, x + width - 1, "│")
        
        # Bottom border
        self.stdscr.addstr(y + height - 1, x, "└" + "─" * (width - 2) + "┘")
    
    def draw_header(self):
        """Draw the header."""
        height, width = self.stdscr.getmaxyx()
        title = "🎲 DUCKDICE BOT - NCURSES INTERFACE 🎲"
        self.stdscr.addstr(0, (width - len(title)) // 2, title, 
                          curses.color_pair(5) | curses.A_BOLD)
    
    def draw_stats_panel(self):
        """Draw statistics panel."""
        height, width = self.stdscr.getmaxyx()
        panel_y, panel_x = 2, 2
        panel_width = width // 2 - 3
        panel_height = 10
        
        self.draw_border(panel_y, panel_x, panel_height, panel_width, "📊 STATISTICS")
        
        # Balance
        balance_color = curses.color_pair(1) if self.balance >= self.starting_balance else curses.color_pair(2)
        self.stdscr.addstr(panel_y + 2, panel_x + 2, "Balance:")
        self.stdscr.addstr(panel_y + 2, panel_x + 15, f"{self.balance:.8f} BTC", balance_color)
        
        # Profit/Loss
        profit_color = curses.color_pair(1) if self.profit >= 0 else curses.color_pair(2)
        profit_symbol = "+" if self.profit >= 0 else ""
        self.stdscr.addstr(panel_y + 3, panel_x + 2, "Profit:")
        self.stdscr.addstr(panel_y + 3, panel_x + 15, f"{profit_symbol}{self.profit:.8f} BTC", profit_color)
        
        # Profit percentage
        if self.starting_balance > 0:
            profit_pct = (self.profit / self.starting_balance) * 100
            self.stdscr.addstr(panel_y + 4, panel_x + 2, "Profit %:")
            self.stdscr.addstr(panel_y + 4, panel_x + 15, f"{profit_pct:+.2f}%", profit_color)
        
        # Bets
        self.stdscr.addstr(panel_y + 6, panel_x + 2, f"Bets: {self.bets_placed}")
        self.stdscr.addstr(panel_y + 7, panel_x + 2, f"Wins: {self.wins}", curses.color_pair(1))
        self.stdscr.addstr(panel_y + 7, panel_x + 20, f"Losses: {self.losses}", curses.color_pair(2))
        
        # Win rate
        if self.bets_placed > 0:
            winrate = (self.wins / self.bets_placed) * 100
            self.stdscr.addstr(panel_y + 8, panel_x + 2, f"Win Rate: {winrate:.2f}%")
    
    def draw_controls_panel(self):
        """Draw controls panel."""
        height, width = self.stdscr.getmaxyx()
        panel_y, panel_x = 2, width // 2 + 1
        panel_width = width // 2 - 3
        panel_height = 10
        
        self.draw_border(panel_y, panel_x, panel_height, panel_width, "🎮 CONTROLS")
        
        # Status
        if self.is_running:
            if self.is_paused:
                status = "⏸  PAUSED"
                status_color = curses.color_pair(3)
            else:
                status = "▶  RUNNING"
                status_color = curses.color_pair(1)
        else:
            status = "⏹  STOPPED"
            status_color = curses.color_pair(2)
        
        self.stdscr.addstr(panel_y + 2, panel_x + 2, "Status:", curses.A_BOLD)
        self.stdscr.addstr(panel_y + 2, panel_x + 12, status, status_color | curses.A_BOLD)
        
        # Keyboard shortcuts
        self.stdscr.addstr(panel_y + 4, panel_x + 2, "Keyboard Shortcuts:", curses.A_UNDERLINE)
        self.stdscr.addstr(panel_y + 5, panel_x + 4, "[S] Start/Resume", curses.color_pair(1))
        self.stdscr.addstr(panel_y + 6, panel_x + 4, "[P] Pause", curses.color_pair(3))
        self.stdscr.addstr(panel_y + 7, panel_x + 4, "[X] Stop", curses.color_pair(2))
        self.stdscr.addstr(panel_y + 8, panel_x + 4, "[Q] Quit", curses.color_pair(4))
    
    def draw_bet_history(self):
        """Draw bet history table."""
        height, width = self.stdscr.getmaxyx()
        panel_y, panel_x = 13, 2
        panel_width = width - 4
        panel_height = height - 16
        
        self.draw_border(panel_y, panel_x, panel_height, panel_width, "📜 BET HISTORY")
        
        # Table header
        header_y = panel_y + 2
        self.stdscr.addstr(header_y, panel_x + 2, "Time", curses.A_BOLD)
        self.stdscr.addstr(header_y, panel_x + 12, "Amount", curses.A_BOLD)
        self.stdscr.addstr(header_y, panel_x + 26, "Chance", curses.A_BOLD)
        self.stdscr.addstr(header_y, panel_x + 36, "Roll", curses.A_BOLD)
        self.stdscr.addstr(header_y, panel_x + 46, "Result", curses.A_BOLD)
        self.stdscr.addstr(header_y, panel_x + 58, "Profit", curses.A_BOLD)
        
        # Separator
        self.stdscr.addstr(header_y + 1, panel_x + 1, "─" * (panel_width - 2))
        
        # Bet history rows
        for i, bet in enumerate(self.bet_history):
            if i >= panel_height - 5:  # Don't overflow panel
                break
            
            row_y = header_y + 2 + i
            result_color = curses.color_pair(1) if bet['win'] else curses.color_pair(2)
            
            self.stdscr.addstr(row_y, panel_x + 2, bet['time'])
            self.stdscr.addstr(row_y, panel_x + 12, f"{bet['amount']:.8f}")
            self.stdscr.addstr(row_y, panel_x + 26, f"{bet['chance']:.2f}%")
            self.stdscr.addstr(row_y, panel_x + 36, f"{bet['roll']:.2f}")
            self.stdscr.addstr(row_y, panel_x + 46, 
                             "WIN ✓" if bet['win'] else "LOSS ✗", result_color)
            profit_text = f"{bet['profit']:+.8f}"
            self.stdscr.addstr(row_y, panel_x + 58, profit_text, result_color)
    
    def draw_footer(self):
        """Draw footer."""
        height, width = self.stdscr.getmaxyx()
        footer = "DuckDice Bot v4.9.2 | Made with ❤️  | Press Q to quit"
        self.stdscr.addstr(height - 1, (width - len(footer)) // 2, footer, curses.color_pair(4))
    
    def refresh_display(self):
        """Refresh the entire display."""
        self.stdscr.clear()
        self.draw_header()
        self.draw_stats_panel()
        self.draw_controls_panel()
        self.draw_bet_history()
        self.draw_footer()
        self.stdscr.refresh()
    
    def simulate_bet(self):
        """Simulate a single bet (for demo purposes)."""
        import random
        
        bet_amount = Decimal("0.00000100")
        win_chance = 50.0
        roll = random.uniform(0, 100)
        won = roll < win_chance
        profit = bet_amount if won else -bet_amount
        
        # Update stats
        self.balance += profit
        self.profit += profit
        self.bets_placed += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        
        # Add to history
        self.bet_history.append({
            'time': datetime.now().strftime("%H:%M:%S"),
            'amount': bet_amount,
            'chance': win_chance,
            'roll': roll,
            'win': won,
            'profit': profit
        })
    
    def handle_input(self):
        """Handle keyboard input."""
        try:
            key = self.stdscr.getch()
            
            if key == ord('q') or key == ord('Q'):
                return False  # Quit
            elif key == ord('s') or key == ord('S'):
                if not self.is_running:
                    self.is_running = True
                    self.is_paused = False
                elif self.is_paused:
                    self.is_paused = False
            elif key == ord('p') or key == ord('P'):
                if self.is_running:
                    self.is_paused = True
            elif key == ord('x') or key == ord('X'):
                self.is_running = False
                self.is_paused = False
        
        except curses.error:
            pass  # No input available
        
        return True
    
    def run(self):
        """Main loop."""
        while True:
            # Handle input
            if not self.handle_input():
                break
            
            # Simulate betting
            if self.is_running and not self.is_paused:
                self.simulate_bet()
            
            # Refresh display
            self.refresh_display()
            
            # Control update rate
            time.sleep(0.5 if self.is_running else 0.1)


def run_ncurses():
    """Launch the ncurses interface."""
    try:
        curses.wrapper(lambda stdscr: NCursesInterface(stdscr).run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run_ncurses()
