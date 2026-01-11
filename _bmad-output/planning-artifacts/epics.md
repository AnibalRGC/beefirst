---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
status: complete
inputDocuments:
  - "_bmad-output/planning-artifacts/prd/functional-requirements.md"
  - "_bmad-output/planning-artifacts/prd/non-functional-requirements.md"
  - "_bmad-output/planning-artifacts/prd/api-backend-specific-requirements.md"
  - "_bmad-output/planning-artifacts/architecture/starter-template-evaluation.md"
  - "_bmad-output/planning-artifacts/architecture/core-architectural-decisions.md"
  - "_bmad-output/planning-artifacts/architecture/implementation-patterns-consistency-rules.md"
---

# beefirst - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for beefirst, decomposing the requirements from the PRD and Architecture into implementable stories. This project demonstrates the "Identity Claim Dilemma" solution with a Trust State Machine pattern.

## Requirements Inventory

### Functional Requirements

FR1: Users can submit an email address and password to begin registration
FR2: System can normalize email addresses (case-insensitive, whitespace-neutral)
FR3: System can atomically claim an email address, preventing duplicate registrations
FR4: System can generate a cryptographically random 4-digit verification code
FR5: System can deliver the verification code to the user (console output for demo)
FR6: System can reject registration attempts for already-claimed or active emails
FR7: Users can submit a verification code with credentials to activate their account
FR8: System can verify the submitted code matches the generated code
FR9: System can verify the submitted password matches the stored hash
FR10: System can verify the verification attempt is within the 60-second window
FR11: System can verify fewer than 3 failed attempts have occurred
FR12: System can transition a user from CLAIMED to ACTIVE upon successful verification
FR13: System can represent user states: AVAILABLE, CLAIMED, ACTIVE, EXPIRED, LOCKED
FR14: System can enforce forward-only state transitions (no backward movement)
FR15: System can transition CLAIMED → EXPIRED when 60 seconds elapse
FR16: System can transition CLAIMED → LOCKED after 3 failed verification attempts
FR17: System can release email addresses from EXPIRED or LOCKED states back to AVAILABLE
FR18: System can prevent race conditions during concurrent registration attempts
FR19: System can track and limit verification attempts per registration
FR20: System can lock accounts after exceeding the attempt threshold
FR21: System can return generic error messages that prevent information disclosure
FR22: System can perform constant-time password comparisons
FR23: System can hash passwords using bcrypt before storage
FR24: System can purge hashed passwords when registrations expire or lock
FR25: System can ensure no "ghost credentials" exist for unverified accounts
FR26: System can timestamp all state transitions using database time
FR27: System can expose a versioned API endpoint for registration (`POST /v1/register`)
FR28: System can expose a versioned API endpoint for activation (`POST /v1/activate`)
FR29: System can accept and return JSON data format exclusively
FR30: System can authenticate activation requests using HTTP BASIC AUTH
FR31: System can auto-generate OpenAPI documentation accessible at `/docs`
FR32: System can run via Docker Compose with a single command
FR33: System can execute all tests via pytest with a single command
FR34: System can categorize tests by scenario type (happy path, adversarial)
FR35: System can report test coverage metrics
FR36: Domain logic can exist without framework imports (FastAPI, Pydantic, psycopg3)
FR37: Domain logic can define its own port interfaces for infrastructure abstraction
FR38: Repository adapters can use raw SQL with explicit transaction control
FR39: README can present architecture and invariants before setup instructions

### NonFunctional Requirements

