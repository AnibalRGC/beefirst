# Story 2.2: PostgreSQL Repository - Email Claim

Status: review

## Story

As a Technical Evaluator,
I want the repository to atomically claim emails preventing race conditions,
So that I can verify concurrent registration attempts are handled correctly.

## Acceptance Criteria

1. **AC1: Repository Implements Protocol**
   - **Given** `src/adapters/repository/postgres.py` exists
   - **When** I inspect the module
   - **Then** `PostgresRegistrationRepository` class exists
   - **And** it implements `RegistrationRepository` protocol from `src/domain/ports.py`
   - **And** it accepts a `ConnectionPool` in its constructor

2. **AC2: Atomic Email Claim with ON CONFLICT**
   - **Given** I inspect the `claim_email()` method
   - **When** I examine the SQL
   - **Then** it uses `INSERT ... ON CONFLICT DO NOTHING` pattern (FR18)
   - **And** it uses parameterized queries with `%s` placeholders (no f-strings)
   - **And** it checks `cursor.rowcount == 1` to determine success
   - **And** returns `True` if claim successful, `False` if email already claimed

3. **AC3: Password Hash Storage**
   - **Given** `claim_email()` receives a password_hash parameter
   - **When** the hash is stored
   - **Then** it is stored directly in the `password_hash` column
   - **And** the hash is already bcrypt-hashed by domain layer (Story 2.1)
   - **And** raw passwords are NEVER passed to repository

4. **AC4: Verification Code Storage**
   - **Given** `claim_email()` receives a code parameter
   - **When** the code is stored
   - **Then** it is stored in the `verification_code` column as plaintext
   - **And** the code is exactly 4 digits

5. **AC5: Concurrent Race Condition Handling**
   - **Given** two concurrent requests try to claim the same email
   - **When** both execute simultaneously
   - **Then** exactly one succeeds (returns `True`)
   - **And** the other fails gracefully (returns `False`)
   - **And** no exceptions are raised
   - **And** database constraint ensures uniqueness

6. **AC6: State Initialization**
   - **Given** a successful email claim
   - **When** the record is inserted
   - **Then** `state` is set to `'CLAIMED'` (default from schema)
   - **And** `attempt_count` is set to `0` (default from schema)
   - **And** `created_at` is set to `NOW()` (default from schema)

## Tasks / Subtasks

- [x] Task 1: Create PostgresRegistrationRepository Class (AC: 1)
  - [x] 1.1: Define `PostgresRegistrationRepository` class with `ConnectionPool` constructor
  - [x] 1.2: Store pool as `self._pool` private attribute
  - [x] 1.3: Add class docstring referencing RegistrationRepository protocol

- [x] Task 2: Implement claim_email Method (AC: 2, 3, 4, 6)
  - [x] 2.1: Add `claim_email(email: str, password_hash: str, code: str) -> bool` method signature
  - [x] 2.2: Write INSERT SQL with ON CONFLICT DO NOTHING
  - [x] 2.3: Use parameterized query with `cursor.execute(sql, (email, password_hash, code))`
  - [x] 2.4: Return `cursor.rowcount == 1` to indicate success/failure
  - [x] 2.5: Add method docstring explaining atomic claim semantics

- [x] Task 3: Write Integration Tests (AC: 2, 5, 6)
  - [x] 3.1: Create `tests/integration/test_postgres_repository.py`
  - [x] 3.2: Create pytest fixture for database connection with transaction rollback
  - [x] 3.3: Test successful email claim returns True
  - [x] 3.4: Test duplicate email claim returns False (not exception)
  - [x] 3.5: Test concurrent claims - exactly one succeeds
  - [x] 3.6: Test record created with correct state ('CLAIMED') and attempt_count (0)
  - [x] 3.7: Test parameterized queries prevent SQL injection

- [x] Task 4: Update Exports and Verify (AC: all)
  - [x] 4.1: Export `PostgresRegistrationRepository` from `src/adapters/repository/__init__.py`
  - [x] 4.2: Verify protocol compliance (implements RegistrationRepository)
  - [x] 4.3: Run all tests to ensure no regressions

## Dev Notes

### Current State (from Story 2.1)

The domain layer is complete with:
- `RegistrationRepository` protocol in `src/domain/ports.py`
- `RegistrationService` using the protocol via dependency injection
- `claim_email(email: str, password_hash: str, code: str) -> bool` signature defined

The postgres.py file exists with:
- `run_migrations()` function for schema setup
- Database connection pool pattern established

### Architecture Patterns (CRITICAL)

From `architecture.md` - Adapter Implementation Pattern:

```python
# src/adapters/repository/postgres.py
from psycopg_pool import ConnectionPool

from src.domain.ports import RegistrationRepository

class PostgresRegistrationRepository:
    """
    Implements RegistrationRepository protocol via psycopg3.

    Uses structural subtyping - no explicit inheritance from Protocol.
    """

    def __init__(self, pool: ConnectionPool):
        self._pool = pool

    def claim_email(self, email: str, password_hash: str, code: str) -> bool:
        """
        Atomically claim an email address for registration.

        Uses INSERT ... ON CONFLICT DO NOTHING for atomic claim.
        Returns True if claim successful, False if email already claimed.
        """
        sql = """
            INSERT INTO registrations (email, password_hash, verification_code)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """

        with self._pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (email, password_hash, code))
                conn.commit()
                return cursor.rowcount == 1
```

### SQL Pattern Details

**INSERT ... ON CONFLICT DO NOTHING:**
- This is the atomic claim pattern that prevents race conditions
- If email already exists, the INSERT silently does nothing
- `cursor.rowcount` is 1 if inserted, 0 if conflict occurred
- No need to SELECT first - single atomic operation

