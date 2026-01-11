# Story 3.4: Timing-Safe Error Responses

Status: review

## Story

As a Technical Evaluator,
I want all error responses to have consistent timing,
So that I can verify the system is resistant to timing oracle attacks.

## Acceptance Criteria

1. **AC1: Constant-Time Code Comparison Verified**
   - **Given** I inspect `src/adapters/repository/postgres.py`
   - **When** I examine the code comparison logic
   - **Then** `secrets.compare_digest()` is used for verification code comparison
   - **And** the comparison runs even when email doesn't exist (timing oracle prevention)
   - **And** no early returns bypass the comparison

2. **AC2: Constant-Time Password Verification Verified**
   - **Given** I inspect `src/adapters/repository/postgres.py`
   - **When** I examine the password verification logic
   - **Then** `bcrypt.checkpw()` is used (constant-time built-in)
   - **And** a dummy hash is compared for non-existent emails
   - **And** the verification runs regardless of code validity

3. **AC3: Dummy Hash Implementation Verified**
   - **Given** the `_DUMMY_BCRYPT_HASH` constant exists
   - **When** activation is attempted for non-existent email
   - **Then** bcrypt comparison runs against the dummy hash
   - **And** timing is indistinguishable from valid email lookups
   - **And** the dummy hash has the same cost factor as real hashes (≥10)

4. **AC4: No Early Returns Before Comparisons**
   - **Given** I trace all code paths in `verify_and_activate`
   - **When** I examine the control flow
   - **Then** both `secrets.compare_digest()` and `bcrypt.checkpw()` run before any return
   - **And** state-based decisions happen AFTER both comparisons complete
   - **And** no conditional logic short-circuits the constant-time operations

5. **AC5: Adversarial Timing Tests Created**
   - **Given** I run `pytest tests/adversarial/test_timing_attacks.py`
   - **When** the timing tests execute
   - **Then** tests measure response times for: valid email, non-existent email, wrong code, wrong password
   - **And** tests verify timing variance is within acceptable noise margin
   - **And** tests are marked with `@pytest.mark.adversarial`

6. **AC6: Statistical Timing Analysis**
   - **Given** I measure N activation attempts for each failure mode
   - **When** I compare the response time distributions
   - **Then** mean response times are within 20% of each other
   - **And** no single failure mode is consistently faster/slower
   - **And** bcrypt dominates the response time (masking other variations)

7. **AC7: API Layer Doesn't Leak Timing**
   - **Given** the API endpoint handles all `VerifyResult` cases
   - **When** I examine the activate endpoint
   - **Then** the same code path executes for all failures (no conditional delays)
   - **And** HTTPException is raised uniformly without additional processing
   - **And** no logging or side effects differ between failure modes

8. **AC8: Documentation of Security Measures**
   - **Given** I inspect the codebase
   - **When** I examine the timing-safe implementation
   - **Then** comments explain WHY each constant-time measure exists
   - **And** the CRITICAL comment blocks are present and accurate
   - **And** the security rationale is documented in module docstrings

## Tasks / Subtasks

- [x] Task 1: Verify Existing Constant-Time Implementation (AC: 1, 2, 3, 4)
  - [x] 1.1: Audit `verify_and_activate` for `secrets.compare_digest()` usage
  - [x] 1.2: Audit `verify_and_activate` for `bcrypt.checkpw()` usage
  - [x] 1.3: Verify `_DUMMY_BCRYPT_HASH` has correct cost factor (≥10)
  - [x] 1.4: Trace all code paths to confirm no early returns before comparisons
  - [x] 1.5: Document any gaps found (should be none if Story 3.2 was correct)

- [x] Task 2: Create Adversarial Timing Test Suite (AC: 5, 6)
  - [x] 2.1: Create `tests/adversarial/` directory if not exists
  - [x] 2.2: Create `tests/adversarial/__init__.py`
  - [x] 2.3: Create `tests/adversarial/test_timing_attacks.py`
  - [x] 2.4: Implement timing measurement infrastructure (measure N iterations)
  - [x] 2.5: Test timing for non-existent email vs valid email
  - [x] 2.6: Test timing for wrong code vs wrong password
  - [x] 2.7: Test timing for expired vs locked accounts
  - [x] 2.8: Add statistical analysis for timing variance
  - [x] 2.9: Mark all tests with `@pytest.mark.adversarial`

- [x] Task 3: Verify API Layer Timing Safety (AC: 7)
  - [x] 3.1: Audit activate endpoint for uniform failure handling
  - [x] 3.2: Verify no conditional logging based on failure type
  - [x] 3.3: Confirm HTTPException raised identically for all failures
  - [x] 3.4: Add API-level timing test if needed

- [x] Task 4: Ensure Documentation is Complete (AC: 8)
  - [x] 4.1: Verify CRITICAL comments exist in `verify_and_activate`
  - [x] 4.2: Verify module docstring explains timing-safe design
  - [x] 4.3: Add any missing security rationale comments
  - [x] 4.4: Update architecture.md if timing measures aren't documented

## Dev Notes

### Current State (from Stories 3.2 and 3.3)

Story 3.2 implemented the timing-safe measures in `PostgresRegistrationRepository`:

```python
# Pre-computed bcrypt hash for timing oracle prevention (postgres.py:22)
_DUMMY_BCRYPT_HASH = bcrypt.hashpw(b"dummy_password_for_timing_safety", bcrypt.gensalt(10)).decode()

def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
    # ... fetch row or use dummy values ...

    # CRITICAL: Always run BOTH comparisons for constant-time behavior
    code_valid = secrets.compare_digest(stored_code.encode(), code.encode())
    password_valid = bcrypt.checkpw(password.encode(), stored_hash.encode())

    # Now process results AFTER constant-time operations
    if row is None:
        return VerifyResult.NOT_FOUND
    # ... rest of logic ...
```

