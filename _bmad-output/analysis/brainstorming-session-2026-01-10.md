---
stepsCompleted: [1, 2, 3, 4]
status: complete
inputDocuments:
  - user_registration_api.md
session_topic: "User Registration API - Complete Architecture & Design"
session_goals: "Implementation optionality with clear architectural decisions, edge case identification, testing strategy, research backlog for PO/PM/CTO audience"
selected_approach: "ai-recommended"
techniques_used:
  - "First Principles Thinking"
  - "Morphological Analysis"
  - "Reverse Brainstorming + Failure Analysis"
  - "Six Thinking Hats"
ideas_generated:
  - "Trust State Machine model"
  - "11 Fundamental Truths"
  - "8 Architecture Decisions"
  - "12 Failure Scenarios with mitigations"
  - "6-Phase Implementation Roadmap"
context_file: "user_registration_api.md"
---

# Brainstorming Session: User Registration API Architecture

**Date:** 2026-01-10
**Facilitator:** Mary (Business Analyst)
**Participant:** Anibal
**Target Audience:** Product Owner, Product Manager, CTO

---

## Session Overview

**Topic:** User Registration API - Complete Architecture & Design

**Goals:**
- Achieve implementation optionality with clear architectural decisions
- Identify edge cases and error scenarios
- Define testing strategy
- Create research backlog for technical unknowns

**Source Requirements:** Python-based API for user registration with:
- Email/password account creation
- 4-digit verification code via email
- BASIC AUTH for code activation
- 1-minute code expiration
- Production-quality code (no ORM magic)
- Docker containerization
- Comprehensive testing

---

## Technique Selection

**Approach:** AI-Recommended Techniques

**Analysis Context:** Multi-dimensional architecture exploration for executive audience

**Recommended Techniques:**

1. **First Principles Thinking:** Strip assumptions, identify fundamental truths
2. **Morphological Analysis:** Systematic parameter exploration for optionality
3. **Reverse Brainstorming + Failure Analysis:** Edge cases and risk identification
4. **Six Thinking Hats:** Executive synthesis with multi-perspective review

**AI Rationale:** This sequence builds from foundational truths → systematic options → risk awareness → executive-ready synthesis, matching the user's need for optionality, clear decisions, and CTO-appropriate documentation.

---

## Phase 1: First Principles Thinking

### Core Concept: The State Machine of Trust

The user registration system is fundamentally a **Trust State Machine** where an entity stakes a claim on a unique identifier and must prove ownership through a time-bounded verification loop.

### The 8 Fundamental Truths

| # | Truth | Guarantee | Failure = Broken |
|---|-------|-----------|------------------|
| **1** | **Unique Claim Lock** | One email = one active verification at a time | Race conditions, duplicate claims |
| **2** | **Channel-Only Secret** | Code delivered exclusively through email channel | Proof becomes meaningless |
| **3** | **Time-Bounded Proof** | 60-second validity, then invalidation | Stale codes remain exploitable |
| **4** | **Dual-Factor Activation** | Code (possession) + Password (knowledge) | Identity not bound to proof |
| **5** | **Provisional Credentials** | Password hashed but dormant until verified | Premature access |
| **6** | **Release on Expiration** | Email freed, credentials discarded | Data hoarding, lockout attacks |
| **7** | **Anti-Blocking** | Cannot indefinitely reserve an email | Malicious identity squatting |
| **8** | **Attempt Limiting** | 3 strikes → Expired + Released | Brute-force bypasses channel proof |

### Trust State Machine Diagram

```
┌─────────────┐       Claim (email + hash(pwd))       ┌─────────────┐
│  AVAILABLE  │ ─────────────────────────────────►   │   CLAIMED   │
│             │         [Email LOCKED]                │ (Provisional)│
└─────────────┘                                       └──────┬──────┘
       ▲                                                     │
       │                                    ┌────────────────┼────────────────┐
       │                                    │                │                │
       │                          Verify Success      Timeout 60s      3 Failed
       │                         (code + auth)                        Attempts
       │                                    │                │                │
       │      Release                       ▼                ▼                ▼
       │      (cleanup)              ┌─────────────┐   ┌─────────────┐  ┌─────────────┐
       └─────────────────────────────│   ACTIVE    │   │   EXPIRED   │  │   LOCKED    │
                                     │  (Trusted)  │   │  (Timeout)  │  │ (Abuse Det) │
                                     └─────────────┘   └──────┬──────┘  └──────┬──────┘
                                                              │                │
                                                              └───────┬────────┘
                                                                      │
                                                              [Email Released]
                                                              [Credentials Discarded]
```

### Data Stewardship Principle

> "We have no right to hold credentials for an unverified identity."

This principle guides expiration handling: when verification fails or times out, all provisional data (including hashed passwords) must be discarded.

