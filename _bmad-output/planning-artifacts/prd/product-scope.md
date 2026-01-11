# Product Scope

## MVP - Minimum Viable Product

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

## Growth Features (Post-MVP)

| Feature | Value | Priority |
|---------|-------|----------|
| Resend Code Endpoint | Better UX if email delivery slow | Low |
| Background Cleanup Worker | Active "Reaper" for expired records | Low |
| Advanced Observability | Structured logging, basic metrics | Low |

**Implementation Strategy:** Complete MVP (Tier 1 + Tier 2) first. Only add Growth features if time permits and core quality is not compromised.

## Vision (Future Extensions)

| Phase | Expansion |
|-------|-----------|
| V1.1 | Resend endpoint, background cleanup worker |
| V1.2 | Persistent rate limiting with Redis |
| V2.0 | Full authentication flow (login, JWT, refresh tokens) |
| V2.1 | Password reset, email change flows |
| V3.0 | Multi-factor authentication, OAuth integration |

**Key Insight:** The Hexagonal Architecture ensures these expansions don't require rewriting the Domain Core—only adding new adapters and use cases.

## Explicitly Out of Scope

| Feature | Reason for Exclusion |
|---------|---------------------|
| Post-Activation Authentication | Spec ends at activation; `/login` not required |
| Password Management | Reset flows are separate concerns |
| Persistent Rate Limiting | In-memory for demo; Redis documented as "Production Recommendation" |
| Admin Features | Dashboards, user lists are operational concerns |
