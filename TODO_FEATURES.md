# TODO List - NiceGUI Web Interface Missing Features

## Priority 1: Critical Features (Required for Production)

### 1. Live API Integration ✅ COMPLETED
- [x] Integrate `EnhancedAPIClient` from `src/duckdice_api/client.py`
- [x] Implement `_run_live()` method in `bot_controller.py`
- [x] Add API error handling and retry logic
- [x] Test connection functionality in settings
- [x] Add rate limiting protection
- [x] Implement session management with API

### 2. Dynamic Strategy Loading ✅ COMPLETED
- [x] Load strategies from `src/betbot_strategies/` directory
- [x] Parse strategy metadata (name, description, parameters)
- [x] Generate dynamic forms based on strategy requirements
- [x] Validate strategy parameters before execution
- [ ] Support custom user-uploaded strategies (future enhancement)

### 3. Real Bet Execution ✅ COMPLETED
- [x] Connect bot_controller to actual strategy classes
- [x] Implement proper StrategyContext creation
- [x] Handle BetResult processing
- [x] Update state from real bet responses
- [x] Error recovery for failed bets

## Priority 2: Enhanced Features

### 4. Matplotlib Charts ✅ COMPLETED
- [x] Add balance over time chart in simulator
- [x] Add profit/loss chart in history
- [x] Max drawdown visualization (via streak analysis)
- [x] Win/loss distribution chart
- [x] Export charts as PNG

### 5. UI Enhancements
- [ ] Add keyboard shortcuts (Ctrl+S for start/stop, etc.)
- [ ] Mobile-responsive layout improvements
- [ ] Loading states for async operations
- [ ] Toast notifications for events
- [ ] Confirmation dialogs for destructive actions

### 6. Data Persistence
- [ ] Save bet history to database (SQLite)
- [ ] Auto-save strategy profiles
- [ ] Session recovery on crash
- [ ] Export/import configuration
- [ ] Backup/restore functionality

## Priority 3: Advanced Features

### 7. Real-time Features
- [ ] WebSocket support for live updates
- [ ] Push notifications for stop conditions
- [ ] Real-time balance updates from API
- [ ] Live bet feed display

### 8. Analytics
- [ ] Statistical analysis of results
- [ ] Strategy performance comparison
- [ ] Risk analysis metrics
- [ ] Bankroll management calculator
- [ ] ROI tracking

### 9. Multi-user Support
- [ ] Per-session state isolation
- [ ] User authentication
- [ ] Multiple concurrent bots
- [ ] User preferences storage

## Priority 4: Testing & Quality

### 10. Test Coverage
- [ ] Unit tests for all components
- [ ] Integration tests for API calls
- [ ] UI component tests
- [ ] End-to-end workflow tests
- [ ] Performance/load tests

### 11. Error Handling
- [ ] Comprehensive error boundaries
- [ ] Graceful degradation
- [ ] User-friendly error messages
- [ ] Error logging and reporting
- [ ] Retry mechanisms

### 12. Documentation
- [ ] API documentation
- [ ] Component documentation
- [ ] User tutorials with screenshots
- [ ] Video guides
- [ ] FAQ section

## Current Status Summary

### ✅ Completed (Priority 1 - ALL DONE!)
- Thread-safe state management
- Simulation mode with fake bets
- **17 strategies dynamically loaded from betbot_strategies**
- **Rich strategy metadata display (risk, pros/cons, tips)**
- **Dynamic form generation from strategy schemas**
- Dashboard with live updates
- Bet history with pagination
- CSV export functionality
- Stop conditions
- Basic validation
- **Live API integration with DuckDiceAPI**
- **API connection testing**
- **Real bet execution using actual strategy classes**
- **StrategyContext creation from app_state**
- **BetSpec/BetResult conversion pipeline**
- **Rate limiting and safety features**
- **All 17 strategies work in live mode**

### 🚧 Next Priority (Priority 2-3)
- Matplotlib charts for visualization
- Database persistence for bet history
- Advanced analytics and statistics

### ❌ Lower Priority (Priority 4)
- Multi-user support
- WebSocket real-time updates
- User authentication

## Implementation Order

### Phase 1 (Week 1) - Live API
1. API client integration
2. Test connection
3. Live mode implementation
4. Error handling

### Phase 2 (Week 2) - Strategy Loading
1. Dynamic strategy discovery
2. Metadata parsing
3. Form generation
4. Validation

### Phase 3 (Week 3) - Charts & Analytics
1. Matplotlib integration
2. Chart components
3. Export functionality
4. Basic analytics

### Phase 4 (Week 4) - Testing & Polish
1. Comprehensive test suite
2. Bug fixes
3. Performance optimization
4. Documentation updates

## Notes

- All features should maintain safety-first approach
- Test in simulation mode first
- Maintain backward compatibility
- Follow existing code patterns
- Update documentation as features are added