### Key Insight: Attempt Limiting Rationale

> "If a user needs 50 tries to get a 4-digit code right, they are not 'forgetful'—they are guessing."

The 4-digit code is proof of channel access, not a password. Multiple attempts indicate bypass attempts, not user error.

---

## Phase 2: Morphological Analysis

### Architecture Decision Matrix

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| **P1** Framework | FastAPI | Routing + DI + Validation without ORM magic |
| **P2** Database | PostgreSQL + raw psycopg3 | ACID guarantees, raw SQL shows "your implementation" |
| **P3** Architecture | Hexagonal (Ports & Adapters) | Domain isolation, testability, demonstrates skill |
| **P4** Email | Port interface + Console/MailHog adapters | Third-party abstraction per spec |
| **P5** Hashing | bcrypt | Battle-tested industry standard |
| **P6** Code Gen | `secrets` module | Only cryptographically secure option |
| **P7** Expiration | Hybrid (lazy check + background cleanup) | Correctness + database cleanliness |
| **P8** Testing | pytest with layered strategy | Domain → Use Cases → Adapters → E2E |

### Hexagonal Architecture Structure

```
                    ┌─────────────────────────────────────────┐
                    │              ADAPTERS                   │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
                    │  │ FastAPI │  │ psycopg3│  │  SMTP   │  │
                    │  │ (HTTP)  │  │  (DB)   │  │ (Email) │  │
                    │  └────┬────┘  └────┬────┘  └────┬────┘  │
                    │       │            │            │       │
                    │  ─────┴────────────┴────────────┴─────  │
                    │                    │                    │
                    │               ┌────┴────┐               │
                    │               │  PORTS  │               │
                    │               │(Interfaces)             │
                    │               └────┬────┘               │
                    │                    │                    │
                    │  ┌─────────────────┴─────────────────┐  │
                    │  │           DOMAIN CORE             │  │
                    │  │  ┌─────────────────────────────┐  │  │
                    │  │  │   Trust State Machine       │  │  │
                    │  │  │   11 Fundamental Truths     │  │  │
                    │  │  │   Registration Use Cases    │  │  │
                    │  │  └─────────────────────────────┘  │  │
                    │  └───────────────────────────────────┘  │
                    └─────────────────────────────────────────┘
```

### Architectural Statement

> "We choose modern, productive tools for commodity concerns (HTTP, validation). We write every line of business logic and data access ourselves."

---

## Phase 3: Reverse Brainstorming + Failure Analysis

### Critical Failure Scenarios Identified

| # | Scenario | Category | Severity | Fix |
|---|----------|----------|----------|-----|
| 1 | **Clock Drift** | Data Integrity | Medium | DB-level `NOW()` for all timestamps |
| 2 | **Persistence Ghost** | Data Integrity | High | Email sent only after DB commit |
| 3 | **Brute Force Pin-Point** | Security | Critical | Rate limiter per IP AND per email |
| 4 | **Race Condition Claim** | Concurrency | High | `ON CONFLICT DO NOTHING` + check result |
| 5 | **Orphaned Commit** | Reliability | Medium | Resend endpoint (same code, reset timer) |
| 6 | **Case Sensitivity Trap** | Data Integrity | Medium | Normalize email: `strip().lower()` |
| 7 | **Timing Oracle** | Security | Low | Constant-time responses, generic errors |
| 8 | **Zombie Registration** | UX/Integrity | Medium | Delete EXPIRED before new INSERT |
| 9 | **Replay Attack** | Security | Low | Atomic status check, idempotent activation |
| 10 | **Password Timing** | Security | Medium | bcrypt verify (constant-time built-in) |
| 11 | **Connection Pool Exhaustion** | Reliability | Medium | AsyncConnectionPool with psycopg3 |
| 12 | **Transaction Isolation** | Concurrency | Medium | `SELECT FOR UPDATE` where needed |

### Research Backlog Resolutions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| **Rate Limiting** | In-memory for demo, Redis for production | Docker simplicity vs horizontal scaling |
| **Transactional Outbox** | Not needed | 60s window + resend endpoint sufficient |
| **psycopg3 Async** | AsyncConnectionPool | Native FastAPI integration, prevents pool exhaustion |
| **Email Resend** | Same code, reset timer | Avoids race conditions with multiple codes |

### Extended Fundamental Truths (Operational)

| # | Truth | Guarantee |
|---|-------|-----------|
| **9** | **Normalization** | Identity is case-insensitive and whitespace-neutral |
| **10** | **Atomicity** | Every state change is an atomic SQL transaction |
| **11** | **Idempotency** | Replay attacks neutralized by status-checking |

---

## Phase 4: Six Thinking Hats - Executive Synthesis

### 🎩 White Hat: Facts & Compliance Verification

