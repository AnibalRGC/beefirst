---
stepsCompleted: [1, 2, 3, 4, 7, 9, 10, 11]
inputDocuments:
  - product-brief-beefirst-2026-01-10.md
  - brainstorming-session-2026-01-10.md
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 1
  projectDocs: 0
workflowType: 'prd'
lastStep: 11
status: complete
project_name: beefirst
author: Anibal
date: 2026-01-11
---

# Product Requirements Document - beefirst

**Author:** Anibal
**Date:** 2026-01-11

## Executive Summary

The **beefirst** project implements a User Registration API that solves the **Identity Claim Dilemma**: ensuring that an entity claiming an email address actually controls that communication channel, within a strict 60-second security window.

This is not a CRUD application. It is a **State Machine of Trust** - a system where invalid states are unrepresentable by design. The architecture enforces safety through invariant guarantees, not just documentation.

### The Core Problem

Three interconnected challenges drive this implementation:

1. **Identity Theft Prevention** - Ensuring the entity claiming an email address actually controls that communication channel
2. **Time-Sensitive Security** - Enforcing a strict 60-second window of proof to minimize exposure of unverified credentials
3. **Engineering Transparency** - Demonstrating senior engineering judgment without hiding behind ORM abstractions or framework "magic"

### Target Audience

**Primary: The Technical Evaluator** - Senior Backend Engineers, Tech Leads, and CTOs reviewing this code as a hiring assessment. They are pattern-matching for signals of senior judgment vs. junior shortcuts.

**Secondary: The Registering User** - A theoretical adversary proxy whose experience tests identity squatting, brute-force attempts, and timing attacks.

### What Makes This Special

**Intentional Engineering.** Every architectural decision is traceable to a security or reliability guarantee. This demonstrates the exact evaluation criteria senior engineers look for: architectural discipline, production thinking, and edge case handling.

| Differentiator | Evidence | Verification |
|----------------|----------|--------------|
| **11 Fundamental Truths** | Invariant guarantees that define "working" vs "broken" | Each Truth has a corresponding test that fails if violated |
| **State Immutability** | Forward-only state machine (see diagram below) | Database constraints prevent backward transitions |
| **Pure Domain Core** | `domain/` contains business logic with zero infrastructure imports | Defines its own port interfaces - true decoupling |
| **Adversarial Engineering** | 12 failure scenarios identified and mitigated before coding | Test suite includes adversarial scenarios |
| **Data Stewardship** | "We have no right to hold credentials for an unverified identity" | Expired records automatically purged |

### Trust State Machine

```
AVAILABLE ──claim──► CLAIMED ──verify──► ACTIVE
                        │
                        ├──timeout──► EXPIRED ──► AVAILABLE
                        │
                        └──3 fails──► LOCKED ──► AVAILABLE
```

*Once ACTIVE, a user cannot be re-claimed or re-activated. The machine only moves forward or resets.*

### The "Aha!" Moment

The evaluator opens the repository and sees `domain/` first in the project structure. The README opens with architecture, not setup instructions. Inside `domain/registration.py`: pure business logic implementing the Trust State Machine with zero infrastructure dependencies and explicit port interfaces.

That's when they realize: *"This candidate isn't just a coder; they designed for invariants."*

## Project Classification

**Technical Type:** api_backend
**Domain:** general (technical demonstration)
**Complexity:** low (no regulatory constraints)
**Project Context:** Greenfield - new project

This is a technical assessment project. While the domain complexity is low, the engineering complexity is intentionally high - demonstrating production-grade thinking is the feature, not a constraint.

## Success Criteria

### User Success (The Technical Evaluator)

Success is measured by a single outcome: **"Proceed to Interview" or "Hire" recommendation.**

This outcome is achieved through three specific proof points that transform possibility into certainty:

| Signal | What They See | What They Think |
|--------|--------------|-----------------|
| **Seniority Signal** | `domain/registration.py` with zero framework imports + self-defined port interfaces | "This candidate manages complexity without magic" |
| **Adversarial Proof** | Test categories explicitly covering Clock Drift, Timing Oracles, Race Conditions | "This candidate anticipated production failures before I asked" |
| **Ethical Signal** | "Zero Ghost Credentials" test querying raw database to verify credential purging | "This candidate's engineering decisions are principled" |

