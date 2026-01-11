# Story 2.1: Domain Registration Service & Port Interfaces

Status: review

## Story

As a Technical Evaluator,
I want the domain layer to define registration logic with zero framework imports,
So that I can verify the Hexagonal Architecture purity.

## Acceptance Criteria

1. **AC1: Domain Purity - Zero Framework Imports**
   - **Given** I inspect `src/domain/registration.py`
   - **When** I check the imports
   - **Then** there are NO imports from FastAPI, Pydantic, or psycopg3
   - **And** only Python stdlib imports are allowed (dataclasses, typing, secrets, enum)

2. **AC2: RegistrationService Class**
   - **Given** `src/domain/registration.py` exists
   - **When** I inspect the module
   - **Then** a `RegistrationService` class exists as a dataclass
   - **And** it has `repository: RegistrationRepository` field (port injection)
   - **And** it has `email_sender: EmailSender` field (port injection)
   - **And** it has `register(email: str, password: str) -> None` method

3. **AC3: Email Normalization Logic**
   - **Given** an email with mixed case and whitespace
   - **When** the `register()` method processes it
   - **Then** the email is normalized: `strip()` + `lower()`
   - **And** `"  User@Example.COM  "` becomes `"user@example.com"`

4. **AC4: Verification Code Generation**
   - **Given** registration is initiated
   - **When** a verification code is generated
   - **Then** it uses `secrets.choice()` for cryptographic randomness (NFR-S3)
   - **And** the code is exactly 4 digits (`0000` to `9999`)
   - **And** the code is a string (preserves leading zeros)

5. **AC5: Password Hashing**
   - **Given** registration is initiated
   - **When** the password is prepared for storage
   - **Then** it is hashed using bcrypt with cost factor >= 10 (NFR-S1)
   - **And** the raw password is never stored or logged

6. **AC6: RegistrationRepository Protocol**
   - **Given** `src/domain/ports.py` exists
   - **When** I inspect the module
   - **Then** `RegistrationRepository` protocol is defined using `typing.Protocol`
   - **And** it has `claim_email(email: str, password_hash: str, code: str) -> bool` method
   - **And** method returns `True` if claim successful, `False` if email already claimed

7. **AC7: EmailSender Protocol**
   - **Given** `src/domain/ports.py` exists
   - **When** I inspect the module
   - **Then** `EmailSender` protocol is defined using `typing.Protocol`
   - **And** it has `send_verification_code(email: str, code: str) -> None` method

8. **AC8: Domain Exceptions**
   - **Given** `src/domain/exceptions.py` exists
   - **When** I inspect the module
   - **Then** `RegistrationError` base exception exists
   - **And** `EmailAlreadyClaimed` exception exists (raised when claim fails)
   - **And** exceptions have zero infrastructure imports

## Tasks / Subtasks

- [x] Task 1: Implement Port Interfaces (AC: 6, 7)
  - [x] 1.1: Define `VerifyResult` enum in ports.py (SUCCESS, INVALID_CODE, EXPIRED, LOCKED, NOT_FOUND)
  - [x] 1.2: Define `RegistrationRepository` protocol with `claim_email()` method signature
  - [x] 1.3: Define `EmailSender` protocol with `send_verification_code()` method signature
  - [x] 1.4: Verify zero framework imports in ports.py

- [x] Task 2: Implement Domain Exceptions (AC: 8)
  - [x] 2.1: Define `RegistrationError` base exception class
  - [x] 2.2: Define `EmailAlreadyClaimed` exception inheriting from `RegistrationError`
  - [x] 2.3: Define `VerificationFailed` exception for future use (Story 3.1)
  - [x] 2.4: Verify zero framework imports in exceptions.py

- [x] Task 3: Implement RegistrationService (AC: 1, 2, 3, 4, 5)
  - [x] 3.1: Create `RegistrationService` as a dataclass with port fields
  - [x] 3.2: Implement private `_normalize_email()` method (strip + lowercase)
  - [x] 3.3: Implement private `_generate_verification_code()` using secrets module
  - [x] 3.4: Implement private `_hash_password()` using bcrypt (cost >= 10)
  - [x] 3.5: Implement `register()` method orchestrating the registration flow
  - [x] 3.6: Raise `EmailAlreadyClaimed` when repository returns `False`
  - [x] 3.7: Verify zero framework imports in registration.py

- [x] Task 4: Write Unit Tests (AC: all)
  - [x] 4.1: Create `tests/unit/test_registration_service.py`
  - [x] 4.2: Test email normalization with various inputs
  - [x] 4.3: Test verification code generation (4 digits, cryptographic)
  - [x] 4.4: Test password hashing (bcrypt, cost >= 10)
  - [x] 4.5: Test successful registration flow with mocked ports
  - [x] 4.6: Test `EmailAlreadyClaimed` raised when claim fails
  - [x] 4.7: Verify domain purity (grep for framework imports)

## Dev Notes

### Current State (from Epic 1)

The domain layer files exist as stubs:

```
src/domain/
├── __init__.py       # Package initialization
├── registration.py   # Stub with docstring only
├── ports.py          # Stub with docstring only
└── exceptions.py     # Stub with docstring only
```

### Architecture Patterns (CRITICAL)

From `architecture.md` - Implementation Patterns & Consistency Rules:

**Port Definition Pattern (using `typing.Protocol`):**

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

class EmailSender(Protocol):
    def send_verification_code(self, email: str, code: str) -> None:
        """Send verification code to email address."""
        ...
```

**Domain Service Pattern:**

```python
# src/domain/registration.py
import secrets
from dataclasses import dataclass

import bcrypt

from .ports import RegistrationRepository, EmailSender
from .exceptions import EmailAlreadyClaimed

