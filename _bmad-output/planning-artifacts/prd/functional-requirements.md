# Functional Requirements

## User Registration

- FR1: Users can submit an email address and password to begin registration
- FR2: System can normalize email addresses (case-insensitive, whitespace-neutral)
- FR3: System can atomically claim an email address, preventing duplicate registrations
- FR4: System can generate a cryptographically random 4-digit verification code
- FR5: System can deliver the verification code to the user (console output for demo)
- FR6: System can reject registration attempts for already-claimed or active emails

## Identity Verification

- FR7: Users can submit a verification code with credentials to activate their account
- FR8: System can verify the submitted code matches the generated code
- FR9: System can verify the submitted password matches the stored hash
- FR10: System can verify the verification attempt is within the 60-second window
- FR11: System can verify fewer than 3 failed attempts have occurred
- FR12: System can transition a user from CLAIMED to ACTIVE upon successful verification

## State Management (Trust State Machine)

- FR13: System can represent user states: AVAILABLE, CLAIMED, ACTIVE, EXPIRED, LOCKED
- FR14: System can enforce forward-only state transitions (no backward movement)
- FR15: System can transition CLAIMED → EXPIRED when 60 seconds elapse
- FR16: System can transition CLAIMED → LOCKED after 3 failed verification attempts
- FR17: System can release email addresses from EXPIRED or LOCKED states back to AVAILABLE

## Security & Protection

- FR18: System can prevent race conditions during concurrent registration attempts
- FR19: System can track and limit verification attempts per registration
- FR20: System can lock accounts after exceeding the attempt threshold
- FR21: System can return generic error messages that prevent information disclosure
- FR22: System can perform constant-time password comparisons
- FR23: System can hash passwords using bcrypt before storage

## Data Lifecycle & Stewardship

- FR24: System can purge hashed passwords when registrations expire or lock
- FR25: System can ensure no "ghost credentials" exist for unverified accounts
- FR26: System can timestamp all state transitions using database time

## API Interface

- FR27: System can expose a versioned API endpoint for registration (`POST /v1/register`)
- FR28: System can expose a versioned API endpoint for activation (`POST /v1/activate`)
- FR29: System can accept and return JSON data format exclusively
- FR30: System can authenticate activation requests using HTTP BASIC AUTH
- FR31: System can auto-generate OpenAPI documentation accessible at `/docs`

## Infrastructure & Operations

- FR32: System can run via Docker Compose with a single command
- FR33: System can execute all tests via pytest with a single command
- FR34: System can categorize tests by scenario type (happy path, adversarial)
- FR35: System can report test coverage metrics

## Architectural Constraints (Evaluator-Facing)

- FR36: Domain logic can exist without framework imports (FastAPI, Pydantic, psycopg3)
- FR37: Domain logic can define its own port interfaces for infrastructure abstraction
- FR38: Repository adapters can use raw SQL with explicit transaction control
- FR39: README can present architecture and invariants before setup instructions
