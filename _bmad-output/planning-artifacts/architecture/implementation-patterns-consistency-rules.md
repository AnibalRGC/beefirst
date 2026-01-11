# Implementation Patterns & Consistency Rules

## Pattern Categories Defined

**Critical Conflict Points Addressed:** 12 areas where AI agents could make inconsistent choices

These patterns ensure any agent implementing this codebase produces code that:
- Maintains domain purity (zero framework imports)
- Follows consistent naming throughout all layers
- Handles errors in a security-first manner
- Uses idiomatic, modern Python patterns

## Naming Patterns

**Database Naming Conventions:**

| Element | Convention | Example |
|---------|------------|---------|
| Tables | snake_case, plural | `registrations` |
| Columns | snake_case | `password_hash`, `created_at` |
| Constraints | descriptive snake_case | `registrations_email_key` |

**Python Code Naming Conventions:**

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `registration.py`, `postgres.py` |
| Classes | PascalCase | `RegistrationService`, `PostgresRepository` |
| Functions | snake_case | `claim_email()`, `verify_and_activate()` |
| Constants | SCREAMING_SNAKE | `MAX_ATTEMPTS = 3`, `TTL_SECONDS = 60` |
| Type Aliases | PascalCase | `Email = str`, `PasswordHash = str` |
| Private | leading underscore | `_normalize_email()`, `_hash_password()` |

**API JSON Field Naming:**

| Decision | Convention | Rationale |
|----------|------------|-----------|
| Field names | snake_case | No translation layer; matches Python/DB throughout |
| Booleans | lowercase | `"is_active": true` |
| Nulls | explicit | `"activated_at": null` |

**Examples:**
```json
// Request
{"email": "user@example.com", "password": "secret123"}

// Response
{"message": "Verification code sent", "expires_in_seconds": 60}
```

## Structure Patterns

**Domain Layer (Flat Structure):**

```
src/domain/
├── __init__.py
├── registration.py    # Trust State Machine entity + logic
├── ports.py           # Protocol interfaces for infrastructure
└── exceptions.py      # Domain-specific exceptions
```

**Rationale:** Single bounded context (Registration). Flat structure maximizes discoverability for the Technical Evaluator.

**Adapters Layer:**

```
src/adapters/
├── __init__.py
├── repository/
│   ├── __init__.py
│   └── postgres.py    # psycopg3 implementation of RegistrationRepository
└── smtp/
    ├── __init__.py
    └── console.py     # Console-based EmailSender implementation
```

**API Layer:**

```
src/api/
├── __init__.py
├── main.py            # FastAPI app, DI wiring, lifespan
├── routes.py          # /v1/register, /v1/activate endpoints
├── schemas.py         # Pydantic request/response models
└── dependencies.py    # FastAPI Depends() factories
```

**Test Organization:**

```
tests/
├── conftest.py        # Shared fixtures (DB, test client)
├── unit/
│   └── test_registration.py    # Domain logic tests (mocked ports)
├── integration/
│   └── test_repository.py      # PostgreSQL adapter tests
└── adversarial/
    ├── test_race_conditions.py # Truth 1: Unique Claim Lock
    ├── test_timing_attacks.py  # Truth 3: Time-Bounded Proof
    └── test_brute_force.py     # Truth 8: Attempt Limiting
```

**Test Naming Convention:**
- Files: `test_<module>.py`
- Functions: `def test_<action>_<scenario>():`
- Example: `def test_claim_email_normalizes_case():`

## Format Patterns

**API Response Formats:**

**Success Responses (direct Pydantic serialization):**
```python
# POST /v1/register → 201
{"message": "Verification code sent", "expires_in_seconds": 60}

# POST /v1/activate → 200
{"message": "Account activated", "email": "user@example.com"}
```

**Error Responses (generic for security):**
```python
# 409 Conflict (email claimed/active)
{"detail": "Registration failed"}

# 401 Unauthorized (wrong code, password, expired, locked)
{"detail": "Invalid credentials or code"}

# 422 Unprocessable Entity (validation)
{"detail": [{"loc": ["body", "email"], "msg": "invalid email", "type": "value_error"}]}
```

**Date/Time Formats:**

| Context | Format | Example |
|---------|--------|---------|
| Database | `TIMESTAMPTZ` | PostgreSQL native |
| API Response | ISO 8601 | `"2026-01-11T14:30:00Z"` |
| Internal | `datetime.datetime` | Python stdlib |

## Port Interface Patterns

**Port Definition (using `typing.Protocol`):**

```python
# src/domain/ports.py
from typing import Protocol
from enum import Enum

class VerifyResult(Enum):
    SUCCESS = "success"
    INVALID_CODE = "invalid_code"
    EXPIRED = "expired"
    LOCKED = "locked"
    NOT_FOUND = "not_found"

class RegistrationRepository(Protocol):
    def claim_email(self, email: str, password_hash: str, code: str) -> bool:
        """Atomically claim email. Returns True if successful, False if already claimed."""
        ...

    def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
        """Verify code + password, update state atomically. Handles attempt counting."""
        ...

class EmailSender(Protocol):
    def send_verification_code(self, email: str, code: str) -> None:
        """Send verification code to email address."""
        ...
```

