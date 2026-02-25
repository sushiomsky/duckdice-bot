from __future__ import annotations
"""
Cold-Number Hunter Strategy

Analyzes ALL previous bets in the local DB for this symbol and bets 0.01%
(exactly one slot out of 10 000) on the numbers that appeared LEAST often
in history — "cold" numbers that are statistically overdue.

Bet sizing philosophy
---------------------
Two phases based on drawdown from starting balance:

  JACKPOT phase  (drawdown < jackpot_threshold_pct)
    Bet bigger — we're hunting a multi-×-balance payday right away.
    base_bet_pct + random jitter.

  RECOVERY phase  (drawdown ≥ jackpot_threshold_pct)
    The jackpot is now the only exit — nothing conservative will dig us
    out. Bet size ramps with the loss multiplier (slow escalation) up to
    max_bet_pct. A single hit at ~9900× is the recovery plan.

On a win: reset multiplier to 1×, immediately refresh the cold map.

Range Dice domain: 0 – 9999 (10 000 slots)
  window width = 1  →  chance = 0.01%  →  multiplier ≈ 9900×
"""
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN   = 10_000
_WIDTH    = 1      # 1 slot = 0.01%
_UNIF_W   = 1.0 / _DOMAIN   # uniform weight per slot


# ── Frequency map ──────────────────────────────────────────────────────────────

class _FreqMap:
    """Slot frequency tracker backed by the bet DB."""

    def __init__(self, history_limit: int) -> None:
        self.history_limit = history_limit
        self.counts: List[int] = [0] * _DOMAIN
        self.total:  int       = 0
        self.loaded: bool      = False

    def load(self, symbol: str) -> int:
        """Load historical rolls for this symbol; return count loaded."""
        try:
            from betbot_engine.bet_database import BetDatabase
            rolls = BetDatabase().get_recent_rolls(symbol=symbol, limit=self.history_limit)
            counts = [0] * _DOMAIN
            for r in rolls:
                slot = min(int(r), _DOMAIN - 1)
                counts[slot] += 1
            self.counts = counts
            self.total  = len(rolls)
            self.loaded = True
            return self.total
        except Exception:
            return 0

    def record(self, slot: int) -> None:
        slot = min(max(slot, 0), _DOMAIN - 1)
        self.counts[slot] += 1
        self.total += 1

    def coldest(self, n: int, rng: Any) -> int:
        """Pick one slot weighted toward the N least-frequently-rolled."""
        if self.total == 0:
            return rng.randint(0, _DOMAIN - _WIDTH)

        # smoothing prevents obsessing over a single never-hit slot
        alpha = max(1.0, self.total / _DOMAIN * 0.10)
        raw   = [1.0 / (c + alpha) for c in self.counts]
        total_raw = sum(raw)
        normed = [w / total_raw for w in raw]

        # Keep only the top-N coldest (highest weight) candidates
        indexed = sorted(enumerate(normed), key=lambda x: x[1], reverse=True)
        top = indexed[:n]
        slots   = [s for s, _ in top]
        weights = [w for _, w in top]
        w_sum   = sum(weights)
        weights = [w / w_sum for w in weights]

        return rng.choices(slots, weights=weights, k=1)[0]


# ── Strategy ───────────────────────────────────────────────────────────────────

