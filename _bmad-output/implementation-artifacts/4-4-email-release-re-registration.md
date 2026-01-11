# Story 4.4: Email Release and Re-Registration

Status: done

## Story

As a Technical Evaluator,
I want to re-register with an email that previously expired or locked,
So that I can verify the email release mechanism.

## Acceptance Criteria

1. **AC1: Re-Registration Succeeds for EXPIRED Emails**
   - **Given** an email address has a registration with state=EXPIRED
   - **When** a new registration attempt is made for that email
   - **Then** the old record is replaced with fresh registration data (FR17)
   - **And** new `created_at` timestamp is set using database time (FR26)
   - **And** `attempt_count` resets to 0
   - **And** new `verification_code` is generated and stored
   - **And** new `password_hash` is stored
   - **And** `state` is set to CLAIMED

2. **AC2: Re-Registration Succeeds for LOCKED Emails**
   - **Given** an email address has a registration with state=LOCKED
   - **When** a new registration attempt is made for that email
   - **Then** the old record is replaced with fresh registration data (FR17)
   - **And** all fields reset as in AC1

3. **AC3: Re-Registration Fails for ACTIVE Emails**
   - **Given** an email address has a registration with state=ACTIVE
   - **When** a new registration attempt is made for that email
   - **Then** the registration attempt fails
   - **And** return value is `False` (email already claimed)
   - **And** the ACTIVE record is NOT modified

4. **AC4: Re-Registration Fails for CLAIMED Emails (In-Progress)**
   - **Given** an email address has a registration with state=CLAIMED
   - **When** a new registration attempt is made for that email
   - **Then** the registration attempt fails
   - **And** return value is `False`
   - **And** the CLAIMED record is NOT modified (let it expire naturally)

5. **AC5: Atomic Operation (No Race Conditions)**
   - **Given** multiple concurrent re-registration attempts for the same EXPIRED email
   - **When** the attempts execute simultaneously
   - **Then** exactly one succeeds
   - **And** no data corruption occurs
   - **And** the winning registration has consistent state

6. **AC6: E2E Re-Registration Flow via API**
   - **Given** I previously registered and the registration expired
   - **When** I call `POST /v1/register` again with the same email
   - **Then** I receive 201 Created
   - **And** a new verification code appears in console logs
   - **And** I can complete the full activation flow

7. **AC7: Verification Code Changes on Re-Registration**
   - **Given** an email was re-registered after expiration
   - **When** I attempt activation with the OLD verification code
   - **Then** the attempt fails with 401
   - **And** only the NEW verification code succeeds

## Tasks / Subtasks

- [x] Task 1: Update claim_email to Support Re-Registration (AC: 1, 2, 3, 4, 5)
  - [x] 1.1: Modify SQL to use `INSERT ... ON CONFLICT ... DO UPDATE`
  - [x] 1.2: Add WHERE clause: only update if state IN ('EXPIRED', 'LOCKED')
  - [x] 1.3: Reset all fields: password_hash, verification_code, state='CLAIMED', attempt_count=0
  - [x] 1.4: Use `created_at = NOW()` for fresh timestamp (FR26)
  - [x] 1.5: Ensure ACTIVE and CLAIMED states are NOT updated
  - [x] 1.6: Verify return value reflects actual insertion/update

- [x] Task 2: Add Re-Registration Tests for EXPIRED State (AC: 1, 7)
  - [x] 2.1: Create `test_claim_email_succeeds_for_expired_email` test
  - [x] 2.2: Verify old record is replaced with fresh data
  - [x] 2.3: Verify created_at is updated to new timestamp
  - [x] 2.4: Verify attempt_count resets to 0
  - [x] 2.5: Verify state is CLAIMED after re-registration

- [x] Task 3: Add Re-Registration Tests for LOCKED State (AC: 2)
  - [x] 3.1: Create `test_claim_email_succeeds_for_locked_email` test
  - [x] 3.2: Verify all fields reset same as EXPIRED case

