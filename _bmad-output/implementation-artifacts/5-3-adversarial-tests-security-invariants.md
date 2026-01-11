# Story 5.3: Adversarial Tests for Security Invariants

Status: review

## Story

As a Technical Evaluator,
I want dedicated adversarial tests proving security properties,
So that I can verify the system handles attack scenarios correctly.

## Acceptance Criteria

1. **AC1: Race Condition Tests (FR18)**
   - **Given** I run `pytest tests/adversarial/`
   - **When** `test_race_conditions.py` executes
   - **Then** tests prove concurrent claims are handled atomically
   - **And** tests verify exactly one concurrent registration succeeds
   - **And** tests verify no data corruption occurs

2. **AC2: Timing Attack Tests (NFR-P2, NFR-P3)**
   - **Given** I run timing attack tests
   - **When** `test_timing_attacks.py` executes
   - **Then** tests prove constant-time responses regardless of:
     - Valid email vs non-existent email
     - Correct password vs wrong password
     - Correct code vs wrong code
   - **And** response time variance is statistically insignificant

3. **AC3: Brute Force Tests (FR16, FR20)**
   - **Given** I run brute force protection tests
   - **When** `test_brute_force.py` executes
   - **Then** tests prove 3-strike lockout works correctly
   - **And** tests verify account locks after 3 failed attempts
   - **And** tests verify locked accounts remain locked with correct credentials

4. **AC4: Adversarial Test Markers (NFR-T4)**
   - **Given** all adversarial tests
   - **When** tests are inspected
   - **Then** tests are marked with `@pytest.mark.adversarial`
   - **And** tests can be run separately: `pytest -m adversarial`

5. **AC5: Test Organization**
   - **Given** the adversarial test directory
   - **When** I inspect `tests/adversarial/`
   - **Then** tests are organized by attack type:
     - `test_race_conditions.py` - Concurrent access attacks
     - `test_timing_attacks.py` - Timing oracle attacks
     - `test_brute_force.py` - Brute force attacks

6. **AC6: Statistical Timing Analysis**
   - **Given** timing attack tests
   - **When** multiple samples are collected
   - **Then** tests use statistical methods (mean, std dev) to compare timings
   - **And** tests have appropriate sample sizes for reliability

## Tasks / Subtasks

- [x] Task 1: Audit Existing Adversarial Test Coverage (AC: 1-6)
  - [x] 1.1: Review tests/adversarial/test_timing_attacks.py
  - [x] 1.2: Check if test_race_conditions.py exists
  - [x] 1.3: Check if test_brute_force.py exists
  - [x] 1.4: Identify gaps in adversarial coverage
  - [x] 1.5: Document existing adversarial tests

- [x] Task 2: Create/Verify Race Condition Tests (AC: 1)
  - [x] 2.1: Create test_race_conditions.py if not exists
  - [x] 2.2: Add test_concurrent_registration_exactly_one_succeeds
  - [x] 2.3: Add test_concurrent_activation_no_double_activation
  - [x] 2.4: Add test_concurrent_reregistration_atomic

- [x] Task 3: Verify Timing Attack Tests (AC: 2, 6)
  - [x] 3.1: Confirm TestTimingAttacks class exists
  - [x] 3.2: Verify test covers non-existent email timing
  - [x] 3.3: Verify test covers wrong password timing
  - [x] 3.4: Verify statistical analysis with multiple samples

- [x] Task 4: Create/Verify Brute Force Tests (AC: 3)
  - [x] 4.1: Create test_brute_force.py if not exists
  - [x] 4.2: Add test_account_locks_after_3_failures
  - [x] 4.3: Add test_locked_account_stays_locked_with_correct_credentials
  - [x] 4.4: Add test_attempt_count_progression

- [x] Task 5: Add Pytest Markers (AC: 4)
  - [x] 5.1: Add @pytest.mark.adversarial to all adversarial tests
  - [x] 5.2: Register 'adversarial' marker in pyproject.toml or pytest.ini
  - [x] 5.3: Verify `pytest -m adversarial` works

- [x] Task 6: Run Full Adversarial Suite (AC: 1-6)
  - [x] 6.1: Run `pytest tests/adversarial/ -v`
  - [x] 6.2: Verify all adversarial tests pass
  - [x] 6.3: Document final adversarial test count

## Dev Notes

### Current Implementation Status

**Existing Adversarial Test Files:**
- `tests/adversarial/test_timing_attacks.py` - Timing oracle prevention tests (exists)

**Missing Files (may need creation):**
- `test_race_conditions.py` - May exist in integration tests instead
- `test_brute_force.py` - May exist in integration tests instead

**Note:** Some adversarial scenarios (race conditions, brute force) are tested in integration tests. This story may involve:
1. Moving/copying tests to adversarial directory
2. Adding @pytest.mark.adversarial markers
3. Creating dedicated adversarial test files