**The "Aha!" Moment:** The evaluator opens `domain/registration.py` and realizes the entire Trust State Machine is implemented without a single import from FastAPI, Pydantic, or psycopg3. The code defines its own port interfaces, proving true architectural decoupling—not just layering.

### Business Success

Success extends beyond the immediate assessment:

| Timeframe | Success Definition |
|-----------|-------------------|
| **Immediate** | Evaluator sees Domain Core → "Proceed to Interview" decision |
| **3 Months** | Portfolio piece demonstrating Hexagonal Mastery + Adversarial Security thinking |
| **Long-term** | Reusable "Trust State Machine" pattern applicable to any time-bounded, sensitive state transition |

**The Reusable Asset:** The "11 Fundamental Truths" framework is a portable methodology for aligning stakeholders and engineers on system guarantees—usable in any future role.

**The Portfolio Value:** A reference implementation proving you can decouple business rules from volatile infrastructure, and that you think like a defender proactively mitigating attacks.

### Technical Success

| Metric | Target | Verification |
|--------|--------|--------------|
| **Setup Time** | < 60 seconds from `git clone` to running API | Timed fresh clone test |
| **Test Coverage** | > 90% | pytest coverage report |
| **Test Pass Rate** | 100% on fresh clone | All tests green, zero flaky tests |
| **Edge Case Coverage** | 12/12 failure scenarios | Each scenario has explicit test |
| **Architectural Purity** | 0 framework imports in `domain/` | Static analysis or manual verification |
| **Documentation Completeness** | 100% endpoints documented | OpenAPI spec auto-generated |

### Measurable Outcomes

**Truth Verification Tests:**

| Fundamental Truth | Test Assertion |
|-------------------|----------------|
| Unique Claim Lock | 10 concurrent requests for same email → exactly 1 succeeds |
| Time-Bounded Proof | Verification at T+61 seconds → fails |
| Dual-Factor Activation | Valid code + wrong password → fails |
| Data Stewardship | Query for unverified hashed passwords after expiration → 0 results |
| Attempt Limiting | 4th failed code attempt → account locked |
| Normalization | `John@Email.com` and `john@email.com` → same identity |
| Atomicity | Simulated DB failure mid-operation → no partial state |

## Product Scope

### MVP - Minimum Viable Product

**Tier 1: Spec Compliance (Non-Negotiable)**

| Feature | Endpoint/Component | Description |
|---------|-------------------|-------------|
| User Registration | `POST /register` | Create user with email and password |
| Verification Delivery | SMTP Adapter | Generate and deliver 4-digit code (console output for demo) |
| Account Activation | `POST /activate` | Verify using BASIC AUTH + 4-digit code |
| Temporal Logic | Domain Core | Strict 60-second expiration window |
| Infrastructure | Docker | Complete `docker-compose` setup for API + PostgreSQL |
| Testing | pytest | Comprehensive test suite with adversarial scenarios |

**Tier 2: Production Signals (Senior Differentiators)**

| Signal | Implementation | Why It Matters |
|--------|----------------|----------------|
| Hexagonal Architecture | Domain Core isolated from FastAPI/psycopg3 | Demonstrates architectural discipline |
| Atomic State Transitions | `ON CONFLICT` + transactions in raw SQL | Prevents race conditions |
| Data Stewardship | Auto-disposal of unverified credentials | Shows security mindset |
| Normalization | Case-insensitive, whitespace-neutral identity | Prevents subtle bugs |
| Adversarial Security | 3-strikes rule, constant-time responses | Mitigates brute-force and timing attacks |

### Growth Features (Post-MVP)

| Feature | Value | Priority |
|---------|-------|----------|
| Resend Code Endpoint | Better UX if email delivery slow | Low |
| Background Cleanup Worker | Active "Reaper" for expired records | Low |
| Advanced Observability | Structured logging, basic metrics | Low |

**Implementation Strategy:** Complete MVP (Tier 1 + Tier 2) first. Only add Growth features if time permits and core quality is not compromised.

### Vision (Future Extensions)

