-- =============================================================================
-- subconcept_mastery table — LearnGPS Mastery Engine
-- =============================================================================
-- Run this in your Supabase SQL editor.
-- Safe to re-run: CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS
-- =============================================================================

-- ── 1. Create the table (full schema) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subconcept_mastery (
  -- Identity
  student_id          uuid        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  subconcept_id       text        NOT NULL,
  chapter_id          text        NOT NULL,

  -- Bloom Progress (curriculum progression, 0–100)
  bloom_level         text        NOT NULL DEFAULT 'remember',
  bloom_target        text        NOT NULL DEFAULT 'apply',
  bloom_progress      smallint    NOT NULL DEFAULT 0,

  -- True Mastery dimensions (each 0–100)
  retention_score     smallint    NOT NULL DEFAULT 0,
  confidence_score    smallint    NOT NULL DEFAULT 50,
  transfer_score      smallint    NOT NULL DEFAULT 0,
  independence_score  smallint    NOT NULL DEFAULT 100,

  -- Composite Mastery Score (0–100)
  -- GPS "done" state = mastery_score >= 70
  mastery_score       smallint    NOT NULL DEFAULT 0,

  -- Raw signals (inputs to dimension calculators)
  hint_count          smallint    NOT NULL DEFAULT 0,
  session_count       integer     NOT NULL DEFAULT 0,
  correct_count       integer     NOT NULL DEFAULT 0,
  total_attempts      integer     NOT NULL DEFAULT 0,
  transfer_contexts   smallint    NOT NULL DEFAULT 0,

  -- Timestamps
  bloom_achieved_at   timestamptz,                        -- first time bloom_target was reached
  last_active         timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),

  -- XP
  xp_total            integer     NOT NULL DEFAULT 0,

  PRIMARY KEY (student_id, subconcept_id)
);

-- ── 2. Add missing columns if upgrading from earlier schema ───────────────────
-- (Safe to run even if the columns already exist)
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS bloom_progress      smallint NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS retention_score     smallint NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS confidence_score    smallint NOT NULL DEFAULT 50;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS transfer_score      smallint NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS independence_score  smallint NOT NULL DEFAULT 100;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS mastery_score       smallint NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS correct_count       integer  NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS total_attempts      integer  NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS transfer_contexts   smallint NOT NULL DEFAULT 0;
ALTER TABLE subconcept_mastery ADD COLUMN IF NOT EXISTS bloom_achieved_at   timestamptz;

-- ── 3. Index ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_mastery_student_chapter
  ON subconcept_mastery (student_id, chapter_id);

-- ── 4. Row-Level Security ─────────────────────────────────────────────────────
ALTER TABLE subconcept_mastery ENABLE ROW LEVEL SECURITY;

-- Students can only read/write their own rows.
-- service_role key (backend) bypasses RLS automatically.
DROP POLICY IF EXISTS "own mastery" ON subconcept_mastery;
CREATE POLICY "own mastery" ON subconcept_mastery
  FOR ALL
  USING     (auth.uid() = student_id)
  WITH CHECK (auth.uid() = student_id);
