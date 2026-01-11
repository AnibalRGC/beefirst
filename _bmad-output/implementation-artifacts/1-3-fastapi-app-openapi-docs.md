# Story 1.3: FastAPI App with OpenAPI Docs

Status: review

## Story

As a Technical Evaluator,
I want to access `/docs` and see auto-generated API documentation,
So that I can test the Trust Loop directly from my browser.

## Acceptance Criteria

1. **AC1: Swagger UI Documentation**
   - **Given** the system is running via `docker-compose up`
   - **When** I navigate to `http://localhost:8000/docs`
   - **Then** I see Swagger UI with API documentation
   - **And** the API title shows "beefirst"
   - **And** the description explains "Trust State Machine Registration API"

2. **AC2: Endpoint Visibility**
   - **Given** I am viewing `/docs`
   - **When** I examine the endpoints
   - **Then** `POST /v1/register` endpoint is listed with request/response schemas
   - **And** `POST /v1/activate` endpoint is listed with request/response schemas
   - **And** endpoints are grouped under "v1" tag

3. **AC3: Request/Response Schemas**
   - **Given** I am viewing `/docs`
   - **When** I expand the `/v1/register` endpoint
   - **Then** I see request schema: `{"email": "string", "password": "string"}`
   - **And** I see response schema for 201: `{"message": "string", "expires_in_seconds": "integer"}`
   - **When** I expand the `/v1/activate` endpoint
   - **Then** I see request schema: `{"code": "string"}`
   - **And** I see response schema for 200: `{"message": "string", "email": "string"}`

4. **AC4: ReDoc Alternative**
   - **Given** the system is running
   - **When** I navigate to `http://localhost:8000/redoc`
   - **Then** I see ReDoc alternative documentation
   - **And** all endpoints and schemas are visible

5. **AC5: Stub Responses**
   - **Given** I call `/v1/register` via Swagger UI
   - **When** the endpoint processes the request
   - **Then** I receive 501 Not Implemented with `{"detail": "Registration not yet implemented"}`
   - **Given** I call `/v1/activate` via Swagger UI
   - **When** the endpoint processes the request
   - **Then** I receive 501 Not Implemented with `{"detail": "Activation not yet implemented"}`

## Tasks / Subtasks

- [x] Task 1: Create API request/response models (AC: 3)
  - [x] 1.1: Create `src/api/models.py` with Pydantic models
  - [x] 1.2: Define `RegisterRequest` model with email and password fields
  - [x] 1.3: Define `RegisterResponse` model with message and expires_in_seconds
  - [x] 1.4: Define `ActivateRequest` model with code field
  - [x] 1.5: Define `ActivateResponse` model with message and email
  - [x] 1.6: Define `ErrorResponse` model with detail field

- [x] Task 2: Create v1 API router (AC: 2, 5)
  - [x] 2.1: Create `src/api/v1/__init__.py` for package
  - [x] 2.2: Create `src/api/v1/routes.py` with APIRouter
  - [x] 2.3: Implement stubbed `POST /register` endpoint returning 501
  - [x] 2.4: Implement stubbed `POST /activate` endpoint returning 501
  - [x] 2.5: Add OpenAPI tags and descriptions to endpoints

- [x] Task 3: Update main.py with router (AC: 1, 4)
  - [x] 3.1: Import v1 router in main.py
  - [x] 3.2: Include router with `/v1` prefix
  - [x] 3.3: Enhance OpenAPI metadata (title, description, version)
  - [x] 3.4: Verify `/docs` and `/redoc` are accessible

- [x] Task 4: Verify OpenAPI documentation (AC: 1, 2, 3, 4)
  - [x] 4.1: Start application and verify `/docs` loads
  - [x] 4.2: Verify `/v1/register` and `/v1/activate` appear in docs
  - [x] 4.3: Verify request/response schemas are correct
  - [x] 4.4: Verify `/redoc` loads as alternative

## Dev Notes

### Current State (from Story 1.2)