@dataclass
class RegistrationService:
    repository: RegistrationRepository
    email_sender: EmailSender

    def register(self, email: str, password: str) -> None:
        normalized_email = self._normalize_email(email)
        password_hash = self._hash_password(password)
        code = self._generate_verification_code()

        claimed = self.repository.claim_email(normalized_email, password_hash, code)
        if not claimed:
            raise EmailAlreadyClaimed(normalized_email)

        self.email_sender.send_verification_code(normalized_email, code)

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def _generate_verification_code(self) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(4))

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()
```

**Exception Pattern:**

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

### Domain Purity Verification

**CRITICAL: Zero Framework Imports Rule (NFR-M1)**

Run this command to verify domain purity after implementation:

```bash
grep -rE "from (fastapi|pydantic|psycopg)" src/domain/
```

This should return **nothing**. Any output indicates a violation.

### Allowed Imports in Domain

Only these Python stdlib and bcrypt are allowed:

```python
# Allowed in src/domain/
from dataclasses import dataclass
from typing import Protocol
from enum import Enum
import secrets
import bcrypt  # Only cryptographic library exception - bcrypt for password hashing
```

### bcrypt Library Notes

bcrypt is the **only** external library allowed in domain because:
1. It's a cryptographic primitive, not a framework
2. Required by NFR-S1 (bcrypt with cost >= 10)
3. Has constant-time comparison built-in

**Version:** bcrypt>=4.0.0 (already in requirements.txt)

**Cost Factor:** MUST use `rounds=10` or higher per NFR-S1

```python
# Correct
bcrypt.gensalt(rounds=10)

# WRONG - default is 12, but being explicit is better
bcrypt.gensalt()
```

### Testing Pattern

Unit tests should mock the ports:

```python
# tests/unit/test_registration_service.py
import pytest
from unittest.mock import Mock
from src.domain.registration import RegistrationService
from src.domain.exceptions import EmailAlreadyClaimed

class TestRegistrationService:
    def test_register_normalizes_email(self):
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("  USER@EXAMPLE.COM  ", "password123")

        # Verify normalized email was passed to repository
        call_args = repo.claim_email.call_args
        assert call_args[0][0] == "user@example.com"

    def test_register_raises_when_claim_fails(self):
        repo = Mock()
        repo.claim_email.return_value = False
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)

        with pytest.raises(EmailAlreadyClaimed):
            service.register("user@example.com", "password123")
```

### Security Considerations

1. **Password Hashing (NFR-S1)**
   - Use bcrypt with cost factor >= 10
   - NEVER log raw passwords
   - Hash before any storage/transmission

2. **Verification Code (NFR-S3)**
   - Use `secrets.choice()` for cryptographic randomness
   - NOT `random.choice()` which is predictable

3. **Email Normalization (FR2)**
   - Prevents identity confusion attacks
   - `User@Example.com` and `user@example.com` must be the same identity

### Directory Structure After This Story

```
src/domain/
├── __init__.py       # Export public symbols
├── registration.py   # RegistrationService with register() method [UPDATED]
├── ports.py          # Protocol interfaces [UPDATED]
└── exceptions.py     # Domain exceptions [UPDATED]
```

### Previous Epic Learnings (Epic 1 Code Review)

From Epic 1 code review:
- Always use `collections.abc.AsyncGenerator` not `typing.AsyncGenerator`
- Run `ruff check --fix` and `ruff format` before considering done
- Use pytest fixtures for test isolation, not module-level clients
- Migration files should have transaction wrappers (BEGIN...COMMIT)

### Dependencies

**Story 2.1 is independent** - no dependencies on other Epic 2 stories.

Epic 2 stories depend on this story:
- Story 2.2 (PostgreSQL Repository) implements `RegistrationRepository` protocol
- Story 2.3 (Console Email Sender) implements `EmailSender` protocol
- Story 2.4 (Register API Endpoint) uses `RegistrationService`

### References

- [Source: architecture.md#Port Interface Patterns]
- [Source: architecture.md#Implementation Patterns & Consistency Rules]
- [Source: prd.md#FR1, FR2, FR3, FR4, FR23]
- [Source: prd.md#NFR-S1, NFR-S3, NFR-M1, NFR-M2]
- [Source: epics.md#Story 2.1]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 4 tasks (22 subtasks) completed successfully
- Implemented pure domain layer with zero framework imports (NFR-M1 satisfied)
- `RegistrationService` dataclass with port injection pattern
- Email normalization: strip() + lower() applied in `_normalize_email()`
- Verification code generation using `secrets.choice()` for cryptographic randomness
- Password hashing using bcrypt with explicit cost factor 10 (NFR-S1 satisfied)
- Protocol interfaces defined: `RegistrationRepository`, `EmailSender`, `VerifyResult` enum
- Domain exceptions: `RegistrationError` base, `EmailAlreadyClaimed`, `VerificationFailed`
- 38 new unit tests covering all acceptance criteria
- Domain purity verified via grep tests (no FastAPI, Pydantic, or psycopg imports)
- All 75 tests passing (38 new + 37 existing from Epic 1)
- ruff check and ruff format passing

### File List

- src/domain/__init__.py (updated - added exports)
- src/domain/ports.py (updated - VerifyResult enum, RegistrationRepository, EmailSender protocols)
- src/domain/exceptions.py (updated - RegistrationError, EmailAlreadyClaimed, VerificationFailed)
- src/domain/registration.py (updated - RegistrationService with register(), _normalize_email(), _generate_verification_code(), _hash_password())
- tests/unit/test_registration_service.py (created - 20 tests for RegistrationService)
- tests/unit/test_domain_ports.py (created - 18 tests for ports, exceptions, domain purity)