| Phase | Expansion |
|-------|-----------|
| V1.1 | Resend endpoint, background cleanup worker |
| V1.2 | Persistent rate limiting with Redis |
| V2.0 | Full authentication flow (login, JWT, refresh tokens) |
| V2.1 | Password reset, email change flows |
| V3.0 | Multi-factor authentication, OAuth integration |

**Key Insight:** The Hexagonal Architecture ensures these expansions don't require rewriting the Domain Core—only adding new adapters and use cases.

### Explicitly Out of Scope

| Feature | Reason for Exclusion |
|---------|---------------------|
| Post-Activation Authentication | Spec ends at activation; `/login` not required |
| Password Management | Reset flows are separate concerns |
| Persistent Rate Limiting | In-memory for demo; Redis documented as "Production Recommendation" |
| Admin Features | Dashboards, user lists are operational concerns |

## User Journeys

### Journey 1: The Evaluator's Review Journey (Architectural Discovery)

**Persona:** Senior Backend Engineer, Tech Lead, or CTO evaluating a technical assessment
**Goal:** Determine if this candidate demonstrates senior engineering judgment
**Success Moment:** The realization that this is production-grade engineering, not a CRUD demo

---

The evaluator receives a link to the repository. They're scanning dozens of assessments this week, looking for reasons to reject quickly. Most candidates bury the interesting stuff under boilerplate.

**Step 1: The README Gateway**
They clone the repo and open the README. Instead of "Install Node.js version X," they see an architecture diagram and the "11 Fundamental Truths" prominently displayed. Their eyebrows raise slightly—this is different.

**Step 2: The "Zero Friction" Execution**
They run `docker-compose up` followed by `pytest`. The containers spin up in seconds. All tests pass—including categories labeled "Adversarial: Clock Drift" and "Adversarial: Race Conditions." They pause. Most candidates don't test for things like this.

**Step 3: The Deep Dive**
They navigate to the `domain/` directory. Inside `registration.py`, they find the complete Trust State Machine—state transitions, invariant checks, port interfaces—without a single import from FastAPI, Pydantic, or psycopg3. This is when the shift happens: *"This candidate designed for invariants."*

**Step 4: Truth Verification**
They examine the repository adapters. In the raw SQL, they find `ON CONFLICT DO NOTHING` for atomic claims and `SELECT FOR UPDATE` for isolation. The "11 Truths" aren't just documentation—they're enforced in code.

**The Verdict:** "Proceed to Interview."

---

**Journey Requirements Revealed:**
- README must lead with architecture, not setup
- Test suite must have explicit adversarial scenario categories
- `domain/` must contain pure business logic with zero framework imports
- SQL must demonstrate atomic operations and proper locking

---

### Journey 2: The Legitimate User's Happy Path (Trust Loop)

**Persona:** A person creating an account (proxy for API consumer)
**Goal:** Prove email ownership and activate account within 60 seconds
**Success Moment:** Transition from CLAIMED to ACTIVE state

---

A user decides to register for the service. They have their email open in another tab, ready to receive the verification code.

**Step 1: The Claim**
The user submits their email and password via `POST /register`. Behind the scenes, the system normalizes the email (`strip().lower()`), hashes the password with bcrypt, and prepares to stake a claim.

**Step 2: State Transition**
The system attempts an atomic insert with `ON CONFLICT DO NOTHING`. If successful, the email is now CLAIMED—locked to this registration attempt. A 60-second timer begins ticking at the database level using `NOW()`.

**Step 3: Secret Delivery**
A cryptographically random 4-digit code is generated via `secrets.choice()`. The code appears in the console output (simulating third-party SMTP delivery). The email is sent only AFTER the database transaction commits—no "Persistence Ghosts."

**Step 4: The Proof**
The user copies the code and provides it along with their credentials via `POST /activate` using BASIC AUTH. This dual-factor approach proves both channel possession (the code) and identity knowledge (the password).

**Step 5: Trust Granted**
The system verifies: (1) the code matches, (2) the password matches, (3) the TTL is under 60 seconds, (4) fewer than 3 failed attempts. All checks pass atomically. The user transitions to ACTIVE.

**The Outcome:** The user is now a trusted, verified identity in the system.

---