**Adapter Implementation (structural subtyping):**

```python
# src/adapters/repository/postgres.py
class PostgresRegistrationRepository:
    """Implements RegistrationRepository protocol via psycopg3."""

    def __init__(self, pool: ConnectionPool):
        self._pool = pool

    def claim_email(self, email: str, password_hash: str, code: str) -> bool:
        # Raw SQL implementation
        ...
```

**Rationale:** Adapters don't inherit from ports. `Protocol` enables structural subtyping—the domain defines what it needs, adapters satisfy the interface implicitly.

## Error Handling Patterns

**Multi-Layer Translation:**

| Layer | Responsibility | Example |
|-------|----------------|---------|
| **Domain** | Define semantic exceptions | `raise EmailAlreadyClaimed(email)` |
| **Adapters** | Catch infra errors → domain exceptions | `except UniqueViolation: raise EmailAlreadyClaimed()` |
| **API** | Catch domain exceptions → HTTP responses | `except EmailAlreadyClaimed: raise HTTPException(409)` |

**Domain Exceptions:**

```python
# src/domain/exceptions.py
class RegistrationError(Exception):
    """Base class for registration domain errors."""
    pass

class EmailAlreadyClaimed(RegistrationError):
    """Email is already in CLAIMED or ACTIVE state."""
    pass

class VerificationFailed(RegistrationError):
    """Code/password mismatch, expired, or locked."""
    pass
```

**API Exception Handling:**

```python
# src/api/routes.py
@app.exception_handler(EmailAlreadyClaimed)
async def handle_email_claimed(request, exc):
    return JSONResponse(status_code=409, content={"detail": "Registration failed"})

@app.exception_handler(VerificationFailed)
async def handle_verification_failed(request, exc):
    return JSONResponse(status_code=401, content={"detail": "Invalid credentials or code"})
```

## Transaction Patterns

| Operation | Pattern | SQL Approach |
|-----------|---------|--------------|
| **Claim Email** | Single atomic INSERT | `INSERT ... ON CONFLICT DO NOTHING` |
| **Verify + Activate** | Row-level lock | `SELECT ... FOR UPDATE` within transaction |
| **Credential Purge** | Lazy on read | `UPDATE ... SET password_hash = NULL` during verify |

## Enforcement Guidelines

**All AI Agents MUST:**

1. **Never import from `adapters/` or `api/` in `domain/`** - Domain stays pure
2. **Use `typing.Protocol` for ports** - Structural subtyping, not ABC inheritance
3. **snake_case everywhere** - Python code, JSON fields, database columns
4. **Generic error messages only** - `"Registration failed"`, `"Invalid credentials or code"`
5. **Explicit SQL** - No query builders, no ORM patterns, no f-strings for queries
6. **Type hints on all public functions** - Enables IDE support and documentation
7. **Parameterized queries only** - `cursor.execute(sql, (param,))` never f-strings
8. **Pass ruff format and check** - All code must pass `ruff format` and `ruff check` before commit

**Pattern Verification:**

| Check | Method |
|-------|--------|
| Domain purity | `grep -r "from src.adapters" src/domain/` should return nothing |
| Code formatting | `ruff format --check src/ tests/` must pass |
| Code linting | `ruff check src/ tests/` must pass |
| Type coverage | `mypy src/` with strict mode |
| Test categories | `pytest tests/adversarial/` runs attack scenarios |
| Coverage target | `pytest --cov=src --cov-fail-under=90` |

## Pattern Examples

**Good Example (Domain):**
```python
# src/domain/registration.py
from dataclasses import dataclass
from .ports import RegistrationRepository, EmailSender
from .exceptions import EmailAlreadyClaimed

@dataclass
class RegistrationService:
    repository: RegistrationRepository
    email_sender: EmailSender

    def register(self, email: str, password: str) -> None:
        normalized = email.strip().lower()
        # ... pure business logic
```

**Anti-Pattern (Domain importing infrastructure):**
```python
# BAD - Never do this in domain/
from psycopg import Connection  # ❌ Infrastructure leak
from fastapi import HTTPException  # ❌ Framework dependency
```

**Good Example (Adapter translating errors):**
```python
# src/adapters/repository/postgres.py
from psycopg.errors import UniqueViolation
from src.domain.exceptions import EmailAlreadyClaimed

def claim_email(self, email: str, password_hash: str, code: str) -> bool:
    try:
        # INSERT ... ON CONFLICT DO NOTHING
        return cursor.rowcount == 1
    except UniqueViolation:
        raise EmailAlreadyClaimed(email)
```

**Anti-Pattern (Leaking infrastructure details):**
```python
# BAD - Never expose raw errors to API
except UniqueViolation as e:
    raise HTTPException(409, detail=str(e))  # ❌ Leaks DB info
```
