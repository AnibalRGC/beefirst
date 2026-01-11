# User Journeys

## Journey 1: The Evaluator's Review Journey (Architectural Discovery)

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

## Journey 2: The Legitimate User's Happy Path (Trust Loop)

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

## Journey 3: The Adversary's Attack Journey (State Protection)

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

## Journey Requirements Summary

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