NFR-S1: Passwords must be hashed using bcrypt with cost factor ≥ 10
NFR-S2: Password verification must use constant-time comparison
NFR-S3: Verification codes must be generated using cryptographically secure randomness
NFR-S4: All error responses must use generic messages that prevent information disclosure
NFR-S5: Database credentials must not appear in application logs
NFR-S6: Hashed passwords for unverified accounts must be purged within 60 seconds of expiration
NFR-P1: System must start and be ready to accept requests within 60 seconds of `docker-compose up`
NFR-P2: Password verification response time must not reveal validity (constant-time)
NFR-P3: Error responses must have consistent timing regardless of failure mode
NFR-T1: Test suite must achieve ≥ 90% code coverage
NFR-T2: All tests must pass on fresh clone (100% pass rate)
NFR-T3: Tests must be categorized by scenario type (happy path, adversarial)
NFR-T4: Adversarial scenarios must have dedicated test coverage
NFR-T5: Tests must be isolated (no shared state between tests)
NFR-M1: Domain logic must have zero imports from infrastructure (FastAPI, Pydantic, psycopg3)
NFR-M2: Domain module must define port interfaces for all infrastructure dependencies
NFR-M3: All SQL queries must be explicit (no ORM magic)
NFR-M4: Code must follow Python conventions (PEP 8, type hints)
NFR-O1: System must run in Docker with no host dependencies beyond Docker
NFR-O2: All environment variables must have sensible defaults for demo mode
NFR-O3: Verification codes must be visible in logs/console for demo purposes

### Additional Requirements

**From Architecture - Starter Template:**
- Minimal scaffold approach (no starter template - build from scratch)
- Project structure itself is a deliverable demonstrating engineering judgment

**From Architecture - Hexagonal Structure:**
- src/domain/ - Pure business logic, zero framework imports
- src/ports/ - Abstract interfaces for infrastructure
- src/adapters/repository/ - psycopg3 PostgreSQL adapter
- src/adapters/smtp/ - Console-based email simulation
- src/api/ - FastAPI routes and request/response models

**From Architecture - Testing:**
- tests/unit/ - Domain logic tests (mocked ports)
- tests/integration/ - PostgreSQL adapter tests
- tests/adversarial/ - Race conditions, timing attacks, brute force

**From Architecture - Infrastructure:**
- Docker Compose for PostgreSQL + API
- Multi-stage Dockerfile for production
- requirements.txt (no Poetry/PDM - simplicity for evaluator)
- pydantic-settings for configuration
- Standard Python logging to stdout

**From Architecture - Implementation Sequence:**
1. Project scaffold - Hexagonal structure, dependencies, Docker setup
2. Database schema - migrations/001_create_registrations.sql
3. Domain Core - Trust State Machine with port interfaces (zero imports)
4. Repository Adapter - psycopg3 implementation of domain ports
5. SMTP Adapter - Console-based email simulation
6. API Layer - FastAPI routes consuming domain via DI
7. Test Suite - Unit, integration, and adversarial test categories

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Submit email and password for registration |
| FR2 | Epic 2 | Normalize email addresses |
| FR3 | Epic 2 | Atomically claim email address |
| FR4 | Epic 2 | Generate cryptographic verification code |
| FR5 | Epic 2 | Deliver verification code (console) |
| FR6 | Epic 2 | Reject duplicate registrations |
| FR7 | Epic 3 | Submit verification code with credentials |
| FR8 | Epic 3 | Verify code matches |
| FR9 | Epic 3 | Verify password matches hash |
| FR10 | Epic 3 | Verify within 60-second window |
| FR11 | Epic 3 | Verify fewer than 3 failed attempts |
| FR12 | Epic 3 | Transition CLAIMED → ACTIVE |
| FR13 | Epic 3 | Represent user states |
| FR14 | Epic 3 | Enforce forward-only transitions |
| FR15 | Epic 4 | Transition CLAIMED → EXPIRED |
| FR16 | Epic 4 | Transition CLAIMED → LOCKED |
| FR17 | Epic 4 | Release emails from EXPIRED/LOCKED |
| FR18 | Epic 2 | Prevent race conditions |
| FR19 | Epic 4 | Track verification attempts |
| FR20 | Epic 4 | Lock after attempt threshold |
| FR21 | Epic 2 | Generic error messages |
| FR22 | Epic 3 | Constant-time password comparison |
| FR23 | Epic 2 | bcrypt password hashing |
| FR24 | Epic 4 | Purge passwords on expire/lock |
| FR25 | Epic 4 | No ghost credentials |
| FR26 | Epic 4 | Timestamp state transitions |
| FR27 | Epic 2 | POST /v1/register endpoint |
| FR28 | Epic 3 | POST /v1/activate endpoint |
| FR29 | Epic 2 | JSON data format |
| FR30 | Epic 3 | HTTP BASIC AUTH |
| FR31 | Epic 2 | OpenAPI documentation |
| FR32 | Epic 1 | Docker Compose single command |
| FR33 | Epic 5 | pytest single command |
| FR34 | Epic 5 | Test categorization |
| FR35 | Epic 5 | Coverage metrics |
| FR36 | Epic 1 | Domain without framework imports |
| FR37 | Epic 1 | Port interfaces for abstraction |
| FR38 | Epic 1 | Raw SQL with transaction control |
| FR39 | Epic 1 | README with architecture first |

