# Faucet Mode Implementation Plan

## Overview
Add complete faucet mode support to DuckDice Bot based on faucetplay project.

## Key Differences: Main vs Faucet Mode
- **House Edge**: Main 1%, Faucet 3%
- **Balances**: Separate main and faucet balances (don't share)
- **Auto-claim**: Faucet needs periodic claiming with browser headers/cookies

## Implementation Tasks

### 1. API Client Enhancement (`src/duckdice_api/api.py`)
- [x] Already has `faucet` parameter in `play_dice()` method
- [ ] Add `claim_faucet()` method with cookie support
- [ ] Add `get_faucet_balance()` helper
- [ ] Add `get_main_balance()` helper
- [ ] Update `get_user_info()` to return faucet balances separately

### 2. Faucet Manager Module (`src/faucet_manager/`)
- [ ] Create `faucet_manager.py` with auto-claim logic
- [ ] Cookie storage and management
- [ ] Claim cooldown tracking (60 seconds)
- [ ] Browser headers configuration
- [ ] Auto-claim thread/scheduler

### 3. GUI Updates (`duckdice_gui_ultimate.py`)
- [ ] Add mode selector (Main / Faucet) to Quick Bet tab
- [ ] Add mode selector to Auto Bet tab
- [ ] Display separate balances for main/faucet
- [ ] Add "Claim Faucet Now" button
- [ ] Auto-claim toggle switch
- [ ] Faucet settings dialog (cookie, interval)
- [ ] Visual indicator for faucet mode (different color?)

### 4. Settings/Configuration
- [ ] Cookie storage for faucet claiming
- [ ] Auto-claim interval setting
- [ ] Last claim time tracking
- [ ] Mode preference saving

### 5. Simulation Mode
- [ ] Support faucet mode in simulation
- [ ] Use 3% house edge for faucet simulations
- [ ] Separate simulation balances

### 6. TLE (Time Limited Event) Support
- [ ] Research TLE API
- [ ] Add TLE mode option
- [ ] Display TLE status/timing

## Implementation Order
1. API client enhancements
2. Faucet manager module
3. Settings dialog for cookies
4. GUI mode selectors
5. Auto-claim integration
6. Testing and polish

## Files to Create/Modify
- `src/faucet_manager/__init__.py`
- `src/faucet_manager/faucet_manager.py`
- `src/faucet_manager/cookie_manager.py`
- `src/duckdice_api/api.py` (modify)
- `duckdice_gui_ultimate.py` (modify)
- Settings dialog component

## Testing Checklist
- [ ] Faucet claiming works
- [ ] Auto-claim respects cooldown
- [ ] Main/faucet balances don't mix
- [ ] Mode switching updates house edge
- [ ] Simulation uses correct edge
- [ ] Cookie storage persists
