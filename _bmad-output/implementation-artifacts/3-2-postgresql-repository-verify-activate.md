# Story 3.2: PostgreSQL Repository - Verify and Activate

Status: review

## Story

As a Technical Evaluator,
I want the repository to verify credentials and update state atomically,
So that I can verify concurrent activation attempts don't cause inconsistencies.

## Acceptance Criteria

1. **AC1: verify_and_activate Method Exists**
   - **Given** `src/adapters/repository/postgres.py` exists
   - **When** I inspect the `PostgresRegistrationRepository` class
   - **Then** a `verify_and_activate(email: str, code: str, password: str) -> VerifyResult` method exists
   - **And** the method signature matches the RegistrationRepository protocol from Story 3.1

2. **AC2: Row-Level Locking with SELECT FOR UPDATE**
   - **Given** the repository's verify_and_activate implementation
   - **When** I inspect the SQL query
   - **Then** it uses `SELECT ... FOR UPDATE` to lock the row during verification
   - **And** prevents concurrent activation attempts from causing race conditions
   - **And** the lock is released when the transaction completes

3. **AC3: Constant-Time Code Comparison (NFR-S2)**
   - **Given** a CLAIMED registration with verification code "1234"
   - **When** code comparison is performed
   - **Then** it uses `secrets.compare_digest()` for constant-time comparison
   - **And** comparison runs even if email not found (timing oracle prevention)
   - **And** code is compared before password to fail fast on wrong code

4. **AC4: Constant-Time Password Verification**
   - **Given** a CLAIMED registration with bcrypt-hashed password
   - **When** password verification is performed
   - **Then** it uses `bcrypt.checkpw()` which provides constant-time comparison
   - **And** verification runs even if code mismatch (prevents timing oracle)
   - **And** a dummy hash comparison runs for non-existent emails

5. **AC5: 60-Second TTL Check (FR10)**
   - **Given** a CLAIMED registration
   - **When** verify_and_activate is called
   - **Then** TTL is checked using database time: `created_at > NOW() - INTERVAL '60 seconds'`
   - **And** expired registrations return `VerifyResult.EXPIRED`
   - **And** TTL check happens in the same transaction as state update

6. **AC6: Attempt Count Check (FR11)**
   - **Given** a CLAIMED registration with attempt_count
   - **When** verify_and_activate is called
   - **Then** attempt count is checked: `attempt_count < 3`
   - **And** if attempts >= 3, returns `VerifyResult.LOCKED`
   - **And** state transitions to LOCKED in the same transaction

7. **AC7: Attempt Increment on Failure (FR19)**
   - **Given** a CLAIMED registration with attempt_count < 3
   - **When** verification fails (wrong code or password)
   - **Then** attempt_count is incremented atomically
   - **And** if new attempt_count = 3, state transitions to LOCKED
   - **And** increment happens within the same transaction (atomic)

8. **AC8: SUCCESS State Transition (FR12)**
   - **Given** all verification checks pass (code, password, TTL, attempts)
   - **When** verify_and_activate completes
   - **Then** state transitions from CLAIMED to ACTIVE
   - **And** `activated_at` timestamp is set using `NOW()` database time
   - **And** returns `VerifyResult.SUCCESS`

9. **AC9: Return Values Match Protocol**
   - **Given** verify_and_activate implementation
   - **When** I examine all return paths
   - **Then** returns `VerifyResult.SUCCESS` on successful activation
   - **And** returns `VerifyResult.NOT_FOUND` when email not in CLAIMED state
   - **And** returns `VerifyResult.INVALID_CODE` for code OR password mismatch
   - **And** returns `VerifyResult.EXPIRED` when TTL exceeded
   - **And** returns `VerifyResult.LOCKED` when attempt_count >= 3

10. **AC10: Generic Error for Security**
    - **Given** a verification failure (code or password mismatch)
    - **When** the result is returned
    - **Then** the same `VerifyResult.INVALID_CODE` is returned for both cases
    - **And** no information leakage about which check failed
    - **And** timing is consistent regardless of which check failed

## Tasks / Subtasks

- [x] Task 1: Import Required Dependencies (AC: 1, 3, 4)
  - [x] 1.1: Add `secrets` import to postgres.py for constant-time comparison
  - [x] 1.2: Add `bcrypt` import to postgres.py for password verification
  - [x] 1.3: Import `VerifyResult` from domain ports
  - [x] 1.4: Import `TrustState` from domain ports (for state constants)