## Epic List

### Epic 1: Project Bootstrap & Infrastructure
**User Outcome:** Evaluator can clone, run `docker-compose up`, and access a running API with PostgreSQL and OpenAPI docs at `/docs`.

**FRs Covered:** FR32, FR36, FR37, FR38, FR39
**NFRs Addressed:** NFR-O1, NFR-O2, NFR-P1, NFR-M1, NFR-M2, NFR-M3, NFR-M4

---

### Epic 2: User Registration Flow
**User Outcome:** Evaluator can register an email via `POST /v1/register` and see verification code in console logs.

**FRs Covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR18, FR21, FR23, FR27, FR29, FR31
**NFRs Addressed:** NFR-S1, NFR-S3, NFR-S4, NFR-O3

---

### Epic 3: Account Activation Flow
**User Outcome:** Evaluator can activate account via `POST /v1/activate` with BASIC AUTH, completing the Trust Loop.

**FRs Covered:** FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR22, FR28, FR30
**NFRs Addressed:** NFR-S2, NFR-P2, NFR-P3

---

### Epic 4: Trust State Machine & Adversarial Handling
**User Outcome:** Evaluator can verify adversarial scenarios: expiration (60s), lockout (3 strikes), race conditions, credential purge.

**FRs Covered:** FR15, FR16, FR17, FR19, FR20, FR24, FR25, FR26
**NFRs Addressed:** NFR-S5, NFR-S6

---

### Epic 5: Test Suite & Quality Assurance
**User Outcome:** Evaluator can run `pytest` and verify ≥90% coverage with categorized tests proving all invariants.

**FRs Covered:** FR33, FR34, FR35
**NFRs Addressed:** NFR-T1, NFR-T2, NFR-T3, NFR-T4, NFR-T5

---

## Epic 1: Project Bootstrap & Infrastructure

**User Outcome:** Evaluator can clone, run `docker-compose up`, and access a running API with PostgreSQL and OpenAPI docs at `/docs`.

### Story 1.1: Project Structure & Dependencies

As a Technical Evaluator,
I want to clone the repository and see a clear Hexagonal Architecture structure,
So that I can immediately understand the engineering approach before reading any code.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I examine the project structure
**Then** I see `src/domain/`, `src/adapters/`, `src/api/` directories
**And** the `src/domain/` directory contains `__init__.py`, `ports.py`, `exceptions.py`
**And** the `src/adapters/` directory contains `repository/` and `smtp/` subdirectories
**And** a `requirements.txt` exists with FastAPI, uvicorn, psycopg[binary], bcrypt, pydantic-settings
**And** a `.env.example` exists with sensible defaults

---

### Story 1.2: Docker Compose & Database Setup

As a Technical Evaluator,
I want to run `docker-compose up` and have a working PostgreSQL database with the schema ready,
So that I can test the API without manual database setup.

**Acceptance Criteria:**

**Given** Docker and Docker Compose are installed
**When** I run `docker-compose up`
**Then** PostgreSQL container starts on port 5432
**And** API container starts and connects to PostgreSQL
**And** database migration `001_create_registrations.sql` executes automatically
**And** the `registrations` table exists with columns: id, email, password_hash, verification_code, state, attempt_count, created_at, activated_at
**And** system is ready within 60 seconds (NFR-P1)

---

### Story 1.3: FastAPI App with OpenAPI Docs

As a Technical Evaluator,
I want to access `/docs` and see auto-generated API documentation,
So that I can test the Trust Loop directly from my browser.

**Acceptance Criteria:**

