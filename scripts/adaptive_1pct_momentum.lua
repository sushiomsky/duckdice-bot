-- =========================================================================
-- Adaptive 1% Momentum Cycle Betting Strategy
-- =========================================================================
-- Strategy Phases:
-- 1. NEUTRAL: Default phase waiting for a win. Bet mildly increases on loss.
-- 2. BOOST: Triggered immediately after any win. Fixed duration with an 
--    increased bet to exploit possible win clustering / variance bursts.
-- 3. RECOVERY: Triggered after BOOST phase expires. Fixed duration with a 
--    reduced bet to minimize drawdown and stabilize the bankroll.
-- =========================================================================

-- 1. CONSTANT CHANCE
-- Sets win probability to 1% (~100x payout)
chance = 1.0

-- 2. CONFIGURATION
config = {
    basebet_pct = 0.001,          -- 0.1% of current balance
    boost_multiplier = 2.5,       -- 2.5x basebet during BOOST phase
    recovery_multiplier = 0.5,    -- 0.5x basebet during RECOVERY phase
    loss_increase = 1.05,         -- 5% bet increase on loss during NEUTRAL phase
    
    boost_bets = 50,              -- Duration of BOOST phase (in bets)
    recovery_bets = 50,           -- Duration of RECOVERY phase (in bets)
    
    maxbet_pct = 0.03,            -- Safety hard cap: max bet is 3% of balance
    
    -- Bonus: Anti-tilt and cooldown configuration
    anti_tilt_loss_streak = 250,  -- Extreme loss streak that triggers emergency RECOVERY
    cooldown_bets = 10            -- Cooldown after a full cycle before BOOST can trigger again
}

-- 3. STATE MANAGEMENT
phase = "NEUTRAL"     -- "NEUTRAL" / "BOOST" / "RECOVERY"
phase_counter = 0     -- Bets remaining in current active phase
current_bet = 0       -- Tracks the current dynamic bet amount
loss_streak = 0       -- Tracks consecutive losses for safety triggers
cooldown_counter = 0  -- Tracks bets until BOOST is allowed again

-- Profit Tracking (Bonus)
start_balance = balance or 0
highest_balance = start_balance

-- Dynamically calculate the baseline bet from current balance
function get_basebet()
    return balance * config.basebet_pct
end

-- Initialize the very first bet of the session
function initialize()
    if start_balance == 0 then start_balance = balance end
    current_bet = get_basebet()
    nextbet = current_bet
end

-- =========================================================================
-- BEHAVIOR LOGIC
-- =========================================================================

-- Handle actions upon winning a bet
function handle_win()
    loss_streak = 0
    
    -- Enter BOOST phase instantly, unless we are restricted by cooldown
    if cooldown_counter <= 0 then
        if phase ~= "BOOST" then
            print("[EVENT] WIN → BOOST")
        end
        -- Jump to BOOST phase and apply boosted betting
        phase = "BOOST"
        phase_counter = config.boost_bets
        current_bet = get_basebet() * config.boost_multiplier
    else
        -- If on cooldown, just recalculate standard basebet
        current_bet = get_basebet()
    end
end

-- Handle actions upon losing a bet
function handle_loss()
    loss_streak = loss_streak + 1
    
    if phase == "NEUTRAL" then
        -- Mildly increase the bet to softly recoup some losses while waiting for a hit
        current_bet = current_bet * config.loss_increase
    elseif phase == "BOOST" then
        -- Maintain the aggressive fixed multiplier during the BOOST window
        current_bet = get_basebet() * config.boost_multiplier
    elseif phase == "RECOVERY" then
        -- Maintain the conservative reduced bet to weather drawdowns
        current_bet = get_basebet() * config.recovery_multiplier
    end
end

-- Check and process any necessary shifts in phases
function update_phase()
    local old_phase = phase
    
    -- We only decrement counter if we are in an active duration-based phase
    if phase ~= "NEUTRAL" then
        phase_counter = phase_counter - 1
        
        -- BOOST has expired -> Transition to RECOVERY
        if phase == "BOOST" and phase_counter <= 0 then
            phase = "RECOVERY"
            phase_counter = config.recovery_bets
            current_bet = get_basebet() * config.recovery_multiplier
            print("[EVENT] BOOST → RECOVERY")
        
        -- RECOVERY has expired -> Transition to NEUTRAL
        elseif phase == "RECOVERY" and phase_counter <= 0 then
            phase = "NEUTRAL"
            phase_counter = 0
            current_bet = get_basebet()
            cooldown_counter = config.cooldown_bets -- Start cooldown to pace the system
            print("[EVENT] RECOVERY → NEUTRAL")
        end
    end
    
    -- Process the cooldown tick
    if cooldown_counter > 0 then
        cooldown_counter = cooldown_counter - 1
    end
end

-- Check system boundaries to prevent ruin
function apply_safety()
    local max_bet_allowed = balance * config.maxbet_pct
    
    -- Hard Cap: if current bet exceeds 3% (or configured max) of balance, reset instantly
    if current_bet > max_bet_allowed then
        print("[SAFETY] Bet capped! Exceeded maxbet_pct. Resetting to basebet.")
        current_bet = get_basebet()
        -- Reset phase state to calm down volatility
        phase = "NEUTRAL"
        phase_counter = 0
    end
    
    -- Anti-tilt: if loss streak is devastating, force RECOVERY state to stall out the bad run
    if loss_streak >= config.anti_tilt_loss_streak and phase ~= "RECOVERY" then
        print("[SAFETY] Anti-tilt activated: Extreme loss streak. Forcing RECOVERY.")
        phase = "RECOVERY"
        phase_counter = config.recovery_bets
        current_bet = get_basebet() * config.recovery_multiplier
        loss_streak = 0 -- Reset slightly so it doesn't trigger every single bet
    end
    
    -- Baseline sanity check: can't bet more than what we actually have
    if current_bet > balance then
        current_bet = balance
    end
end

-- Output structured debug information
function debug_log()
    if balance > highest_balance then highest_balance = balance end
    local profit = balance - start_balance
    -- Format helps align output columns neatly in the DiceBot console
    print(string.format("[PHASE] %-8s | Bet: %.8f | Balance: %.8f | Profit: %+.8f", 
        phase, current_bet, balance, profit))
end

-- =========================================================================
-- MAIN LOOP (Executed by DiceBot after every single roll)
-- =========================================================================
function dobet()
    -- Initialize on the very first execution
    if nextbet == 0 or start_balance == 0 then
        initialize()
        return
    end

    -- Process Result logic
    if win then
        handle_win()
    else
        handle_loss()
    end

    -- Update current phase timers and transitions
    update_phase()
    
    -- Enforce balance safety constraints
    apply_safety()

    -- Bind our calculated bet to the DiceBot's reserved `nextbet` variable
    nextbet = current_bet
    
    -- Log session state
    debug_log()
end
