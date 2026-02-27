from __future__ import annotations
"""
Dynamic Phase Hunter — Tiered Profit Target Recovery Strategy

Core mechanic: win chance ~1% (≈99× multiplier).  Each bet is sized so that
a single win pays back ALL accumulated cycle losses PLUS the current dynamic
profit target.  As consecutive losses mount, the profit target steps down
through five tiers, shifting from aggressive growth to pure capital recovery.

Bet formula (derived from DuckDice native multiplier 98/chance_pct):

    M   = 98.0 / chance_pct              ← net profit multiplier per unit bet
    bet = (A + T × S) / M

Where:
    A = accumulated losses since last win (sum of all losing bets this cycle)
    S = cycle-start balance (balance at the moment L was last reset to 0)
    T = current profit target as a fraction of S  (phase-dependent)

Guarantee: if the next bet wins  →  net profit = A + T × S  ✓
           new balance           =  S − A  +  A + T × S  =  S × (1 + T)  ✓

Five tiers (default thresholds and targets):
    Tier 0  L = 0          GREED-A    target +250%  (S × 2.50)
    Tier 1  L = 1–3        GREED-B    target +150%  (S × 1.50)
    Tier 2  L = 4–7        RECOVERY   target  +75%  (S × 0.75)
    Tier 3  L = 8–15       SALVAGE-A  target  +25%  (S × 0.25)
    Tier 4  L = 16+        SALVAGE-B  target    0%  (break-even only)

All five targets and the four loss-count thresholds are user-configurable.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_MIN_BET = Decimal("0.00000001")

_TIER_NAMES  = ["GREED-A", "GREED-B", "RECOVERY", "SALVAGE-A", "SALVAGE-B"]
_TIER_ICONS  = ["💰",       "📈",       "⚖️ ",       "🛟 ",        "🆘 "]


@register("dynamic-phase-hunter")
class DynamicPhaseHunter:
    """
    Starts each cycle in maximum-greed mode (+250% target) and steps down
    through recovery and salvage phases as losses accumulate.  Bet sizing
    is mathematically exact: one win always covers losses + current target.
    """

    # ── Class-level API ────────────────────────────────────────────────────

    @classmethod
    def name(cls) -> str:
        return "dynamic-phase-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Tiered profit-target hunter at ~1% win chance.  Starts at +250% target, "
            "steps down to break-even as losses mount.  Each bet is sized to cover "
            "all accumulated losses plus the current phase target in a single hit."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Medium-Large",
            volatility="Extreme",
            time_to_profit="Rare but Large",
            recommended_for="Advanced",
            pros=[
                "Each bet is mathematically exact: one win always fully covers losses + target",
                "Five-tier cascade prevents irrational overbetting in deep streaks",
                "Early hits produce +150% to +250% balance jumps",
                "Late-stage bets shift to pure capital recovery, not hopeless profit chasing",
                "Automatic balance scaling — cycle start updates after every win",
                "Hard bet cap prevents any single bet from wiping the account",
                "Clean phase-transition logging with expected payouts at each stage",
            ],
            cons=[
                "Very high variance — long loss streaks are statistically common at 1% chance",
                "Deep salvage phase still requires significant bankroll depth",
                "Not EV-positive; expected value is negative due to house edge",
                "A complete run-through of all tiers without a win is possible",
                "Requires patience and discipline during extended cold periods",
            ],
            best_use_case=(
                "Players wanting structured high-variance play with explicit phase awareness. "
                "Set stop-loss at -20% to -30% of starting balance. "
                "The hard bet cap (max_bet_pct) is the primary risk control — keep it ≤ 0.25."
            ),
            tips=[
                "chance=1.00 gives ~98x net multiplier — good balance of depth vs hit rate",
                "chance=0.50 gives ~196x — rarer hits but larger single-bet gains",
                "Raise max_bet_pct to 0.30–0.40 for more aggressive progression",
                "Lower max_bet_pct to 0.15–0.20 for more conservative play",
                "soft_stop_losses=40–60 is a good psychological checkpoint",
                "compound_factor=1.05 grows the effective base bet by 5% per cycle",
                "All five tier targets are individually configurable",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            # Core
            "chance": {
                "type": "float", "default": 1.00,
                "desc": "Win chance % (1.00% = ~98x net multiplier; 0.50% = ~196x)",
            },
            "is_high": {
                "type": "bool", "default": True,
                "desc": "Bet High (True) or Low (False)",
            },
            # Profit targets per tier (as multiplier of cycle-start balance)
            "target_greed_a": {
                "type": "float", "default": 2.50,
                "desc": "Tier 0 (L=0): profit target as × of cycle-start balance",
            },
            "target_greed_b": {
                "type": "float", "default": 1.50,
                "desc": "Tier 1 (L=1–3): profit target",
            },
            "target_recovery": {
                "type": "float", "default": 0.75,
                "desc": "Tier 2 (L=4–7): profit target",
            },
            "target_salvage_a": {
                "type": "float", "default": 0.25,
                "desc": "Tier 3 (L=8–15): profit target",
            },
            "target_salvage_b": {
                "type": "float", "default": 0.00,
                "desc": "Tier 4 (L=16+): break-even only (0% profit)",
            },
            # Loss-count tier boundaries
            "tier1_at_loss": {
                "type": "int", "default": 1,
                "desc": "Enter Tier 1 (GREED-B) at this consecutive loss count",
            },
            "tier2_at_loss": {
                "type": "int", "default": 4,
                "desc": "Enter Tier 2 (RECOVERY) at this consecutive loss count",
            },
            "tier3_at_loss": {
                "type": "int", "default": 8,
                "desc": "Enter Tier 3 (SALVAGE-A) at this consecutive loss count",
            },
            "tier4_at_loss": {
                "type": "int", "default": 16,
                "desc": "Enter Tier 4 (SALVAGE-B / break-even) at this loss count",
            },
            # Risk controls
            "max_bet_pct": {
                "type": "float", "default": 0.25,
                "desc": "Hard stop: calculated bet may not exceed this fraction of current balance",
            },
            "soft_stop_losses": {
                "type": "int", "default": 50,
                "desc": "Log a prominent warning after this many consecutive losses (0 = off)",
            },
            # Optional progressive base scaling
            "compound_factor": {
                "type": "float", "default": 1.00,
                "desc": "Multiply cycle-start balance by this after each profitable win (>1 = growing aggressively; 1.0 = natural scaling only)",
            },
        }

    # ── Init ───────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        def _f(k, d): return float(params.get(k, d))
        def _i(k, d): return int(params.get(k, d))

        self._chance          = _f("chance",          1.00)
        self._is_high         = bool(params.get("is_high", True))

        # Five tier targets
        self._targets: List[float] = [
            _f("target_greed_a",  2.50),
            _f("target_greed_b",  1.50),
            _f("target_recovery", 0.75),
            _f("target_salvage_a",0.25),
            _f("target_salvage_b",0.00),
        ]
        # Four loss-count boundaries (tier transitions happen AT these counts)
        self._tier_at: List[int] = [
            _i("tier1_at_loss", 1),
            _i("tier2_at_loss", 4),
            _i("tier3_at_loss", 8),
            _i("tier4_at_loss", 16),
        ]

        self._max_bet_pct      = _f("max_bet_pct",       0.25)
        self._soft_stop_losses = _i("soft_stop_losses",  50)
        self._compound_factor  = _f("compound_factor",   1.00)

        # Net profit multiplier: profit = bet × M
        self._M = 98.0 / self._chance

        self._reset_session()

    def _reset_session(self) -> None:
        self._L:          int     = 0             # consecutive loss count
        self._A:          Decimal = Decimal("0")  # accumulated cycle losses
        self._S:          Decimal = Decimal("0")  # cycle-start balance
        self._H:          int     = 0             # total session bets
        self._cycles:     int     = 0             # completed win cycles
        self._best_pct:   float   = 0.0           # best single win % gain
        self._hard_stop:  bool    = False
        self._prev_tier:  int     = -1            # for transition detection
        self._session_start: Decimal = Decimal("0")
        self._peak_bal:   Decimal = Decimal("0")

    # ── Tier logic ─────────────────────────────────────────────────────────

    def _get_tier(self, L: int) -> int:
        """Return tier index 0–4 for a given consecutive loss count."""
        for i, threshold in enumerate(self._tier_at):
            if L < threshold:
                return i
        return 4  # Tier 4: SALVAGE-B

    def _tier_info(self, tier: int) -> Tuple[str, str, float]:
        """Return (name, icon, profit_target_fraction) for a tier."""
        return _TIER_NAMES[tier], _TIER_ICONS[tier], self._targets[tier]

    # ── Bet calculation ────────────────────────────────────────────────────

    def _calc_bet(self) -> Tuple[Decimal, int, float]:
        """
        Returns (bet_amount, tier, profit_target_fraction).

        Derivation:
            net_profit_on_win = bet × M
            Set net_profit_on_win = A + T × S   (cover losses + earn target)
            ⟹  bet = (A + T × S) / M
        """
        tier = self._get_tier(self._L)
        T    = self._targets[tier]

        required = self._A + Decimal(str(T)) * self._S
        # Avoid non-positive required (can't happen normally; guard for edge cases)
        if required <= Decimal("0"):
            required = _MIN_BET * Decimal(str(self._M))

        bet = required / Decimal(str(self._M))
        bet = max(_MIN_BET, bet)

        # Hard cap: never exceed max_bet_pct of current balance
        current = Decimal(self.ctx.current_balance_str() or self.ctx.starting_balance or "1")
        cap     = current * Decimal(str(self._max_bet_pct))
        if bet > cap:
            self._hard_stop = True

        return bet, tier, T

    # ── Session hooks ──────────────────────────────────────────────────────

    def on_session_start(self) -> None:
        self._reset_session()
        bal = Decimal(self.ctx.starting_balance or "0")
        self._S              = bal
        self._session_start  = bal
        self._peak_bal       = bal

        # Show opening bet preview
        bet_preview, _, _ = self._calc_bet()
        expected_win = float(bet_preview) * self._M
        p = self.ctx.printer
        p(f"\n{'═'*62}")
        p(f"  🎯  DYNAMIC PHASE HUNTER")
        p(f"{'═'*62}")
        p(f"  Win chance   : {self._chance:.2f}%  (net multiplier {self._M:.1f}×)")
        p(f"  Cycle balance: {float(bal):.8f}")
        p(f"  Opening bet  : {float(bet_preview):.8f}  "
          f"→ win now: +{expected_win:.6f}  (+{self._targets[0]*100:.0f}%)")
        p(f"  Hard cap     : {self._max_bet_pct:.0%} of current balance per bet")
        p(f"  Tier boundaries: L<{self._tier_at[0]} / L<{self._tier_at[1]} / "
          f"L<{self._tier_at[2]} / L<{self._tier_at[3]} / L≥{self._tier_at[3]}")
        p(f"  Profit targets : {' → '.join(f'{t*100:.0f}%' for t in self._targets)}")
        p(f"{'═'*62}\n")

    # ── Core loop ──────────────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        if self._hard_stop:
            self.ctx.printer(
                f"🛑 HARD STOP: calculated bet exceeds {self._max_bet_pct:.0%} of balance. "
                f"Session ending. (L={self._L}, A={float(self._A):.8f})"
            )
            return None

        self._H += 1

        # Soft-stop warning (non-fatal)
        if self._soft_stop_losses > 0 and self._L == self._soft_stop_losses:
            self.ctx.printer(
                f"⚠️  SOFT STOP WARNING: {self._L} consecutive losses.  "
                f"Accumulated: {float(self._A):.8f}.  "
                f"Consider stopping manually."
            )

        bet, tier, T = self._calc_bet()

        # Hard stop triggered inside _calc_bet — abort this bet too
        if self._hard_stop:
            self.ctx.printer(
                f"🛑 HARD STOP: bet {float(bet):.8f} would exceed "
                f"{self._max_bet_pct:.0%} of balance. "
                f"(L={self._L}, A={float(self._A):.8f})"
            )
            return None

        # Log tier transitions and every 10 bets
        if tier != self._prev_tier:
            self._log_tier_transition(tier, T, bet)
            self._prev_tier = tier
        elif self._H % 10 == 1:
            self._log_status(tier, T, bet)

        return BetSpec(
            game="dice",
            amount=str(bet),
            chance=f"{self._chance:.4f}",
            is_high=self._is_high,
        )

    # ── Result processing ──────────────────────────────────────────────────

    def on_bet_result(self, result: BetResult) -> None:
        win     = bool(result.get("win", False))
        profit  = Decimal(str(result.get("profit", "0")))
        balance = Decimal(str(result.get("balance", "0") or "0"))

        if balance > self._peak_bal:
            self._peak_bal = balance

        self.ctx.recent_results.append(result)

        if win:
            self._on_win(profit, balance)
        else:
            # Track loss: profit field is negative on loss, so -profit = bet amount
            lost_amount = abs(profit) if profit < 0 else (self._A * 0 + abs(profit))
            self._A += lost_amount
            self._L += 1

    def _on_win(self, profit: Decimal, balance: Decimal) -> None:
        self._cycles += 1
        gain_on_S = float(profit) / max(float(self._S), 1e-12) * 100.0

        if gain_on_S > self._best_pct:
            self._best_pct = gain_on_S

        p = self.ctx.printer
        p(f"\n{'★'*62}")
        p(f"  💥  HIT!  Cycle #{self._cycles}  (was in {_TIER_NAMES[self._get_tier(self._L)]})")
        p(f"  Losses recovered : {self._L}  bets  ({float(self._A):.8f} total)")
        p(f"  Net profit       : +{float(profit):.8f}  (+{gain_on_S:.1f}% of cycle start)")
        p(f"  New balance      : {float(balance):.8f}")
        p(f"{'★'*62}\n")

        # Update cycle-start: scale by compound_factor if profitable
        new_S = balance
        if self._compound_factor > 1.0 and float(profit) > 0:
            new_S = balance * Decimal(str(self._compound_factor))
            p(f"  📊 Compound factor {self._compound_factor}× applied: "
              f"effective S = {float(new_S):.8f}")

        # Reset cycle state
        self._S    = new_S
        self._L    = 0
        self._A    = Decimal("0")
        self._prev_tier = -1  # force transition log on next bet

    # ── Logging helpers ────────────────────────────────────────────────────

    def _log_tier_transition(self, tier: int, T: float, bet: Decimal) -> None:
        name, icon, _ = self._tier_info(tier)
        win_profit  = float(bet) * self._M
        win_total   = float(self._S) * (1.0 + T) if T > 0 else float(self._S - self._A + bet * Decimal(str(self._M)))
        p = self.ctx.printer

        if tier == 0:
            p(f"{icon} [{name}]  Cycle start — S={float(self._S):.8f}  "
              f"Target: +{T*100:.0f}%  "
              f"Bet: {float(bet):.8f}  →  win=+{win_profit:.6f}")
        else:
            p(f"{icon} [{name}]  L={self._L}  A={float(self._A):.8f}  "
              f"Target now: +{T*100:.0f}% of S  "
              f"Bet: {float(bet):.8f}  →  win=+{win_profit:.6f}")

    def _log_status(self, tier: int, T: float, bet: Decimal) -> None:
        name, icon, _ = self._tier_info(tier)
        win_profit = float(bet) * self._M
        current_bal = Decimal(self.ctx.current_balance_str() or self.ctx.starting_balance or "0")
        bet_pct = float(bet) / max(float(current_bal), 1e-12) * 100.0
        self.ctx.printer(
            f"{icon} bet#{self._H:<5}  [{name}]  L={self._L}  "
            f"A={float(self._A):.6f}  bet={float(bet):.8f}({bet_pct:.2f}%)  "
            f"→win=+{win_profit:.6f}(+{T*100:.0f}%)"
        )

    # ── Session end ────────────────────────────────────────────────────────

    def on_session_end(self, reason: str) -> None:
        final    = Decimal(self.ctx.current_balance_str() or self.ctx.starting_balance or "0")
        pnl      = final - self._session_start
        pnl_pct  = float(pnl) / max(float(self._session_start), 1e-12) * 100.0
        peak_pct = float(self._peak_bal - self._session_start) / max(float(self._session_start), 1e-12) * 100.0

        tier       = self._get_tier(self._L)
        name, _, _ = self._tier_info(tier)

        p = self.ctx.printer
        p(f"\n{'═'*62}")
        p(f"  🏁  DYNAMIC PHASE HUNTER — SESSION END")
        p(f"{'═'*62}")
        p(f"  Reason         : {reason}")
        p(f"  Total bets     : {self._H}")
        p(f"  Win cycles     : {self._cycles}")
        p(f"  Best hit       : +{self._best_pct:.1f}% of cycle start")
        p(f"  Final phase    : [{name}]  L={self._L}")
        p(f"  Open cycle A   : {float(self._A):.8f}  (unrecovered losses)")
        p(f"  Peak balance   : {float(self._peak_bal):.8f}  (+{peak_pct:.1f}%)")
        p(f"  Session PnL    : {float(pnl):+.8f}  ({pnl_pct:+.2f}%)")
        p(f"  Final balance  : {float(final):.8f}")
        p(f"{'═'*62}\n")