**Parameterized Queries:**
- ALWAYS use `%s` placeholders with tuple of values
- NEVER use f-strings or string formatting for SQL
- psycopg3 handles proper escaping and type conversion

```python
# CORRECT
cursor.execute("INSERT INTO t (a) VALUES (%s)", (value,))

# WRONG - SQL injection risk
cursor.execute(f"INSERT INTO t (a) VALUES ('{value}')")
```

### Database Schema Reference

From `migrations/001_create_registrations.sql`:

```sql
CREATE TABLE IF NOT EXISTS registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    verification_code CHAR(4) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'CLAIMED',
    attempt_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);
```

Key constraints:
- `email UNIQUE` - enforces uniqueness at database level
- `state DEFAULT 'CLAIMED'` - no need to set in INSERT
- `attempt_count DEFAULT 0` - no need to set in INSERT
- `created_at DEFAULT NOW()` - database timestamp, no application time

### Testing Pattern

Integration tests should use real database with transaction rollback:

```python
# tests/integration/test_postgres_repository.py
import pytest
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.config.settings import get_settings


@pytest.fixture
def pool():
    """Create connection pool for tests."""
    settings = get_settings()
    pool = ConnectionPool(conninfo=settings.database_url, min_size=1, max_size=5)
    yield pool
    pool.close()


@pytest.fixture
def repository(pool):
    """Create repository instance."""
    return PostgresRegistrationRepository(pool)


@pytest.fixture(autouse=True)
def clean_database(pool):
    """Clean registrations table before each test."""
    with pool.connection() as conn:
        conn.execute("DELETE FROM registrations")
        conn.commit()
    yield


class TestClaimEmail:
    def test_claim_email_success(self, repository):
        """Claiming unclaimed email returns True."""
        result = repository.claim_email(
            email="test@example.com",
            password_hash="$2b$10$hashedpassword",
            code="1234"
        )
        assert result is True

    def test_claim_email_duplicate_returns_false(self, repository):
        """Claiming already-claimed email returns False."""
        repository.claim_email("test@example.com", "$2b$10$hash1", "1234")
        result = repository.claim_email("test@example.com", "$2b$10$hash2", "5678")
        assert result is False
```

### Concurrent Test Pattern

Testing race conditions requires threading:

```python
import threading
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_claims_exactly_one_succeeds(repository):
    """When two concurrent claims for same email, exactly one succeeds."""
    results = []

    def claim():
        result = repository.claim_email("race@example.com", "$2b$10$hash", "1234")
        results.append(result)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(claim) for _ in range(2)]
        for f in futures:
            f.result()

    assert results.count(True) == 1
    assert results.count(False) == 1
```

### Directory Structure After This Story

```
src/adapters/repository/
├── __init__.py                   # Export PostgresRegistrationRepository
└── postgres.py                   # run_migrations() + PostgresRegistrationRepository [UPDATED]

tests/integration/
├── test_openapi.py               # Existing from Epic 1
└── test_postgres_repository.py   # [NEW] Repository integration tests
```

### Security Considerations

1. **No Raw Passwords**
   - Repository receives pre-hashed password from domain layer
   - NEVER hash in repository - that's domain responsibility

2. **Parameterized Queries**
   - All SQL uses `%s` placeholders
   - Prevents SQL injection attacks

3. **Atomic Operations**
   - ON CONFLICT DO NOTHING is atomic
   - No race condition window between SELECT and INSERT

### Previous Story Learnings

From Story 2.1:
- Domain layer provides hashed passwords (bcrypt cost >= 10)
- Email is normalized (lowercase, stripped) before reaching repository
- Verification code is 4-digit string from secrets module

From Epic 1 Code Review:
- Use pytest fixtures for test isolation
- Run ruff check and format before done
- Transaction management is critical

### Dependencies

**Story 2.2 depends on:**
- Story 2.1 (Domain layer with RegistrationRepository protocol) ✅ Complete

**Stories depending on 2.2:**
- Story 2.4 (Register API Endpoint) - uses repository via DI
- Story 3.2 (Repository - Verify and Activate) - extends this class

### References

- [Source: architecture.md#Data Architecture]
- [Source: architecture.md#Transaction Patterns]
- [Source: architecture.md#Port Interface Patterns]
- [Source: prd.md#FR3, FR6, FR18, FR23]
- [Source: prd.md#NFR-S1, NFR-M3]
- [Source: epics.md#Story 2.2]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation proceeded without issues.

### Completion Notes List

1. Created `PostgresRegistrationRepository` class implementing `RegistrationRepository` protocol via structural subtyping
2. Implemented `claim_email()` method using `INSERT ... ON CONFLICT DO NOTHING` pattern for atomic email claims
3. Used parameterized queries with `%s` placeholders to prevent SQL injection
4. Returns `cursor.rowcount == 1` to determine claim success (True) or duplicate (False)
5. Created comprehensive integration tests (12 tests) covering:
   - Successful email claim
   - Duplicate email detection (returns False, not exception)
   - Concurrent race condition handling (exactly one succeeds)
   - Record state verification (CLAIMED state, 0 attempt_count, timestamps)
   - SQL injection prevention via parameterized queries
6. Fixed Ruff SIM117 linting error: combined nested `with` statements into single statement
7. All 75 unit tests passing; integration tests require running PostgreSQL (`docker-compose up`)

### File List

**Modified:**
- `src/adapters/repository/postgres.py` - Added `PostgresRegistrationRepository` class with `claim_email()` method
- `src/adapters/repository/__init__.py` - Added export for `PostgresRegistrationRepository`

**Created:**
- `tests/integration/test_postgres_repository.py` - 12 integration tests for repository operations
