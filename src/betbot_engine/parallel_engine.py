"""
Parallel betting engine with thread-safe strategy execution.

Key innovations:
1. Betting requests submitted in parallel (multiple threads)
2. API calls happen simultaneously (non-blocking)
3. Results processed sequentially (queue + lock)
4. Strategy state protected (mutex)
5. Streak logic remains correct (ordered processing)
"""

import time
import threading
import random
from queue import Queue, Empty
from decimal import Decimal
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from duckdice_api.api import DuckDiceAPI
from betbot_engine.engine import EngineConfig
from betbot_strategies.base import StrategyContext, SessionLimits


@dataclass
class BetRequest:
    """A bet request to be submitted"""
    bet_id: int
    spec: Dict[str, Any]
    timestamp: float


@dataclass  
class BetResult:
    """A bet result from API"""
    bet_id: int
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    timestamp: float


class ParallelBettingEngine:
    """
    Thread-safe parallel betting engine.
    
    Architecture:
    - Main thread: Strategy logic (sequential, locked)
    - Worker threads: API calls (parallel, unlocked)
    - Result thread: Process results in order (sequential, locked)
    """
    
    def __init__(
        self,
        api: DuckDiceAPI,
        config: EngineConfig,
        max_concurrent: int = 5  # Max parallel API calls
    ):
        self.api = api
        self.config = config
        self.max_concurrent = max_concurrent
        
        # Thread synchronization
        self.strategy_lock = threading.Lock()  # Protects strategy state
        self.bet_queue = Queue()  # Bets to submit
        self.result_queue = Queue()  # Results to process
        self.stop_event = threading.Event()
        
        # Tracking
        self.next_bet_id = 0
        self.pending_bets = {}  # bet_id -> BetRequest
        self.pending_results = {}  # bet_id -> BetResult (out-of-order buffer)
        self.next_expected_result_id = 0
        
        # RNG for simulation
        self.rng = random.Random(int(time.time() * 1000) & 0xFFFFFFFF)

    def _collect_results(self, block_timeout: float = 0.0) -> int:
        """Move finished worker results into the in-memory order buffer."""
        collected = 0

        if block_timeout > 0:
            try:
                first = self.result_queue.get(timeout=block_timeout)
                self.pending_results[first.bet_id] = first
                collected += 1
            except Empty:
                return 0

        while True:
            try:
                result = self.result_queue.get_nowait()
                self.pending_results[result.bet_id] = result
                collected += 1
            except Empty:
                break

        return collected

    @staticmethod
    def _format_strategy_result(result: BetResult) -> Dict[str, Any]:
        """Normalize API payload for strategy callback."""
        data = result.data or {}
        bet_data = data.get("bet", {}) if isinstance(data, dict) else {}
        user_data = data.get("user", {}) if isinstance(data, dict) else {}
        return {
            "win": bet_data.get("result", False),
            "profit": bet_data.get("profit", 0),
            "balance": user_data.get("balance", 0),
            "amount": bet_data.get("amount", 0),
            "chance": bet_data.get("chance", 0),
            "multiplier": bet_data.get("multiplier", 0),
        }

    def _process_ordered_results(
        self,
        strategy,
        printer: Optional[Callable],
        json_sink: Optional[Callable],
        stop_reason: str,
    ) -> tuple[int, str]:
        """
        Apply buffered results strictly in bet-id order.
        Returns (processed_count, updated_stop_reason).
        """
        processed = 0
        current_stop_reason = stop_reason

        while self.next_expected_result_id in self.pending_results:
            bet_id = self.next_expected_result_id
            result = self.pending_results.pop(bet_id)
            self.pending_bets.pop(bet_id, None)

            with self.strategy_lock:
                if result.success:
                    bet_result = self._format_strategy_result(result)
                    strategy.on_bet_result(bet_result)
                    if json_sink:
                        json_sink(bet_result)
                else:
                    if printer:
                        printer(f"❌ Bet #{result.bet_id} failed: {result.error}")
                    if "insufficient" in str(result.error).lower() or "422" in str(result.error):
                        current_stop_reason = "insufficient_balance"

            processed += 1
            self.next_expected_result_id += 1

            if current_stop_reason == "insufficient_balance":
                break

        return processed, current_stop_reason
        
    def submit_bet_worker(self):
        """Worker thread: Submit bets to API or simulate"""
        while not self.stop_event.is_set():
            try:
                request = self.bet_queue.get(timeout=0.1)
            except Empty:
                continue
                
            try:
                # Check if dry_run mode (simulation)
                if self.config.dry_run:
                    # Simulate bet result
                    simulated = True
                    if request.spec.get("game") == "dice":
                        chance = str(request.spec.get("chance"))
                        p = float(Decimal(chance) / Decimal(100)) if chance else 0.5
                        win = self.rng.random() < p
                        # Payout formula: 99/chance
                        try:
                            payout_val = float(Decimal(99) / Decimal(chance))
                        except Exception:
                            payout_val = 2.0
                        amount_val = float(Decimal(request.spec["amount"]))
                        profit = (payout_val - 1.0) * amount_val if win else -amount_val
                        number = int(self.rng.random() * 10000)
                        
                        # Mock API response structure
                        api_result = {
                            "bet": {
                                "result": win,
                                "profit": profit,
                                "amount": amount_val,
                                "chance": float(chance),
                                "multiplier": payout_val,
                                "number": number
                            },
                            "user": {
                                "balance": 100.0  # Placeholder - actual balance managed by strategy
                            }
                        }
                    else:
                        # Range dice simulation (simplified)
                        range_vals = request.spec.get("range", (0, 10000))
                        is_in = request.spec.get("is_in", True)
                        range_size = abs(range_vals[1] - range_vals[0])
                        chance = (range_size / 10000.0) * 100 if is_in else (1 - range_size / 10000.0) * 100
                        p = chance / 100.0
                        win = self.rng.random() < p
                        payout_val = 99.0 / chance if chance > 0 else 2.0
                        amount_val = float(Decimal(request.spec["amount"]))
                        profit = (payout_val - 1.0) * amount_val if win else -amount_val
                        number = int(self.rng.random() * 10000)
                        
                        api_result = {
                            "bet": {
                                "result": win,
                                "profit": profit,
                                "amount": amount_val,
                                "chance": chance,
                                "multiplier": payout_val,
                                "number": number
                            },
                            "user": {
                                "balance": 100.0
                            }
                        }
                else:
                    # Real API call
                    if request.spec.get("game") == "dice":
                        api_result = self.api.play_dice(
                            symbol=self.config.symbol,
                            amount=request.spec["amount"],
                            chance=request.spec["chance"],
                            is_high=request.spec.get("is_high", True),
                            faucet=request.spec.get("faucet", False)
                        )
                    else:
                        # Range dice
                        r = request.spec.get("range", (0, 0))
                        api_result = self.api.play_range_dice(
                            symbol=self.config.symbol,
                            amount=request.spec["amount"],
                            range_values=[int(r[0]), int(r[1])],
                            is_in=request.spec.get("is_in", True),
                            faucet=request.spec.get("faucet", False)
                        )
                
                # Queue result for processing
                result = BetResult(
                    bet_id=request.bet_id,
                    success=True,
                    data=api_result,
                    error=None,
                    timestamp=time.time()
                )
                self.result_queue.put(result)
                
            except Exception as e:
                # Queue error
                result = BetResult(
                    bet_id=request.bet_id,
                    success=False,
                    data=None,
                    error=str(e),
                    timestamp=time.time()
                )
                self.result_queue.put(result)
            
            finally:
                self.bet_queue.task_done()
    
    def run(
        self,
        strategy,
        printer: Optional[Callable] = None,
        json_sink: Optional[Callable] = None,
        stop_checker: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run parallel betting session.
        
        Flow:
        1. Strategy generates bet (locked)
        2. Bet queued for submission
        3. Workers submit in parallel (unlocked)
        4. Results processed in order (locked)
        5. Strategy updated with result (locked)
        6. Loop
        """
        
        # Get session limits from strategy context
        limits = getattr(strategy, 'ctx', None)
        if limits:
            limits = limits.limits
        
        # Start worker threads
        workers = []
        for i in range(self.max_concurrent):
            worker = threading.Thread(
                target=self.submit_bet_worker,
                name=f"BetWorker-{i}",
                daemon=True
            )
            worker.start()
            workers.append(worker)
        
        stop_reason = "completed"
        start_ts = time.time()
        
        try:
            strategy.on_session_start()
            
            bets_submitted = 0
            bets_processed = 0
            strategy_done = False
            
            while True:
                # Always drain + apply available results first
                self._collect_results()
                processed_now, stop_reason = self._process_ordered_results(
                    strategy, printer, json_sink, stop_reason
                )
                bets_processed += processed_now

                if stop_reason == "insufficient_balance":
                    break

                # Stop checks (do not enqueue new bets after these triggers)
                if not strategy_done:
                    if stop_checker and stop_checker():
                        stop_reason = "user_stop"
                        break
                    if self.stop_event.is_set():
                        stop_reason = "stopped"
                        break

                    if limits:
                        if limits.max_bets is not None and bets_submitted >= limits.max_bets:
                            stop_reason = "max_bets"
                            strategy_done = True
                        elif limits.max_duration_sec and (time.time() - start_ts) >= limits.max_duration_sec:
                            stop_reason = "max_duration"
                            strategy_done = True

                # Strategy exhausted submission path: just wait for remaining in-order results
                if strategy_done:
                    if not self.pending_bets:
                        break
                    self._collect_results(block_timeout=0.05)
                    continue

                # Bound inflight work to avoid unbounded queue growth
                if len(self.pending_bets) >= self.max_concurrent:
                    self._collect_results(block_timeout=0.05)
                    continue

                # Generate next bet (LOCKED - strategy state)
                with self.strategy_lock:
                    bet_spec = strategy.next_bet()
                    if bet_spec is None:
                        stop_reason = "strategy_complete"
                        strategy_done = True
                        continue

                    bet_id = self.next_bet_id
                    self.next_bet_id += 1

                    request = BetRequest(
                        bet_id=bet_id,
                        spec=bet_spec,
                        timestamp=time.time()
                    )

                    self.pending_bets[bet_id] = request
                    self.bet_queue.put(request)
                    bets_submitted += 1

                # Rate limiting (optional)
                if self.config.delay_ms > 0:
                    time.sleep(self.config.delay_ms / 1000.0)

            # Final bounded drain for already-submitted bets
            drain_deadline = time.time() + 5.0
            while self.pending_bets and time.time() < drain_deadline:
                self._collect_results(block_timeout=0.1)
                processed_now, stop_reason = self._process_ordered_results(
                    strategy, printer, json_sink, stop_reason
                )
                bets_processed += processed_now
                if stop_reason == "insufficient_balance":
                    break
            
        except KeyboardInterrupt:
            stop_reason = "user_stop"
        except Exception as e:
            if printer:
                printer(f"❌ Error: {e}")
            stop_reason = "error"
        finally:
            # Cleanup
            self.stop_event.set()
            for worker in workers:
                worker.join(timeout=1.0)
            
            strategy.on_session_end(stop_reason)
        
        # Return result dict (compatible with sequential engine)
        return {
            "stop_reason": stop_reason,
            "bets_placed": bets_processed
        }


# Example usage:
"""
from parallel_engine import ParallelBettingEngine

engine = ParallelBettingEngine(
    api=api,
    config=config,
    max_concurrent=5  # 5 parallel API calls
)

result = engine.run(
    strategy=strategy,
    printer=print,
    json_sink=log_bet,
    stop_checker=lambda: should_stop
)
"""
