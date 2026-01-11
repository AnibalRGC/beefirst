# Story 5.1: Unit Tests for Domain Logic

Status: review

## Story

As a Technical Evaluator,
I want to run unit tests that verify domain logic with mocked ports,
So that I can confirm the Trust State Machine rules are enforced in pure domain code.

## Acceptance Criteria

1. **AC1: Domain Logic Tests with Mocked Ports**
   - **Given** I run `pytest tests/unit/`
   - **When** the tests execute
   - **Then** all domain logic is tested with mocked repository and email sender
   - **And** domain tests have zero external dependencies

2. **AC2: Email Normalization Tests**
   - **Given** the RegistrationService receives various email formats
   - **When** emails are processed
   - **Then** tests verify: lowercase conversion, whitespace stripping
   - **And** tests cover edge cases: mixed case, leading/trailing spaces

3. **AC3: Verification Code Generation Tests**
   - **Given** the RegistrationService generates verification codes
   - **When** codes are created
   - **Then** tests verify: 4-digit format, numeric only, randomness
   - **And** tests verify codes vary across multiple generations

4. **AC4: Password Hashing Tests**
   - **Given** the RegistrationService hashes passwords
   - **When** passwords are processed
   - **Then** tests verify: bcrypt format, cost factor ≥10, verifiability
   - **And** tests verify hashed password can be verified with bcrypt.checkpw()

5. **AC5: Registration Flow Tests**
   - **Given** the RegistrationService.register() is called
   - **When** registration succeeds or fails
   - **Then** tests verify: repository claim_email called with correct args
   - **And** tests verify: email sender called only on success
   - **And** tests verify: EmailAlreadyClaimed exception on failure

6. **AC6: Verify and Activate Flow Tests**
   - **Given** the RegistrationService.verify_and_activate() is called
   - **When** various results are returned
   - **Then** tests verify: email normalization before repository call
   - **And** tests verify: all VerifyResult values are handled correctly

7. **AC7: Test Isolation (NFR-T5)**
   - **Given** all unit tests
   - **When** tests execute
   - **Then** tests are isolated with no shared state between tests
   - **And** tests use fresh mocks for each test function

## Tasks / Subtasks

- [x] Task 1: Audit Existing Unit Test Coverage (AC: 1-7)
  - [x] 1.1: Review tests/unit/test_registration_service.py for completeness
  - [x] 1.2: Review tests/unit/test_domain_ports.py for port definitions
  - [x] 1.3: Review tests/unit/test_console_email_sender.py for adapter tests
  - [x] 1.4: Identify any gaps in domain logic coverage
  - [x] 1.5: Document what tests exist vs what's needed

- [x] Task 2: Verify Email Normalization Tests (AC: 2)
  - [x] 2.1: Confirm test_normalize_email_strips_whitespace exists
  - [x] 2.2: Confirm test_normalize_email_lowercases exists
  - [x] 2.3: Confirm test_normalize_email_combined exists
  - [x] 2.4: Add any missing edge case tests

- [x] Task 3: Verify Code Generation Tests (AC: 3)
  - [x] 3.1: Confirm test_verification_code_is_4_digits exists
  - [x] 3.2: Confirm test_verification_code_is_string exists
  - [x] 3.3: Confirm test_verification_codes_vary exists
  - [x] 3.4: Add test for numeric-only pattern if missing

- [x] Task 4: Verify Password Hashing Tests (AC: 4)
  - [x] 4.1: Confirm test_password_is_hashed exists
  - [x] 4.2: Confirm test_password_hash_is_bcrypt exists
  - [x] 4.3: Confirm test_password_hash_cost_factor_at_least_10 exists
  - [x] 4.4: Confirm test_password_hash_verifiable exists

- [x] Task 5: Verify Registration Flow Tests (AC: 5)
  - [x] 5.1: Confirm test_register_calls_repository_claim_email exists
  - [x] 5.2: Confirm test_register_calls_email_sender_on_success exists
  - [x] 5.3: Confirm test_register_does_not_send_email_on_claim_failure exists
  - [x] 5.4: Confirm test_raises_email_already_claimed_when_claim_fails exists

- [x] Task 6: Verify Activate Flow Tests (AC: 6)
  - [x] 6.1: Confirm test_verify_and_activate_normalizes_email exists
  - [x] 6.2: Confirm test_verify_and_activate_returns_repository_result exists
  - [x] 6.3: Confirm all VerifyResult enum values have dedicated tests

- [x] Task 7: Verify Test Isolation (AC: 7)
  - [x] 7.1: Audit test files for shared state patterns
  - [x] 7.2: Ensure all tests use function-scoped fixtures
  - [x] 7.3: Verify no global state mutations between tests