- [x] Task 4: Add Non-Releasable State Tests (AC: 3, 4)
  - [x] 4.1: Create `test_claim_email_fails_for_active_email` test
  - [x] 4.2: Create `test_claim_email_fails_for_claimed_email` test
  - [x] 4.3: Verify ACTIVE record is not modified
  - [x] 4.4: Verify CLAIMED record is not modified

- [x] Task 5: Add Concurrent Re-Registration Test (AC: 5)
  - [x] 5.1: Create `test_concurrent_reregistration_exactly_one_succeeds` test
  - [x] 5.2: Use ThreadPoolExecutor pattern from existing concurrent tests
  - [x] 5.3: Verify no data corruption

- [x] Task 6: Add E2E Re-Registration Flow Test (AC: 6, 7)
  - [x] 6.1: Create `test_full_reregistration_flow_after_expiration` in test_register_flow.py
  - [x] 6.2: Register, let expire, re-register, activate with new code
  - [x] 6.3: Create `test_old_code_fails_after_reregistration` test
  - [x] 6.4: Verify old verification code is rejected

- [x] Task 7: Run Full Test Suite and Verify (AC: 1-7)
  - [x] 7.1: Run `pytest tests/` to verify all tests pass (194 passed)
  - [x] 7.2: Run `ruff check` and `ruff format` for code quality
  - [x] 7.3: Verify no regressions in existing functionality

## Dev Notes

### Current Implementation

**File:** `src/adapters/repository/postgres.py:68-92`

```python
def claim_email(self, email: str, password_hash: str, code: str) -> bool:
    sql = """
        INSERT INTO registrations (email, password_hash, verification_code)
        VALUES (%s, %s, %s)
        ON CONFLICT (email) DO NOTHING
    """
    with self._pool.connection() as conn, conn.cursor() as cursor:
        cursor.execute(sql, (email, password_hash, code))
        conn.commit()
        return cursor.rowcount == 1
```

**Gap:** Currently returns `False` for ANY existing email, regardless of state.

### Required Change Pattern

```python
def claim_email(self, email: str, password_hash: str, code: str) -> bool:
    """
    Atomically claim an email address for registration.

    Supports re-registration for EXPIRED and LOCKED emails (FR17).
    ACTIVE and CLAIMED emails cannot be re-registered.
    """
    sql = """
        INSERT INTO registrations (email, password_hash, verification_code, state, attempt_count, created_at)
        VALUES (%s, %s, %s, 'CLAIMED', 0, NOW())
        ON CONFLICT (email) DO UPDATE
        SET password_hash = EXCLUDED.password_hash,
            verification_code = EXCLUDED.verification_code,
            state = 'CLAIMED',
            attempt_count = 0,
            created_at = NOW(),
            activated_at = NULL
        WHERE registrations.state IN ('EXPIRED', 'LOCKED')
    """
    with self._pool.connection() as conn, conn.cursor() as cursor:
        cursor.execute(sql, (email, password_hash, code))
        conn.commit()
        return cursor.rowcount == 1
```

### SQL Explanation

The `ON CONFLICT ... DO UPDATE ... WHERE` pattern:
1. **INSERT** - Attempts to insert new record
2. **ON CONFLICT** - Triggers when email UNIQUE constraint violated
3. **DO UPDATE** - Executes UPDATE instead of failing
4. **WHERE** - Only updates if existing row matches condition (EXPIRED or LOCKED)
5. **rowcount** - Returns 1 if INSERT succeeded OR UPDATE matched WHERE clause

### State Transition Matrix

| Current State | Re-Registration Result | Rationale |
|---------------|----------------------|-----------|
| (none) | SUCCESS - New record | Normal first registration |
| CLAIMED | FAIL | In-progress registration, let it expire |
| ACTIVE | FAIL | Successfully verified, cannot re-register |
| EXPIRED | SUCCESS - Record reset | Email released after TTL (FR17) |
| LOCKED | SUCCESS - Record reset | Email released after lockout (FR17) |

### FR/NFR Mapping

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR17 | Release emails from EXPIRED/LOCKED | `ON CONFLICT DO UPDATE WHERE state IN (...)` |
| FR26 | Timestamp state transitions | `created_at = NOW()` |
| FR18 | Prevent race conditions | Single atomic SQL statement |

