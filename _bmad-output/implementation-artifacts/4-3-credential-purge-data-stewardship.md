# Story 4.3: Credential Purge (Data Stewardship)

Status: review

## Story

As a Technical Evaluator,
I want password hashes to be purged when registrations expire or lock,
So that I can verify the Data Stewardship principle.

## Acceptance Criteria

1. **AC1: Password Hash Purged on Expiration**
   - **Given** a registration transitions to EXPIRED state
   - **When** the lazy state transition occurs
   - **Then** `password_hash` is set to NULL in the database (FR24)
   - **And** purge is atomic with state transition

2. **AC2: Password Hash Purged on Lockout**
   - **Given** a registration transitions to LOCKED state
   - **When** the 3rd failed attempt triggers lockout
   - **Then** `password_hash` is set to NULL in the database (FR24)
   - **And** purge is atomic with state transition

3. **AC3: No Ghost Credentials for Non-CLAIMED States**
   - **Given** a registration is in EXPIRED, LOCKED, or ACTIVE state
   - **When** I query the database for that registration
   - **Then** only ACTIVE state MAY have a password_hash (for future login)
   - **And** EXPIRED and LOCKED states MUST have password_hash = NULL (FR25)

4. **AC4: Purge Happens Within 60 Seconds (NFR-S6)**
   - **Given** a registration becomes eligible for expiration (TTL exceeded)
   - **When** the next verification attempt occurs (lazy purge)
   - **Then** the password_hash is purged within 60 seconds of expiration eligibility
   - **And** the purge follows the "lazy deletion" pattern (on read, not background job)

5. **AC5: Database Credentials Not Logged (NFR-S5)**
   - **Given** the application processes registrations
   - **When** database operations occur
   - **Then** password_hash values never appear in application logs
   - **And** database connection strings with passwords are not logged
   - **And** verification codes are logged (intentionally for demo - NFR-O3)

6. **AC6: Dedicated Data Stewardship Test Suite**
   - **Given** I run the integration test suite
   - **When** I filter for Data Stewardship tests
   - **Then** tests explicitly verify password_hash is NULL for EXPIRED state
   - **And** tests explicitly verify password_hash is NULL for LOCKED state
   - **And** tests verify no ghost credentials exist
   - **And** tests are in `tests/integration/test_postgres_repository.py`

## Tasks / Subtasks

- [x] Task 1: Audit Existing Credential Purge Implementation (AC: 1, 2)
  - [x] 1.1: Verify expiration purge in `verify_and_activate` (lines 193-205)
  - [x] 1.2: Verify lockout purge in `lock_sql` (line 140)
  - [x] 1.3: Confirm both use atomic UPDATE with password_hash = NULL
  - [x] 1.4: Document implementation locations for traceability

- [x] Task 2: Verify No Ghost Credentials (AC: 3)
  - [x] 2.1: Create `test_no_ghost_credentials_after_expiration` test
  - [x] 2.2: Create `test_no_ghost_credentials_after_lockout` test
  - [x] 2.3: Query database to verify password_hash is NULL for each state
  - [x] 2.4: Verify ACTIVE state retains password_hash (test_active_state_may_have_password_hash)

- [x] Task 3: Verify Lazy Purge Timing (AC: 4)
  - [x] 3.1: Review existing `test_password_hash_purged_on_expiration` covers timing
  - [x] 3.2: Verify purge happens on verification attempt (lazy, not background)
  - [x] 3.3: Document that NFR-S6 is satisfied by lazy deletion pattern

- [x] Task 4: Verify Logging Security (AC: 5)
  - [x] 4.1: Review application logging configuration
  - [x] 4.2: Verify password_hash is never logged in repository operations
  - [x] 4.3: Verify database connection strings are not logged
  - [x] 4.4: Confirm verification codes ARE logged (intentional for demo)
  - [x] 4.5: Logging test not needed - code audit confirms no password_hash logging

