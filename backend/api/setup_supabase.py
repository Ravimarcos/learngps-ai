"""
Supabase Schema Setup — Day 3
==============================
Run once to create all LearnGPS tables.

Usage:
    python -m backend.api.setup_supabase

Tables created:
    students            — student profiles
    student_progress    — mastery per SubConcept
    sessions            — each learning session
    vark_state          — VARK style probabilities per student
    xp_ledger           — XP earned events
"""

import asyncio
from supabase import create_client
from backend.config.settings import get_settings


SQL = """
-- ── Students ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    email           TEXT UNIQUE,
    grade           INT NOT NULL CHECK (grade BETWEEN 8 AND 10),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Student Progress (one row per student × SubConcept) ───────────────────
CREATE TABLE IF NOT EXISTS student_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID REFERENCES students(id) ON DELETE CASCADE,
    subconcept_id   TEXT NOT NULL,          -- Neo4j SubConcept id
    bloom_level     TEXT NOT NULL DEFAULT 'Remember',
    mastered        BOOLEAN DEFAULT FALSE,
    attempts        INT DEFAULT 0,
    last_seen_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, subconcept_id)
);

-- ── Sessions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID REFERENCES students(id) ON DELETE CASCADE,
    chapter_id      TEXT NOT NULL,          -- Neo4j Chapter id
    subconcept_id   TEXT NOT NULL,          -- SubConcept studied this session
    duration_secs   INT,
    xp_earned       INT DEFAULT 0,
    vark_signal     TEXT,                   -- "V"|"A"|"R"|"K" observed this session
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ
);

-- ── VARK State (Bayesian probabilities, updated each session) ─────────────
CREATE TABLE IF NOT EXISTS vark_state (
    student_id      UUID PRIMARY KEY REFERENCES students(id) ON DELETE CASCADE,
    v_score         FLOAT DEFAULT 0.25,     -- Visual probability
    a_score         FLOAT DEFAULT 0.25,     -- Auditory
    r_score         FLOAT DEFAULT 0.25,     -- Read/Write
    k_score         FLOAT DEFAULT 0.25,     -- Kinesthetic
    confidence      FLOAT DEFAULT 0.0,      -- 0.0 → 1.0
    dominant_style  TEXT DEFAULT NULL,      -- Set when confidence >= 0.75
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── XP Ledger (append-only log of XP events) ──────────────────────────────
CREATE TABLE IF NOT EXISTS xp_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID REFERENCES students(id) ON DELETE CASCADE,
    amount          INT NOT NULL,
    reason          TEXT NOT NULL,          -- e.g. "correct_answer", "mastery_unlock"
    subconcept_id   TEXT,
    earned_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_progress_student ON student_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_xp_student ON xp_ledger(student_id);
"""


def setup():
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_service_key)

    # Run SQL via Supabase's postgres endpoint
    result = client.rpc("exec_sql", {"query": SQL}).execute()
    print("✅ Supabase tables created")
    return result


# Alternative: use direct postgres connection
async def setup_via_sql():
    """
    If RPC doesn't work, paste the SQL directly in:
    Supabase Dashboard → SQL Editor → New query → paste SQL → Run
    """
    print("📋 Paste the SQL below into Supabase SQL Editor:")
    print(SQL)


if __name__ == "__main__":
    # Try direct approach — paste SQL in dashboard if this fails
    asyncio.run(setup_via_sql())