### Architecture Requirements

From `architecture.md`:
- **Atomic Operations**: Single SQL statement for claim operation
- **Email Release**: EXPIRED and LOCKED states are releasable
- **No Ghost Credentials**: New registration gets fresh password_hash

### Previous Story Intelligence

From Story 4.1 (Registration Expiration):
- Expiration purges password_hash to NULL
- Pattern: Database state verification after operation

From Story 4.2 (Account Lockout):
- Lockout purges password_hash to NULL
- Pattern: LOCKED accounts cannot be activated

From Story 4.3 (Data Stewardship):
- EXPIRED and LOCKED have NULL password_hash
- Re-registration will set a new password_hash

### Testing Patterns to Follow

```python
class TestEmailRelease:
    """Email release and re-registration tests - FR17, FR26."""

    def test_claim_email_succeeds_for_expired_email(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration succeeds for EXPIRED emails (FR17)."""
        email = "reregister@example.com"

        # Create EXPIRED registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state)
                   VALUES (%s, NULL, '0000', 'EXPIRED')""",
                (email,),
            )
            conn.commit()

        # Re-register
        result = repository.claim_email(email, "$2b$10$newhash", "9999")
        assert result is True

        # Verify record was reset
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, verification_code, attempt_count, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "CLAIMED"
        assert row[1] == "9999"  # New code
        assert row[2] == 0       # Reset attempt count
        assert row[3] is not None  # New password hash
```

### E2E Test Pattern

```python
def test_full_reregistration_flow_after_expiration(
    self, client: TestClient, email_capture
) -> None:
    """Complete re-registration flow after expiration."""
    email = "reregister@example.com"

    # First registration
    response1 = client.post("/v1/register", json={"email": email, "password": "pass1"})
    assert response1.status_code == 201
    first_code = email_capture.get_code(email)

    # Let it expire (manipulate DB or mock time)
    # ...

    # Re-register with new password
    response2 = client.post("/v1/register", json={"email": email, "password": "pass2"})
    assert response2.status_code == 201
    second_code = email_capture.get_code(email)

    # Old code should fail
    response3 = client.post(
        "/v1/activate",
        json={"code": first_code},
        headers=basic_auth_header(email, "pass2"),
    )
    assert response3.status_code == 401

    # New code should succeed
    response4 = client.post(
        "/v1/activate",
        json={"code": second_code},
        headers=basic_auth_header(email, "pass2"),
    )
    assert response4.status_code == 200
```

### Concurrent Re-Registration Test Pattern

```python
def test_concurrent_reregistration_exactly_one_succeeds(
    self, pool: ConnectionPool
) -> None:
    """Concurrent re-registration attempts for EXPIRED email."""
    email = "concurrent@example.com"

    # Create EXPIRED registration
    with pool.connection() as conn:
        conn.execute(
            """INSERT INTO registrations (email, password_hash, verification_code, state)
               VALUES (%s, NULL, '0000', 'EXPIRED')""",
            (email,),
        )
        conn.commit()

    results: list[bool] = []

    def attempt_reregister(code: str) -> None:
        repo = PostgresRegistrationRepository(pool)
        result = repo.claim_email(email, f"$2b$10$hash{code}", code)
        results.append(result)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_reregister, str(i)) for i in range(5)]
        for f in futures:
            f.result()

    # Exactly one should succeed (first UPDATE wins)
    assert results.count(True) == 1
    assert results.count(False) == 4
```

### References

