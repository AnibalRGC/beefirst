# Project Structure & Boundaries

## Requirements to Structure Mapping

| FR Category | Component | Location |
|-------------|-----------|----------|
| User Registration (FR1-FR6) | RegistrationService | `src/domain/registration.py` |
| Identity Verification (FR7-FR12) | VerifyResult, verify_and_activate | `src/domain/ports.py`, `src/adapters/repository/postgres.py` |
| State Management (FR13-FR17) | Trust State Machine | `src/domain/registration.py` |
| Security & Protection (FR18-FR23) | bcrypt, secrets | `src/domain/registration.py`, `src/adapters/repository/postgres.py` |
| Data Lifecycle (FR24-FR26) | Lazy deletion logic | `src/adapters/repository/postgres.py` |
| API Interface (FR27-FR31) | FastAPI routes | `src/api/routes.py`, `src/api/schemas.py` |
| Infrastructure (FR32-FR35) | Docker, pytest | `docker-compose.yml`, `tests/` |
| Architectural Constraints (FR36-FR39) | Hexagonal structure | `src/domain/` (pure), `src/adapters/` |

## Complete Project Directory Structure

```
beefirst/
├── README.md                          # Architecture-first documentation
├── requirements.txt                   # Production dependencies
├── requirements-dev.txt               # Development/test dependencies
├── pyproject.toml                     # Project metadata, tool config
├── .env.example                       # Environment template
├── .gitignore
├── Dockerfile                         # Multi-stage production build
├── docker-compose.yml                 # API + PostgreSQL orchestration
│
├── migrations/
│   └── 001_create_registrations.sql   # Raw DDL for transparency
│
├── src/
│   ├── __init__.py
│   │
│   ├── domain/                        # PURE BUSINESS LOGIC (zero imports)
│   │   ├── __init__.py
│   │   ├── registration.py            # Trust State Machine, RegistrationService
│   │   ├── ports.py                   # Protocol interfaces: RegistrationRepository, EmailSender
│   │   └── exceptions.py              # EmailAlreadyClaimed, VerificationFailed
│   │
│   ├── adapters/                      # INFRASTRUCTURE IMPLEMENTATIONS
│   │   ├── __init__.py
│   │   ├── repository/
│   │   │   ├── __init__.py
│   │   │   └── postgres.py            # PostgresRegistrationRepository (psycopg3)
│   │   └── smtp/
│   │       ├── __init__.py
│   │       └── console.py             # ConsoleEmailSender (logging for demo)
│   │
│   ├── api/                           # FASTAPI LAYER
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, lifespan, exception handlers
│   │   ├── routes.py                  # /v1/register, /v1/activate endpoints
│   │   ├── schemas.py                 # Pydantic request/response models
│   │   └── dependencies.py            # Depends() factories for DI
│   │
│   └── config/                        # CONFIGURATION
│       ├── __init__.py
│       └── settings.py                # pydantic-settings: DB_URL, TTL_SECONDS, etc.
│
└── tests/
    ├── __init__.py
    ├── conftest.py                    # Shared fixtures: db_pool, test_client
    │
    ├── unit/                          # DOMAIN TESTS (mocked ports)
    │   ├── __init__.py
    │   └── test_registration.py       # Trust State Machine logic tests
    │
    ├── integration/                   # ADAPTER TESTS (real DB)
    │   ├── __init__.py
    │   └── test_repository.py         # PostgresRegistrationRepository tests
    │
    └── adversarial/                   # ATTACK SCENARIO TESTS
        ├── __init__.py
        ├── test_race_conditions.py    # Truth 1: Concurrent claim attempts
        ├── test_timing_attacks.py     # Truth 3: Expiration boundary testing
        └── test_brute_force.py        # Truth 8: Attempt limiting verification
```

## Architectural Boundaries