**Given** the system is running via `docker-compose up`
**When** I navigate to `http://localhost:8000/docs`
**Then** I see Swagger UI with API documentation
**And** `/v1/register` and `/v1/activate` endpoints are listed (stubbed)
**And** I can view request/response schemas
**When** I navigate to `http://localhost:8000/redoc`
**Then** I see ReDoc alternative documentation

---

### Story 1.4: README with Architecture Documentation

As a Technical Evaluator,
I want to read the README and understand the architecture before setup instructions,
So that I can evaluate the engineering judgment before running anything.

**Acceptance Criteria:**

**Given** I open the README.md
**When** I read from top to bottom
**Then** I see Architecture section BEFORE Setup/Installation section
**And** the Trust State Machine is explained with state diagram
**And** Hexagonal Architecture boundaries are documented
**And** the "Identity Claim Dilemma" problem is explained
**And** setup is a single `docker-compose up` command

---

## Epic 2: User Registration Flow

**User Outcome:** Evaluator can register an email via `POST /v1/register` and see verification code in console logs.

### Story 2.1: Domain Registration Service & Port Interfaces

As a Technical Evaluator,
I want the domain layer to define registration logic with zero framework imports,
So that I can verify the Hexagonal Architecture purity.

**Acceptance Criteria:**

**Given** I inspect `src/domain/registration.py`
**When** I check the imports
**Then** there are NO imports from FastAPI, Pydantic, or psycopg3
**And** `RegistrationService` class exists with `register()` method
**And** email normalization logic exists (strip + lowercase)
**And** verification code generation uses `secrets` module (4 digits)
**And** `src/domain/ports.py` defines `RegistrationRepository` protocol with `claim_email()` method
**And** `src/domain/ports.py` defines `EmailSender` protocol with `send_verification_code()` method

---

### Story 2.2: PostgreSQL Repository - Email Claim

As a Technical Evaluator,
I want the repository to atomically claim emails preventing race conditions,
So that I can verify concurrent registration attempts are handled correctly.

**Acceptance Criteria:**

**Given** `src/adapters/repository/postgres.py` implements `RegistrationRepository`
**When** I inspect the `claim_email()` method
**Then** it uses raw SQL with `INSERT ... ON CONFLICT DO NOTHING` (FR18)
**And** it uses parameterized queries (no f-strings)
**And** password is hashed with bcrypt cost factor ≥10 before storage (NFR-S1)
**And** returns `True` if claim successful, `False` if email already claimed
**When** two concurrent requests try to claim the same email
**Then** exactly one succeeds, the other fails gracefully

---

### Story 2.3: Console Email Sender Adapter

As a Technical Evaluator,
I want verification codes to appear in console logs,
So that I can complete the Trust Loop without a real email server.

**Acceptance Criteria:**

**Given** `src/adapters/smtp/console.py` implements `EmailSender`
**When** `send_verification_code()` is called
**Then** the verification code is printed to stdout (NFR-O3)
**And** format is clearly visible: `[VERIFICATION] Email: user@example.com Code: 1234`
**And** code is visible in `docker-compose logs`

---

### Story 2.4: Register API Endpoint

As a Technical Evaluator,
I want to call `POST /v1/register` with email and password,
So that I can begin the registration flow via Swagger UI.

**Acceptance Criteria:**

**Given** I call `POST /v1/register` with valid JSON `{"email": "user@example.com", "password": "secure123"}`
**When** the email is not already claimed
**Then** I receive 201 Created with `{"message": "Verification code sent", "expires_in_seconds": 60}`
**And** the verification code appears in console logs
**And** the email is normalized (FR2): `" User@Example.COM "` → `"user@example.com"`

**Given** I call `POST /v1/register` with an already-claimed email
**When** the registration is processed
**Then** I receive 409 Conflict with `{"detail": "Registration failed"}` (FR21, NFR-S4)
**And** the error message is generic (no email enumeration)

**Given** I call `POST /v1/register` with invalid JSON
**When** validation fails
**Then** I receive 422 with Pydantic validation details

---

## Epic 3: Account Activation Flow

**User Outcome:** Evaluator can activate account via `POST /v1/activate` with BASIC AUTH, completing the Trust Loop.