**Journey Requirements Revealed:**
- `POST /register` endpoint accepting email + password
- Email normalization (case-insensitive, whitespace-neutral)
- Atomic claim with database-level uniqueness
- Secure 4-digit code generation
- `POST /activate` endpoint with BASIC AUTH
- Multi-condition verification (code + password + TTL + attempts)

---

### Journey 3: The Adversary's Attack Journey (State Protection)

**Persona:** A theoretical attacker probing the system for vulnerabilities
**Goal:** Compromise identity, bypass verification, or extract information
**Success Moment (for the system):** Every attack fails; invalid states remain unrepresentable

---

An adversary targets the registration system, attempting multiple attack vectors. Each attack demonstrates a specific defense.

**Attack A: The Squatter (Race Condition)**
The attacker tries to register an email that's already in CLAIMED or ACTIVE state—perhaps to block a legitimate user or hijack their identity.

*System Response:* The database-level `UNIQUE` constraint combined with `ON CONFLICT DO NOTHING` rejects the second claim atomically. The attacker receives a generic error; the legitimate claim remains protected.

*Truth Enforced:* Unique Claim Lock

**Attack B: The Brute-Forcer**
The attacker doesn't have access to the target's email but tries to guess the 4-digit code through repeated attempts.

*System Response:* On the 4th failed attempt (after 3 strikes), the system atomically: (1) moves the record to EXPIRED status, (2) purges the hashed password from the database, (3) releases the email for future registration. The attacker gains nothing; the legitimate user can simply re-register.

*Truths Enforced:* Attempt Limiting, Data Stewardship

**Attack C: The Patient Attacker**
The attacker intercepts a code but waits until 61 seconds have passed, hoping the system has a timing bug.

*System Response:* The verification query includes `WHERE created_at > NOW() - INTERVAL '60 seconds'`. At T+61, the code is mathematically invalid regardless of correctness. The system rejects the transition.

*Truth Enforced:* Time-Bounded Proof

**Attack D: The Timing Oracle**
The attacker probes different emails to determine which are registered by measuring response times or analyzing error messages.

*System Response:* All responses use generic "Invalid credentials or code" messages. Password verification uses bcrypt's built-in constant-time comparison. Response timing is normalized to prevent inference.

*Truth Enforced:* Anti-Enumeration (implicit)

---

**Journey Requirements Revealed:**
- Database constraints must enforce uniqueness at the storage level
- Attempt counter with automatic lockout after 3 failures
- Credential purging on expiration/lockout
- Strict temporal checks using database timestamps
- Generic error messages for all failure modes
- Constant-time operations for sensitive comparisons

---

### Journey Requirements Summary

| Journey | Primary Capability Areas |
|---------|-------------------------|
| **Evaluator's Review** | Project structure, documentation, test organization, architectural purity |
| **Legitimate User** | Registration endpoint, verification flow, state transitions, dual-factor activation |
| **Adversary Attacks** | Race condition prevention, brute-force protection, temporal enforcement, information hiding |

**Cross-Journey Requirements:**

| Requirement | Revealed By |
|-------------|-------------|
| Atomic database operations | Evaluator (Deep Dive), Adversary (Squatter) |
| Pure domain logic | Evaluator (Deep Dive) |
| Adversarial test coverage | Evaluator (Zero Friction), Adversary (All attacks) |
| Data stewardship | Adversary (Brute-Forcer) |
| Temporal invariants | Legitimate User (Trust Loop), Adversary (Patient Attacker) |
| Constant-time responses | Adversary (Timing Oracle) |

## API Backend Specific Requirements

### API Design Principles

This API follows RESTful conventions with deliberate choices that signal senior engineering judgment:

| Principle | Decision | Rationale |
|-----------|----------|-----------|
| **Data Format** | JSON only | Industry standard, natively supported by FastAPI/Pydantic |
| **Versioning** | Explicit path versioning (`/v1/`) | Demonstrates design for contract evolution |
| **Documentation** | Auto-generated OpenAPI (Swagger) | Evaluator can test Trust Loop without writing client code |
| **Error Responses** | Generic messages, consistent structure | Security-first: prevents information leakage |

