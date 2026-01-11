# Story 4.2: Account Lockout (3 Failed Attempts)

Status: review

## Story

As a Technical Evaluator,
I want accounts to lock after 3 failed verification attempts,
So that I can verify brute-force protection.

## Acceptance Criteria

1. **AC1: Attempt Count Increments on Each Failure**
   - **Given** a user has a CLAIMED registration
   - **When** they submit an incorrect verification code OR wrong password
   - **Then** `attempt_count` increments from 0→1→2→3 (FR19)
   - **And** both wrong code AND wrong password increment the counter

2. **AC2: State Transitions to LOCKED After 3 Failures**
   - **Given** a user has 2 failed attempts (`attempt_count = 2`)
   - **When** they submit a 3rd incorrect verification attempt
   - **Then** state transitions from CLAIMED → LOCKED (FR16, FR20)
   - **And** `attempt_count` is set to 3

3. **AC3: Password Hash Purged on Lockout (Data Stewardship)**
   - **Given** a registration transitions to LOCKED state
   - **When** the state transition occurs
   - **Then** `password_hash` is set to NULL in the database (FR24)
   - **And** no "ghost credentials" exist for locked accounts (FR25)

4. **AC4: Locked Account Returns Generic Error**
   - **Given** an account is in LOCKED state
   - **When** a verification attempt is made (even with correct credentials)
   - **Then** result is `VerifyResult.LOCKED`
   - **And** API returns 401 with "Invalid credentials or code" (FR21)
   - **And** the locked state persists permanently

5. **AC5: Progression Through Attempt Counts**
   - **Given** a fresh CLAIMED registration
   - **When** I track attempt_count after each failed attempt
   - **Then** progression is: 0 (initial) → 1 (after 1st fail) → 2 (after 2nd) → 3 (locked)
   - **And** each intermediate state is verifiable in the database

6. **AC6: E2E Lockout Flow via API**
   - **Given** I use the `/v1/activate` API endpoint
   - **When** I make 3 failed activation attempts
   - **Then** the first 2 return 401 (INVALID_CODE behavior)
   - **And** the 3rd returns 401 (LOCKED behavior)
   - **And** subsequent attempts with correct code also return 401

## Tasks / Subtasks

- [x] Task 1: Verify Existing Lockout Implementation (AC: 1, 2, 3, 4)
  - [x] 1.1: Audit `verify_and_activate` in postgres.py for attempt counting logic
  - [x] 1.2: Verify state transition CLAIMED → LOCKED on 3rd failure
  - [x] 1.3: Verify password_hash=NULL in lock_sql
  - [x] 1.4: Verify locked accounts return VerifyResult.LOCKED
  - [x] 1.5: Document any gaps found (expected: none if Epic 3 was correct)

- [x] Task 2: Add Attempt Count Progression Test (AC: 5)
  - [x] 2.1: Create `test_attempt_count_progression_0_to_3` test
  - [x] 2.2: Verify attempt_count=0 initially
  - [x] 2.3: Verify attempt_count=1 after 1st failure
  - [x] 2.4: Verify attempt_count=2 after 2nd failure
  - [x] 2.5: Verify attempt_count=3 and state=LOCKED after 3rd failure

- [x] Task 3: Add Wrong Password Increments Test (AC: 1)
  - [x] 3.1: Create `test_wrong_password_increments_attempt_count` test
  - [x] 3.2: Verify wrong password (correct code) increments attempt_count
  - [x] 3.3: Verify both wrong code and wrong password contribute to lockout

- [x] Task 4: Add E2E API Lockout Test (AC: 6)
  - [x] 4.1: Verified existing `test_activation_after_3_failed_attempts_locks_account` covers AC6
  - [x] 4.2: Test registers user and captures verification code
  - [x] 4.3: Test makes 3 failed activation attempts via API
  - [x] 4.4: Test verifies 401 responses for all attempts
  - [x] 4.5: Test verifies correct code fails after lockout

- [x] Task 5: Add Locked With Correct Credentials Test (AC: 4)
  - [x] 5.1: Create `test_locked_account_fails_with_correct_credentials` test
  - [x] 5.2: Create locked account directly in DB
  - [x] 5.3: Attempt activation with correct code AND password
  - [x] 5.4: Verify result is still LOCKED (state persists)

- [x] Task 6: Run Full Test Suite and Verify (AC: 1-6)
  - [x] 6.1: Run `pytest tests/` to verify all tests pass (175 passed)
  - [x] 6.2: Run `ruff check` and `ruff format` for code quality
  - [x] 6.3: Verify no regressions in existing functionality

## Dev Notes

### Current Implementation Status

**IMPORTANT:** The lockout functionality is **already implemented** in Epic 3 (Story 3.2).

**File:** `src/adapters/repository/postgres.py:207-229`