### Story 3.1: Domain State Machine & Verification Logic

As a Technical Evaluator,
I want the domain to enforce Trust State Machine rules with forward-only transitions,
So that I can verify the state machine invariants are protected in pure domain code.

**Acceptance Criteria:**

**Given** I inspect `src/domain/registration.py`
**When** I examine the state definitions
**Then** states are defined as enum: CLAIMED, ACTIVE, EXPIRED, LOCKED (FR13)
**And** `verify_and_activate()` method exists in domain service
**And** verification checks: code match (FR8), password match (FR9), within 60s (FR10), attempts < 3 (FR11)
**And** successful verification transitions CLAIMED → ACTIVE (FR12)
**And** state transitions are forward-only (FR14) - no ACTIVE → CLAIMED allowed

---

### Story 3.2: PostgreSQL Repository - Verify and Activate

As a Technical Evaluator,
I want the repository to verify credentials and update state atomically,
So that I can verify concurrent activation attempts don't cause inconsistencies.

**Acceptance Criteria:**

**Given** `src/adapters/repository/postgres.py` has `verify_and_activate()` method
**When** I inspect the implementation
**Then** it uses `SELECT ... FOR UPDATE` to lock the row during verification
**And** code comparison uses `secrets.compare_digest()` for constant-time (NFR-S2)
**And** password verification uses bcrypt's built-in constant-time comparison
**And** returns `VerifyResult` enum: SUCCESS, INVALID_CODE, EXPIRED, LOCKED, NOT_FOUND
**And** on SUCCESS: state updated to ACTIVE, activated_at timestamp set

---

### Story 3.3: Activate API Endpoint with BASIC AUTH

As a Technical Evaluator,
I want to call `POST /v1/activate` with BASIC AUTH and verification code,
So that I can complete the Trust Loop and activate my account.

**Acceptance Criteria:**

**Given** I registered with `user@example.com` and received code `1234`
**When** I call `POST /v1/activate` with:
- Header: `Authorization: Basic base64(user@example.com:password)`
- Body: `{"code": "1234"}`
**Then** I receive 200 OK with `{"message": "Account activated", "email": "user@example.com"}`
**And** the account state is now ACTIVE

**Given** I provide wrong code OR wrong password OR expired registration
**When** I call `POST /v1/activate`
**Then** I receive 401 Unauthorized with `{"detail": "Invalid credentials or code"}` (FR21)
**And** the error message is identical regardless of failure reason (NFR-P3)
**And** response timing is consistent regardless of failure mode (NFR-P2)

---

### Story 3.4: Timing-Safe Error Responses

As a Technical Evaluator,
I want all error responses to have consistent timing,
So that I can verify the system is resistant to timing oracle attacks.

**Acceptance Criteria:**

**Given** I measure response times for activation attempts
**When** I compare timing for: wrong password, wrong code, expired, non-existent email
**Then** response times are statistically indistinguishable (within noise margin)
**And** bcrypt verification runs even for non-existent emails (dummy hash comparison)
**And** `secrets.compare_digest()` is used for all string comparisons
**And** no early returns that could leak information via timing

---

## Epic 4: Trust State Machine & Adversarial Handling

**User Outcome:** Evaluator can verify adversarial scenarios: expiration (60s), lockout (3 strikes), race conditions, credential purge.

### Story 4.1: Registration Expiration (60-Second Timeout)

As a Technical Evaluator,
I want registrations to expire after 60 seconds,
So that I can verify the time-bounded proof invariant.

**Acceptance Criteria:**

**Given** a user registered but did not activate
**When** 60 seconds elapse since registration
**Then** the registration state becomes EXPIRED (FR15)
**And** activation attempts return "Invalid credentials or code"
**And** the `created_at` timestamp is used to calculate expiration
**And** expiration check uses database time: `created_at > NOW() - INTERVAL '60 seconds'`

---

### Story 4.2: Account Lockout (3 Failed Attempts)

As a Technical Evaluator,
I want accounts to lock after 3 failed verification attempts,
So that I can verify brute-force protection.

**Acceptance Criteria:**