Our design is **strictly compliant** with every specification constraint:

| Requirement | Compliance | Implementation |
|-------------|------------|----------------|
| Python language | ✅ | Python 3.11+ |
| Framework for routing/DI only | ✅ | FastAPI (no ORM magic) |
| No SQLite | ✅ | PostgreSQL |
| No ORM (e.g., SQLAlchemy) | ✅ | Raw psycopg3 driver |
| 4-digit verification code | ✅ | `secrets` module |
| 60-second expiration | ✅ | Hybrid passive/active strategy |
| BASIC AUTH for activation | ✅ | Password required at activation |
| SMTP as third-party service | ✅ | Port interface + adapters |
| Docker containerization | ✅ | docker-compose planned |
| Tests required | ✅ | 4-layer pytest strategy |
| Architecture schema | ✅ | Hexagonal + State Machine diagrams |

### 🟡 Yellow Hat: Value Proposition

**The "State Machine of Trust" model transforms this from a code exercise into an architecture demonstration.**

| Stakeholder | Value Delivered |
|-------------|-----------------|
| **CTO** | Hexagonal Architecture separates commodity concerns (HTTP) from proprietary business rules. Core logic is 100% testable without infrastructure. |
| **Product Manager** | Clear mental model with defined states (Available → Claimed → Active/Expired). System behavior is predictable and explainable. |
| **Product Owner** | Data stewardship principles built-in. "Release on Expiration" and "Anti-Blocking" truths protect users from malicious actors. |

### ⚫ Black Hat: Risk Mitigation Summary

**12 failure modes identified and mitigated:**

| Category | Key Risks | Mitigation |
|----------|-----------|------------|
| **Data Integrity** | Clock Drift, Persistence Ghost | DB-level `NOW()`, email after commit |
| **Security** | Brute Force, Timing Oracle | Rate limiting, constant-time responses |
| **Concurrency** | Race Conditions, Transaction Isolation | `ON CONFLICT`, `SELECT FOR UPDATE` |
| **Reliability** | Orphaned Commit, Pool Exhaustion | Resend endpoint, AsyncConnectionPool |

### 🔵 Blue Hat: Implementation Roadmap

```
Phase 1: Domain Core
├── Entities (User, VerificationCode)
├── Value Objects (Email, HashedPassword)
├── State Machine logic
└── Port interfaces

Phase 2: Infrastructure Adapters
├── PostgreSQL repository (psycopg3)
├── Console email adapter
└── Database schema

Phase 3: API Layer
├── FastAPI routes
├── Basic Auth middleware
└── Pydantic models

Phase 4: Testing
├── Domain unit tests
├── Use case tests (mocked ports)
├── Integration tests (Docker DB)
└── E2E tests

Phase 5: Containerization
├── Dockerfile
├── docker-compose.yml
└── README

Phase 6: Documentation
├── Architecture diagram
├── OpenAPI spec (auto-generated)
└── Design rationale (this document)
```

---

## Executive Summary

### The Challenge
Build a production-quality user registration API with email verification, demonstrating software engineering skill without relying on ORM abstractions.

### Our Approach
We reframed the problem as a **Trust State Machine** - a system where an entity stakes a claim on a unique identifier and must prove ownership through a time-bounded verification loop.

### Key Deliverables

| Artifact | Description |
|----------|-------------|
| **11 Fundamental Truths** | Non-negotiable guarantees that define "working" vs "broken" |
| **8 Architecture Decisions** | Justified choices with trade-off analysis |
| **12 Failure Scenarios** | Edge cases identified with mitigations |
| **Hexagonal Architecture** | Domain isolation, infrastructure independence |
| **Implementation Roadmap** | Phased approach starting from domain core |

### Technical Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Web Framework** | FastAPI | Routing + DI + validation, no magic |
| **Database** | PostgreSQL + psycopg3 | ACID guarantees, hand-written SQL |
| **Architecture** | Hexagonal | Testability, demonstrates skill |
| **Security** | bcrypt + secrets | Industry standard, cryptographically secure |
| **Testing** | pytest | 4-layer strategy for production quality |

### Guiding Principles

> **"We have no right to hold credentials for an unverified identity."**

> **"If a user needs 50 tries to get a 4-digit code right, they are not 'forgetful'—they are guessing."**

> **"We choose modern, productive tools for commodity concerns. We write every line of business logic and data access ourselves."**

---

## Session Metadata

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-10 |
| **Duration** | ~90 minutes |
| **Techniques Used** | First Principles, Morphological Analysis, Reverse Brainstorming, Six Thinking Hats |
| **Facilitator** | Mary (Business Analyst) |
| **Participant** | Anibal |
| **Output** | Architecture decision document for PO/PM/CTO audience |

---

*Document generated through BMAD Brainstorming Workflow*