@register("cold-number-hunter")
class ColdNumberHunter:
    """0.01% Range Dice hunter: bets on the slot least seen in bet history."""

    @classmethod
    def name(cls) -> str:
        return "cold-number-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Analyzes your full bet history for this symbol and always bets on "
            "the slot (0–9999) that appeared LEAST often — hunting cold numbers "
            "for 9900× payouts. Bet size adapts: bigger in jackpot phase, "
            "escalates slowly in recovery mode."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Extreme",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Very Long",
            recommended_for="Expert",
            pros=[
                "Uses ALL your bet history to pick underrepresented slots",
                "Cold-number selection may exploit short-term RNG variance",
                "~9900× payout — one hit = massive recovery",
                "Adaptive sizing: jackpot hunt then recovery escalation",
                "Automatically refreshes cold map as history grows",
            ],
            cons=[
                "House edge ~1% per bet regardless of cold map",
                "Average ~10 000 bets between wins",
                "Recovery escalation can deplete balance fast",
                "Requires DB history — blind on first session",
                "No statistical guarantee — RNG is designed to be uniform",
            ],
            best_use_case=(
                "Long-running jackpot sessions where you accept high variance "
                "in exchange for the chance of a single massive win covering all losses."
            ),
            tips=[
                "More history = better cold map (run other strategies first)",
                "Set profit_target_pct to lock in a win automatically",
                "Use base_bet_pct ≤ 0.005 to extend session length",
                "cold_pick_n=1 = deterministic coldest slot; higher = more random",
                "Watch the RECOVERY label — it means jackpot is your only exit",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "history_limit": {
                "type": "int",
                "default": 200_000,
                "desc": "Max number of historical bets to load for frequency analysis",
            },
            "cold_pick_n": {
                "type": "int",
                "default": 30,
                "desc": "Pick randomly from the top-N coldest slots (1 = always coldest)",
            },
            "base_bet_pct": {
                "type": "float",
                "default": 0.004,
                "desc": "Base bet as fraction of current balance (0.004 = 0.4%)",
            },
            "jitter": {
                "type": "float",
                "default": 0.30,
                "desc": "Random ±jitter fraction applied to each bet (0.30 = ±30%)",
            },
            "loss_mult": {
                "type": "float",
                "default": 1.06,
                "desc": "Multiply bet by this after each loss (1.06 = +6% per loss)",
            },
            "max_mult": {
                "type": "float",
                "default": 25.0,
                "desc": "Cap on the accumulated loss multiplier",
            },
            "max_bet_pct": {
                "type": "float",
                "default": 0.12,
                "desc": "Hard cap: bet never exceeds this fraction of current balance",
            },
            "jackpot_threshold_pct": {
                "type": "float",
                "default": 15.0,
                "desc": "Drawdown % at which mode switches from JACKPOT to RECOVERY",
            },
            "profit_target_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Auto-stop when profit ≥ this % of starting balance (0 = off)",
            },
            "refresh_every": {
                "type": "int",
                "default": 150,
                "desc": "Re-load cold map from DB every N bets",
            },
        }

    # ──────────────────────────────────────────────────────────────── init

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.history_limit        = int(params.get("history_limit",        200_000))
        self.cold_pick_n          = max(1, int(params.get("cold_pick_n",   30)))
        self.base_bet_pct         = float(params.get("base_bet_pct",       0.004))
        self.jitter               = float(params.get("jitter",             0.30))
        self.loss_mult            = max(1.0, float(params.get("loss_mult", 1.06)))
        self.max_mult             = max(1.0, float(params.get("max_mult",  25.0)))
        self.max_bet_pct          = float(params.get("max_bet_pct",        0.12))
        self.jackpot_threshold    = float(params.get("jackpot_threshold_pct", 15.0)) / 100.0
        self.profit_target_pct    = float(params.get("profit_target_pct",  0.0))
        self.refresh_every        = max(1, int(params.get("refresh_every", 150)))

        self._freq        = _FreqMap(self.history_limit)
        self._cur_mult:   float   = 1.0
        self._starting_bal: Decimal = Decimal("0")
        self._peak_bal:   Decimal = Decimal("0")
        self._live_bal:   Decimal = Decimal("0")
        self._target_bal: Decimal = Decimal("0")
        self._bets:       int     = 0
        self._wins:       int     = 0
        self._biggest_win: Decimal = Decimal("0")
        self._phase:      str     = "JACKPOT"

    # ──────────────────────────────────────────────────────── session hooks

    def on_session_start(self) -> None:
        bal = _dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal
        self._peak_bal     = bal
        self._cur_mult     = 1.0
        self._bets         = 0
        self._wins         = 0
        self._biggest_win  = Decimal("0")
        self._phase        = "JACKPOT"

        if self.profit_target_pct > 0:
            self._target_bal = bal * Decimal(str(1 + self.profit_target_pct / 100))
        else:
            self._target_bal = Decimal("0")

        loaded = self._freq.load(self.ctx.symbol)
        self.ctx.printer(
            f"[cold-number-hunter] started | balance={bal} | "
            f"history={loaded:,} bets loaded | "
            f"cold_pick_n={self.cold_pick_n} | "
            f"base={self.base_bet_pct*100:.3f}% | mult_cap={self.max_mult}×"
            + (f" | target=+{self.profit_target_pct:.0f}%" if self._target_bal else "")
        )

    def on_session_end(self, reason: str) -> None:
        start  = self._starting_bal
        final  = self._live_bal
        pnl    = final - start
        pct    = float(pnl / start * 100) if start else 0.0
        sign   = "+" if pnl >= 0 else ""
        self.ctx.printer(
            f"[cold-number-hunter] session ended ({reason}) | "
            f"bets={self._bets} wins={self._wins} | "
            f"PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%) | "
            f"biggest_win={self._biggest_win:.8f} | phase={self._phase}"
        )

    # ───────────────────────────────────────────────────────────── next bet

    def next_bet(self) -> Optional[BetSpec]:
        # Profit target check
        if self._target_bal > 0 and self._live_bal >= self._target_bal:
            self.ctx.printer(
                f"[cold-number-hunter] 🎯 target reached "
                f"({self._live_bal:.8f} ≥ {self._target_bal:.8f}) — stopping"
            )
            return None

        bal = self._live_bal
        if bal <= 0:
            return None

        # Periodic refresh of cold map
        if self._bets > 0 and self._bets % self.refresh_every == 0:
            loaded = self._freq.load(self.ctx.symbol)
            self.ctx.printer(
                f"[cold-number-hunter] ↻ cold map refreshed — "
                f"{loaded:,} bets | phase={self._phase} | mult={self._cur_mult:.2f}×"
            )

        # Update phase
        drawdown = _drawdown(self._peak_bal, bal)
        old_phase = self._phase
        self._phase = "RECOVERY" if drawdown >= self.jackpot_threshold else "JACKPOT"
        if self._phase != old_phase:
            self.ctx.printer(
                f"[cold-number-hunter] ⚡ phase → {self._phase} "
                f"(drawdown={drawdown*100:.1f}%  bal={bal:.8f})"
            )

        # Bet amount
        amt = self._calc_bet(bal)
        if amt <= 0:
            return None

        # Pick coldest slot
        slot = self._freq.coldest(self.cold_pick_n, self.ctx.rng)

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (slot, slot),   # width=1 → exactly 0.01%
            "is_in":  True,
            "faucet": self.ctx.faucet,
        }

    # ─────────────────────────────────────────────────────────── bet result

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)
        self._bets += 1

        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass
        if self._live_bal > self._peak_bal:
            self._peak_bal = self._live_bal

        # Record this roll in the live frequency map
        roll_raw = result.get("number")
        if roll_raw is not None:
            try:
                self._freq.record(int(float(roll_raw)))
            except Exception:
                pass

        won = bool(result.get("win"))
        if won:
            self._wins    += 1
            self._cur_mult = 1.0
            try:
                profit = Decimal(str(result.get("profit", "0")))
                if profit > self._biggest_win:
                    self._biggest_win = profit
                self.ctx.printer(
                    f"[cold-number-hunter] 🎰 WIN! profit={profit:.8f} "
                    f"bal={self._live_bal:.8f} after {self._bets} bets"
                )
            except Exception:
                pass
            # Immediately refresh cold map after a win
            self._freq.load(self.ctx.symbol)
        else:
            if self.loss_mult > 1.0:
                self._cur_mult = min(self._cur_mult * self.loss_mult, self.max_mult)

    # ──────────────────────────────────────────────────────────── helpers

    def _calc_bet(self, bal: Decimal) -> Decimal:
        """Calculate bet amount with jitter, multiplier, and hard cap."""
        # Base × multiplier
        eff_mult = min(self._cur_mult, self.max_mult)
        base = bal * Decimal(str(self.base_bet_pct)) * Decimal(str(eff_mult))

        # ±jitter random variation
        j = 1.0 + self.ctx.rng.uniform(-self.jitter, self.jitter)
        amt = base * Decimal(str(max(0.01, j)))  # never below 1% of base

        # Hard cap
        cap = bal * Decimal(str(self.max_bet_pct))
        if amt > cap:
            amt = cap

        return amt.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


# ── module-level helpers ────────────────────────────────────────────────────────

def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _drawdown(peak: Decimal, current: Decimal) -> float:
    if peak <= 0:
        return 0.0
    drop = peak - current
    if drop <= 0:
        return 0.0
    return float(drop / peak)
