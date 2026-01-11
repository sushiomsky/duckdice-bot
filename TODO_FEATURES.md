# TODO List - NiceGUI Web Interface Missing Features

## Priority 1: Critical Features (Required for Production)

### 1. Live API Integration
- [ ] Integrate `EnhancedAPIClient` from `src/duckdice_api/client.py`
- [ ] Implement `_run_live()` method in `bot_controller.py`
- [ ] Add API error handling and retry logic
- [ ] Test connection functionality in settings
- [ ] Add rate limiting protection
- [ ] Implement session management with API

### 2. Dynamic Strategy Loading
- [ ] Load strategies from `src/betbot_strategies/` directory
- [ ] Parse strategy metadata (name, description, parameters)
- [ ] Generate dynamic forms based on strategy requirements
- [ ] Validate strategy parameters before execution
- [ ] Support custom user-uploaded strategies

### 3. Real Bet Execution
- [ ] Connect bot_controller to actual strategy classes
- [ ] Implement proper StrategyContext creation
- [ ] Handle BetResult processing
- [ ] Update state from real bet responses
- [ ] Error recovery for failed bets

## Priority 2: Enhanced Features

### 4. Matplotlib Charts
- [ ] Add balance over time chart in simulator
- [ ] Add profit/loss chart in history
- [ ] Max drawdown visualization
- [ ] Win/loss distribution chart
- [ ] Export charts as PNG

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

### ✅ Completed
- Thread-safe state management
- Simulation mode with fake bets
- 5 pre-configured strategies
- Dashboard with live updates
- Bet history with pagination
- CSV export functionality
- Stop conditions
- Basic validation

### 🚧 In Progress
- None (all current features complete)

### ❌ Not Started
- Live API integration
- Dynamic strategy loading
- Matplotlib charts
- Real bet execution
- Database persistence
- Advanced analytics

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