### Existing Timing Attack Tests

**File:** `tests/adversarial/test_timing_attacks.py`

```python
class TestTimingAttacks:
    """Adversarial tests for timing oracle attack prevention."""

    def test_nonexistent_email_timing_similar_to_valid_email_wrong_code(
        self, repository, pool
    ):
        """Timing should be similar regardless of email existence."""
        # Creates valid registration
        # Measures timing for valid email + wrong code
        # Measures timing for non-existent email
        # Asserts timings are statistically similar
```

### Race Condition Tests (Currently in Integration)

**File:** `tests/integration/test_postgres_repository.py`

```python
def test_concurrent_registrations_exactly_one_succeeds(self, pool):
    """Only one concurrent registration should succeed."""
    # Uses ThreadPoolExecutor with 5 workers
    # Asserts exactly 1 success, 4 failures

def test_concurrent_reregistration_exactly_one_succeeds(self, pool):
    """Concurrent re-registration - exactly one succeeds."""
    # Tests FR18 atomicity
```

### Brute Force Tests (Currently in Integration)

**File:** `tests/integration/test_postgres_repository.py`

```python
def test_attempt_count_progression_0_to_3(self, repository, pool):
    """Verifies complete progression: 0 → 1 → 2 → 3 (locked)."""

def test_locked_account_fails_with_correct_credentials(self, repository, pool):
    """Locked account stays locked even with correct credentials."""
```

### FR/NFR Mapping

| Requirement | Description | Test File |
|-------------|-------------|-----------|
| FR16 | CLAIMED→LOCKED after 3 failures | test_brute_force.py |
| FR18 | Prevent race conditions | test_race_conditions.py |
| FR20 | Lock after threshold | test_brute_force.py |
| NFR-P2 | Constant-time password verification | test_timing_attacks.py |
| NFR-P3 | Consistent error timing | test_timing_attacks.py |
| NFR-T4 | Adversarial test markers | All adversarial tests |

### Pytest Marker Configuration

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "adversarial: marks tests as adversarial security tests (deselect with '-m \"not adversarial\"')",
]
```

### Statistical Timing Analysis Pattern

```python
def test_timing_similarity(self):
    """Use statistical analysis for timing comparison."""
    samples_a = [measure_time(scenario_a) for _ in range(20)]
    samples_b = [measure_time(scenario_b) for _ in range(20)]

    mean_a = statistics.mean(samples_a)
    mean_b = statistics.mean(samples_b)

    # Timings should be within 20% of each other
    assert abs(mean_a - mean_b) / max(mean_a, mean_b) < 0.2
```

### References

- [Source: architecture.md#Authentication & Security]
- [Source: prd.md#FR16 (CLAIMED→LOCKED transition)]
- [Source: prd.md#FR18 (Prevent race conditions)]
- [Source: prd.md#FR20 (Lock after threshold)]
- [Source: prd.md#NFR-P2 (Constant-time password verification)]
- [Source: prd.md#NFR-P3 (Consistent error timing)]
- [Source: prd.md#NFR-T4 (Adversarial test markers)]
- [Source: epics.md#Story 5.3 Acceptance Criteria]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Adversarial tests run: `pytest tests/adversarial/ -v` - 21 passed in 61.23s
- Marker verification: `pytest -m adversarial --co` - 21 tests selected, 187 deselected

### Completion Notes List

- **Task 1 (Audit)**: Found test_timing_attacks.py existed, identified need to create test_race_conditions.py and test_brute_force.py
- **Task 2 (Race Conditions)**: Created test_race_conditions.py with 5 tests covering:
  - TestRaceConditionAttacks: concurrent registration, high-volume attack, concurrent re-registration, concurrent activation
  - TestDataIntegrityUnderConcurrency: data integrity verification
- **Task 3 (Timing Attacks)**: Verified existing TestTimingAttacks class with statistical analysis (20 iterations, 20% threshold)
- **Task 4 (Brute Force)**: Created test_brute_force.py with 8 tests covering:
  - TestBruteForceAttacks: code brute force, password brute force, mixed failures, locked stays locked, rapid attacks
  - TestAttemptCountProgression: 0->1->2->3 progression
  - TestCredentialPurgeOnLockout: password hash purge, no ghost credentials
- **Task 5 (Markers)**: All tests marked with @pytest.mark.adversarial, marker already registered in pyproject.toml
- **Task 6 (Verification)**: All 21 adversarial tests pass, `pytest -m adversarial` works correctly
- **Final Adversarial Test Count**: 21 tests across 3 test files

### File List

Created:
- tests/adversarial/test_race_conditions.py (5 tests)
- tests/adversarial/test_brute_force.py (8 tests)

Already existed:
- tests/adversarial/test_timing_attacks.py (8 tests)