The FastAPI application already exists in `src/api/main.py` with:
- Lifespan context manager for startup/shutdown
- Connection pool stored in `app.state.pool`
- Health check endpoint at `/health`
- Basic OpenAPI metadata (title, description, version)

```python
# Current main.py structure
app = FastAPI(
    title="beefirst",
    description="Trust State Machine Registration API",
    version="0.1.0",
    lifespan=lifespan,
)
```

### Pydantic Models Pattern

```python
# src/api/models.py
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class RegisterResponse(BaseModel):
    message: str
    expires_in_seconds: int

class ActivateRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=4)

class ActivateResponse(BaseModel):
    message: str
    email: str

class ErrorResponse(BaseModel):
    detail: str
```

### Router Pattern

```python
# src/api/v1/routes.py
from fastapi import APIRouter, HTTPException, status
from src.api.models import (
    RegisterRequest, RegisterResponse,
    ActivateRequest, ActivateResponse,
)

router = APIRouter(prefix="/v1", tags=["v1"])

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
async def register(request: RegisterRequest) -> RegisterResponse:
    """Register a new user and send verification code."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Registration not yet implemented",
    )

@router.post(
    "/activate",
    response_model=ActivateResponse,
    responses={401: {"model": ErrorResponse}},
)
async def activate(request: ActivateRequest) -> ActivateResponse:
    """Activate account with verification code."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Activation not yet implemented",
    )
```

### Directory Structure After This Story

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI app with lifespan
│   ├── models.py        # Pydantic request/response models [NEW]
│   └── v1/
│       ├── __init__.py  # [NEW]
│       └── routes.py    # API endpoints [NEW]
├── adapters/
├── config/
└── domain/
```

### OpenAPI Enhancement

Add tags metadata for better documentation grouping:

```python
# In main.py
tags_metadata = [
    {
        "name": "v1",
        "description": "Trust State Machine Registration API v1",
    },
]

app = FastAPI(
    title="beefirst",
    description="Trust State Machine Registration API - Demonstrates the Identity Claim Dilemma solution",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
```

### Previous Story Learnings (Story 1.2)

- Connection pool is available via `app.state.pool` for dependency injection
- Settings loaded via `get_settings()` from `src.config.settings`
- Logging configured at module level with `logging.getLogger(__name__)`
- Migrations run automatically on startup

### Critical Constraints

1. **FR31**: OpenAPI documentation at `/docs` - Auto-generated by FastAPI
2. **FR27, FR28**: Endpoints must be `/v1/register` and `/v1/activate`
3. **FR29**: JSON data format exclusively - Enforced by Pydantic models
4. Stubs return 501 until Epic 2/3 implementation

### Testing Approach

Manual verification via browser:
1. Run `docker-compose up`
2. Navigate to `http://localhost:8000/docs`
3. Verify endpoints appear with correct schemas
4. Test stub responses via "Try it out"
5. Navigate to `http://localhost:8000/redoc` for alternative

### References

- [Source: prd/functional-requirements.md#FR27, FR28, FR29, FR31]
- [Source: architecture/core-architectural-decisions.md#API Layer]
- [Source: Story 1.2 - main.py patterns established]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 4 tasks (18 subtasks) completed successfully
- Added email-validator to requirements.txt for EmailStr validation
- Pydantic models with full validation (email format, password min length, code pattern)
- v1 router with OpenAPI tags and descriptions
- Stubbed endpoints return 501 Not Implemented as specified
- 37 total tests: 15 unit tests + 10 route tests + 12 OpenAPI schema tests
- OpenAPI schema verification tests ensure documentation completeness

### File List

- requirements.txt (updated - added email-validator)
- src/api/models.py (created)
- src/api/v1/__init__.py (created)
- src/api/v1/routes.py (created)
- src/api/main.py (updated)
- tests/unit/test_api_models.py (created)
- tests/integration/test_api_routes.py (created)
- tests/integration/test_openapi.py (created)
