-- beefirst - Trust State Machine Schema
-- Migration: 001_create_registrations.sql
--
-- This table implements the Trust State Machine for user registration.
-- See: architecture/core-architectural-decisions.md#Data Architecture

BEGIN;

CREATE TABLE IF NOT EXISTS registrations (
    -- Primary key: UUID auto-generated
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Email: unique identifier, normalized (lowercase) at application level
    email VARCHAR(255) UNIQUE NOT NULL,

    -- Password hash: NULLed upon expiration/lockout (Data Stewardship - Truth 6)
    password_hash VARCHAR(255),

    -- Verification code: 4-digit code for email verification
    verification_code CHAR(4) NOT NULL,

    -- State: Trust State Machine states
    -- CLAIMED: Initial state after registration
    -- ACTIVE: Successfully verified
    -- EXPIRED: Verification window (60s) elapsed
    -- LOCKED: Max attempts (3) exceeded
    state VARCHAR(20) NOT NULL DEFAULT 'CLAIMED'
        CHECK (state IN ('CLAIMED', 'ACTIVE', 'EXPIRED', 'LOCKED')),

    -- Attempt count: Tracks failed verification attempts (Truth 8)
    attempt_count INT NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);

-- Index for email lookups (already covered by UNIQUE constraint)
-- Additional index for state-based queries if needed in future
CREATE INDEX IF NOT EXISTS idx_registrations_state ON registrations(state);
CREATE INDEX IF NOT EXISTS idx_registrations_created_at ON registrations(created_at);

COMMIT;
