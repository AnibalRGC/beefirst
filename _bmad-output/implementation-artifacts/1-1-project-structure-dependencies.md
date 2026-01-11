# Story 1.1: Project Structure & Dependencies

Status: review

## Story

As a Technical Evaluator,
I want to clone the repository and see a clear Hexagonal Architecture structure,
So that I can immediately understand the engineering approach before reading any code.

## Acceptance Criteria

1. **AC1: Hexagonal Directory Structure**
   - **Given** a fresh clone of the repository
   - **When** I examine the project structure
   - **Then** I see `src/domain/`, `src/adapters/`, `src/api/` directories
   - **And** the structure matches the Hexagonal Architecture pattern

2. **AC2: Domain Layer Scaffold**
   - **Given** I inspect the `src/domain/` directory
   - **When** I list the files
   - **Then** I see `__init__.py`, `registration.py`, `ports.py`, `exceptions.py`
   - **And** all files contain placeholder docstrings (implementation in later stories)

3. **AC3: Adapters Layer Scaffold**
   - **Given** I inspect the `src/adapters/` directory
   - **When** I list the contents
   - **Then** I see `repository/` and `smtp/` subdirectories
   - **And** each subdirectory contains `__init__.py` and main module file

4. **AC4: API Layer Scaffold**
   - **Given** I inspect the `src/api/` directory
   - **When** I list the files
   - **Then** I see `__init__.py`, `main.py`, `routes.py`, `schemas.py`, `dependencies.py`

5. **AC5: Requirements File**
   - **Given** I examine `requirements.txt`
   - **When** I read the contents
   - **Then** I see: `fastapi`, `uvicorn`, `psycopg[binary]`, `bcrypt`, `pydantic-settings`
   - **And** versions are pinned for reproducibility

6. **AC6: Development Requirements**
   - **Given** I examine `requirements-dev.txt`
   - **When** I read the contents
   - **Then** I see: `pytest`, `pytest-cov`, `httpx`, `mypy`, `ruff`

7. **AC7: Environment Template**
   - **Given** I examine `.env.example`
   - **When** I read the contents
   - **Then** I see `DATABASE_URL`, `TTL_SECONDS=60`, `BCRYPT_COST=10`
   - **And** all values have sensible defaults for demo mode

8. **AC8: Test Directory Structure**
   - **Given** I inspect the `tests/` directory
   - **When** I list the contents
   - **Then** I see `unit/`, `integration/`, `adversarial/` subdirectories
   - **And** each contains `__init__.py`
   - **And** `conftest.py` exists at tests root

## Tasks / Subtasks

- [x] Task 1: Create project root structure (AC: 1, 5, 6, 7)
  - [x] 1.1: Create `beefirst/` root directory
  - [x] 1.2: Create `requirements.txt` with production deps
  - [x] 1.3: Create `requirements-dev.txt` with dev/test deps
  - [x] 1.4: Create `.env.example` with default configuration
  - [x] 1.5: Create `.gitignore` (Python, venv, .env, __pycache__)
  - [x] 1.6: Create `pyproject.toml` with tool config (ruff, pytest, mypy)

- [x] Task 2: Create domain layer scaffold (AC: 1, 2)
  - [x] 2.1: Create `src/` directory with `__init__.py`
  - [x] 2.2: Create `src/domain/__init__.py`
  - [x] 2.3: Create `src/domain/registration.py` (placeholder)
  - [x] 2.4: Create `src/domain/ports.py` (placeholder)
  - [x] 2.5: Create `src/domain/exceptions.py` (placeholder)

- [x] Task 3: Create adapters layer scaffold (AC: 1, 3)
  - [x] 3.1: Create `src/adapters/__init__.py`
  - [x] 3.2: Create `src/adapters/repository/__init__.py`
  - [x] 3.3: Create `src/adapters/repository/postgres.py` (placeholder)
  - [x] 3.4: Create `src/adapters/smtp/__init__.py`
  - [x] 3.5: Create `src/adapters/smtp/console.py` (placeholder)

- [x] Task 4: Create API layer scaffold (AC: 1, 4)
  - [x] 4.1: Create `src/api/__init__.py`
  - [x] 4.2: Create `src/api/main.py` (placeholder)
  - [x] 4.3: Create `src/api/routes.py` (placeholder)
  - [x] 4.4: Create `src/api/schemas.py` (placeholder)
  - [x] 4.5: Create `src/api/dependencies.py` (placeholder)

- [x] Task 5: Create config module (AC: 1)
  - [x] 5.1: Create `src/config/__init__.py`
  - [x] 5.2: Create `src/config/settings.py` (placeholder)

- [x] Task 6: Create test directory scaffold (AC: 8)
  - [x] 6.1: Create `tests/__init__.py`
  - [x] 6.2: Create `tests/conftest.py` (placeholder)
  - [x] 6.3: Create `tests/unit/__init__.py`
  - [x] 6.4: Create `tests/integration/__init__.py`
  - [x] 6.5: Create `tests/adversarial/__init__.py`

