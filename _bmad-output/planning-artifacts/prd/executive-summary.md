# Executive Summary

The **beefirst** project implements a User Registration API that solves the **Identity Claim Dilemma**: ensuring that an entity claiming an email address actually controls that communication channel, within a strict 60-second security window.

This is not a CRUD application. It is a **State Machine of Trust** - a system where invalid states are unrepresentable by design. The architecture enforces safety through invariant guarantees, not just documentation.

## The Core Problem

Three interconnected challenges drive this implementation:

1. **Identity Theft Prevention** - Ensuring the entity claiming an email address actually controls that communication channel
2. **Time-Sensitive Security** - Enforcing a strict 60-second window of proof to minimize exposure of unverified credentials
3. **Engineering Transparency** - Demonstrating senior engineering judgment without hiding behind ORM abstractions or framework "magic"

## Target Audience

**Primary: The Technical Evaluator** - Senior Backend Engineers, Tech Leads, and CTOs reviewing this code as a hiring assessment. They are pattern-matching for signals of senior judgment vs. junior shortcuts.

**Secondary: The Registering User** - A theoretical adversary proxy whose experience tests identity squatting, brute-force attempts, and timing attacks.

## What Makes This Special

**Intentional Engineering.** Every architectural decision is traceable to a security or reliability guarantee. This demonstrates the exact evaluation criteria senior engineers look for: architectural discipline, production thinking, and edge case handling.

| Differentiator | Evidence | Verification |
|----------------|----------|--------------|
| **11 Fundamental Truths** | Invariant guarantees that define "working" vs "broken" | Each Truth has a corresponding test that fails if violated |
| **State Immutability** | Forward-only state machine (see diagram below) | Database constraints prevent backward transitions |
| **Pure Domain Core** | `domain/` contains business logic with zero infrastructure imports | Defines its own port interfaces - true decoupling |
| **Adversarial Engineering** | 12 failure scenarios identified and mitigated before coding | Test suite includes adversarial scenarios |
| **Data Stewardship** | "We have no right to hold credentials for an unverified identity" | Expired records automatically purged |

## Trust State Machine

```
AVAILABLE ──claim──► CLAIMED ──verify──► ACTIVE
                        │
                        ├──timeout──► EXPIRED ──► AVAILABLE
                        │
                        └──3 fails──► LOCKED ──► AVAILABLE
```

*Once ACTIVE, a user cannot be re-claimed or re-activated. The machine only moves forward or resets.*

## The "Aha!" Moment

The evaluator opens the repository and sees `domain/` first in the project structure. The README opens with architecture, not setup instructions. Inside `domain/registration.py`: pure business logic implementing the Trust State Machine with zero infrastructure dependencies and explicit port interfaces.

That's when they realize: *"This candidate isn't just a coder; they designed for invariants."*