Story 3.3 implemented the API endpoint which uniformly handles all failures:

```python
if result == VerifyResult.SUCCESS:
    return ActivateResponse(message="Account activated", email=email)

# All failures return identical generic error (NFR-S4, NFR-P3)
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials or code",
)
```

### Adversarial Testing Strategy

**Timing Test Pattern:**
```python
import statistics
import time

import pytest

@pytest.mark.adversarial
class TestTimingAttacks:
    """Verify constant-time behavior prevents timing oracle attacks."""

    ITERATIONS = 50  # Number of measurements per scenario
    MAX_VARIANCE_RATIO = 0.20  # 20% max difference in mean times

    def measure_activation_time(self, email: str, code: str, password: str) -> float:
        """Measure time for single activation attempt."""
        start = time.perf_counter()
        self.repository.verify_and_activate(email, code, password)
        return time.perf_counter() - start

    def test_nonexistent_email_timing_similar_to_valid(self, repository, pool):
        """Non-existent email timing should be similar to valid email."""
        # Create a valid registration
        # ... setup ...

        # Measure valid email (wrong code)
        valid_times = [self.measure_activation_time("valid@example.com", "0000", "pass")
                       for _ in range(self.ITERATIONS)]

        # Measure non-existent email
        invalid_times = [self.measure_activation_time("nonexistent@example.com", "0000", "pass")
                         for _ in range(self.ITERATIONS)]

        # Statistical comparison
        valid_mean = statistics.mean(valid_times)
        invalid_mean = statistics.mean(invalid_times)

        ratio = abs(valid_mean - invalid_mean) / max(valid_mean, invalid_mean)
        assert ratio < self.MAX_VARIANCE_RATIO, (
            f"Timing difference too large: {ratio:.2%} (valid={valid_mean:.4f}s, invalid={invalid_mean:.4f}s)"
        )
```

### Why Timing Attacks Matter

**Timing Oracle Attack Pattern:**
1. Attacker measures response time for known-invalid email
2. Attacker measures response time for target email
3. If target email is faster → no bcrypt comparison → email doesn't exist
4. If target email is slower → bcrypt ran → email exists
5. Attacker now knows which emails are registered (information disclosure)

**Our Defense:**
- Always run `bcrypt.checkpw()` against either real hash or `_DUMMY_BCRYPT_HASH`
- Always run `secrets.compare_digest()` for code comparison
- bcrypt (~100ms) dominates response time, masking other variations
- All code paths execute both comparisons before returning

### Test Directory Structure After This Story

```
tests/
├── adversarial/           # NEW
│   ├── __init__.py        # NEW
│   └── test_timing_attacks.py  # NEW - Timing oracle attack tests
├── unit/
│   └── ...
└── integration/
    └── ...
```

### Running Adversarial Tests

```bash
# Run only adversarial tests
pytest tests/adversarial/ -v

# Run with marker
pytest -m adversarial -v

# Run all tests including adversarial
pytest tests/ -v
```

### Dependencies

**Story 3.4 Depends On:**
- Story 3.2 (PostgreSQL Repository - Verify and Activate) - timing-safe implementation
- Story 3.3 (Activate API Endpoint) - uniform error handling

**Stories Depending on 3.4:**
- Epic 5 Story 5.3 (Adversarial Tests) - builds on this test infrastructure

### References

- [Source: architecture.md#Authentication & Security]
- [Source: prd.md#NFR-S2 (Constant-time password verification)]
- [Source: prd.md#NFR-P2 (Password verification timing)]
- [Source: prd.md#NFR-P3 (Consistent error timing)]
- [Source: epics.md#Story 3.4]
- [Source: Story 3.2 Dev Agent Record (timing-safe implementation)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 4 tasks (18 subtasks) completed successfully
- Task 1: Verified existing constant-time implementation (AC1-4)
  - `secrets.compare_digest()` used for code comparison at postgres.py:141
  - `bcrypt.checkpw()` used for password verification at postgres.py:142
  - `_DUMMY_BCRYPT_HASH` has cost factor 10 at postgres.py:48
  - Both comparisons run BEFORE any state-based returns (lines 141-142)
- Task 2: Created comprehensive adversarial timing test suite (AC5-6)
  - 8 new adversarial tests in `tests/adversarial/test_timing_attacks.py`
  - Tests measure timing for: nonexistent email, wrong code, wrong password, expired, locked
  - Statistical analysis verifies timing variance within 20% threshold
  - All tests marked with `@pytest.mark.adversarial`
- Task 3: Verified API layer timing safety (AC7)
  - All failures reach identical HTTPException (routes.py:95-98)
  - No conditional logging based on failure type
  - No differing side effects between failure modes
- Task 4: Enhanced documentation (AC8)
  - CRITICAL comments exist at postgres.py:126 and postgres.py:139
  - Enhanced module docstring with timing-safe design rationale
  - architecture.md already documents timing measures
- Bug fix: Fixed NoneType error for LOCKED accounts with NULL password_hash
  - Added fallback to _DUMMY_BCRYPT_HASH when password_hash is NULL (postgres.py:128)
- All 163 tests passing (107 unit + 48 integration + 8 adversarial)
- ruff check and ruff format passing

### File List

- src/adapters/repository/postgres.py (updated - fixed NULL password_hash handling, enhanced module docstring)
- tests/adversarial/test_timing_attacks.py (new - 8 adversarial timing tests)
