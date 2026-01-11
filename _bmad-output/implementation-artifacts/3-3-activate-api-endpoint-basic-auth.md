# Story 3.3: Activate API Endpoint with BASIC AUTH

Status: review

## Story

As a Technical Evaluator,
I want to call `POST /v1/activate` with BASIC AUTH and verification code,
So that I can complete the Trust Loop and activate my account.

## Acceptance Criteria

1. **AC1: HTTP BASIC AUTH Credential Extraction**
   - **Given** I call `POST /v1/activate`
   - **When** I provide an `Authorization: Basic base64(email:password)` header
   - **Then** the email and password are correctly extracted from the header
   - **And** the email is normalized (lowercase, stripped)
   - **And** missing or malformed Authorization header returns 401

2. **AC2: Verification Code in Request Body**
   - **Given** I call `POST /v1/activate` with valid BASIC AUTH
   - **When** I provide body `{"code": "1234"}`
   - **Then** the 4-digit code is extracted from the JSON body
   - **And** the existing `ActivateRequest` model validates the code format
   - **And** invalid code format returns 422 Unprocessable Entity

3. **AC3: Successful Activation Returns 200**
   - **Given** I registered with `user@example.com`, received code `1234`
   - **When** I call `POST /v1/activate` with:
     - Header: `Authorization: Basic base64(user@example.com:password)`
     - Body: `{"code": "1234"}`
   - **Then** I receive 200 OK with `{"message": "Account activated", "email": "user@example.com"}`
   - **And** the account state transitions from CLAIMED to ACTIVE

4. **AC4: Invalid Code Returns 401**
   - **Given** a CLAIMED registration with code `1234`
   - **When** I provide wrong code `9999` in the request body
   - **Then** I receive 401 Unauthorized with `{"detail": "Invalid credentials or code"}`
   - **And** the error message is generic (FR21, NFR-S4)

5. **AC5: Invalid Password Returns 401**
   - **Given** a CLAIMED registration with password `correctpassword`
   - **When** I provide wrong password in BASIC AUTH header
   - **Then** I receive 401 Unauthorized with `{"detail": "Invalid credentials or code"}`
   - **And** the same generic error as wrong code (NFR-P3 - no information leakage)

6. **AC6: Expired Registration Returns 401**
   - **Given** a CLAIMED registration older than 60 seconds
   - **When** I provide correct code and password
   - **Then** I receive 401 Unauthorized with `{"detail": "Invalid credentials or code"}`
   - **And** the error message is identical to other failures

7. **AC7: Locked Account Returns 401**
   - **Given** a registration with 3 or more failed attempts (LOCKED)
   - **When** I provide correct code and password
   - **Then** I receive 401 Unauthorized with `{"detail": "Invalid credentials or code"}`
   - **And** the error message is identical to other failures

8. **AC8: Non-Existent Email Returns 401**
   - **Given** the email `nonexistent@example.com` has no registration
   - **When** I try to activate with that email
   - **Then** I receive 401 Unauthorized with `{"detail": "Invalid credentials or code"}`
   - **And** response timing is consistent with other failures (timing oracle prevention)

9. **AC9: OpenAPI Documentation**
   - **Given** I access `/docs` (Swagger UI)
   - **When** I view the `/v1/activate` endpoint
   - **Then** I see HTTP BASIC AUTH security requirement documented
   - **And** the request body schema shows `code` field
   - **And** 401 error response is documented

10. **AC10: Consistent Error Timing (NFR-P2, NFR-P3)**
    - **Given** I measure response times for different failure modes
    - **When** I compare: wrong code, wrong password, expired, locked, not found
    - **Then** response times are statistically similar (within noise margin)
    - **And** the domain/repository constant-time operations are used

## Tasks / Subtasks

- [x] Task 1: Implement HTTP BASIC AUTH Parsing (AC: 1, 8)
  - [x] 1.1: Create `get_basic_auth_credentials` dependency in `dependencies.py`
  - [x] 1.2: Use FastAPI's `HTTPBasic` security scheme for OpenAPI docs
  - [x] 1.3: Parse Authorization header and decode base64 credentials
  - [x] 1.4: Normalize email (strip, lowercase) before returning
  - [x] 1.5: Return 401 for missing or malformed Authorization header