- [x] Task 7: Create migrations directory (AC: 1)
  - [x] 7.1: Create `migrations/` directory
  - [x] 7.2: Create placeholder `migrations/.gitkeep`

## Dev Notes

### Architecture Pattern: Hexagonal (Ports & Adapters)

This story establishes the Hexagonal Architecture structure that enforces:
- **Domain purity**: `src/domain/` has ZERO external framework imports
- **Dependency inversion**: Domain defines ports, adapters implement them
- **Testability**: Each layer can be tested in isolation

### Critical Constraints

1. **Domain Layer (src/domain/)** - Must NEVER import from:
   - `fastapi`, `pydantic` (framework)
   - `psycopg` (infrastructure)
   - `src.adapters.*`, `src.api.*` (other layers)

2. **Naming Conventions** (enforce from start):
   - Modules: `snake_case` (e.g., `registration.py`)
   - Classes: `PascalCase` (e.g., `RegistrationService`)
   - Functions: `snake_case` (e.g., `claim_email`)
   - Constants: `SCREAMING_SNAKE` (e.g., `MAX_ATTEMPTS`)

3. **Python Version**: 3.11+ required for modern typing features

### Project Structure Notes

```
beefirst/
├── requirements.txt          # fastapi, uvicorn, psycopg[binary], bcrypt, pydantic-settings
├── requirements-dev.txt      # pytest, pytest-cov, httpx, mypy, ruff
├── pyproject.toml            # Tool config: ruff, pytest paths, mypy settings
├── .env.example              # DATABASE_URL, TTL_SECONDS=60, BCRYPT_COST=10
├── .gitignore
├── migrations/               # Raw SQL migrations (created in Story 1.2)
│
├── src/
│   ├── __init__.py
│   ├── domain/               # PURE - zero framework imports
│   │   ├── __init__.py
│   │   ├── registration.py   # Trust State Machine (Story 2.1)
│   │   ├── ports.py          # Protocol interfaces (Story 2.1)
│   │   └── exceptions.py     # Domain exceptions (Story 2.1)
│   │
│   ├── adapters/             # Infrastructure implementations
│   │   ├── __init__.py
│   │   ├── repository/
│   │   │   ├── __init__.py
│   │   │   └── postgres.py   # PostgresRegistrationRepository (Story 2.2)
│   │   └── smtp/
│   │       ├── __init__.py
│   │       └── console.py    # ConsoleEmailSender (Story 2.3)
│   │
│   ├── api/                  # FastAPI layer
│   │   ├── __init__.py
│   │   ├── main.py           # App factory, lifespan (Story 1.3)
│   │   ├── routes.py         # Endpoints (Story 2.4)
│   │   ├── schemas.py        # Pydantic models (Story 2.4)
│   │   └── dependencies.py   # DI factories (Story 2.4)
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py       # pydantic-settings (Story 1.2)
│
└── tests/
    ├── __init__.py
    ├── conftest.py           # Shared fixtures (Story 5.1)
    ├── unit/                 # Domain tests (Story 5.1)
    ├── integration/          # DB tests (Story 5.2)
    └── adversarial/          # Attack tests (Story 5.3)
```

### Dependencies Specification

**requirements.txt:**
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
psycopg[binary]>=3.1.0
bcrypt>=4.1.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
```

**requirements-dev.txt:**
```
-r requirements.txt
pytest>=8.0.0
pytest-cov>=4.1.0
httpx>=0.26.0
mypy>=1.8.0
ruff>=0.2.0
```

### References

- [Source: architecture/project-structure-boundaries.md#Complete Project Directory Structure]
- [Source: architecture/starter-template-evaluation.md#Selected Approach: Minimal Scaffold]
- [Source: architecture/implementation-patterns-consistency-rules.md#Naming Patterns]
- [Source: architecture/implementation-patterns-consistency-rules.md#Structure Patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Created complete Hexagonal Architecture scaffold with 27 files
- All placeholder modules contain docstrings referencing implementation stories
- requirements.txt includes all production dependencies with version pinning
- requirements-dev.txt includes all dev/test tools
- pyproject.toml configured with ruff, pytest, mypy settings and 90% coverage threshold
- .env.example includes DATABASE_URL, TTL_SECONDS=60, BCRYPT_COST=10
- Test directory structure supports unit, integration, and adversarial test categories
- Verified pytest discovers test directories correctly

### File List

**Created:**
- requirements.txt
- requirements-dev.txt
- .env.example
- .gitignore
- pyproject.toml
- migrations/.gitkeep
- src/__init__.py
- src/domain/__init__.py
- src/domain/registration.py
- src/domain/ports.py
- src/domain/exceptions.py
- src/adapters/__init__.py
- src/adapters/repository/__init__.py
- src/adapters/repository/postgres.py
- src/adapters/smtp/__init__.py
- src/adapters/smtp/console.py
- src/api/__init__.py
- src/api/main.py
- src/api/routes.py
- src/api/schemas.py
- src/api/dependencies.py
- src/config/__init__.py
- src/config/settings.py
- tests/__init__.py
- tests/conftest.py
- tests/unit/__init__.py
- tests/integration/__init__.py
- tests/adversarial/__init__.py
