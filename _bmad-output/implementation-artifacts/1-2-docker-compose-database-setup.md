# Story 1.2: Docker Compose & Database Setup

Status: review

## Story

As a Technical Evaluator,
I want to run `docker-compose up` and have a working PostgreSQL database with the schema ready,
So that I can test the API without manual database setup.

## Acceptance Criteria

1. **AC1: Docker Compose Configuration**
   - **Given** Docker and Docker Compose are installed
   - **When** I run `docker-compose up`
   - **Then** PostgreSQL container starts on port 5432
   - **And** API container builds and starts
   - **And** API connects to PostgreSQL successfully

2. **AC2: Database Migration**
   - **Given** the containers are starting
   - **When** the API container initializes
   - **Then** migration `001_create_registrations.sql` executes automatically
   - **And** the migration is idempotent (can run multiple times safely)

3. **AC3: Registrations Table Schema**
   - **Given** migrations have run
   - **When** I inspect the database
   - **Then** `registrations` table exists with columns:
     - `id` (UUID, primary key, auto-generated)
     - `email` (VARCHAR(255), unique, not null)
     - `password_hash` (VARCHAR(255), nullable for Data Stewardship)
     - `verification_code` (CHAR(4), not null)
     - `state` (VARCHAR(20), not null, default 'CLAIMED')
     - `attempt_count` (INT, not null, default 0)
     - `created_at` (TIMESTAMPTZ, not null, default NOW())
     - `activated_at` (TIMESTAMPTZ, nullable)

4. **AC4: Startup Time**
   - **Given** I run `docker-compose up`
   - **When** measuring from command execution to API ready
   - **Then** system is ready to accept requests within 60 seconds (NFR-P1)

5. **AC5: Configuration Settings**
   - **Given** pydantic-settings is configured
   - **When** the API starts
   - **Then** settings load from environment variables
   - **And** DATABASE_URL defaults to PostgreSQL connection string
   - **And** TTL_SECONDS defaults to 60
   - **And** BCRYPT_COST defaults to 10

## Tasks / Subtasks

- [x] Task 1: Create Dockerfile (AC: 1, 4)
  - [x] 1.1: Create multi-stage Dockerfile with builder and production stages
  - [x] 1.2: Use Python 3.11-slim as base image
  - [x] 1.3: Install dependencies from requirements.txt
  - [x] 1.4: Copy src/ directory and set PYTHONPATH
  - [x] 1.5: Configure uvicorn as entrypoint on port 8000

- [x] Task 2: Create docker-compose.yml (AC: 1, 4)
  - [x] 2.1: Define `db` service with postgres:16 image
  - [x] 2.2: Configure PostgreSQL with POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  - [x] 2.3: Define `api` service with build context
  - [x] 2.4: Configure API environment variables (DATABASE_URL)
  - [x] 2.5: Set depends_on for api → db
  - [x] 2.6: Expose port 8000 for API

- [x] Task 3: Create database migration (AC: 2, 3)
  - [x] 3.1: Create `migrations/001_create_registrations.sql`
  - [x] 3.2: Define registrations table with all required columns
  - [x] 3.3: Add UNIQUE constraint on email column
  - [x] 3.4: Add CHECK constraint for valid state values
  - [x] 3.5: Make migration idempotent with CREATE TABLE IF NOT EXISTS

- [x] Task 4: Implement Settings configuration (AC: 5)
  - [x] 4.1: Update `src/config/settings.py` with pydantic-settings
  - [x] 4.2: Define DATABASE_URL with default connection string
  - [x] 4.3: Define TTL_SECONDS with default 60
  - [x] 4.4: Define BCRYPT_COST with default 10
  - [x] 4.5: Define MAX_ATTEMPTS with default 3

- [x] Task 5: Implement migration runner (AC: 2)
  - [x] 5.1: Create migration runner function in repository adapter
  - [x] 5.2: Execute SQL files from migrations/ directory
  - [x] 5.3: Add migration call to API lifespan startup

- [x] Task 6: Update API main.py with lifespan (AC: 1, 2)
  - [x] 6.1: Implement FastAPI lifespan context manager
  - [x] 6.2: Create database connection pool on startup
  - [x] 6.3: Run migrations on startup
  - [x] 6.4: Close connection pool on shutdown

## Dev Notes

### Database Schema (from Architecture)

```sql
CREATE TABLE IF NOT EXISTS registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULLed upon expiration/lockout (Data Stewardship)
    verification_code CHAR(4) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'CLAIMED'
        CHECK (state IN ('CLAIMED', 'ACTIVE', 'EXPIRED', 'LOCKED')),
    attempt_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);
```

### Schema Enforcement of Trust Truths

| Truth | Schema Mechanism |
|-------|------------------|
| **Truth 1: Unique Claim Lock** | `email UNIQUE` constraint |
| **Truth 3: Time-Bounded Proof** | `created_at` for expiration checks |
| **Truth 6: Data Stewardship** | `password_hash` nullable for purge |
| **Truth 8: Attempt Limiting** | `attempt_count` column |

### Docker Compose Architecture

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: beefirst
      POSTGRES_PASSWORD: beefirst
      POSTGRES_DB: beefirst
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U beefirst"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://beefirst:beefirst@db:5432/beefirst
    depends_on:
      db:
        condition: service_healthy
```

### Settings Pattern (pydantic-settings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://beefirst:beefirst@localhost:5432/beefirst"
    ttl_seconds: int = 60
    bcrypt_cost: int = 10
    max_attempts: int = 3

    class Config:
        env_file = ".env"
```

### Connection Pool Pattern (psycopg3)

```python
from contextlib import asynccontextmanager
from psycopg_pool import ConnectionPool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    pool = ConnectionPool(settings.database_url)
    run_migrations(pool)
    app.state.pool = pool
    yield
    # Shutdown
    pool.close()
```

### Migration Runner Pattern

```python
def run_migrations(pool: ConnectionPool) -> None:
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        with pool.connection() as conn:
            conn.execute(sql_file.read_text())
```

### Critical Constraints

1. **NFR-P1**: System ready within 60 seconds of `docker-compose up`
2. **NFR-O1**: No host dependencies beyond Docker
3. **NFR-O2**: Sensible defaults for demo mode
4. **NFR-S5**: No database credentials in logs

### References

- [Source: architecture/core-architectural-decisions.md#Data Architecture]
- [Source: architecture/core-architectural-decisions.md#Infrastructure & Deployment]
- [Source: prd/non-functional-requirements.md#NFR-P1, NFR-O1, NFR-O2]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 6 tasks completed successfully
- Multi-stage Dockerfile optimized for production (Python 3.11-slim)
- Docker Compose with PostgreSQL 16 and healthchecks
- Migration runner pattern with sorted file execution
- pydantic-settings for environment variable configuration
- FastAPI lifespan pattern for startup/shutdown management
- Connection pool stored in app.state for dependency injection

### File List

- Dockerfile (created)
- docker-compose.yml (created)
- migrations/001_create_registrations.sql (created)
- src/config/settings.py (updated)
- src/adapters/repository/postgres.py (updated)
- src/api/main.py (updated)
