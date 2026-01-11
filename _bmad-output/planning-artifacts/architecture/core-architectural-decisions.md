# Core Architectural Decisions

## Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Database schema design (Trust State Machine representation)
- Security implementation (constant-time comparison, credential lifecycle)
- Hexagonal Architecture boundaries (domain purity)

**Important Decisions (Shape Architecture):**
- Migration strategy (raw SQL for transparency)
- Configuration management (pydantic-settings for validation)
- Connection pooling (psycopg3 native)

**Deferred Decisions (Post-MVP):**
- Background cleanup worker (Tier 3 stretch goal)
- Persistent rate limiting with Redis (V1.2)
- Structured logging with structlog (if needed)

## Data Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Schema Design** | Single table with state column | Simplicity for demo; clearly illustrates Trust State Machine transitions |
| **Migration Strategy** | Raw SQL scripts in `migrations/` | Maximizes transparency; evaluator sees exact DDL |
| **Connection Pooling** | psycopg3 `ConnectionPool` | Native to driver; handles demo concurrency without PgBouncer complexity |

**Core Schema:**

```sql
CREATE TABLE registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULLed upon expiration/lockout (Data Stewardship)
    verification_code CHAR(4) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'CLAIMED',  -- CLAIMED, ACTIVE, EXPIRED, LOCKED
    attempt_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);
```

**Schema Enforcement of Trust Truths:**

| Truth | Schema Mechanism |
|-------|------------------|
| **Truth 1: Unique Claim Lock** | `email UNIQUE` constraint + `ON CONFLICT DO NOTHING` |
| **Truth 3: Time-Bounded Proof** | `created_at > NOW() - INTERVAL '60 seconds'` in queries |
| **Truth 9: Normalization** | `lower(email)` applied at query level |
| **Truth 6: Data Stewardship** | `password_hash` NULLed on expiration/lockout |
| **Truth 8: Attempt Limiting** | `attempt_count` checked before verification |

## Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Password Hashing** | bcrypt (cost factor ≥10) | Industry standard, constant-time comparison built-in |
| **Code Comparison** | `secrets.compare_digest()` | Explicitly mitigates timing attacks on 4-digit codes |
| **Credential Lifecycle** | Lazy deletion (SET NULL on check) | Fulfills Data Stewardship without background task complexity |
| **Auth Method** | HTTP BASIC AUTH on `/v1/activate` | Dual-factor: proves password knowledge + code possession |

**Security Implementation Notes:**

- All error responses use generic messages: `"Invalid credentials or code"`
- Password verification uses bcrypt's built-in constant-time comparison
- Verification code comparison uses `secrets.compare_digest()`
- No credential logging (NFR-S5 compliance)

## API & Communication Patterns

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **API Style** | REST with explicit versioning (`/v1/`) | Signals design for contract evolution |
| **Documentation** | Auto-generated OpenAPI at `/docs` | Zero-friction evaluation via Swagger UI |
| **Error Handling** | Generic messages, consistent structure | Security-first: prevents information leakage |
| **Data Format** | JSON exclusively | Industry standard, native FastAPI/Pydantic support |

## Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Configuration** | pydantic-settings | Type-safe, validates at startup, aligns with FastAPI ecosystem |
| **Logging** | Standard Python logging to stdout | Docker-native; verification codes visible in `docker-compose logs` |
| **Containerization** | Docker Compose (API + PostgreSQL) | Zero-friction setup: `docker-compose up` → working API |
| **Environment** | `.env` file with sensible defaults | Demo-ready without manual configuration |

## Decision Impact Analysis

**Implementation Sequence:**

1. **Project scaffold** - Hexagonal structure, dependencies, Docker setup
2. **Database schema** - migrations/001_create_registrations.sql
3. **Domain Core** - Trust State Machine with port interfaces (zero imports)
4. **Repository Adapter** - psycopg3 implementation of domain ports
5. **SMTP Adapter** - Console-based email simulation
6. **API Layer** - FastAPI routes consuming domain via DI
7. **Test Suite** - Unit, integration, and adversarial test categories

**Cross-Component Dependencies:**

| Component | Depends On | Depended By |
|-----------|------------|-------------|
| Domain Core | Nothing (pure) | API Layer, Repository Adapter |
| Ports (interfaces) | Domain Core | All Adapters |
| Repository Adapter | Ports, psycopg3 | API Layer (via DI) |
| SMTP Adapter | Ports | API Layer (via DI) |
| API Layer | Domain Core, Adapters | Tests |