**Given** a user has a CLAIMED registration
**When** they submit 3 incorrect verification codes
**Then** `attempt_count` increments with each failure (FR19)
**And** after 3rd failure, state transitions to LOCKED (FR16, FR20)
**And** subsequent attempts return "Invalid credentials or code"
**And** locked state persists even with correct code

---

### Story 4.3: Credential Purge (Data Stewardship)

As a Technical Evaluator,
I want password hashes to be purged when registrations expire or lock,
So that I can verify the Data Stewardship principle.

**Acceptance Criteria:**

**Given** a registration has EXPIRED or LOCKED state
**When** the state transition occurs (or on next verification check - lazy purge)
**Then** `password_hash` is set to NULL in the database (FR24)
**And** no "ghost credentials" exist for unverified accounts (FR25)
**And** purge happens within 60 seconds of expiration (NFR-S6)
**And** database credentials never appear in application logs (NFR-S5)

---

### Story 4.4: Email Release and Re-Registration

As a Technical Evaluator,
I want to re-register with an email that previously expired or locked,
So that I can verify the email release mechanism.

**Acceptance Criteria:**

**Given** an email address has EXPIRED or LOCKED registration
**When** a new registration attempt is made for that email
**Then** the old record is released/cleaned up (FR17)
**And** new registration succeeds with fresh verification code
**And** `attempt_count` resets to 0
**And** new `created_at` timestamp is set (FR26)
**And** the process is atomic (no race conditions)

---

## Epic 5: Test Suite & Quality Assurance

**User Outcome:** Evaluator can run `pytest` and verify ≥90% coverage with categorized tests proving all invariants.

### Story 5.1: Unit Tests for Domain Logic

As a Technical Evaluator,
I want to run unit tests that verify domain logic with mocked ports,
So that I can confirm the Trust State Machine rules are enforced in pure domain code.

**Acceptance Criteria:**

**Given** I run `pytest tests/unit/`
**When** the tests execute
**Then** all domain logic is tested with mocked repository and email sender
**And** tests verify: email normalization, code generation, state transitions
**And** tests verify: forward-only state machine enforcement
**And** tests are isolated with no shared state (NFR-T5)
**And** test file naming: `test_registration.py`
**And** test function naming: `test_<action>_<scenario>()`

---

### Story 5.2: Integration Tests for Repository

As a Technical Evaluator,
I want to run integration tests against a real PostgreSQL database,
So that I can verify the SQL implementation is correct.

**Acceptance Criteria:**

**Given** I run `pytest tests/integration/`
**When** the tests execute against PostgreSQL
**Then** tests verify: atomic email claim with race condition handling
**And** tests verify: verify_and_activate with row locking
**And** tests verify: credential purge on expiration/lockout
**And** `conftest.py` provides database fixtures with transaction rollback
**And** each test runs in isolated transaction (NFR-T5)
**And** tests clean up after themselves

---

### Story 5.3: Adversarial Tests for Security Invariants

As a Technical Evaluator,
I want dedicated adversarial tests proving security properties,
So that I can verify the system handles attack scenarios correctly.

**Acceptance Criteria:**

**Given** I run `pytest tests/adversarial/`
**When** the adversarial tests execute
**Then** `test_race_conditions.py` proves concurrent claims are handled (FR18)
**And** `test_timing_attacks.py` proves constant-time responses (NFR-P2)
**And** `test_brute_force.py` proves 3-strike lockout works (FR16, FR20)
**And** tests are marked with `@pytest.mark.adversarial` (NFR-T4)
**And** tests can be run separately: `pytest -m adversarial`

---

### Story 5.4: Coverage Reporting & CI Configuration

As a Technical Evaluator,
I want to run `pytest` and see ≥90% code coverage,
So that I can verify comprehensive test coverage.

**Acceptance Criteria:**

**Given** I run `pytest --cov=src --cov-report=term-missing`
**When** the full test suite executes
**Then** coverage report shows ≥90% coverage (NFR-T1)
**And** all tests pass on fresh clone (NFR-T2)
**And** tests are categorized: unit, integration, adversarial (NFR-T3)
**And** `pytest.ini` or `pyproject.toml` configures coverage settings
**And** coverage can fail build: `--cov-fail-under=90`
