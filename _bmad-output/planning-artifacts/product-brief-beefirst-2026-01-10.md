---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: complete
inputDocuments:
  - brainstorming-session-2026-01-10.md
  - user_registration_api.md
date: 2026-01-10
author: Anibal
project_name: beefirst
---

# Product Brief: User Registration API

## Executive Summary

The User Registration API is not merely a user onboarding system—it is a **State Machine of Trust** that solves the fundamental **Identity Claim Dilemma**: ensuring that an entity claiming an email address actually controls that communication channel, within a strict time-bounded security window.

This project serves dual stakeholders: the **Technical Evaluator** who needs to see production-grade engineering judgment without framework abstractions, and the **Registering User** who requires a secure, frictionless experience where their identity cannot be squatted or brute-forced.

The implementation is guided by 11 Fundamental Truths that define "working" vs "broken," a Hexagonal Architecture that isolates business rules from infrastructure, and adversarial engineering that anticipates 12 failure scenarios before they become production incidents.

**Key Differentiator:** This is not code that works—it is code that demonstrates *why* it works, with every architectural decision traceable to a security or reliability guarantee.

---

## Core Vision

### Problem Statement

The Identity Claim Dilemma presents three interconnected challenges:

1. **Identity Theft Prevention** - Ensuring the entity claiming an email address actually controls that communication channel
2. **Time-Sensitive Security** - Enforcing a strict 60-second window of proof to minimize exposure of unverified credentials
3. **Engineering Transparency** - Demonstrating senior engineering judgment without hiding behind ORM abstractions or framework "magic"

### Problem Impact

**For Technical Evaluators:**
- Inability to assess candidate's true engineering capabilities when code hides behind abstractions
- Difficulty distinguishing "demo quality" from "production quality" implementations
- Missing visibility into how candidates handle edge cases, concurrency, and security

