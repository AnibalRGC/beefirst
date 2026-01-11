# beefirst

A Trust State Machine implementation demonstrating the solution to the **Identity Claim Dilemma** - a production-grade approach to user registration that prevents credential storage before email verification.

## Table of Contents

- [The Problem: Identity Claim Dilemma](#the-problem-identity-claim-dilemma)
- [The Solution: Trust State Machine](#the-solution-trust-state-machine)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## The Problem: Identity Claim Dilemma

Traditional user registration flows face a fundamental security challenge:

**The Dilemma:** When a user submits an email and password to register, should you store the password immediately?

- **If YES:** You're storing credentials for potentially unverified identities. What happens if the email is never verified? You now have "ghost credentials" - passwords tied to accounts that may belong to someone else.

- **If NO:** You need to ask the user for their password again after verification, creating friction and potential abandonment.

**The Risk:** Storing passwords before verification creates several problems:
1. **Ghost Credentials** - Passwords exist for accounts that were never activated
2. **Email Enumeration** - Attackers can probe which emails have pending registrations
3. **Credential Exposure** - More credentials stored = larger attack surface
4. **Data Stewardship** - You're holding sensitive data for potentially abandoned registrations

---

## The Solution: Trust State Machine

beefirst solves the Identity Claim Dilemma with a **Trust State Machine** - a formal state model that manages the registration lifecycle with explicit transitions and time bounds.

### State Diagram

```
                     ┌──────────────┐
      Register       │              │
  ──────────────────>│   CLAIMED    │
                     │              │
                     └──────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │  EXPIRED  │     │  ACTIVE   │     │  LOCKED   │
    │  (60s)    │     │  (done)   │     │  (3x)     │
    └───────────┘     └───────────┘     └───────────┘
          │                                   │
          └─────────────┬─────────────────────┘
                        ▼
                  Email Released
                (Can re-register)
```

### States

| State | Description |
|-------|-------------|
| **CLAIMED** | Email claimed, verification pending. Password stored (hashed). 60-second window active. |
| **ACTIVE** | Verification successful. Account fully activated. Trust established. |
| **EXPIRED** | 60-second window elapsed without successful verification. Password purged. |
| **LOCKED** | 3 failed verification attempts. Password purged. Brute-force protection triggered. |

### Transitions

| From | To | Trigger |
|------|----|---------|
| (new) | CLAIMED | User submits email + password via `/v1/register` |
| CLAIMED | ACTIVE | Correct verification code + password within 60 seconds |
| CLAIMED | EXPIRED | 60 seconds elapsed without successful verification |
| CLAIMED | LOCKED | 3 incorrect verification attempts |
| EXPIRED | (released) | Email can be re-registered |
| LOCKED | (released) | Email can be re-registered |

### Trust Invariants

1. **Unique Claim Lock** - Only one registration can claim an email at a time
2. **Time-Bounded Proof** - Verification must complete within 60 seconds
3. **Attempt Limiting** - Maximum 3 failed verification attempts
4. **Forward-Only Transitions** - States never move backward
5. **Data Stewardship** - Passwords purged on expiration/lockout (no ghost credentials)

---

## Architecture

beefirst implements **Hexagonal Architecture** (Ports & Adapters) to maintain clear boundaries between business logic and infrastructure.

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                              │
│                  (FastAPI, Pydantic)                        │
│         Routes, Request/Response Models, OpenAPI            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                            │
│           (Pure Python - ZERO framework imports)            │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │     Ports       │    │   Registration Service      │    │
│  │   (Protocols)   │    │    (Business Logic)         │    │
│  │                 │    │                             │    │
│  │ - Repository    │    │ - Email normalization       │    │
│  │ - EmailSender   │    │ - Code generation           │    │
│  └─────────────────┘    │ - State transitions         │    │
│                         └─────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│  PostgreSQL Adapter │           │  Console SMTP       │
│     (psycopg3)      │           │     Adapter         │
│                     │           │                     │
│ - Raw SQL queries   │           │ - Prints codes to   │
│ - Connection pool   │           │   stdout for demo   │
│ - Atomic operations │           │                     │
└─────────────────────┘           └─────────────────────┘
```

### Key Principles

1. **Domain Purity** - The domain layer has ZERO imports from FastAPI, Pydantic, or psycopg3. Business logic is framework-agnostic.

2. **Port Interfaces** - Domain defines abstract protocols that adapters implement:
   - `RegistrationRepository` - Database operations
   - `EmailSender` - Notification delivery

3. **Dependency Inversion** - High-level domain logic depends on abstractions (ports), not concrete implementations (adapters).

4. **Explicit SQL** - No ORM magic. All database queries are raw SQL for full transparency and control.

---

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Run

```bash
# Clone and start
git clone <repository-url>
cd beefirst
docker-compose up
```

The system is ready when you see:
```
api_1  | INFO:     Application startup complete
api_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

> **Note:** Database migrations run automatically on application startup. No manual setup required.

### Verify

Open http://localhost:8000/docs for interactive API documentation (Swagger UI).

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/register` | Register email and receive verification code |
| POST | `/v1/activate` | Activate account with verification code |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI documentation |
| GET | `/redoc` | ReDoc documentation |

### POST /v1/register

Register a new user and initiate the Trust Loop.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure123"
}
```

**Response (201 Created):**
```json
{
  "message": "Verification code sent",
  "expires_in_seconds": 60
}
```

**Errors:**
- `409 Conflict` - Email already claimed
- `422 Unprocessable Entity` - Validation error

### POST /v1/activate

Activate account using the verification code. Requires HTTP Basic Auth with email:password.

**Headers:**
```
Authorization: Basic base64(email:password)
Content-Type: application/json
```

**Request:**
```json
{
  "code": "1234"
}
```

**Response (200 OK):**
```json
{
  "message": "Account activated",
  "email": "user@example.com"
}
```

**Errors:**
- `401 Unauthorized` - Invalid credentials or code (generic message for security)

### Complete Trust Loop Example

```bash
# Step 1: Register
curl -X POST http://localhost:8000/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure123"}'

# Response: {"message": "Verification code sent", "expires_in_seconds": 60}

# Step 2: Get verification code from logs
docker-compose logs api | grep VERIFICATION
# Output: [VERIFICATION] Email: user@example.com Code: 1234

# Step 3: Activate (within 60 seconds!)
curl -X POST http://localhost:8000/v1/activate \
  -u "user@example.com:secure123" \
  -H "Content-Type: application/json" \
  -d '{"code": "1234"}'

# Response: {"message": "Account activated", "email": "user@example.com"}
```

---

## Testing

All tests run via Docker - **no local Python installation required**.

### Run All Tests

```bash
docker-compose --profile test run --rm test
```

This runs the full test suite with coverage reporting (default command).

### Run Tests with Custom Options

```bash
# Verbose output
docker-compose --profile test run --rm test pytest -v

# Stop on first failure
docker-compose --profile test run --rm test pytest -x

# Run specific test file
docker-compose --profile test run --rm test pytest tests/unit/test_registration_service.py
```

### Test Categories

| Category | Path | Tests | Description |
|----------|------|-------|-------------|
| Unit | `tests/unit/` | 107 | Domain logic with mocked dependencies |
| Integration | `tests/integration/` | 83 | Full API and database tests |
| Adversarial | `tests/adversarial/` | 21 | Security and attack scenarios |

### Run Specific Categories

```bash
# Unit tests only
docker-compose --profile test run --rm test pytest tests/unit/

# Integration tests only
docker-compose --profile test run --rm test pytest tests/integration/

# Adversarial security tests
docker-compose --profile test run --rm test pytest tests/adversarial/

# Or use markers
docker-compose --profile test run --rm test pytest -m adversarial
```

### Test Quality Metrics

| Metric | Value |
|--------|-------|
| Total Tests | 211 |
| Code Coverage | 100% |
| Coverage Threshold | 90% (enforced) |

---

## Quick Verification for Testers

Complete end-to-end verification using only Docker:

```bash
# 1. Start the application
docker-compose up -d

# 2. Wait for startup and verify health
sleep 10
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 3. Register a new user
curl -X POST http://localhost:8000/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "tester@example.com", "password": "secure123"}'
# Expected: {"message":"Verification code sent","email":"tester@example.com","expires_in_seconds":60}

# 4. Get the verification code from logs
docker-compose logs api | grep VERIFICATION
# Expected: [VERIFICATION] Email: tester@example.com Code: XXXX

# 5. Activate the account (replace XXXX with actual code, within 60 seconds!)
curl -X POST http://localhost:8000/v1/activate \
  -u "tester@example.com:secure123" \
  -H "Content-Type: application/json" \
  -d '{"code": "XXXX"}'
# Expected: {"message":"Account activated","email":"tester@example.com"}

# 6. Run the full test suite
docker-compose --profile test run --rm test
# Expected: 211 passed, 100% coverage

# 7. Cleanup
docker-compose down
```

### What to Verify

| Check | Expected Result |
|-------|-----------------|
| Health endpoint | `{"status":"healthy"}` |
| Registration | 201 Created with expiration time |
| Code in logs | 4-digit code visible |
| Activation | 200 OK with email confirmation |
| Test suite | 211 passed, 100% coverage |

---

## Project Structure

```
beefirst/
├── src/
│   ├── api/                    # API Layer (FastAPI)
│   │   ├── main.py             # Application factory, lifespan
│   │   ├── models.py           # Pydantic request/response models
│   │   └── v1/
│   │       └── routes.py       # API endpoints
│   │
│   ├── domain/                 # Domain Layer (Pure Python)
│   │   ├── registration.py     # Registration service
│   │   ├── ports.py            # Port interfaces (protocols)
│   │   └── exceptions.py       # Domain exceptions
│   │
│   ├── adapters/               # Adapter Layer
│   │   ├── repository/
│   │   │   └── postgres.py     # PostgreSQL implementation
│   │   └── smtp/
│   │       └── console.py      # Console email sender
│   │
│   └── config/
│       └── settings.py         # pydantic-settings configuration
│
├── tests/
│   ├── unit/                   # Unit tests (mocked dependencies)
│   ├── integration/            # Integration tests (real DB)
│   └── adversarial/            # Security tests
│
├── migrations/
│   └── 001_create_registrations.sql
│
├── docker-compose.yml          # PostgreSQL + API
├── Dockerfile                  # Multi-stage production build
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Development dependencies
```

---

## Configuration

Environment variables (with defaults for demo mode):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://beefirst:beefirst@localhost:5432/beefirst` | PostgreSQL connection string |
| `TTL_SECONDS` | `60` | Verification window duration |
| `MAX_ATTEMPTS` | `3` | Failed attempts before lockout |
| `BCRYPT_COST` | `10` | bcrypt work factor |

---

## License

MIT
