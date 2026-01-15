#!/usr/bin/env python3
"""
DuckDice Bot TUI Launcher

Launch the Terminal User Interface for DuckDice Bot.
Supports both modern Textual and classic ncurses interfaces.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="🎲 DuckDice Bot - Terminal User Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Launch modern Textual interface (default)
  %(prog)s --ncurses    # Launch classic ncurses interface
  %(prog)s --help       # Show this help message

Keyboard Controls:
  Textual Interface:
    Ctrl+S - Start/Resume betting
    Ctrl+P - Pause betting  
    Ctrl+X - Stop betting
    Ctrl+Q - Quit

  Ncurses Interface:
    S - Start/Resume betting
    P - Pause betting
    X - Stop betting
    Q - Quit
        """
    )
    
    parser.add_argument(
        '--ncurses',
        action='store_true',
        help='Use classic ncurses interface (lightweight)'
    )
    
    parser.add_argument(
        '--textual',
        action='store_true',
        help='Use modern Textual interface (default)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='DuckDice Bot v4.9.2'
    )
    
    args = parser.parse_args()
    
    # Determine which interface to use
    use_ncurses = args.ncurses
    use_textual = args.textual or not use_ncurses  # Default to Textual
    
    try:
        if use_ncurses:
            print("Launching classic ncurses interface...")
            from src.interfaces.tui.ncurses_interface import run_ncurses
            run_ncurses()
        else:
            print("Launching modern Textual interface...")
            from src.interfaces.tui.textual_interface import run_tui
            run_tui()
    
    except ImportError as e:
        if 'textual' in str(e).lower() and not use_ncurses:
            print("❌ Textual not installed. Install with: pip install textual")
            print("   Or use classic ncurses interface: duckdice-tui --ncurses")
            sys.exit(1)
        else:
            print(f"❌ Import error: {e}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