**For Registering Users:**
- Risk of identity squatting (malicious actors claiming emails they don't own)
- Vulnerability to brute-force attacks on verification codes
- Credential exposure when unverified data lingers in systems

### Why Existing Solutions Fall Short

Traditional registration implementations often:
- Rely on ORM "magic" that obscures data access patterns and race condition handling
- Treat verification codes as passwords (allowing unlimited guesses) rather than channel proofs
- Retain credentials indefinitely for unverified users, violating data stewardship principles
- Ignore edge cases like clock drift, orphaned commits, and concurrent claims

### Proposed Solution

A **Trust State Machine** implementation with:

- **Atomic State Transitions** - Email claims handled via `ON CONFLICT` logic preventing race conditions
- **Time-Bounded Proofs** - 60-second verification window enforced at the database level
- **Dual-Factor Activation** - Code (channel possession) + Password (identity knowledge) required together
- **Data Stewardship** - Automatic credential disposal for failed/expired verifications
- **Hexagonal Architecture** - Business rules (the "Trust Truths") remain pure and infrastructure-independent

### Key Differentiators

| Differentiator | Evidence |
|----------------|----------|
| **Philosophical Foundation** | 11 Fundamental Truths define system guarantees |
| **Adversarial Engineering** | 12 failure scenarios identified and mitigated before coding |
| **Architectural Clarity** | Hexagonal pattern separates "commodity" (HTTP) from "proprietary" (business logic) |
| **Production Mindset** | Clock drift, race conditions, timing oracles - all addressed |
| **Transparent Implementation** | Raw psycopg3 SQL - every query visible and intentional |

### Guiding Principles

> **"We have no right to hold credentials for an unverified identity."**
> — The No-Hoarding Rule

> **"If a user needs 50 tries to get a 4-digit code right, they are not 'forgetful'—they are guessing."**
> — Anti-Guessing Logic

> **"We choose modern, productive tools for commodity concerns. We write every line of business logic and data access ourselves."**
> — Engineering Transparency

---

## Target Users

### Primary User: The Technical Evaluator (The Discerning Judge)

This is the **Primary Stakeholder**. Their satisfaction determines project success.

**Profile & Context:**
- **Roles:** Senior Backend Engineer, Tech Lead, or CTO (often at a startup)
- **Typical Day:** Reviewing multiple technical assessments while balancing their own roadmap. They are looking for reasons to *not* hire—scanning for structure and "shortcuts" immediately.
- **Mindset:** Time-constrained, pattern-matching for signals of senior judgment vs. junior shortcuts

**What They're Looking For (Green Flags):**

| Signal | Evidence |
|--------|----------|
| **Senior Judgment** | Ability to explain *why* a technology was chosen (FastAPI for DI, raw psycopg3 for transparency) |
| **Architectural Discipline** | Domain Core isolated from web framework via Hexagonal Architecture |
| **Attention to Detail** | Handling edge cases (Clock Drift, Race Conditions) without being prompted |
| **Production Mindset** | Security and reliability considerations beyond "happy path" |

**Red Flags They Watch For:**

| Anti-Pattern | Why It Fails |
|--------------|--------------|
| **Reliance on "Magic"** | Using ORM when spec explicitly forbids it |
| **Ignoring Concurrency** | Missing `ON CONFLICT` or proper transactions for simultaneous registrations |
| **Poor Data Stewardship** | Keeping hashed passwords for unverified users indefinitely |
| **Missing Edge Cases** | No handling for timeout, retries, or adversarial scenarios |

**The "Aha!" Moment:**

The moment of success occurs when the Evaluator opens the code and realizes this isn't a "CRUD" app—it's a **State Machine of Trust**.

1. **The Code Pause:** They see the 11 Fundamental Truths documented as core system guarantees
2. **The Logic Realization:** They notice atomic state transitions and adversarial failure scenarios handled in raw SQL
3. **The Verdict:** *"This candidate isn't just a coder; they are an architect who anticipates production failures before they happen."*

---

### Secondary User: The Registering User (The Theoretical Adversary)

In this project, the Registering User is less of a persona to be delighted and more of a **proxy for security and UX constraints**. Their experience serves as evidence of engineering skill.

**Dual Profiles:**

| Profile | Role | Focus |
|---------|------|-------|
| **Legitimate User** | Person creating an account | Needs frictionless, secure 60-second verification flow |
| **Theoretical Adversary** | Attacker probing the system | Tests identity squatting, brute-force, and timing attacks |

**Success Criteria:**

- **Identity Security:** Email cannot be claimed or blocked by someone else indefinitely
- **Reliability:** 4-digit code works exactly as expected within the 60-second window
- **Resilience:** Basic Auth provides seamless but secure second factor for activation
- **Graceful Degradation:** If email is slow, architecture supports "Resend" strategy with instant feedback

**Design Implication:**

Every UX decision for the Registering User is ultimately an engineering demonstration for the Technical Evaluator. Good UX = Good Architecture.

---

### User Journey: The Evaluator's Review Path

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EVALUATOR JOURNEY                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. DISCOVERY                                                       │
│     └── Opens repository, scans README and project structure        │
│                                                                     │
│  2. FIRST IMPRESSION                                                │
│     └── Sees Hexagonal Architecture, clear separation of concerns   │
│     └── Notes: "This person organized their code thoughtfully"      │
│                                                                     │
│  3. DEEP DIVE                                                       │
│     └── Reads Domain Core - discovers 11 Fundamental Truths         │
│     └── Examines raw SQL - sees ON CONFLICT, atomic transactions    │
│     └── Notes: "They understand concurrency and security"           │
│                                                                     │
│  4. "AHA!" MOMENT                                                   │
│     └── Realizes this is a State Machine of Trust, not CRUD         │
│     └── Sees failure scenarios addressed proactively                │
│     └── Thinks: "This is production-grade thinking"                 │
│                                                                     │
│  5. VALIDATION                                                      │
│     └── Runs docker-compose, executes tests                         │
│     └── Tests pass, API works as documented                         │
│     └── Verdict: "This candidate demonstrates senior judgment"      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

### Primary Success Metric: Evaluator Sentiment

**Ultimate Outcome:** "Proceed to Interview" or "Hire" recommendation

**Intermediate Success Signals (Signal-to-Noise Ratio):**

| Signal | What It Demonstrates | How We Achieve It |
|--------|---------------------|-------------------|
| **Zero Friction Setup** | Production mindset, attention to developer experience | `docker-compose up` works first time with zero manual configuration |
| **Architectural Recognition** | Design stood out from other candidates | Evaluator asks about "Hexagonal" structure or "Trust State Machine" in follow-up |
| **Seniority Signal** | Anticipation of production concerns | Evaluator notes edge case handling (Clock Drift, Race Conditions) not explicitly in spec |

**Success Indicator:** The evaluator's internal reaction shifts from "does it work?" to "this candidate thinks like we do."

---

### Technical Validation Metrics

The 11 Fundamental Truths are transformed into **explicit, automated test suites** that serve as measurable proof for the evaluator.

| Guarantee | Success Metric | Verification Method |
|-----------|----------------|---------------------|
| **Truth 1: Unique Claim Lock** | Zero Identity Collisions | Parallel test: 10 concurrent requests for same email; exactly 1 must succeed |
| **Truth 3: Time-Bounded Proof** | 100% Window Enforcement | Test: Verification must fail at exactly T+61 seconds |
| **Truth 4: Dual-Factor Activation** | Auth Required | Test: Valid code with wrong password must fail |
| **Truth 6: Data Stewardship** | Zero "Ghost" Credentials | Test: Query DB for unverified hashed passwords after expiration; result must be 0 |
| **Truth 8: Attempt Limiting** | "3-Strikes" Accuracy | Test: Account must be locked/released after precisely 3 failed code entries |
| **Truth 9: Normalization** | Case-Insensitive Identity | Test: `John@Email.com` and `john@email.com` must resolve to same identity |
| **Truth 10: Atomicity** | Transaction Integrity | Test: Simulated DB failure mid-operation must not leave partial state |

**Coverage Target:** 100% of Fundamental Truths have corresponding automated tests.

---

### Business Objectives (Deliverable Completeness)

| Deliverable | Success Criteria | Priority |
|-------------|------------------|----------|
| **Docker Setup** | `docker-compose up` runs without manual configuration | Critical |
| **Test Suite** | All tests pass, including edge case scenarios | Critical |
| **Architecture Diagram** | Clear visualization of Hexagonal structure | Required |
| **README** | Self-sufficient - evaluator needs no external help | Required |
| **API Documentation** | OpenAPI spec auto-generated and accessible | Required |
| **Design Rationale** | Brainstorming document explains "why" behind decisions | Differentiator |

---

### Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| **Setup Time** | < 60 seconds | Time from `git clone` to working API |
| **Test Coverage** | > 90% | pytest coverage report |
| **Test Pass Rate** | 100% | All tests green on fresh clone |
| **Documentation Completeness** | 100% | All endpoints documented in OpenAPI |
| **Edge Case Coverage** | 12/12 | All identified failure scenarios have tests |

---

## MVP Scope

### Tier 1: Spec Compliance (Non-Negotiable)

Features explicitly required to pass the assessment:

| Feature | Endpoint/Component | Description |
|---------|-------------------|-------------|
| **User Registration** | `POST /register` | Create user with email and password |
| **Verification Delivery** | SMTP Adapter | Generate and "deliver" 4-digit code via simulated third-party service (console output) |
| **Account Activation** | `POST /activate` | Verify using BASIC AUTH + 4-digit code |
| **Temporal Logic** | Domain Core | Strict enforcement of 60-second expiration window |
| **Infrastructure** | Docker | Complete `docker-compose` setup for API + PostgreSQL |
| **Testing** | pytest | Comprehensive test suite covering all requirements |

---

### Tier 2: Production Signals (Senior Differentiators)

Not explicitly in the spec, but essential for demonstrating "production quality":

| Signal | Implementation | Why It Matters |
|--------|----------------|----------------|
| **Hexagonal Architecture** | Domain Core isolated from FastAPI/psycopg3 | Demonstrates architectural discipline |
| **Atomic State Transitions** | `ON CONFLICT` + transactions in raw SQL | Prevents race conditions during claims |
| **Data Stewardship** | Auto-disposal of unverified credentials | Shows security mindset and data ethics |
| **Normalization** | Case-insensitive, whitespace-neutral identity | Prevents subtle bugs and user confusion |
| **Adversarial Security** | 3-strikes rule, constant-time responses | Mitigates brute-force and timing attacks |

---

### Tier 3: Stretch Goals (Nice-to-Have)

Features that add polish but are secondary to the core engineering demonstration:

| Feature | Value | Priority |
|---------|-------|----------|
| **Resend Code Endpoint** | Better UX if simulated SMTP "fails" | Low |
| **Background Cleanup Worker** | Active "Reaper" to complement lazy expiration | Low |
| **Advanced Observability** | Structured logging or basic metrics | Low |

**Implementation Strategy:** Complete Tier 1 + Tier 2 first. Only add Tier 3 if time permits and core quality is not compromised.

---

### Explicitly Out of Scope

To avoid scope creep and maintain focus on the Identity Claim Dilemma:

| Feature | Reason for Exclusion |
|---------|---------------------|
| **Post-Activation Authentication** | Spec ends at activation; `/login` or JWT issuance not required |
| **Password Management** | Reset flows, "forgot password," or profile updates are separate concerns |
| **Persistent Rate Limiting** | In-memory for demo; Redis documented as "Production Recommendation" |
| **Admin Features** | Dashboards, user lists, manual activation tools are operational concerns |

---

### MVP Success Criteria

The MVP is successful when:

| Criterion | Validation |
|-----------|------------|
| **Spec Compliance** | All Tier 1 features work as specified |
| **Zero Friction Setup** | `docker-compose up` → working API in < 60 seconds |
| **All Tests Pass** | `pytest` returns 100% pass rate |
| **Edge Cases Covered** | Tests for all 12 identified failure scenarios |
| **Architecture Visible** | Hexagonal structure clear from project layout |
| **Documentation Complete** | README, OpenAPI, and design rationale present |

---

### Future Vision

If this assessment leads to employment, the architecture supports evolution:

| Phase | Expansion |
|-------|-----------|
| **V1.1** | Add resend endpoint, background cleanup worker |
| **V1.2** | Persistent rate limiting with Redis |
| **V2.0** | Full authentication flow (login, JWT, refresh tokens) |
| **V2.1** | Password reset, email change flows |
| **V3.0** | Multi-factor authentication, OAuth integration |

**Key Insight:** The Hexagonal Architecture ensures these expansions don't require rewriting the Domain Core—only adding new adapters and use cases.

---