- [x] Task 2: Wire Activate Endpoint to Domain Service (AC: 2, 3, 9)
  - [x] 2.1: Update `activate` function signature to include BASIC AUTH dependency
  - [x] 2.2: Inject `RegistrationService` via `Depends(get_registration_service)`
  - [x] 2.3: Call `service.verify_and_activate(email, code, password)`
  - [x] 2.4: Return 200 with `ActivateResponse` on `VerifyResult.SUCCESS`
  - [x] 2.5: Update OpenAPI schema to show security requirement

- [x] Task 3: Handle All VerifyResult Cases (AC: 4, 5, 6, 7, 8, 10)
  - [x] 3.1: Map `VerifyResult.INVALID_CODE` → 401 "Invalid credentials or code"
  - [x] 3.2: Map `VerifyResult.EXPIRED` → 401 "Invalid credentials or code"
  - [x] 3.3: Map `VerifyResult.LOCKED` → 401 "Invalid credentials or code"
  - [x] 3.4: Map `VerifyResult.NOT_FOUND` → 401 "Invalid credentials or code"
  - [x] 3.5: Ensure all 401 responses use identical error message

- [x] Task 4: Write Unit Tests for Activate Endpoint (AC: 1-9)
  - [x] 4.1: Test successful activation returns 200 with correct response
  - [x] 4.2: Test wrong code returns 401 with generic error
  - [x] 4.3: Test wrong password returns 401 with generic error
  - [x] 4.4: Test expired registration returns 401
  - [x] 4.5: Test locked account returns 401
  - [x] 4.6: Test non-existent email returns 401
  - [x] 4.7: Test missing Authorization header returns 401
  - [x] 4.8: Test malformed Authorization header returns 401
  - [x] 4.9: Test invalid code format returns 422

## Dev Notes

### Current State (from Story 3.2)

Story 3.2 implemented `verify_and_activate` in `PostgresRegistrationRepository` with:
- SELECT FOR UPDATE for row-level locking
- Constant-time code comparison (`secrets.compare_digest()`)
- Constant-time password verification (`bcrypt.checkpw()`)
- Timing oracle prevention with dummy hash
- All security measures for constant-time responses

The domain service `RegistrationService.verify_and_activate()` from Story 3.1:
```python
def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
    normalized_email = self._normalize_email(email)
    return self.repository.verify_and_activate(normalized_email, code, password)
```

### Existing API Structure

**Current `/v1/activate` Endpoint (stubbed in `src/api/v1/routes.py:73`):**
```python
@router.post("/activate", ...)
async def activate(request: ActivateRequest) -> ActivateResponse:
    raise HTTPException(status_code=501, detail="Activation not yet implemented")
```

**Existing Models (`src/api/models.py`):**
```python
class ActivateRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class ActivateResponse(BaseModel):
    message: str
    email: str
```

### HTTP BASIC AUTH Implementation Pattern

**FastAPI HTTPBasic Security Scheme:**
```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

async def get_basic_auth_credentials(
    credentials: HTTPBasicCredentials = Depends(security)
) -> tuple[str, str]:
    """Extract and validate BASIC AUTH credentials."""
    email = credentials.username.strip().lower()
    password = credentials.password
    return email, password
```

**Updated Activate Endpoint:**
```python
@router.post("/activate", ...)
async def activate(
    request_data: ActivateRequest,
    credentials: HTTPBasicCredentials = Depends(security),
    service: RegistrationService = Depends(get_registration_service),
) -> ActivateResponse:
    email = credentials.username.strip().lower()
    password = credentials.password

    result = service.verify_and_activate(email, request_data.code, password)

    if result == VerifyResult.SUCCESS:
        return ActivateResponse(message="Account activated", email=email)

    # All failures return identical generic error (NFR-S4, NFR-P3)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials or code",
    )
```

### Security Considerations (CRITICAL)

**Generic Error Messages (FR21, NFR-S4):**
All failure modes MUST return the identical response:
- `401 Unauthorized`
- `{"detail": "Invalid credentials or code"}`

