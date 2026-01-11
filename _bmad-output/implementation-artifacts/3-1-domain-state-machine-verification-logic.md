# Story 3.1: Domain State Machine & Verification Logic

Status: review

## Story

As a Technical Evaluator,
I want the domain to enforce Trust State Machine rules with forward-only transitions,
So that I can verify the state machine invariants are protected in pure domain code.

## Acceptance Criteria

1. **AC1: TrustState Enum Definition**
   - **Given** I inspect `src/domain/registration.py` or `src/domain/ports.py`
   - **When** I look for state definitions
   - **Then** a `TrustState` enum exists with values: CLAIMED, ACTIVE, EXPIRED, LOCKED (FR13)
   - **And** the enum uses `str` mixin for JSON serialization compatibility
   - **And** states are ordered to represent forward-only progression

2. **AC2: verify_and_activate Method Exists**
   - **Given** `src/domain/registration.py` exists
   - **When** I inspect the `RegistrationService` class
   - **Then** a `verify_and_activate(email: str, code: str, password: str) -> VerifyResult` method exists
   - **And** it accepts email, verification code, and password parameters
   - **And** it returns a `VerifyResult` enum indicating success or specific failure

3. **AC3: Code Match Verification (FR8)**
   - **Given** a CLAIMED registration with verification code "1234"
   - **When** `verify_and_activate()` is called with code "1234"
   - **Then** code comparison uses `secrets.compare_digest()` for constant-time comparison (NFR-S2)
   - **And** code "1234" matches successfully
   - **When** `verify_and_activate()` is called with code "5678"
   - **Then** returns `VerifyResult.INVALID_CODE`

4. **AC4: Password Match Verification (FR9)**
   - **Given** a CLAIMED registration with hashed password
   - **When** `verify_and_activate()` is called with correct password
   - **Then** password verification uses bcrypt's built-in constant-time comparison
   - **And** verification succeeds
   - **When** `verify_and_activate()` is called with wrong password
   - **Then** returns `VerifyResult.INVALID_CODE` (generic error, same as code mismatch)

5. **AC5: 60-Second TTL Verification (FR10)**
   - **Given** a CLAIMED registration created 59 seconds ago
   - **When** `verify_and_activate()` is called within 60 seconds
   - **Then** verification can succeed (if code and password match)
   - **Given** a CLAIMED registration created 61 seconds ago
   - **When** `verify_and_activate()` is called
   - **Then** returns `VerifyResult.EXPIRED`
   - **And** TTL check uses database time: `created_at > NOW() - INTERVAL '60 seconds'`

6. **AC6: Attempt Limit Verification (FR11)**
   - **Given** a CLAIMED registration with attempt_count < 3
   - **When** `verify_and_activate()` is called with wrong code
   - **Then** attempt_count is incremented
   - **Given** a CLAIMED registration with attempt_count = 3
   - **When** `verify_and_activate()` is called (even with correct code)
   - **Then** returns `VerifyResult.LOCKED`
   - **And** state transitions to LOCKED (FR16)

7. **AC7: CLAIMED to ACTIVE Transition (FR12)**
   - **Given** a CLAIMED registration with valid code, password, within TTL, attempts < 3
   - **When** `verify_and_activate()` is called
   - **Then** state transitions from CLAIMED to ACTIVE
   - **And** `activated_at` timestamp is set using database time
   - **And** returns `VerifyResult.SUCCESS`

8. **AC8: Forward-Only State Transitions (FR14)**
   - **Given** a registration in ACTIVE state
   - **When** any operation attempts to change state backwards
   - **Then** the operation is rejected (no ACTIVE -> CLAIMED allowed)
   - **And** state can only move forward: CLAIMED -> ACTIVE, CLAIMED -> EXPIRED, CLAIMED -> LOCKED
   - **And** ACTIVE is a terminal state (no further transitions)

9. **AC9: Domain Purity Maintained**
   - **Given** I inspect `src/domain/registration.py`
   - **When** I check the imports
   - **Then** there are NO imports from FastAPI, Pydantic, or psycopg3
   - **And** only Python stdlib imports are allowed (plus bcrypt)
   - **And** TTL and attempt limit are passed to repository (not hardcoded in domain)