**Dependency Direction (Hexagonal Rule):**

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│                    (src/api/)                                │
│         Depends on: Domain, Adapters (via DI)                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Core                             │
│                   (src/domain/)                              │
│              Depends on: NOTHING (pure)                      │
│         Defines: Ports (Protocol interfaces)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       Adapters                               │
│                  (src/adapters/)                             │
│          Implements: Domain Ports                            │
│          Depends on: Domain (for interfaces), Infrastructure │
└─────────────────────────────────────────────────────────────┘
```

**API Boundaries:**

| Boundary | Location | Responsibility |
|----------|----------|----------------|
| External API | `src/api/routes.py` | HTTP endpoints, request validation |
| Domain Entry | `src/domain/registration.py` | Business logic orchestration |
| Repository | `src/adapters/repository/postgres.py` | Data persistence |
| Email | `src/adapters/smtp/console.py` | Verification code delivery |

**Data Boundaries:**

| Boundary | Pattern | Location |
|----------|---------|----------|
| Request → Domain | Pydantic → plain types | `src/api/routes.py` |
| Domain → Repository | Protocol methods | `src/domain/ports.py` |
| Repository → DB | Raw SQL, parameterized | `src/adapters/repository/postgres.py` |
| DB → Domain | Query results → VerifyResult enum | `src/adapters/repository/postgres.py` |

## Integration Points

**Internal Communication:**

| From | To | Mechanism |
|------|-----|-----------|
| API routes | RegistrationService | Constructor injection via `Depends()` |
| RegistrationService | Repository | Protocol interface (structural subtyping) |
| RegistrationService | EmailSender | Protocol interface (structural subtyping) |
| Repository | PostgreSQL | psycopg3 `ConnectionPool` |

**External Integrations:**

| Integration | Pattern | Production Path |
|-------------|---------|-----------------|
| PostgreSQL | Connection pool | `src/adapters/repository/postgres.py` |
| SMTP (simulated) | Console logging | `src/adapters/smtp/console.py` |
| SMTP (production) | Swap adapter | Implement new adapter, same Protocol |

**Data Flow (Registration):**

```
POST /v1/register
       │
       ▼
┌──────────────────┐
│ RegisterRequest  │  (Pydantic validation)
│ email, password  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ RegistrationSvc  │  (normalize email, hash password, generate code)
│ .register()      │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Repo   │ │ Email  │
│ claim  │ │ send   │
└────┬───┘ └────────┘
     │
     ▼
┌──────────────────┐
│ PostgreSQL       │  (INSERT ... ON CONFLICT DO NOTHING)
│ registrations    │
└──────────────────┘
```

## File Organization Patterns

**Configuration Files (Root):**

| File | Purpose |
|------|---------|
| `requirements.txt` | Production: fastapi, uvicorn, psycopg[binary], bcrypt, pydantic-settings |
| `requirements-dev.txt` | Dev: pytest, pytest-cov, httpx, mypy, ruff |
| `pyproject.toml` | Tool config: pytest paths, mypy settings, ruff rules, coverage thresholds |
| `.env.example` | Template: DATABASE_URL, TTL_SECONDS, BCRYPT_COST |
| `docker-compose.yml` | Services: api (build context), db (postgres:16) |
| `Dockerfile` | Multi-stage: builder → production image |

**Source Organization:**

| Directory | Rule | Example Files |
|-----------|------|---------------|
| `src/domain/` | Zero external imports | registration.py, ports.py, exceptions.py |
| `src/adapters/` | One adapter per subdirectory | repository/postgres.py, smtp/console.py |
| `src/api/` | FastAPI-specific code | main.py, routes.py, schemas.py |
| `src/config/` | pydantic-settings only | settings.py |

**Test Organization:**

| Directory | Scope | Fixtures |
|-----------|-------|----------|
| `tests/unit/` | Domain logic only | Mock repositories and email senders |
| `tests/integration/` | Real PostgreSQL | `db_pool` fixture with transaction rollback |
| `tests/adversarial/` | Attack scenarios | Concurrent requests, timing manipulation |

## Development Workflow Integration

**Local Development:**
```bash
# Start infrastructure
docker-compose up -d db

# Run API with hot reload
uvicorn src.api.main:app --reload

# Format and lint (MANDATORY before commit)
ruff format src/ tests/
ruff check src/ tests/ --fix

# Run tests with coverage
pytest --cov=src --cov-fail-under=90
```

**Build Process:**
```bash
# Build production image
docker build -t beefirst:latest .

# Run migrations (via startup or script)
docker-compose run --rm api python -c "from src.adapters.repository.postgres import run_migrations; run_migrations()"
```

**Deployment Structure:**
```bash
docker-compose up -d  # Starts both API and PostgreSQL
# API available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```
