# Interactive Mode - Implementation Complete ✅

**Status**: Fully Functional  
**Date**: January 12, 2026  
**File**: `duckdice_cli.py` (920 lines)

## Overview

Interactive mode provides a guided, user-friendly way to configure and run betting sessions. No command-line arguments or documentation reading required - just answer prompts!

## Features Implemented

### ✅ Core Functionality
- **Zero-Configuration Start** - Just run `python3 duckdice_cli.py` with no arguments
- **7-Step Guided Setup** - Clear progression through all configuration options
- **Smart Defaults** - Sensible defaults for every option (just press Enter!)
- **Input Validation** - Type checking and error recovery for all inputs
- **Visual Grouping** - Strategies organized by risk level (Conservative, Moderate, Aggressive, Specialized)

### ✅ Workflow Steps

#### Step 1: Betting Mode Selection
- **simulation** - Virtual balance testing (recommended for first-time users)
- **live-main** - Real betting with main balance
- **live-faucet** - Real betting with faucet (good for testing with real API)

#### Step 2: Currency Selection
- Supports all 6 currencies: BTC, DOGE, ETH, LTC, BCH, TRX
- Number selection (1-6) or name entry
- Remembers previous choice as default

#### Step 3: Initial Balance (Simulation Only)
- Set starting virtual balance
- Default: 100.0 units
- Supports decimal values

#### Step 4: Strategy Selection
- **18 total strategies** grouped by risk:
  - 🟢 **Conservative**: dalembert, oscars-grind, one-three-two-six
  - 🟡 **Moderate**: fibonacci, labouchere, paroli, fib-loss-cluster
  - 🔴 **Aggressive**: classic-martingale, anti-martingale-streak, streak-hunter
  - 🔵 **Specialized**: 8 advanced strategies (RNG analysis, faucet strategies, etc.)
- Number selection (1-18) or name entry
- Full strategy list displayed for easy reference

#### Step 5: Strategy Configuration
- **Profile Management**:
  - Load previously saved configurations
  - View all available profiles with strategy names
  - Select by number or name
  
- **Parameter Configuration**:
  - Option to configure or use defaults
  - Type-safe parameter entry (int, float, bool, string)
  - Automatic type conversion with fallback to defaults
  - Each parameter shows description and default value
  - Press Enter to accept default for any parameter
  
- **Profile Saving**:
  - Save configured parameters as named profile
  - Reuse profiles in future sessions
  - Stored in `~/.duckdice/profiles.json`

#### Step 6: Risk Management
- **Stop-Loss** - Exit when balance drops by X%
  - Default: -50% (enter as -0.5)
  - Example: -0.3 = stop at -30% loss
  
- **Take-Profit** - Exit when balance increases by X%
  - Default: +100% (enter as 1.0)
  - Example: 0.5 = stop at +50% profit
  
- **Maximum Bets** - Limit total number of bets
  - Default: 0 (unlimited)
  - Example: 100 = stop after 100 bets
  
- **Max Consecutive Losses** - Stop after N losses in a row
  - Default: 0 (unlimited)
  - Example: 5 = stop after 5 consecutive losses

#### Step 7: API Key (Live Mode Only)
- Check for saved API key
- Option to use saved key or enter new one
- Option to save key for future sessions
- Stored securely in `~/.duckdice/config.json`

### ✅ Session Summary
Before starting, displays:
- Betting mode
- Currency
- Starting balance (simulation)
- Selected strategy
- Number of configured parameters
- Risk limits (stop-loss, take-profit, max bets, max losses)
- Final confirmation prompt

### ✅ Technical Implementation

**Code Location**: `duckdice_cli.py` lines 603-840

**Key Functions**:
- `cmd_interactive(args)` - Main interactive mode handler (238 lines)
- `prompt_choice()` - Smart choice selection with validation
- `prompt_with_default()` - Type-safe input with defaults

**Features**:
- Exception handling for EOF and invalid input
- Automatic type conversion (int, float, bool, str)
- Step numbering adjusts based on mode (simulation vs live)
- Profile integration with ConfigManager
- Parameter schema introspection for type safety

## Usage Examples

### Example 1: Quick Start (All Defaults)
```bash
$ python3 duckdice_cli.py

# Just press Enter for all prompts to use defaults:
# - Simulation mode
# - BTC currency
# - 100.0 starting balance
# - First strategy in list
# - Default parameters
# - Default risk limits

# Result: Safe, quick simulation session
```