- [x] Task 2: Implement verify_and_activate Method (AC: 1, 2, 8, 9)
  - [x] 2.1: Add method signature matching RegistrationRepository protocol
  - [x] 2.2: Implement `SELECT ... FOR UPDATE` query to fetch and lock registration
  - [x] 2.3: Handle NOT_FOUND case when email doesn't exist or not CLAIMED
  - [x] 2.4: Implement SUCCESS path with UPDATE to ACTIVE state and activated_at
  - [x] 2.5: Return appropriate VerifyResult enum values

- [x] Task 3: Implement TTL and Attempt Checks (AC: 5, 6, 7)
  - [x] 3.1: Add TTL check in SQL: `created_at > NOW() - INTERVAL '60 seconds'`
  - [x] 3.2: Return EXPIRED if TTL exceeded
  - [x] 3.3: Check attempt_count < 3 before verification
  - [x] 3.4: Return LOCKED if attempt_count >= 3
  - [x] 3.5: Increment attempt_count on verification failure
  - [x] 3.6: Transition to LOCKED state if attempt_count reaches 3

- [x] Task 4: Implement Constant-Time Security (AC: 3, 4, 10)
  - [x] 4.1: Use `secrets.compare_digest()` for code comparison
  - [x] 4.2: Use `bcrypt.checkpw()` for password verification
  - [x] 4.3: Ensure both checks run even on early failures (timing oracle prevention)
  - [x] 4.4: Use dummy hash comparison for non-existent emails
  - [x] 4.5: Return generic INVALID_CODE for both code and password failures

- [x] Task 5: Write Integration Tests (AC: 1-10)
  - [x] 5.1: Test verify_and_activate with valid credentials returns SUCCESS
  - [x] 5.2: Test verify_and_activate with wrong code returns INVALID_CODE
  - [x] 5.3: Test verify_and_activate with wrong password returns INVALID_CODE
  - [x] 5.4: Test verify_and_activate with expired registration returns EXPIRED
  - [x] 5.5: Test verify_and_activate with locked registration returns LOCKED
  - [x] 5.6: Test verify_and_activate with non-existent email returns NOT_FOUND
  - [x] 5.7: Test attempt_count increments on failure
  - [x] 5.8: Test state transitions to LOCKED after 3 failures
  - [x] 5.9: Test activated_at is set on SUCCESS

## Dev Notes

### Current State (from Story 3.1)

Story 3.1 established the domain layer with:

```python
# src/domain/ports.py
class VerifyResult(Enum):
    SUCCESS = "success"
    INVALID_CODE = "invalid_code"
    EXPIRED = "expired"
    LOCKED = "locked"
    NOT_FOUND = "not_found"

class RegistrationRepository(Protocol):
    def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
        """Verify code and password, activate account if valid."""
        ...
```

The existing `PostgresRegistrationRepository` has `claim_email()` but NOT `verify_and_activate()`.

### Architecture Patterns (CRITICAL)

**SELECT FOR UPDATE Pattern:**
```sql
SELECT email, password_hash, verification_code, state, attempt_count, created_at
FROM registrations
WHERE email = %s
  AND state = 'CLAIMED'
FOR UPDATE
```

This locks the row for the duration of the transaction, preventing:
- Concurrent activation attempts
- Race conditions during attempt counting
- Double-activation scenarios

**Atomic State Transition Pattern:**
```sql
-- On SUCCESS
UPDATE registrations
SET state = 'ACTIVE', activated_at = NOW()
WHERE email = %s AND state = 'CLAIMED'

-- On LOCKED (3 failures)
UPDATE registrations
SET state = 'LOCKED', attempt_count = attempt_count + 1, password_hash = NULL
WHERE email = %s AND state = 'CLAIMED'

-- On failure (increment attempt)
UPDATE registrations
SET attempt_count = attempt_count + 1
WHERE email = %s AND state = 'CLAIMED'
```

### Security Implementation (CRITICAL)

**Constant-Time Code Comparison:**
```python
import secrets

# WRONG - timing oracle vulnerability
if stored_code == submitted_code:  # DON'T DO THIS
    ...

# CORRECT - constant-time comparison
if secrets.compare_digest(stored_code.encode(), submitted_code.encode()):
    ...
```

**Constant-Time Password Verification:**
```python
import bcrypt

# bcrypt.checkpw is already constant-time
if bcrypt.checkpw(password.encode(), password_hash.encode()):
    ...
```

**Timing Oracle Prevention:**
```python
def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
    # Fetch registration (or None)
    registration = self._fetch_registration(email)

    # CRITICAL: Always run both comparisons to prevent timing oracle
    # Use dummy values if registration not found
    stored_code = registration.code if registration else "0000"
    stored_hash = registration.password_hash if registration else DUMMY_HASH

    code_valid = secrets.compare_digest(stored_code.encode(), code.encode())
    password_valid = bcrypt.checkpw(password.encode(), stored_hash.encode())

    if registration is None:
        return VerifyResult.NOT_FOUND

    # Continue with checks...
```

