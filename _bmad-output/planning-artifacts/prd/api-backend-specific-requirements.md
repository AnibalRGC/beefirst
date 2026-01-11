# API Backend Specific Requirements

## API Design Principles

This API follows RESTful conventions with deliberate choices that signal senior engineering judgment:

| Principle | Decision | Rationale |
|-----------|----------|-----------|
| **Data Format** | JSON only | Industry standard, natively supported by FastAPI/Pydantic |
| **Versioning** | Explicit path versioning (`/v1/`) | Demonstrates design for contract evolution |
| **Documentation** | Auto-generated OpenAPI (Swagger) | Evaluator can test Trust Loop without writing client code |
| **Error Responses** | Generic messages, consistent structure | Security-first: prevents information leakage |

## Endpoint Specifications

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/v1/register` | POST | Claim an email and begin verification | None |
| `/v1/activate` | POST | Verify code and activate account | BASIC AUTH |

### POST /v1/register

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

### POST /v1/activate

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

## Authentication Model

| Aspect | Implementation | Security Consideration |
|--------|---------------|----------------------|
| **Registration** | No auth required | Public endpoint for new users |
| **Activation** | HTTP BASIC AUTH | Dual-factor: proves password knowledge + code possession |
| **Password Storage** | bcrypt hash | Industry standard, constant-time comparison |
| **Credential Lifecycle** | Purged on expiration/lockout | Data stewardship principle |

## Data Schemas

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

## Error Handling Strategy

| Scenario | HTTP Status | Response Body | Security Note |
|----------|-------------|---------------|---------------|
| Email already claimed | 409 | Generic "Registration failed" | Prevents enumeration |
| Invalid/expired code | 401 | Generic "Invalid credentials or code" | Prevents timing oracle |
| Wrong password | 401 | Generic "Invalid credentials or code" | Same as wrong code |
| Account locked (3 strikes) | 401 | Generic "Invalid credentials or code" | No lockout disclosure |
| Validation error | 422 | Pydantic validation details | Safe to expose |

## Rate Limiting

| Mechanism | Scope | Limit | Action |
|-----------|-------|-------|--------|
| **Verification Attempts** | Per registration | 3 attempts | Lock + purge credentials |
| **API Rate Limiting** | Per IP (future) | TBD | In-memory for demo, Redis for production |

*Note: The 3-strikes rule is the primary brute-force protection. General API rate limiting is documented as a "Production Recommendation" for future implementation.*

## API Documentation

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