This prevents:
- Email enumeration (knowing if email exists)
- Code/password differentiation (knowing which was wrong)
- Timing attacks (all paths through constant-time operations)

**FastAPI HTTPBasic Auto-401:**
When using `HTTPBasic()`, FastAPI automatically returns 401 for missing credentials with `WWW-Authenticate: Basic` header. This is correct behavior.

### Testing Strategy

**Unit Tests (`tests/unit/test_api_activate.py`):**
Mock the `RegistrationService` and test:
- Each `VerifyResult` maps to correct HTTP response
- BASIC AUTH credentials are parsed correctly
- Email is normalized before service call

**Integration Tests (Optional, if time permits):**
Full API tests against real database for complete Trust Loop:
1. Register via `/v1/register`
2. Activate via `/v1/activate` with code from logs
3. Verify state is ACTIVE in database

**Test Client Setup:**
```python
from fastapi.testclient import TestClient
from base64 import b64encode

def basic_auth_header(email: str, password: str) -> dict:
    credentials = f"{email}:{password}"
    encoded = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

# Example test
def test_activate_success(client: TestClient, mock_service):
    mock_service.verify_and_activate.return_value = VerifyResult.SUCCESS
    response = client.post(
        "/v1/activate",
        json={"code": "1234"},
        headers=basic_auth_header("test@example.com", "password123"),
    )
    assert response.status_code == 200
```

### Directory Structure After This Story

```
src/api/
├── v1/routes.py       # Updated /activate endpoint [MODIFIED]
├── dependencies.py    # get_basic_auth_credentials [MODIFIED]
└── models.py          # Unchanged (ActivateRequest/Response exist)

tests/unit/
└── test_api_activate.py  # New unit tests for activate endpoint [NEW]
```

### Dependencies

**Story 3.3 Depends On:**
- Story 2.4 (Register API Endpoint) - Existing API structure and models
- Story 3.1 (Domain State Machine) - verify_and_activate in RegistrationService
- Story 3.2 (PostgreSQL Repository) - verify_and_activate implementation

**Stories Depending on 3.3:**
- Story 3.4 (Timing-Safe Error Responses) - builds on verification flow

### Git Intelligence

Recent commits:
```
0ae3513 Implement domain state machine verification logic
08361e9 Fix Epic 2 code review issues
3914c07 Implement register api endpoint
```

Story 3.2 is in "review" status with verify_and_activate fully implemented.

### References

- [Source: architecture.md#Authentication & Security]
- [Source: architecture.md#API & Communication Patterns]
- [Source: architecture.md#Error Handling Patterns]
- [Source: prd.md#FR7 (Submit verification code with credentials)]
- [Source: prd.md#FR28 (POST /v1/activate endpoint)]
- [Source: prd.md#FR30 (HTTP BASIC AUTH)]
- [Source: prd.md#NFR-S4, NFR-P2, NFR-P3 (Generic errors, constant-time)]
- [Source: epics.md#Story 3.3]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 4 tasks (22 subtasks) completed successfully
- Implemented HTTP BASIC AUTH parsing with FastAPI's HTTPBasic security scheme (AC1)
- Added `http_basic` security scheme and `get_basic_auth_credentials` dependency (AC1, AC8)
- Email normalization (strip, lowercase) in credential extraction (AC1)
- FastAPI automatically handles missing/malformed Authorization headers with 401 (AC1)
- Wired activate endpoint to `service.verify_and_activate()` (AC2, AC3)
- OpenAPI docs now show HTTP BASIC AUTH security requirement on /v1/activate (AC9)
- All VerifyResult failure cases map to identical 401 "Invalid credentials or code" (AC4-8, AC10)
- Generic error messages prevent information leakage (NFR-S4, NFR-P3)
- Added 16 new unit tests for activate endpoint (replaced 5 stub tests)
- All 107 unit tests passing
- All 48 integration tests passing
- ruff check and ruff format passing

### File List

- src/api/dependencies.py (updated - added HTTPBasic, get_basic_auth_credentials)
- src/api/v1/routes.py (updated - implemented activate endpoint with BASIC AUTH and VerifyResult handling)
- tests/unit/test_api_routes.py (updated - replaced stub tests with 16 comprehensive activate tests)