```python
# Check if already locked (3+ attempts)
if attempt_count >= 3:
    conn.commit()
    return VerifyResult.LOCKED

# Verify code and password
if not code_valid or not password_valid:
    # Increment attempt count
    new_attempt_count = attempt_count + 1

    if new_attempt_count >= 3:
        # Lock account and purge password hash (Data Stewardship)
        cursor.execute(
            lock_sql,
            (TrustState.LOCKED.value, email, TrustState.CLAIMED.value),
        )
        conn.commit()
        return VerifyResult.LOCKED
    else:
        # Just increment attempt count
        cursor.execute(increment_sql, (email, TrustState.CLAIMED.value))
        conn.commit()
        return VerifyResult.INVALID_CODE
```

### Existing Test Coverage

**File:** `tests/integration/test_postgres_repository.py:376-490`

| Test | Coverage | Status |
|------|----------|--------|
| `test_attempt_count_increments_on_failure` | FR19 partial | ✅ Exists (checks 0→1) |
| `test_state_transitions_to_locked_after_3_failures` | FR16, FR20 | ✅ Exists |
| `test_locked_account_returns_locked` | AC4 partial | ✅ Exists |
| `test_password_hash_purged_on_lockout` | FR24, FR25 | ✅ Exists |

### Gaps to Address in This Story

| Gap | Test to Add | Purpose |
|-----|-------------|---------|
| Attempt progression 0→1→2→3 | `test_attempt_count_progression_0_to_3` | Verify each increment |
| Wrong password increments | `test_wrong_password_increments_attempt_count` | FR19 complete coverage |
| E2E API lockout | `test_lockout_flow_via_api` | End-to-end verification |
| Correct creds after lock | `test_locked_account_fails_with_correct_credentials` | AC4 complete |

### FR/NFR Mapping

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR16 | CLAIMED → LOCKED after 3 failures | lock_sql execution |
| FR19 | Track and limit verification attempts | attempt_count field |
| FR20 | Lock accounts after threshold | if new_attempt_count >= 3 |
| FR21 | Generic error messages | "Invalid credentials or code" |
| FR24 | Purge password on lock | password_hash = NULL |
| FR25 | No ghost credentials | Atomic purge with lock |

### SQL Statements (Already Exist)

```sql
-- Increment attempt count (lines 131-135)
UPDATE registrations
SET attempt_count = attempt_count + 1
WHERE email = $1 AND state = 'CLAIMED';

-- Lock account with credential purge (lines 138-142)
UPDATE registrations
SET state = 'LOCKED', attempt_count = attempt_count + 1, password_hash = NULL
WHERE email = $1 AND state = 'CLAIMED';
```

### Previous Story Intelligence

From Story 4.1 (Registration Expiration):
- Pattern for verifying database state after operations
- Pattern for verifying password_hash is NULL
- E2E test pattern in test_register_flow.py
- All 171 tests passing before this story

### Testing Patterns to Follow

```python
# Verify attempt_count progression
with pool.connection() as conn, conn.cursor() as cursor:
    cursor.execute(
        "SELECT attempt_count, state FROM registrations WHERE email = %s",
        (email,),
    )
    row = cursor.fetchone()
assert row[0] == expected_count
assert row[1] == expected_state

# E2E API test pattern (from test_register_flow.py)
response = client.post(
    "/v1/activate",
    json={"code": wrong_code},
    headers=basic_auth_header(email, password),
)
assert response.status_code == 401
```

### References

- [Source: architecture.md#Security Implementation - Attempt limiting]
- [Source: epics.md#Story 4.2 Acceptance Criteria]
- [Source: prd.md#FR16 (CLAIMED → LOCKED transition)]
- [Source: prd.md#FR19 (Track verification attempts)]
- [Source: prd.md#FR20 (Lock after threshold)]
- [Source: prd.md#FR21 (Generic error messages)]
- [Source: Story 3.2 Implementation - Lock SQL and attempt counting]
- [Source: Story 4.1 Dev Notes - Database state verification patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 6 tasks (23 subtasks) completed successfully
- **Task 1**: Verified existing lockout implementation from Epic 3 (Story 3.2)
  - Attempt counting logic correct (lines 213-229 in postgres.py)
  - State transition CLAIMED → LOCKED on 3rd failure confirmed
  - password_hash=NULL in lock_sql confirmed (line 140)
  - Locked accounts return VerifyResult.LOCKED confirmed
  - No gaps found - implementation was complete
- **Task 2**: Added `test_attempt_count_progression_0_to_3`
  - Verifies complete progression: 0 (initial) → 1 → 2 → 3 (locked)
  - Each intermediate state verified in database
- **Task 3**: Added `test_wrong_password_increments_attempt_count` and `test_mixed_failures_contribute_to_lockout`
  - Wrong password with correct code increments attempt_count
  - Both wrong code and wrong password contribute to lockout
- **Task 4**: Verified existing E2E test covers AC6
  - `test_activation_after_3_failed_attempts_locks_account` in test_register_flow.py
  - Covers full lockout flow via API
- **Task 5**: Added `test_locked_account_fails_with_correct_credentials`
  - Locked account created directly in DB with correct password_hash
  - Verifies correct code AND password still returns LOCKED
- **Task 6**: Full test suite verification
  - All 175 tests pass (4 new tests added)
  - ruff check passes, ruff format applied
  - No regressions

### File List

- tests/integration/test_postgres_repository.py (modified - added 4 new lockout tests)

