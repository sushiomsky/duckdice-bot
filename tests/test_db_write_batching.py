import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from betbot_engine.bet_database import BetDatabase  # noqa: E402


def test_bet_database_flush_persists_batched_writes(tmp_path: Path):
    db_file = tmp_path / "batched.db"
    db = BetDatabase(db_file, commit_every=1000)

    session_id = "test_session_batch"
    db.start_session(
        session_id=session_id,
        strategy_name="test-strat",
        symbol="BTC",
        simulation_mode=True,
        starting_balance=Decimal("100"),
        strategy_params={},
        limits={},
        metadata={},
    )

    for i in range(1, 6):
        db.log_bet(
            session_id=session_id,
            bet_data={
                "symbol": "BTC",
                "strategy": "test-strat",
                "amount": "0.00000001",
                "chance": "49.5",
                "game": "dice",
                "is_high": True,
            },
            result_data={
                "win": (i % 2 == 0),
                "profit": "0.00000001" if i % 2 == 0 else "-0.00000001",
                "number": 1234 + i,
                "payout": "2.0",
                "timestamp": f"2026-03-21T00:00:0{i}",
                "api_raw": {},
            },
            bet_number=i,
            balance=Decimal("100"),
            loss_streak=0,
            simulation_mode=True,
            strategy_state={},
        )

    # Before flush, read path may not see uncommitted write connection state.
    bets_before = db.get_session_bets(session_id)
    assert len(bets_before) <= 5

    db.flush()
    bets_after = db.get_session_bets(session_id)
    assert len(bets_after) == 5

    db.end_session(
        session_id=session_id,
        ending_balance=Decimal("100"),
        stop_reason="done",
        total_bets=5,
        wins=2,
        losses=3,
    )
    db.close()