10. **AC10: RegistrationRepository Protocol Extended**
    - **Given** `src/domain/ports.py` exists
    - **When** I inspect `RegistrationRepository` protocol
    - **Then** `verify_and_activate(email: str, code: str, password: str) -> VerifyResult` method exists
    - **And** the method signature matches the domain service method
    - **And** the protocol handles atomicity (SELECT FOR UPDATE in implementation)

## Tasks / Subtasks

- [x] Task 1: Define TrustState Enum (AC: 1)
  - [x] 1.1: Add `TrustState` enum to `src/domain/ports.py` with CLAIMED, ACTIVE, EXPIRED, LOCKED
  - [x] 1.2: Use `str` mixin for JSON serialization: `class TrustState(str, Enum)`
  - [x] 1.3: Document state transition rules in docstring
  - [x] 1.4: Verify zero framework imports maintained

- [x] Task 2: Extend RegistrationRepository Protocol (AC: 10)
  - [x] 2.1: Add `verify_and_activate(email: str, code: str, password: str) -> VerifyResult` to protocol
  - [x] 2.2: Document method contract: atomic verification with row locking
  - [x] 2.3: Document return values for each failure scenario
  - [x] 2.4: Document that implementation handles: code match, password match, TTL, attempts

- [x] Task 3: Implement verify_and_activate in RegistrationService (AC: 2, 9)
  - [x] 3.1: Add `verify_and_activate(email: str, code: str, password: str) -> VerifyResult` method
  - [x] 3.2: Normalize email before passing to repository
  - [x] 3.3: Delegate actual verification to repository (repository handles atomicity)
  - [x] 3.4: Return VerifyResult from repository directly
  - [x] 3.5: Verify no framework imports added

- [x] Task 4: Write Unit Tests for Domain Logic (AC: 1, 2, 8, 9)
  - [x] 4.1: Test TrustState enum has all required states
  - [x] 4.2: Test TrustState is JSON serializable (str mixin)
  - [x] 4.3: Test verify_and_activate calls repository with normalized email
  - [x] 4.4: Test verify_and_activate returns repository result unchanged
  - [x] 4.5: Test domain purity maintained (grep test for imports)

- [x] Task 5: Document Forward-Only Transition Rules (AC: 8)
  - [x] 5.1: Add transition diagram in domain docstring
  - [x] 5.2: Document valid transitions: CLAIMED->ACTIVE, CLAIMED->EXPIRED, CLAIMED->LOCKED
  - [x] 5.3: Document invalid transitions: any backward movement
  - [x] 5.4: Note: actual enforcement happens in repository SQL (next story)

## Dev Notes

### Current State (from Epic 2)

The domain layer currently has:

```
src/domain/
├── __init__.py       # Package initialization
├── registration.py   # RegistrationService with register() method
├── ports.py          # VerifyResult enum, RegistrationRepository, EmailSender protocols
└── exceptions.py     # RegistrationError, EmailAlreadyClaimed, VerificationFailed
```

**VerifyResult enum already exists** with SUCCESS, INVALID_CODE, EXPIRED, LOCKED, NOT_FOUND values.

### Architecture Patterns (CRITICAL)

From `architecture.md` - Story 3.1 specifically requires:

**Trust State Machine States (FR13):**
```python
class TrustState(str, Enum):
    """
    Trust State Machine states for registration lifecycle.

    State Transitions (forward-only):
    - CLAIMED -> ACTIVE (successful verification)
    - CLAIMED -> EXPIRED (60-second TTL exceeded)
    - CLAIMED -> LOCKED (3 failed attempts)

    Terminal States:
    - ACTIVE: Registration complete, no further transitions
    - EXPIRED: Can be released for re-registration
    - LOCKED: Can be released for re-registration
    """
    CLAIMED = "CLAIMED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    LOCKED = "LOCKED"
```

**verify_and_activate Method Pattern:**
```python
def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
    """
    Verify code and password, activate if valid.

    Verification checks (all must pass):
    1. Code matches (constant-time comparison)
    2. Password matches (bcrypt constant-time)
    3. Within 60-second TTL
    4. Fewer than 3 failed attempts

    Args:
        email: User's email (will be normalized)
        code: 4-digit verification code
        password: User's password

    Returns:
        VerifyResult indicating success or specific failure
    """
    normalized_email = self._normalize_email(email)
    return self.repository.verify_and_activate(normalized_email, code, password)
```

**Key Design Decision: Repository Handles Atomicity**