- [Source: architecture.md#Database Schema - Email release mechanism]
- [Source: epics.md#Story 4.4 Acceptance Criteria]
- [Source: prd.md#FR17 (Release emails from EXPIRED/LOCKED)]
- [Source: prd.md#FR26 (Timestamp state transitions)]
- [Source: prd.md#FR18 (Prevent race conditions)]
- [Source: Story 4.1 Dev Notes - Expiration implementation]
- [Source: Story 4.2 Dev Notes - Lockout implementation]
- [Source: Story 4.3 Dev Notes - Data Stewardship verification]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 7 tasks (26 subtasks) completed successfully
- **Task 1**: Updated `claim_email` method in postgres.py
  - Changed from `ON CONFLICT DO NOTHING` to `ON CONFLICT DO UPDATE WHERE state IN ('EXPIRED', 'LOCKED')`
  - Explicitly sets all fields: password_hash, verification_code, state='CLAIMED', attempt_count=0
  - Uses `created_at = NOW()` for fresh timestamp (FR26)
  - Sets `activated_at = NULL` for re-registrations
  - FR17, FR18, FR26 correctly implemented
- **Task 2**: Added EXPIRED state re-registration tests
  - `test_claim_email_succeeds_for_expired_email` - verifies all fields reset
  - `test_created_at_updated_on_reregistration` - verifies FR26 timestamp
  - `test_activated_at_cleared_on_reregistration` - verifies activated_at reset
- **Task 3**: Added LOCKED state re-registration tests
  - `test_claim_email_succeeds_for_locked_email` - same reset behavior as EXPIRED
- **Task 4**: Added non-releasable state tests
  - `test_claim_email_fails_for_active_email` - ACTIVE protected
  - `test_claim_email_fails_for_claimed_email` - CLAIMED protected (let expire naturally)
- **Task 5**: Added concurrent re-registration test
  - `test_concurrent_reregistration_exactly_one_succeeds` - uses ThreadPoolExecutor
  - Verifies FR18 (no race conditions), no data corruption
- **Task 6**: Added E2E re-registration tests in test_register_flow.py
  - `test_full_reregistration_flow_after_expiration` - complete flow with code change
  - `test_reregistration_after_lockout` - full flow after account lockout
  - `test_old_code_fails_after_reregistration` - AC7 explicit test
  - `test_reregistration_fails_for_active_account` - E2E ACTIVE protection
  - `test_reregistration_fails_for_inprogress_registration` - E2E CLAIMED protection
- **Task 7**: Full test suite verification
  - All 194 tests pass (12 new tests added: 8 repository + 4 E2E, plus additional helper tests)
  - ruff check passes, all files formatted
  - No regressions

### File List

- src/adapters/repository/postgres.py (modified - updated claim_email method, added inline documentation)
- tests/integration/test_postgres_repository.py (modified - added TestEmailRelease class with 9 tests, fixed ConnectionPool deprecation)
- tests/integration/test_register_flow.py (modified - added TestReRegistrationFlow class with 5 tests, fixed ConnectionPool deprecation, enhanced AC7 assertions)
- tests/adversarial/test_timing_attacks.py (modified - fixed ConnectionPool deprecation)
- _bmad-output/planning-artifacts/architecture/core-architectural-decisions.md (modified - updated Truth 1 to reflect FR17 email release)

### Code Review Fixes

**Date**: 2026-01-11
**Reviewer**: Claude Opus 4.5 (Adversarial Code Review)
**Issues Found**: 1 High, 4 Medium, 3 Low
**Issues Fixed**: 1 High, 5 Medium (including bonus ConnectionPool fix), 1 Low

**HIGH Issues Fixed:**
1. **AC7 Verification Gap** - Added explicit assertion that verification codes differ on re-registration in `test_full_reregistration_flow_after_expiration`

**MEDIUM Issues Fixed:**
2. **Architecture Documentation** - Updated `core-architectural-decisions.md` Truth 1 to reflect `ON CONFLICT DO UPDATE WHERE` pattern for FR17
3. **ConnectionPool Deprecation** - Added `open=True` parameter to all 3 test fixtures (test_postgres_repository.py, test_register_flow.py, test_timing_attacks.py)
4. **Edge Case Test** - Added `test_reregistration_with_empty_password_hash` to verify repository layer accepts any string (domain validation responsibility)
5. **Incomplete Test** - Fixed `test_old_code_fails_after_reregistration` to capture and verify new code works (complete AC7 coverage)

**LOW Issues Fixed:**
6. **Inline SQL Documentation** - Added comment explaining `rowcount == 1` return behavior in claim_email

**Test Results After Fixes:**
- 195 tests pass (added 1 new edge case test)
- 0 deprecation warnings (down from 3)
- All ruff checks pass
- No regressions