### Example 2: Custom Configuration
```bash
$ python3 duckdice_cli.py

Select [1-3]: 1              # Simulation
Select [1-6]: 2              # DOGE
Starting balance: 200        # 200 DOGE
Select [1-18]: 17            # streak-hunter
Configure parameters? n      # Use defaults
Stop-loss: -0.2              # -20%
Take-profit: 0.8             # +80%
Maximum bets: 100            # Stop after 100 bets
Max losses: 5                # Stop after 5 consecutive losses
Ready? y                     # Start!
```

### Example 3: Profile Workflow
```bash
$ python3 duckdice_cli.py

# First session - configure and save
Select [1-3]: 1
Select [1-6]: 1
Balance: 50
Select [1-18]: 2             # classic-martingale
Configure parameters? y      # Yes, customize
  base_amount: 0.00001
  chance: 49.5
  is_high: True
  multiplier: 2.0
  max_streak: 8
  reset_on_win: True
Save as profile? y           # Save it!
Profile name: my-martingale

# Future sessions - just load profile
Select [1-3]: 1
Select [1-6]: 1
Balance: 50
Select [1-18]: 2
Use saved profile? y         # Load saved config
Select profile: 1            # my-martingale
# All parameters loaded automatically!
```

## Testing Results

### ✅ All Tests Passing

**Test 1: Default Flow**
- All defaults accepted ✓
- Session starts correctly ✓
- Summary displays correct values ✓

**Test 2: Custom Values**
- All inputs validated ✓
- Type conversion works (int, float, bool, str) ✓
- Invalid input falls back to defaults ✓

**Test 3: Profile Management**
- Profiles saved correctly ✓
- Profiles loaded correctly ✓
- Profile list displays properly ✓
- Parameters restored from profile ✓

**Test 4: Risk Management**
- Percentage formatting correct ✓
- Stop-loss/take-profit values accurate ✓
- Max bets/losses handled correctly ✓
- Zero values (unlimited) work ✓

**Test 5: All 18 Strategies**
- All strategies accessible ✓
- Strategy grouping correct ✓
- Parameter schemas load properly ✓
- Strategy selection by number/name works ✓

## Files Modified

### duckdice_cli.py
- Added `cmd_interactive()` function (lines 603-840)
- Modified `main()` to default to interactive mode when no command provided
- Added interactive subcommand to argument parser
- Improved parameter type handling in configuration flow

### CLI_GUIDE.md
- Updated strategy count (17 → 18)
- Added comprehensive Interactive Mode section with example session
- Updated Quick Start with interactive mode as recommended option

### QUICK_REFERENCE.md
- Added interactive mode to Basic Commands table
- Reordered Quick Start to feature interactive mode first
- Added step-by-step guide for interactive workflow

## Known Limitations

1. **Boolean Parameters** - Still accepts True/False strings, but could be improved with y/n prompts
2. **List Parameters** - Not yet supported (no strategies use lists currently)
3. **Parameter Validation** - Uses try/except for type errors but doesn't validate ranges/constraints
4. **Multi-line Input** - Parameter descriptions sometimes wrap awkwardly on small terminals

## Future Enhancements

- [ ] Add parameter constraints to schema (min/max values, allowed choices)
- [ ] Improve boolean input (convert to y/n prompts)
- [ ] Add ability to edit saved profiles
- [ ] Add profile deletion command
- [ ] Add interactive parameter editing for existing profiles
- [ ] Add color-coded risk indicators for parameter values
- [ ] Add estimated session duration based on settings
- [ ] Add "recommended settings" for each risk level

## Documentation

- **Primary Guide**: `CLI_GUIDE.md` - Full interactive mode walkthrough
- **Quick Reference**: `QUICK_REFERENCE.md` - Interactive mode quick start
- **Code Documentation**: Inline docstrings in `duckdice_cli.py`

## Conclusion

Interactive mode is **production-ready** and provides the best user experience for both beginners and experienced users. The guided workflow, smart defaults, and profile management make it easy to:

- Get started quickly (< 1 minute for first session)
- Experiment safely (simulation mode default)
- Save time (profile reuse)
- Avoid errors (type validation, defaults)
- Learn as you go (descriptions, risk grouping, examples)

**Recommended as primary interface for all users.**

---

*Implementation completed: January 12, 2026*  
*Version: 4.0.0*  
*Total code: 238 lines (in 920-line CLI)*
