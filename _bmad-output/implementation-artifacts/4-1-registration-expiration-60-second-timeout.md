# Story 4.1: Registration Expiration (60-Second Timeout)

Status: review

## Story

As a Technical Evaluator,
I want registrations to expire after 60 seconds,
So that I can verify the time-bounded proof invariant.

## Acceptance Criteria

1. **AC1: Expired Registration Returns EXPIRED Result**
   - **Given** a user registered but did not activate
   - **When** 60 seconds elapse since `created_at`
   - **Then** activation attempts return `VerifyResult.EXPIRED`
   - **And** the error response is "Invalid credentials or code" (generic message)

2. **AC2: Database State Transitions to EXPIRED**
   - **Given** a registration with state=CLAIMED has exceeded 60-second TTL
   - **When** a verification attempt is made
   - **Then** the database state is updated from CLAIMED → EXPIRED (FR15)
   - **And** this is a "lazy transition" - occurs on verification attempt, not background job

3. **AC3: Password Hash Purged on Expiration (Data Stewardship)**
   - **Given** a registration transitions to EXPIRED state
   - **When** the state transition occurs
   - **Then** `password_hash` is set to NULL in the database (FR24)
   - **And** no "ghost credentials" exist for expired accounts (FR25)
   - **And** purge happens atomically with state transition

4. **AC4: TTL Calculation Uses Database Time**
   - **Given** the repository checks expiration
   - **When** comparing timestamps
   - **Then** the check uses `created_at > NOW() - INTERVAL '60 seconds'`
   - **And** database time (PostgreSQL NOW()) is used, not application time
   - **And** this prevents clock drift issues between app and database

5. **AC5: Boundary Condition at 60 Seconds**
   - **Given** registrations at exactly 59 and 61 seconds old
   - **When** verification is attempted
   - **Then** 59-second registration is still valid (within window)
   - **And** 61-second registration returns EXPIRED
   - **And** boundary is exclusive: `> 60 seconds` means expired

6. **AC6: Already EXPIRED State Returns NOT_FOUND**
   - **Given** a registration is already in EXPIRED state
   - **When** another verification attempt is made
   - **Then** result is `VerifyResult.NOT_FOUND` (not EXPIRED again)
   - **And** this is consistent with other non-CLAIMED states (ACTIVE, LOCKED)

7. **AC7: Integration Test Verifies Complete Flow**
   - **Given** I run the integration test suite
   - **When** expiration tests execute
   - **Then** tests verify the database state actually changes to EXPIRED
   - **And** tests verify password_hash is NULL after expiration
   - **And** tests are in `tests/integration/test_postgres_repository.py`

## Tasks / Subtasks

- [x] Task 1: Update verify_and_activate to Transition State on Expiration (AC: 2, 3, 4)
  - [x] 1.1: Add SQL UPDATE to set state=EXPIRED when TTL exceeded
  - [x] 1.2: Add password_hash=NULL to the same UPDATE (atomic purge)
  - [x] 1.3: Ensure UPDATE happens BEFORE returning VerifyResult.EXPIRED
  - [x] 1.4: Verify existing TTL check query is correct (already uses NOW())

- [x] Task 2: Update Existing Expiration Tests (AC: 5, 7)
  - [x] 2.1: Enhance `test_expired_registration_returns_expired` to verify DB state
  - [x] 2.2: Add assertion that state is "EXPIRED" in database after call
  - [x] 2.3: Add assertion that password_hash is NULL after expiration

- [x] Task 3: Add Password Purge Verification Test (AC: 3, 7)
  - [x] 3.1: Create `test_password_hash_purged_on_expiration` test
  - [x] 3.2: Verify password_hash is set and not NULL before expiration
  - [x] 3.3: Verify password_hash is NULL after expiration transition

- [x] Task 4: Add Already-Expired State Test (AC: 6)
  - [x] 4.1: Create `test_already_expired_returns_not_found` test
  - [x] 4.2: Insert record with state=EXPIRED directly
  - [x] 4.3: Verify verify_and_activate returns NOT_FOUND

- [x] Task 5: Verify Boundary Conditions (AC: 5)
  - [x] 5.1: Review existing `test_registration_at_59_seconds_still_valid`
  - [x] 5.2: Ensure boundary is exactly 60 seconds (not 59, not 61)
  - [x] 5.3: Add comment explaining boundary behavior if not present

- [x] Task 6: Run Full Test Suite and Verify (AC: 1-7)
  - [x] 6.1: Run `pytest tests/` to verify all tests pass
  - [x] 6.2: Run `ruff check` and `ruff format` for code quality
  - [x] 6.3: Verify no regressions in existing functionality

## Dev Notes

### Current Implementation Gap

**File:** `src/adapters/repository/postgres.py:185-195`

The current code RETURNS `VerifyResult.EXPIRED` but does NOT update the database:

```python
# CURRENT (lines 185-195) - HAS GAP
# Check TTL (60-second window) using database time
ttl_sql = """
    SELECT 1 FROM registrations
    WHERE email = %s
      AND state = %s
      AND created_at > NOW() - INTERVAL '60 seconds'
"""
cursor.execute(ttl_sql, (email, TrustState.CLAIMED.value))
if cursor.fetchone() is None:
    conn.commit()
    return VerifyResult.EXPIRED  # <-- Returns but doesn't update state!
```

**Required Change Pattern:**

```python
# SHOULD BE - with state transition and credential purge
if cursor.fetchone() is None:
    # Lazy transition: CLAIMED → EXPIRED with credential purge
    expire_sql = """
        UPDATE registrations
        SET state = %s, password_hash = NULL
        WHERE email = %s AND state = %s
    """
    cursor.execute(expire_sql, (TrustState.EXPIRED.value, email, TrustState.CLAIMED.value))
    conn.commit()
    return VerifyResult.EXPIRED
```

### Architecture Requirements

From `architecture.md`:
- **Lazy Deletion Pattern**: "Lazy deletion (SET NULL on check)" - credential purge on read
- **Temporal Enforcement**: "60-second TTL at database level, not application"
- **Data Stewardship**: "password_hash NULLed on expiration/lockout"

### FR/NFR Mapping

| Requirement | Implementation |
|-------------|----------------|
| FR15: CLAIMED → EXPIRED transition | UPDATE state = 'EXPIRED' |
| FR24: Purge password on expiration | SET password_hash = NULL |
| FR25: No ghost credentials | Atomic purge with state transition |
| FR26: Database timestamps | Uses NOW() in PostgreSQL |
| NFR-S6: Purge within 60 seconds | Lazy purge on next verification attempt |

### Existing Test Coverage

**File:** `tests/integration/test_postgres_repository.py:527-570`

| Test | Current Coverage | Gap |
|------|------------------|-----|
| `test_expired_registration_returns_expired` | Returns EXPIRED ✅ | Missing: DB state check, password_hash check |
| `test_registration_at_59_seconds_still_valid` | Boundary check ✅ | Complete |

### SQL for State Transition

```sql
-- Expire registration with credential purge
UPDATE registrations
SET state = 'EXPIRED', password_hash = NULL
WHERE email = $1 AND state = 'CLAIMED';
```

### Project Structure Notes

- **Repository file**: `src/adapters/repository/postgres.py`
- **Test file**: `tests/integration/test_postgres_repository.py`
- **Domain enum**: `src/domain/ports.py` (TrustState.EXPIRED already exists)

### Previous Story Intelligence

From Story 3.4 (Timing-Safe Error Responses):
- Established pattern for secure code/password verification
- CRITICAL comments for security-sensitive code
- All verification runs BEFORE state-based checks
- Bug fix pattern: handle NULL password_hash gracefully (line 128)

### Testing Pattern from Epic 3

```python
# Verify database state after operation
with pool.connection() as conn, conn.cursor() as cursor:
    cursor.execute(
        "SELECT state, password_hash FROM registrations WHERE email = %s",
        (email,),
    )
    row = cursor.fetchone()

assert row is not None
assert row[0] == "EXPIRED"  # State transitioned
assert row[1] is None       # Password hash purged
```

### References

- [Source: architecture.md#Database Schema - Truth 6: Data Stewardship]
- [Source: architecture.md#Security Implementation - Lazy deletion]
- [Source: epics.md#Story 4.1 Acceptance Criteria]
- [Source: prd.md#FR15 (CLAIMED → EXPIRED transition)]
- [Source: prd.md#FR24 (Purge hashed passwords on expiration)]
- [Source: prd.md#NFR-S6 (Purge within 60 seconds)]
- [Source: Story 3.4 Dev Notes - NULL password_hash handling pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 6 tasks (18 subtasks) completed successfully
- **Task 1**: Implemented lazy state transition CLAIMED → EXPIRED with credential purge
  - Added SQL UPDATE to set state=EXPIRED and password_hash=NULL
  - Follows architecture's "lazy deletion" pattern
  - Implements FR15, FR24, FR25, NFR-S6
- **Task 2**: Enhanced existing test to verify database state transition
  - Added assertions for state="EXPIRED" and password_hash=NULL
- **Task 3**: Added `test_password_hash_purged_on_expiration`
  - Verifies password_hash exists before, NULL after expiration
  - Tests Data Stewardship requirements
- **Task 4**: Added `test_already_expired_returns_not_found`
  - Verifies already-EXPIRED registrations return NOT_FOUND
  - Consistent with handling of other non-CLAIMED states
- **Task 5**: Verified boundary conditions
  - 59 seconds: still valid (SUCCESS)
  - 61 seconds: expired (EXPIRED)
  - Added documentation comment to test
- **Task 6**: Full test suite verification
  - All 171 tests pass (2 new tests added)
  - ruff check passes, ruff format applied
  - No regressions

### File List

- src/adapters/repository/postgres.py (modified - added state transition and credential purge on expiration)
- tests/integration/test_postgres_repository.py (modified - enhanced existing test, added 2 new tests)

