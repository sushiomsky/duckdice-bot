# 🎯 Phase 3: Bet Verification System - Implementation Plan

## Overview
Implement provably fair bet verification for DuckDice using SHA-256 hashing. Users can verify that bets were fair and not manipulated by the server.

**Duration**: 3-4 hours  
**Priority**: MEDIUM  
**Status**: 🚀 IN PROGRESS

---

## 📋 Detailed Task Breakdown

### Task 3.1: BetVerifier Core (1.5 hours)

**Goal**: Create the core verification engine

**DuckDice Provably Fair Algorithm**:
```
1. Server generates server_seed (secret until revealed)
2. Client provides client_seed
3. For each bet with nonce N:
   - Combine: server_seed + client_seed + nonce
   - Hash with SHA-256
   - Take first 5 hex chars
   - Convert to decimal
   - Roll result = (decimal % 100000) / 1000
   - Result range: 0.000 - 99.999
```

**Subtasks**:
1. Create `BetVerifier` class:
   ```python
   class BetVerifier:
       def verify_bet(server_seed, client_seed, nonce) -> float
       def is_result_valid(calculated, actual) -> bool
       def verify_batch(bets: List[Bet]) -> VerificationReport
   ```

2. Implement SHA-256 hashing:
   - Concatenate seeds + nonce
   - Hash with hashlib.sha256
   - Extract result from hash

3. Add result calculation:
   - Parse hex to decimal
   - Apply modulo and division
   - Return roll value (0.000 - 99.999)

4. Add win/loss verification:
   - Check if result matches prediction
   - Validate payout calculation

**Files to Create**:
- `src/verification/bet_verifier.py`
- `src/verification/__init__.py`

**Tests to Write**:
- Test with known seed combinations
- Verify hash generation
- Test edge cases (nonce 0, max nonce)
- Batch verification

---

### Task 3.2: Verification Models (0.5 hours)

**Goal**: Data models for verification results

**Subtasks**:
1. Create `VerificationResult` dataclass:
   ```python
   @dataclass
   class VerificationResult:
       is_valid: bool
       calculated_roll: float
       actual_roll: float
       server_seed: str
       client_seed: str
       nonce: int
       hash_value: str
       error: Optional[str]
   ```

2. Create `VerificationReport` for batch:
   ```python
   @dataclass
   class VerificationReport:
       total_bets: int
       verified_bets: int
       failed_bets: int
       results: List[VerificationResult]
       timestamp: datetime
   ```

**Files to Create**:
- `src/verification/models.py`

---

### Task 3.3: GUI Integration (1.5 hours)

**Goal**: Add verification UI to History page

**Subtasks**:
1. Update History page:
   - Add "Verify" button to each bet row
   - Add "Verify All" button for batch
   - Show verification status icons

2. Create verification dialog:
   - Display calculation steps
   - Show hash breakdown
   - Highlight verification status
   - Export verification report

3. Add verification status column:
   - ✅ Verified (green)
   - ❌ Failed (red)
   - ⏳ Pending (yellow)
   - ➖ Not verified yet (gray)

4. Create verification report export:
   - CSV format with all details
   - Include hash, seeds, results
   - Timestamp and summary

**Files to Modify**:
- `app/ui/pages/history.py`

**Files to Create**:
- `app/ui/components/verification_dialog.py`

---

### Task 3.4: API Integration (0.5 hours)

**Goal**: Fetch server seed from API when revealed

**Subtasks**:
1. Add API method to get revealed seeds:
   ```python
   def get_server_seed(seed_hash: str) -> Optional[str]
   ```

2. Update bet history to include:
   - Server seed hash
   - Revealed server seed (if available)
   - Client seed
   - Nonce

3. Handle unrevealed seeds:
   - Show "Not yet revealed" message
   - Allow verification once revealed

**Files to Modify**:
- `src/duckdice_api/api.py`

---

## 📊 Technical Specifications

### Provably Fair Verification

**Algorithm Details**:
```python
import hashlib

def calculate_roll(server_seed: str, client_seed: str, nonce: int) -> float:
    # Combine seeds and nonce
    message = f"{server_seed}{client_seed}{nonce}"
    
    # SHA-256 hash
    hash_object = hashlib.sha256(message.encode())
    hash_hex = hash_object.hexdigest()
    
    # Take first 5 hex characters
    first_5_hex = hash_hex[:5]
    
    # Convert to decimal
    decimal_value = int(first_5_hex, 16)
    
    # Calculate roll (0.000 - 99.999)
    roll = (decimal_value % 100000) / 1000.0
    
    return roll
```

**Example Verification**:
```python
server_seed = "abc123..."
client_seed = "my_seed"
nonce = 42

calculated = calculate_roll(server_seed, client_seed, nonce)
# Result: 45.678

# Compare with actual bet result
actual = 45.678
is_valid = abs(calculated - actual) < 0.001  # Allow small float precision
```

---

## 🎨 UI Design

### History Page Enhancement

**Bet Row Layout**:
```
| ID | Time | Amount | Chance | Roll | Result | Profit | [Verify] |
|----|------|--------|--------|------|--------|--------|----------|
| #1 | 12:34| 0.01   | 50.0   | 45.6 | WIN    | +0.01  | ✅       |
```

**Verification Dialog**:
```
╔═══════════════════════════════════════════════════╗
║         Bet Verification                          ║
╠═══════════════════════════════════════════════════╣
║                                                   ║
║  Server Seed: abc123...def456                     ║
║  Client Seed: my_client_seed                      ║
║  Nonce: 42                                        ║
║                                                   ║
║  SHA-256 Hash:                                    ║
║  5a3b9...                                         ║
║                                                   ║
║  First 5 Hex: 5a3b9                               ║
║  Decimal: 370617                                  ║
║  Roll = (370617 % 100000) / 1000 = 70.617         ║
║                                                   ║
║  Calculated Roll: 70.617                          ║
║  Actual Roll:     70.617                          ║
║                                                   ║
║  ✅ VERIFIED - Bet is provably fair               ║
║                                                   ║
║  [Export Report]  [Close]                         ║
╚═══════════════════════════════════════════════════╝
```

---

## 🧪 Testing Strategy

### Unit Tests
1. Test hash calculation with known values
2. Test roll conversion accuracy
3. Test edge cases (empty seeds, zero nonce)
4. Test batch verification

### Integration Tests
1. Verify real bet from DuckDice
2. Test with revealed server seeds
3. Test unrevealed seed handling
4. Export report validation

### Manual Tests
1. Verify multiple bets
2. Check UI responsiveness
3. Test export functionality
4. Verify batch processing

---

## 📈 Success Criteria

✅ **Accuracy**: 100% match with DuckDice verification  
✅ **Performance**: Verify 1000 bets in < 1 second  
✅ **UI**: Clear, intuitive verification display  
✅ **Export**: Clean CSV with all verification data  
✅ **Error Handling**: Graceful handling of missing seeds  

---

## 🚀 Implementation Order

1. ✅ Create implementation plan
2. ⬜ Build BetVerifier core (1.5h)
3. ⬜ Create verification models (0.5h)
4. ⬜ Add GUI integration (1.5h)
5. ⬜ API integration (0.5h)
6. ⬜ Testing and validation (0.5h)

**Total**: 3.5-4 hours

---

## 📝 Notes

- DuckDice uses standard provably fair algorithm
- Server seed is hashed and shown to user before betting
- Server seed is revealed after user changes it
- Users can verify past bets once seed is revealed
- Verification proves server didn't manipulate results

---

**Created**: January 9, 2026  
**Status**: Ready to implement  
**Next**: Task 3.1 - Build BetVerifier core
