# Non-Functional Requirements

## Security

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-S1 | Passwords must be hashed using bcrypt with cost factor ≥ 10 | Code inspection |
| NFR-S2 | Password verification must use constant-time comparison | Timing analysis test |
| NFR-S3 | Verification codes must be generated using cryptographically secure randomness | Code inspection (`secrets` module) |
| NFR-S4 | All error responses must use generic messages that prevent information disclosure | Response inspection |
| NFR-S5 | Database credentials must not appear in application logs | Log inspection |
| NFR-S6 | Hashed passwords for unverified accounts must be purged within 60 seconds of expiration | Database query after expiration |

## Performance

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-P1 | System must start and be ready to accept requests within 60 seconds of `docker-compose up` | Timed startup test |
| NFR-P2 | Password verification response time must not reveal validity (constant-time) | Timing distribution analysis |
| NFR-P3 | Error responses must have consistent timing regardless of failure mode | Timing distribution analysis |

## Testability & Quality

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-T1 | Test suite must achieve ≥ 90% code coverage | pytest coverage report |
| NFR-T2 | All tests must pass on fresh clone (100% pass rate) | CI/fresh clone test |
| NFR-T3 | Tests must be categorized by scenario type (happy path, adversarial) | Test organization inspection |
| NFR-T4 | Adversarial scenarios must have dedicated test coverage | Test suite includes adversarial markers |
| NFR-T5 | Tests must be isolated (no shared state between tests) | Test independence verification |

## Maintainability & Architecture

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-M1 | Domain logic must have zero imports from infrastructure (FastAPI, Pydantic, psycopg3) | Static analysis / import inspection |
| NFR-M2 | Domain module must define port interfaces for all infrastructure dependencies | Code inspection |
| NFR-M3 | All SQL queries must be explicit (no ORM magic) | Code inspection |
| NFR-M4 | Code must follow Python conventions (PEP 8, type hints) | Linter output |

## Operational

| NFR | Requirement | Verification |
|-----|-------------|--------------|
| NFR-O1 | System must run in Docker with no host dependencies beyond Docker | Fresh machine test |
| NFR-O2 | All environment variables must have sensible defaults for demo mode | Default configuration test |
| NFR-O3 | Verification codes must be visible in logs/console for demo purposes | Log inspection |
