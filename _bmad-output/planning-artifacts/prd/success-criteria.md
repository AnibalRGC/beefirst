# Success Criteria

## User Success (The Technical Evaluator)

Success is measured by a single outcome: **"Proceed to Interview" or "Hire" recommendation.**

This outcome is achieved through three specific proof points that transform possibility into certainty:

| Signal | What They See | What They Think |
|--------|--------------|-----------------|
| **Seniority Signal** | `domain/registration.py` with zero framework imports + self-defined port interfaces | "This candidate manages complexity without magic" |
| **Adversarial Proof** | Test categories explicitly covering Clock Drift, Timing Oracles, Race Conditions | "This candidate anticipated production failures before I asked" |
| **Ethical Signal** | "Zero Ghost Credentials" test querying raw database to verify credential purging | "This candidate's engineering decisions are principled" |

**The "Aha!" Moment:** The evaluator opens `domain/registration.py` and realizes the entire Trust State Machine is implemented without a single import from FastAPI, Pydantic, or psycopg3. The code defines its own port interfaces, proving true architectural decoupling—not just layering.

## Business Success

Success extends beyond the immediate assessment:

| Timeframe | Success Definition |
|-----------|-------------------|
| **Immediate** | Evaluator sees Domain Core → "Proceed to Interview" decision |
| **3 Months** | Portfolio piece demonstrating Hexagonal Mastery + Adversarial Security thinking |
| **Long-term** | Reusable "Trust State Machine" pattern applicable to any time-bounded, sensitive state transition |

**The Reusable Asset:** The "11 Fundamental Truths" framework is a portable methodology for aligning stakeholders and engineers on system guarantees—usable in any future role.

**The Portfolio Value:** A reference implementation proving you can decouple business rules from volatile infrastructure, and that you think like a defender proactively mitigating attacks.

## Technical Success

| Metric | Target | Verification |
|--------|--------|--------------|
| **Setup Time** | < 60 seconds from `git clone` to running API | Timed fresh clone test |
| **Test Coverage** | > 90% | pytest coverage report |
| **Test Pass Rate** | 100% on fresh clone | All tests green, zero flaky tests |
| **Edge Case Coverage** | 12/12 failure scenarios | Each scenario has explicit test |
| **Architectural Purity** | 0 framework imports in `domain/` | Static analysis or manual verification |
| **Documentation Completeness** | 100% endpoints documented | OpenAPI spec auto-generated |

## Measurable Outcomes

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