The domain service delegates verification to the repository because:
1. All checks must happen atomically within a database transaction
2. Row-level locking (`SELECT FOR UPDATE`) prevents race conditions
3. TTL check uses database time (`NOW()`) not application time
4. Attempt count increment and state transition must be atomic

### Security Implementation Notes

**Constant-Time Comparison (NFR-S2, NFR-P2):**
- Code comparison: `secrets.compare_digest(a.encode(), b.encode())`
- Password comparison: `bcrypt.checkpw()` (constant-time built-in)
- Both checks MUST run even for non-existent emails (timing oracle prevention)

**Generic Error Messages (NFR-S4):**
- Same `VerifyResult.INVALID_CODE` for wrong code OR wrong password
- Prevents enumeration of valid email/code combinations
- API layer will translate all failures to same HTTP response

**TTL Enforcement at Database Level:**
```sql
-- Check within repository, not domain
WHERE created_at > NOW() - INTERVAL '60 seconds'
```

### Testing Strategy

**Unit Tests (this story):**
- TrustState enum values and serialization
- verify_and_activate method signature
- Email normalization before repository call
- Repository result passthrough
- Domain purity verification

**Integration Tests (Story 3.2):**
- Actual verification with database
- Atomic state transitions
- Row locking under concurrent access
- TTL boundary testing (59s vs 61s)

**Adversarial Tests (Epic 5):**
- Timing attack resistance
- Brute force protection
- Race condition handling

### Directory Structure After This Story

```
src/domain/
├── __init__.py       # Export TrustState
├── registration.py   # RegistrationService with verify_and_activate() [UPDATED]
├── ports.py          # TrustState enum, extended RegistrationRepository [UPDATED]
└── exceptions.py     # Unchanged
```

### Dependencies

**Story 3.1 Depends On:**
- Story 2.1 (Domain Registration Service) - RegistrationService exists

**Stories Depending on 3.1:**
- Story 3.2 (PostgreSQL Repository - Verify and Activate) - implements verify_and_activate
- Story 3.3 (Activate API Endpoint) - uses verify_and_activate
- Story 3.4 (Timing-Safe Error Responses) - builds on verification flow

### Implementation Notes from Previous Stories

From Epic 2 code review (Story 2.1-2.4):
- Domain purity is strictly enforced - no framework imports
- `secrets.compare_digest()` required for constant-time string comparison
- Password verification uses bcrypt's built-in constant-time comparison
- All error messages must be generic to prevent information disclosure
- Repository handles atomicity via `INSERT ... ON CONFLICT DO NOTHING`
- Email normalization: `email.strip().lower()`

### Git Intelligence

Recent commits show Epic 2 completion with code review fixes:
- `847a283` Fix Epic 2 code review issues
- `a4faa69` Implement register api endpoint
- `bea7ba5` Implement console email sender adapter

All Epic 2 stories are in "review" status and code patterns are established.

### References

- [Source: architecture.md#Authentication & Security]
- [Source: architecture.md#Port Interface Patterns]
- [Source: architecture.md#Transaction Patterns]
- [Source: prd.md#FR7-FR14 (Verification and State Management)]
- [Source: prd.md#NFR-S2, NFR-P2, NFR-P3 (Constant-time requirements)]
- [Source: epics.md#Story 3.1]
- [Source: epics.md#Epic 3 Overview]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 5 tasks (19 subtasks) completed successfully
- Implemented TrustState enum with str mixin for JSON serialization (AC1)
- Extended RegistrationRepository protocol with verify_and_activate method (AC10)
- Implemented verify_and_activate in RegistrationService with email normalization (AC2)
- Added 8 new TrustState tests + 8 new verify_and_activate tests = 16 new unit tests
- Domain purity maintained - zero framework imports (AC9)
- Forward-only transition rules documented in module docstring (AC8)
- TrustState exported from domain package __init__.py
- All 95 unit tests passing
- ruff check and ruff format passing

### File List

- src/domain/__init__.py (updated - added TrustState export)
- src/domain/ports.py (updated - added TrustState enum, extended RegistrationRepository with verify_and_activate)
- src/domain/registration.py (updated - added verify_and_activate method, added Trust State Machine documentation)
- tests/unit/test_domain_ports.py (updated - added 8 TrustState tests, 3 verify_and_activate protocol tests)
- tests/unit/test_registration_service.py (updated - added 8 verify_and_activate service tests)