- [x] Task 5: Add Comprehensive Data Stewardship Tests (AC: 6)
  - [x] 5.1: Create `TestDataStewardship` test class for organization
  - [x] 5.2: Add `test_expired_state_has_null_password_hash`
  - [x] 5.3: Add `test_locked_state_has_null_password_hash`
  - [x] 5.4: Add `test_claimed_state_has_password_hash` (positive test)
  - [x] 5.5: Add docstrings citing FR24, FR25, NFR-S6

- [x] Task 6: Run Full Test Suite and Verify (AC: 1-6)
  - [x] 6.1: Run `pytest tests/` to verify all tests pass (182 passed)
  - [x] 6.2: Run `ruff check` and `ruff format` for code quality
  - [x] 6.3: Verify no regressions in existing functionality

## Dev Notes

### Current Implementation Status

**IMPORTANT:** The credential purge functionality is **already implemented** in Epic 4 Stories 4.1 and 4.2.

**Expiration Purge - Story 4.1 Implementation:**

**File:** `src/adapters/repository/postgres.py:193-205`

```python
# Lazy transition: CLAIMED → EXPIRED with credential purge (FR15, FR24)
# Data Stewardship: No ghost credentials for expired accounts (FR25)
expire_sql = """
    UPDATE registrations
    SET state = %s, password_hash = NULL
    WHERE email = %s AND state = %s
"""
cursor.execute(
    expire_sql, (TrustState.EXPIRED.value, email, TrustState.CLAIMED.value)
)
conn.commit()
return VerifyResult.EXPIRED
```

**Lockout Purge - Epic 3/Story 4.2 Implementation:**

**File:** `src/adapters/repository/postgres.py:137-142`

```python
# SQL to lock account (3 failures)
lock_sql = """
    UPDATE registrations
    SET state = %s, attempt_count = attempt_count + 1, password_hash = NULL
    WHERE email = %s AND state = %s
"""
```

### Existing Test Coverage

**File:** `tests/integration/test_postgres_repository.py`

| Test | Coverage | Status |
|------|----------|--------|
| `test_password_hash_purged_on_lockout` | FR24 on lockout | ✅ Exists |
| `test_password_hash_purged_on_expiration` | FR24 on expiration | ✅ Exists |
| `test_expired_registration_returns_expired` | Verifies NULL hash | ✅ Exists |

### Gaps to Address in This Story

| Gap | Test/Action to Add | Purpose |
|-----|-------------------|---------|
| Ghost credentials audit | `test_no_ghost_credentials_*` | Explicit FR25 verification |
| Organized test class | `TestDataStewardship` | Group related tests |
| Logging security | Audit + optional test | NFR-S5 verification |
| Documentation | Docstrings with FR citations | Traceability |

### FR/NFR Mapping

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR24 | Purge passwords on expire/lock | `password_hash = NULL` in UPDATE |
| FR25 | No ghost credentials | Atomic purge with state transition |
| NFR-S5 | No credential logging | Review logging config |
| NFR-S6 | Purge within 60 seconds | Lazy deletion pattern satisfies |

### Architecture Requirements

From `architecture.md`:
- **Lazy Deletion Pattern**: "Lazy deletion (SET NULL on check)" - credential purge on read
- **Data Stewardship**: "password_hash NULLed on expiration/lockout"
- **Schema Design**: `password_hash VARCHAR(255)` - NULLable by design for Data Stewardship

### Ghost Credentials Definition

"Ghost credentials" refers to password hashes that exist in the database for accounts that:
- Cannot be activated (EXPIRED, LOCKED states)
- Were never fully verified (unactivated accounts)

This is a security risk because:
- Attackers could potentially access these hashes
- No legitimate use exists for credentials on non-active accounts
- Data minimization principle (GDPR-aligned) suggests deletion

### Previous Story Intelligence

From Story 4.1 (Registration Expiration):
- Implemented lazy state transition CLAIMED → EXPIRED with credential purge
- Added `test_password_hash_purged_on_expiration`
- Pattern: Verify database state after operation

