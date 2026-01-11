# Project Context Analysis

## Requirements Overview

**Functional Requirements:**

39 requirements spanning 8 categories:
- User Registration (FR1-FR6): Email claim, normalization, atomic registration, code generation
- Identity Verification (FR7-FR12): Dual-factor activation (code + password), TTL enforcement
- State Management (FR13-FR17): Trust State Machine with forward-only transitions
- Security & Protection (FR18-FR23): Race condition prevention, attempt limiting, constant-time ops
- Data Lifecycle (FR24-FR26): Credential purging, no ghost credentials, DB timestamps
- API Interface (FR27-FR31): Versioned endpoints, JSON, BASIC AUTH, OpenAPI
- Infrastructure (FR32-FR35): Docker Compose, pytest, categorized tests
- Architectural Constraints (FR36-FR39): Pure domain, raw SQL, README-first architecture

**Non-Functional Requirements:**

18 requirements across 5 domains:
- Security (6): bcrypt ≥10, constant-time comparison, secrets module, generic errors, no credential logging, credential purging
- Performance (3): <60s startup, constant-time responses regardless of outcome
- Testability (5): ≥90% coverage, 100% pass rate, adversarial test categories, test isolation
- Maintainability (4): Zero framework imports in domain, port interfaces, explicit SQL, PEP 8
- Operational (3): Docker-only dependencies, sensible defaults, visible verification codes

**Scale & Complexity:**

- Primary domain: API Backend
- Complexity level: Low domain complexity, high engineering rigor
- Estimated architectural components: 6 (Domain Core, Ports, Repository Adapter, SMTP Adapter, API Layer, Test Suite)

## Technical Constraints & Dependencies

| Constraint | Rationale |
|------------|-----------|
| FastAPI | Dependency injection, auto-generated OpenAPI |
| Raw psycopg3 | Engineering transparency, no ORM magic |
| PostgreSQL | ACID guarantees, ON CONFLICT, temporal queries |
| Docker Compose | Zero-friction setup for evaluator |
| pytest | Categorized adversarial test suites |
| Hexagonal Architecture | Domain purity, infrastructure isolation |

## Cross-Cutting Concerns Identified

| Concern | Impact |
|---------|--------|
| **Security** | Affects all layers: hashing, timing, error messages, data lifecycle |
| **Atomicity** | Database operations, state transitions, claim logic |
| **Temporal Enforcement** | 60-second TTL at database level, not application |
| **Testability** | Adversarial scenarios, port-based mocking, coverage targets |
| **Observability** | Verification codes visible in logs for demo |