- [x] Task 8: Fill Any Coverage Gaps (AC: 1-7)
  - [x] 8.1: Add any missing tests identified in audit
  - [x] 8.2: Run pytest tests/unit/ -v to verify all pass
  - [x] 8.3: Document final unit test count

## Dev Notes

### Current Implementation Status

**IMPORTANT:** Unit tests already exist from Epic 1-4 implementation. This story is primarily an AUDIT and GAP-FILL task.

**Existing Unit Test Files:**
- `tests/unit/test_registration_service.py` - Domain service tests
- `tests/unit/test_domain_ports.py` - Port/protocol definitions
- `tests/unit/test_console_email_sender.py` - Email adapter tests
- `tests/unit/test_api_routes.py` - API route tests
- `tests/unit/test_api_models.py` - Pydantic model tests

### Testing Patterns Established

From previous stories (Epic 1-4):

**Mock Pattern:**
```python
@pytest.fixture
def mock_repository():
    """Create mock repository for unit tests."""
    return Mock(spec=RegistrationRepository)

@pytest.fixture
def mock_email_sender():
    """Create mock email sender for unit tests."""
    return Mock(spec=EmailSender)
```

**Test Naming Convention:**
- `test_<function>_<scenario>()` format
- Example: `test_normalize_email_strips_whitespace()`

**Assertion Pattern:**
```python
def test_register_calls_repository_claim_email(
    mock_repository, mock_email_sender
):
    """Registration calls repository with normalized email."""
    service = RegistrationService(mock_repository, mock_email_sender)
    mock_repository.claim_email.return_value = True

    service.register("Test@Example.com", "password123")

    mock_repository.claim_email.assert_called_once()
    call_args = mock_repository.claim_email.call_args
    assert call_args[0][0] == "test@example.com"  # Normalized
```

### FR/NFR Mapping

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| NFR-T1 | ≥90% coverage | Unit tests contribute to overall coverage |
| NFR-T3 | Categorized tests | Tests in tests/unit/ directory |
| NFR-T5 | Test isolation | Function-scoped fixtures, fresh mocks |

### Architecture Requirements

From `architecture.md`:
- **Domain Purity**: Domain layer has zero framework imports
- **Port Interfaces**: Repository and EmailSender defined as Protocols
- **Structural Subtyping**: No explicit inheritance from Protocol

### Previous Story Intelligence

From Stories 4.1-4.4:
- Unit tests were added incrementally with each story
- Pattern: Test mocks for repository and email sender
- Pattern: Verify normalized email in all calls
- Total current test count: 195 tests (unit + integration + adversarial)

### References

- [Source: architecture.md#Testing Framework]
- [Source: prd.md#NFR-T1 (≥90% coverage)]
- [Source: prd.md#NFR-T3 (Categorized tests)]
- [Source: prd.md#NFR-T5 (Test isolation)]
- [Source: epics.md#Story 5.1 Acceptance Criteria]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Unit tests run: `pytest tests/unit/ -v` - 107 passed in 5.70s

### Completion Notes List

- **Task 1-8 (Audit)**: All acceptance criteria verified - comprehensive unit test coverage already exists
- **AC1**: All domain tests use Mock objects for repository and email sender - zero external dependencies
- **AC2**: Email normalization tests: test_normalize_email_strips_whitespace, test_normalize_email_lowercases, test_normalize_email_combined
- **AC3**: Code generation tests: test_verification_code_is_4_digits, test_verification_code_is_string, test_verification_codes_vary, test_verification_code_pattern_valid
- **AC4**: Password hashing tests: test_password_is_hashed, test_password_hash_is_bcrypt, test_password_hash_cost_factor_at_least_10, test_password_hash_verifiable
- **AC5**: Registration flow tests: test_register_calls_repository_claim_email, test_register_calls_email_sender_on_success, test_register_does_not_send_email_on_claim_failure, test_raises_email_already_claimed_when_claim_fails
- **AC6**: All VerifyResult enum values have dedicated tests (SUCCESS, INVALID_CODE, EXPIRED, LOCKED, NOT_FOUND)
- **AC7**: All tests use function-scoped fixtures with fresh Mock objects - no shared state patterns detected
- **Gaps Found**: None - all acceptance criteria were already met by existing tests
- **Final Unit Test Count**: 107 tests across 5 test files

### File List

Audited (no modifications needed):
- tests/unit/test_registration_service.py (30 tests)
- tests/unit/test_domain_ports.py (26 tests)
- tests/unit/test_console_email_sender.py (12 tests)
- tests/unit/test_api_routes.py (26 tests)
- tests/unit/test_api_models.py (15 tests)

