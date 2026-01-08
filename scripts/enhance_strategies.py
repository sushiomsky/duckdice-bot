#!/usr/bin/env python3
"""
Script to add enhanced metadata to all strategy files.
Adds metadata() classmethod with rich information for each strategy.
"""

# Strategy metadata definitions
STRATEGY_METADATA = {
    'labouchere': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Moderate",
            recommended_for="Advanced",
            pros=[
                "Flexible sequence allows customization",
                "Can end profitably even with more losses than wins",
                "Mathematical elegance for strategic minds",
                "Completing sequence guarantees profit",
                "Good control over bet sizing"
            ],
            cons=[
                "Sequence can grow long during losing streaks",
                "Complex to track and manage mentally",
                "Not intuitive for beginners",
                "Can lead to large bets if unlucky"
            ],
            best_use_case="For experienced players who enjoy strategic depth. Works well for patient grinders.",
            tips=[
                "Start with short sequences [1,2,3] or [1,2,2,1]",
                "Longer sequences = more risk but slower growth",
                "Track your sequence carefully during play",
                "Consider max sequence length limit (e.g., 10 numbers)",
                "Works best with 48-50% win rate",
                "Take breaks when sequence gets long (5+ numbers)"
            ]
        )'''
    },
    'oscars-grind': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Low",
            time_to_profit="Slow",
            recommended_for="Beginners",
            pros=[
                "Extremely conservative approach",
                "Named after legendary gambler Oscar",
                "Only increases bet after wins",
                "Small consistent profits per cycle",
                "Very low risk of ruin"
            ],
            cons=[
                "Painfully slow profit accumulation",
                "Requires extreme patience",
                "Multiple sessions needed for meaningful profit",
                "Can be frustrating during losing streaks"
            ],
            best_use_case="Perfect for ultra-conservative players. Great for learning betting systems.",
            tips=[
                "Set profit_target at 1-2x base_amount for quick cycles",
                "Extremely safe for bankroll preservation",
                "Combine with 48-50% win probability",
                "Great for building confidence with new strategies",
                "Max bet should be 10-20x base amount",
                "Perfect for multi-session long-term play"
            ]
        )'''
    },
    'kelly-capped': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Experts",
            pros=[
                "Mathematically optimal bet sizing",
                "Adapts to actual win rates dynamically",
                "Based on proven Kelly Criterion theory",
                "EWMA smoothing reduces variance",
                "Self-adjusting to game conditions"
            ],
            cons=[
                "Complex mathematics may confuse beginners",
                "Requires understanding of probability theory",
                "House edge makes true Kelly often suggest zero bet",
                "Parameter tuning requires expertise",
                "Can be overly conservative"
            ],
            best_use_case="For mathematically-inclined experts. Experimental research tool.",
            tips=[
                "Start with kelly_cap at 0.25 (quarter Kelly)",
                "Adjust house_edge to match actual game edge",
                "Set bankroll_hint accurately for correct sizing",
                "Monitor EWMA winrate adjustments carefully",
                "This is experimental - use with caution",
                "Best for those who understand Kelly Criterion deeply"
            ]
        )'''
    },
    'anti-martingale-streak': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Quick",
            recommended_for="Intermediate",
            pros=[
                "Capitalizes on winning streaks",
                "Limited downside on losses",
                "Exciting during hot streaks",
                "Base bet stays constant on losses",
                "Better risk profile than Martingale"
            ],
            cons=[
                "Requires winning streaks to profit",
                "Loses all streak progress on single loss",
                "Highly dependent on luck/variance",
                "Frustrating when streaks break early"
            ],
            best_use_case="For players who want to ride winning streaks. Good for short burst sessions.",
            tips=[
                "Set realistic streak_target (3-5 is optimal)",
                "Exit after hitting 1-2 max streaks",
                "Works best with 45-50% win probability",
                "Consider 'partial reset' after breaking streak",
                "Great for bonus hunting strategies",
                "Use strict session time limits"
            ]
        )'''
    },
    'one-three-two-six': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Medium",
            time_to_profit="Quick",
            recommended_for="Beginners",
            pros=[
                "Fixed simple sequence: 1-3-2-6 units",
                "Easy to understand and follow",
                "Limited risk with profit lock-in",
                "Completing sequence = 12 units profit",
                "Great for beginners learning progressions"
            ],
            cons=[
                "Requires 4 consecutive wins for full profit",
                "Any loss resets to start",
                "4-win streaks are rare (~6% at 49.5%)",
                "Can be frustrating with bad timing"
            ],
            best_use_case="Perfect introduction to positive progression systems. Beginner-friendly.",
            tips=[
                "Classic sequence is 1-3-2-6 (don't modify)",
                "Lock in profit after completing sequence",
                "With 49.5% chance, expect 1 complete per ~16 attempts",
                "Celebrate full sequence completions!",
                "Consider stopping after 1-2 completions",
                "Great for understanding positive progressions"
            ]
        )'''
    },
    'faucet-cashout': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very Low",
            bankroll_required="None (Free)",
            volatility="Low",
            time_to_profit="Slow",
            recommended_for="Beginners",
            pros=[
                "Zero risk - uses free faucet bets",
                "Perfect for learning without deposit",
                "Slow grind but absolutely free",
                "Great for testing strategies",
                "Can build up from nothing"
            ],
            cons=[
                "Extremely slow progress",
                "Requires huge time investment",
                "Faucet limits may apply",
                "Not realistic profit strategy",
                "Better options exist for real play"
            ],
            best_use_case="Learning tool for absolute beginners. Test platform features risk-free.",
            tips=[
                "Be patient - this is a marathon not a sprint",
                "Use to learn platform mechanics",
                "Don't expect meaningful profits",
                "Great for strategy testing",
                "Transition to real betting once comfortable",
                "Set realistic cashout targets (e.g., 0.0001)"
            ]
        )'''
    },
    'fib-loss-cluster': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Moderate",
            recommended_for="Advanced",
            pros=[
                "Fibonacci with cluster detection",
                "Adapts to losing patterns",
                "More sophisticated than basic Fibonacci",
                "Can reduce damage from bad variance",
                "Good for pattern-aware betting"
            ],
            cons=[
                "Complex logic harder to understand",
                "Cluster detection adds overhead",
                "Still vulnerable to sustained bad luck",
                "Requires parameter tuning",
                "Not proven more effective than basic Fib"
            ],
            best_use_case="For advanced players who believe in pattern detection. Experimental.",
            tips=[
                "Tune cluster_size to game characteristics",
                "Monitor cluster detection effectiveness",
                "Combine with strict stop-loss",
                "Test in simulation mode first",
                "May not outperform basic Fibonacci",
                "For players who enjoy complexity"
            ]
        )'''
    },
    'max-wager-flow': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Large",
            volatility="Very High",
            time_to_profit="Quick",
            recommended_for="Experts",
            pros=[
                "Aggressive profit targeting",
                "Can generate quick wins",
                "Maximum utilization of bankroll",
                "Exciting high-action play",
                "Good for bonus clearing"
            ],
            cons=[
                "Very high risk of ruin",
                "Not for risk-averse players",
                "Can lose bankroll quickly",
                "Requires nerves of steel",
                "House edge amplified by bet size"
            ],
            best_use_case="High-risk/high-reward play. Only for experienced players with large bankrolls.",
            tips=[
                "Set very strict stop-loss (10-20% max)",
                "Use only with money you can afford to lose",
                "Exit immediately on profit target",
                "Not recommended for beginners",
                "Consider as entertainment expense",
                "Know when to walk away"
            ]
        )'''
    },
    'range50-random': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Small",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Uses Range Dice for 50/50 odds",
                "Randomization adds unpredictability",
                "Different game type provides variety",
                "True 50% probability",
                "Good for breaking patterns"
            ],
            cons=[
                "Randomness doesn't improve odds",
                "Still subject to house edge",
                "No mathematical advantage",
                "Complexity doesn't add value",
                "May confuse bet tracking"
            ],
            best_use_case="For variety and testing Range Dice. No real advantage over standard play.",
            tips=[
                "Understand this is experimental/fun",
                "No proven edge over simple betting",
                "Good for exploring Range Dice",
                "Use conservative bet sizing",
                "Mainly for entertainment/variety",
                "Track results vs simple strategies"
            ]
        )'''
    },
    'target-aware': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Low",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Goal-oriented betting approach",
                "Adjusts bets based on target proximity",
                "Good psychological framework",
                "Helps with discipline and exit planning",
                "Reduces overplay after targets hit"
            ],
            cons=[
                "Target-awareness doesn't change odds",
                "Can be overly conservative near target",
                "Psychological tool more than mathematical",
                "Complexity without proven edge"
            ],
            best_use_case="For disciplined players who benefit from goal-setting. Good session management.",
            tips=[
                "Set realistic profit targets (10-20%)",
                "Actually stop when target hit (discipline!)",
                "Use as session management tool",
                "Combine with other strategies",
                "Good for preventing overplay",
                "Focus on consistency over big wins"
            ]
        )'''
    },
    'custom-script': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Variable",
            bankroll_required="Variable",
            volatility="Variable",
            time_to_profit="Variable",
            recommended_for="Experts",
            pros=[
                "Complete customization freedom",
                "Implement any strategy logic",
                "Great for research and testing",
                "Learn Python while betting",
                "Share strategies with community"
            ],
            cons=[
                "Requires programming knowledge",
                "Bugs can cause losses",
                "No safety guarantees",
                "Debugging can be frustrating",
                "Easy to make mistakes"
            ],
            best_use_case="For developers creating custom strategies. Test thoroughly in simulation!",
            tips=[
                "ALWAYS test in simulation mode first",
                "Add extensive error handling",
                "Log everything for debugging",
                "Start with simple logic, add complexity slowly",
                "Review code multiple times before live use",
                "Consider open-sourcing successful strategies"
            ]
        )'''
    },
    'rng-analysis-strategy': {
        'import_line': 'from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata',
        'metadata': '''    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Large",
            volatility="High",
            time_to_profit="Variable",
            recommended_for="Experts",
            pros=[
                "Advanced statistical analysis",
                "Pattern detection algorithms",
                "Machine learning potential",
                "Intellectually fascinating",
                "Research-grade implementation"
            ],
            cons=[
                "RNG patterns don't exist (cryptographic RNG)",
                "False pattern detection (gambler's fallacy)",
                "Overfitting to randomness",
                "Complexity creates illusion of edge",
                "No mathematical advantage possible"
            ],
            best_use_case="EXPERIMENTAL ONLY. For statistical research, not profit. Use simulation mode.",
            tips=[
                "Understand this cannot beat cryptographic RNG",
                "Use ONLY for research/educational purposes",
                "Test extensively in simulation",
                "Any 'patterns' are statistical noise",
                "Great learning tool for statistics/ML",
                "Do not expect real profits from pattern detection"
            ]
        )'''
    },
}

def add_metadata_to_file(filepath, strategy_key):
    """Add metadata() method to a strategy file."""
    if strategy_key not in STRATEGY_METADATA:
        print(f"  ⚠️  No metadata defined for {strategy_key}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if metadata already exists
    if 'def metadata(cls)' in content:
        print(f"  ✓ {strategy_key} already has metadata")
        return True
    
    # Update import line
    old_import = 'from .base import StrategyContext, BetSpec, BetResult'
    new_import = STRATEGY_METADATA[strategy_key]['import_line']
    content = content.replace(old_import, new_import)
    
    # Find describe() method and add metadata() after it
    describe_end = content.find('    @classmethod\n    def schema(cls)')
    if describe_end == -1:
        print(f"  ❌ Could not find schema() method in {strategy_key}")
        return False
    
    # Insert metadata before schema
    metadata_code = '\n\n' + STRATEGY_METADATA[strategy_key]['metadata'] + '\n'
    content = content[:describe_end] + metadata_code + '\n' + content[describe_end:]
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  ✅ Added metadata to {strategy_key}")
    return True

def main():
    import os
    
    strategies_dir = 'src/betbot_strategies'
    
    print("🔧 Enhancing strategy files with rich metadata...\n")
    
    for strategy_key in STRATEGY_METADATA.keys():
        filename = strategy_key.replace('-', '_') + '.py'
        filepath = os.path.join(strategies_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"  ⚠️  File not found: {filepath}")
            continue
        
        add_metadata_to_file(filepath, strategy_key)
    
    print("\n✨ Strategy enhancement complete!")

if __name__ == '__main__':
    main()