From Story 4.2 (Account Lockout):
- Verified existing lockout implementation includes credential purge
- Added `test_locked_account_fails_with_correct_credentials`
- Pattern: Test with correct credentials after state change

### Testing Patterns to Follow

```python
class TestDataStewardship:
    """Data Stewardship tests - FR24, FR25, NFR-S5, NFR-S6."""

    def test_expired_state_has_null_password_hash(self, repository, pool):
        """EXPIRED registrations have password_hash = NULL (FR24, FR25)."""
        # Setup: Create and expire registration
        # Assert: password_hash is NULL

    def test_locked_state_has_null_password_hash(self, repository, pool):
        """LOCKED registrations have password_hash = NULL (FR24, FR25)."""
        # Setup: Create and lock registration
        # Assert: password_hash is NULL

    def test_claimed_state_has_password_hash(self, repository, pool):
        """CLAIMED registrations retain password_hash (positive test)."""
        # Setup: Create fresh registration
        # Assert: password_hash is NOT NULL
```

### Logging Security Notes

**Expected Logging Behavior:**
- ✅ Verification codes logged: `[VERIFICATION] Email: user@example.com Code: 1234`
- ❌ Password hashes never logged
- ❌ Database connection strings never logged
- ✅ State transitions may be logged: `Registration state: CLAIMED → EXPIRED`

**Current Implementation:**
- Console email sender logs verification codes (intentional - NFR-O3)
- Repository uses standard Python logging
- No explicit password_hash logging (verify this)

### References

- [Source: architecture.md#Database Schema - Truth 6: Data Stewardship]
- [Source: architecture.md#Security Implementation - Lazy deletion]
- [Source: epics.md#Story 4.3 Acceptance Criteria]
- [Source: prd.md#FR24 (Purge hashed passwords on expiration)]
- [Source: prd.md#FR25 (No ghost credentials)]
- [Source: prd.md#NFR-S5 (No credential logging)]
- [Source: prd.md#NFR-S6 (Purge within 60 seconds)]
- [Source: Story 4.1 Dev Notes - Expiration purge implementation]
- [Source: Story 4.2 Dev Notes - Lockout purge verification]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 6 tasks (24 subtasks) completed successfully
- **Task 1**: Audited existing credential purge implementation
  - Expiration purge: `postgres.py:194-205` - `SET state = %s, password_hash = NULL`
  - Lockout purge: `postgres.py:137-142` - `lock_sql` with `password_hash = NULL`
  - Both use atomic single UPDATE statements
  - FR15, FR24, FR25 correctly cited in comments
- **Task 2**: Added ghost credentials tests
  - `test_no_ghost_credentials_after_expiration` - Verifies transition from non-NULL to NULL
  - `test_no_ghost_credentials_after_lockout` - Same pattern for lockout
  - `test_active_state_may_have_password_hash` - Positive test for ACTIVE state
- **Task 3**: Verified lazy purge timing
  - Existing tests cover timing (lazy deletion on verification attempt)
  - NFR-S6 satisfied by lazy deletion pattern
  - `test_credential_purge_is_atomic_with_state_transition` added
- **Task 4**: Verified logging security (NFR-S5)
  - Audited all logging in src/: main.py, postgres.py, console.py
  - password_hash is NEVER logged anywhere in codebase
  - Database connection strings not logged
  - Verification codes ARE logged (intentional - NFR-O3)
- **Task 5**: Added comprehensive Data Stewardship test class
  - `TestDataStewardship` class with 7 tests and FR citations
  - Tests cover EXPIRED, LOCKED, CLAIMED, ACTIVE states
  - All docstrings cite FR24, FR25, NFR-S5, NFR-S6
- **Task 6**: Full test suite verification
  - All 182 tests pass (7 new tests added)
  - ruff check passes, all files formatted
  - No regressions

### File List

- tests/integration/test_postgres_repository.py (modified - added TestDataStewardship class with 7 tests)