### Endpoint Specifications

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/v1/register` | POST | Claim an email and begin verification | None |
| `/v1/activate` | POST | Verify code and activate account | BASIC AUTH |

#### POST /v1/register

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Success Response (201 Created):**
```json
{
  "message": "Verification code sent",
  "expires_in_seconds": 60
}
```

**Error Response (409 Conflict - Email already claimed/active):**
```json
{
  "detail": "Registration failed"
}
```

*Note: Generic error message prevents email enumeration attacks.*

#### POST /v1/activate

**Request:**
- Header: `Authorization: Basic base64(email:password)`
- Body:
```json
{
  "code": "1234"
}
```

**Success Response (200 OK):**
```json
{
  "message": "Account activated",
  "email": "user@example.com"
}
```

**Error Responses (401 Unauthorized):**
```json
{
  "detail": "Invalid credentials or code"
}
```

*Note: Same generic message for wrong password, wrong code, expired code, or locked account. Prevents timing oracle attacks.*

### Authentication Model

| Aspect | Implementation | Security Consideration |
|--------|---------------|----------------------|
| **Registration** | No auth required | Public endpoint for new users |
| **Activation** | HTTP BASIC AUTH | Dual-factor: proves password knowledge + code possession |
| **Password Storage** | bcrypt hash | Industry standard, constant-time comparison |
| **Credential Lifecycle** | Purged on expiration/lockout | Data stewardship principle |

### Data Schemas

**Email Normalization:**
- `strip()` - Remove leading/trailing whitespace
- `lower()` - Case-insensitive comparison
- Result: `" John@Email.COM "` → `"john@email.com"`

**Verification Code:**
- 4 digits, cryptographically random (`secrets.choice()`)
- Stored as plaintext (not a password, it's a channel proof)
- Single-use, expires with registration attempt

**Password Requirements:**
- Minimum length enforced by Pydantic validation
- Hashed with bcrypt before storage
- Never stored for unverified accounts after expiration

### Error Handling Strategy

| Scenario | HTTP Status | Response Body | Security Note |
|----------|-------------|---------------|---------------|
| Email already claimed | 409 | Generic "Registration failed" | Prevents enumeration |
| Invalid/expired code | 401 | Generic "Invalid credentials or code" | Prevents timing oracle |
| Wrong password | 401 | Generic "Invalid credentials or code" | Same as wrong code |
| Account locked (3 strikes) | 401 | Generic "Invalid credentials or code" | No lockout disclosure |
| Validation error | 422 | Pydantic validation details | Safe to expose |

### Rate Limiting

| Mechanism | Scope | Limit | Action |
|-----------|-------|-------|--------|
| **Verification Attempts** | Per registration | 3 attempts | Lock + purge credentials |
| **API Rate Limiting** | Per IP (future) | TBD | In-memory for demo, Redis for production |

*Note: The 3-strikes rule is the primary brute-force protection. General API rate limiting is documented as a "Production Recommendation" for future implementation.*

### API Documentation

**Auto-Generated OpenAPI:**
- Endpoint: `/docs` (Swagger UI)
- Endpoint: `/redoc` (ReDoc alternative)
- Endpoint: `/openapi.json` (Raw spec)

**Evaluator Experience:**
The Technical Evaluator can:
1. Open `/docs` in browser
2. Execute the full Trust Loop (register → activate) via Swagger UI
3. Test adversarial scenarios directly without writing client code

This makes the API self-documenting and immediately testable—zero friction for evaluation.

## Functional Requirements

### User Registration

- FR1: Users can submit an email address and password to begin registration
- FR2: System can normalize email addresses (case-insensitive, whitespace-neutral)
- FR3: System can atomically claim an email address, preventing duplicate registrations
- FR4: System can generate a cryptographically random 4-digit verification code
- FR5: System can deliver the verification code to the user (console output for demo)
- FR6: System can reject registration attempts for already-claimed or active emails

### Identity Verification

- FR7: Users can submit a verification code with credentials to activate their account
- FR8: System can verify the submitted code matches the generated code
- FR9: System can verify the submitted password matches the stored hash
- FR10: System can verify the verification attempt is within the 60-second window
- FR11: System can verify fewer than 3 failed attempts have occurred
- FR12: System can transition a user from CLAIMED to ACTIVE upon successful verification

### State Management (Trust State Machine)

- FR13: System can represent user states: AVAILABLE, CLAIMED, ACTIVE, EXPIRED, LOCKED
- FR14: System can enforce forward-only state transitions (no backward movement)
- FR15: System can transition CLAIMED → EXPIRED when 60 seconds elapse
- FR16: System can transition CLAIMED → LOCKED after 3 failed verification attempts
- FR17: System can release email addresses from EXPIRED or LOCKED states back to AVAILABLE

### Security & Protection

- FR18: System can prevent race conditions during concurrent registration attempts
- FR19: System can track and limit verification attempts per registration
- FR20: System can lock accounts after exceeding the attempt threshold
- FR21: System can return generic error messages that prevent information disclosure
- FR22: System can perform constant-time password comparisons
- FR23: System can hash passwords using bcrypt before storage

### Data Lifecycle & Stewardship

- FR24: System can purge hashed passwords when registrations expire or lock
- FR25: System can ensure no "ghost credentials" exist for unverified accounts
- FR26: System can timestamp all state transitions using database time

### API Interface

- FR27: System can expose a versioned API endpoint for registration (`POST /v1/register`)
- FR28: System can expose a versioned API endpoint for activation (`POST /v1/activate`)
- FR29: System can accept and return JSON data format exclusively
- FR30: System can authenticate activation requests using HTTP BASIC AUTH
- FR31: System can auto-generate OpenAPI documentation accessible at `/docs`

### Infrastructure & Operations

- FR32: System can run via Docker Compose with a single command
- FR33: System can execute all tests via pytest with a single command
- FR34: System can categorize tests by scenario type (happy path, adversarial)
- FR35: System can report test coverage metrics

### Architectural Constraints (Evaluator-Facing)

- FR36: Domain logic can exist without framework imports (FastAPI, Pydantic, psycopg3)
- FR37: Domain logic can define its own port interfaces for infrastructure abstraction
- FR38: Repository adapters can use raw SQL with explicit transaction control
- FR39: README can present architecture and invariants before setup instructions

## Non-Functional Requirements

### Security

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-S1 | Passwords must be hashed using bcrypt with cost factor ≥ 10 | Code inspection |
| NFR-S2 | Password verification must use constant-time comparison | Timing analysis test |
| NFR-S3 | Verification codes must be generated using cryptographically secure randomness | Code inspection (`secrets` module) |
| NFR-S4 | All error responses must use generic messages that prevent information disclosure | Response inspection |
| NFR-S5 | Database credentials must not appear in application logs | Log inspection |
| NFR-S6 | Hashed passwords for unverified accounts must be purged within 60 seconds of expiration | Database query after expiration |

### Performance

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-P1 | System must start and be ready to accept requests within 60 seconds of `docker-compose up` | Timed startup test |
| NFR-P2 | Password verification response time must not reveal validity (constant-time) | Timing distribution analysis |
| NFR-P3 | Error responses must have consistent timing regardless of failure mode | Timing distribution analysis |

### Testability & Quality

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-T1 | Test suite must achieve ≥ 90% code coverage | pytest coverage report |
| NFR-T2 | All tests must pass on fresh clone (100% pass rate) | CI/fresh clone test |
| NFR-T3 | Tests must be categorized by scenario type (happy path, adversarial) | Test organization inspection |
| NFR-T4 | Adversarial scenarios must have dedicated test coverage | Test suite includes adversarial markers |
| NFR-T5 | Tests must be isolated (no shared state between tests) | Test independence verification |

### Maintainability & Architecture

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-M1 | Domain logic must have zero imports from infrastructure (FastAPI, Pydantic, psycopg3) | Static analysis / import inspection |
| NFR-M2 | Domain module must define port interfaces for all infrastructure dependencies | Code inspection |
| NFR-M3 | All SQL queries must be explicit (no ORM magic) | Code inspection |
| NFR-M4 | Code must follow Python conventions (PEP 8, type hints) | Linter output |

### Operational

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-O1 | System must run in Docker with no host dependencies beyond Docker | Fresh machine test |
| NFR-O2 | All environment variables must have sensible defaults for demo mode | Default configuration test |
| NFR-O3 | Verification codes must be visible in logs/console for demo purposes | Log inspection |