**Dummy Hash for Non-Existent Emails:**
```python
# Pre-computed bcrypt hash of "dummy_password" with cost 10
# Used to ensure constant-time comparison even for non-existent emails
DUMMY_BCRYPT_HASH = "$2b$10$..."  # Generate once at module load
```

### Database Schema Reference

```sql
CREATE TABLE registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULLed on expiration/lockout
    verification_code CHAR(4) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'CLAIMED',
    attempt_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);
```

### Testing Strategy

**Integration Tests (this story):**
- Actual verification with PostgreSQL database
- Test all VerifyResult return values
- Test state transitions (CLAIMED -> ACTIVE, CLAIMED -> LOCKED)
- Test attempt counting and lockout at 3
- Test TTL boundary (59s valid, 61s expired)

**Test Fixture Pattern:**
```python
@pytest.fixture
def claimed_registration(pool: ConnectionPool) -> dict:
    """Create a CLAIMED registration for testing."""
    email = "test@example.com"
    password = "secure123"
    code = "1234"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
            (email, password_hash, code)
        )

    return {"email": email, "password": password, "code": code}
```

### Implementation Notes from Story 2.2

From Epic 2 code review:
- Use parameterized queries (no f-strings for SQL)
- Use `with pool.connection() as conn` context manager
- psycopg3 auto-commits unless you use explicit transactions
- For atomic operations spanning SELECT + UPDATE, use explicit transaction control

### Directory Structure After This Story

```
src/adapters/repository/
└── postgres.py   # PostgresRegistrationRepository with verify_and_activate [UPDATED]

tests/integration/
├── test_postgres_repository.py  # Existing tests [UPDATED with verify_and_activate tests]
└── conftest.py                  # Database fixtures
```

### Dependencies

**Story 3.2 Depends On:**
- Story 2.2 (PostgreSQL Repository - Email Claim) - PostgresRegistrationRepository exists
- Story 3.1 (Domain State Machine) - verify_and_activate signature defined in protocol

**Stories Depending on 3.2:**
- Story 3.3 (Activate API Endpoint) - uses verify_and_activate
- Story 3.4 (Timing-Safe Error Responses) - builds on verification flow

### Git Intelligence

Recent commits show Story 3.1 completion:
- `xxx` Implement Story 3.1 Domain State Machine (TrustState, verify_and_activate protocol)

Story 3.1 is in "review" status with 95 unit tests passing.

### References

- [Source: architecture.md#Authentication & Security]
- [Source: architecture.md#Data Architecture]
- [Source: architecture.md#Implementation Patterns]
- [Source: prd.md#FR8-FR12 (Verification and Activation)]
- [Source: prd.md#NFR-S2, NFR-P2 (Constant-time requirements)]
- [Source: epics.md#Story 3.2]
- [Source: Story 3.1 Dev Agent Record (verify_and_activate protocol)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 5 tasks (27 subtasks) completed successfully
- Implemented verify_and_activate method in PostgresRegistrationRepository (AC1, AC2)
- Uses SELECT FOR UPDATE for row-level locking to prevent race conditions (AC2)
- Constant-time code comparison via secrets.compare_digest() (AC3)
- Constant-time password verification via bcrypt.checkpw() (AC4)
- Timing oracle prevention with dummy hash for non-existent emails (AC4)
- TTL check using database time: `created_at > NOW() - INTERVAL '60 seconds'` (AC5)
- Attempt counting with lockout at 3 failures (AC6, AC7)
- State transition CLAIMED -> ACTIVE on success with activated_at timestamp (AC8)
- All VerifyResult return values implemented correctly (AC9)
- Generic INVALID_CODE for both code and password failures for security (AC10)
- Password hash purged on lockout (Data Stewardship)
- Added _DUMMY_BCRYPT_HASH module constant for timing oracle prevention
- Added 13 new integration tests covering all verify_and_activate scenarios
- All 95 unit tests passing
- All 25 integration tests passing
- ruff check and ruff format passing
- Docker port changed to 5433 to avoid conflict with other postgres instances

### File List

- src/adapters/repository/postgres.py (updated - added verify_and_activate method with all security measures)
- src/config/settings.py (updated - changed default database port to 5433)
- docker-compose.yml (updated - changed database port mapping to 5433:5432)
- tests/integration/test_postgres_repository.py (updated - added 13 verify_and_activate integration tests)
