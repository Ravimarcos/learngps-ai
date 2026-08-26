"""
LearnGPS Mastery Engine — backend/db/mastery.py
================================================
Two distinct measurements per subconcept:

  bloom_progress  — curriculum progression (how far through Bloom hierarchy
                    toward the node's target level).  Shows learning breadth.

  mastery_score   — true mastery (multi-dimensional, learning quality signal).
                    Drives GPS routing decisions.

Mastery formula
---------------
  mastery_score = 40% × bloom_progress
               + 25% × retention       (decays when student stops practising)
               + 15% × confidence      (accuracy proxy)
               + 10% × transfer        (cross-context application)
               + 10% × independence    (1 − hint_dependency)

GPS state decisions use mastery_score (done ≥ 70), NOT bloom_progress alone.
"""

from __future__ import annotations

import asyncio
import math
import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client

# ── Supabase client (service role — bypasses RLS) ─────────────────────────────
# SECURITY: service_role key is never exposed to the client.
# Store it in Railway Variables (encrypted). Never commit to git.

_sb: Optional[Client] = None


def _supabase() -> Client:
    global _sb
    if _sb is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]   # service_role — keep secret
        _sb = create_client(url, key)
    return _sb


# ── Bloom ordering ─────────────────────────────────────────────────────────────

BLOOM_ORDER = ["remember", "understand", "apply", "analyse", "evaluate", "create"]

# mastery_score threshold to count a subconcept as GPS-state "done"
MASTERY_DONE_THRESHOLD = 70


def bloom_idx(level: str) -> int:
    """Return numeric index for a bloom level string (case-insensitive)."""
    try:
        return BLOOM_ORDER.index(level.strip().lower())
    except ValueError:
        return 0


# ── Individual dimension calculators ─────────────────────────────────────────

def calc_bloom_progress(bloom_level: str, bloom_target: str) -> int:
    """
    How far along the Bloom hierarchy toward the target level (0–100).

    Examples:
      bloom_level=remember, bloom_target=apply  → 0/2 → 0%
      bloom_level=understand, bloom_target=apply → 1/2 → 50%
      bloom_level=apply, bloom_target=apply      → 2/2 → 100%
      bloom_level=analyse, bloom_target=apply    → capped at 100%
    """
    target_idx  = bloom_idx(bloom_target)
    current_idx = bloom_idx(bloom_level)
    if target_idx == 0:
        return 100   # target = remember → already there
    return min(100, round(current_idx / target_idx * 100))


def calc_retention(
    bloom_achieved_at: Optional[datetime],
    last_active:       datetime,
) -> int:
    """
    Retention decays exponentially after bloom_target is first achieved.
    Half-life: 21 days of inactivity.
    Revised each session to reflect last_active timestamp.

    Returns 0 if bloom_target has never been reached (nothing to retain yet).
    """
    if bloom_achieved_at is None:
        return 0
    now       = datetime.now(timezone.utc)
    days_idle = max(0.0, (now - last_active).total_seconds() / 86_400)
    half_life = 21.0
    score     = 100.0 * math.pow(0.5, days_idle / half_life)
    return max(0, min(100, round(score)))


def calc_confidence(correct_count: int, total_attempts: int) -> int:
    """
    Accuracy-based confidence proxy (0–100).
    Defaults to 50 (neutral) before any attempts.
    Future: incorporate student self-reported confidence ratings.
    """
    if total_attempts == 0:
        return 50
    return min(100, round(correct_count / total_attempts * 100))


def calc_transfer(transfer_contexts: int) -> int:
    """
    Cross-context application score (0–100).
    0 distinct contexts = 0%, 3+ distinct real-world contexts = 100%.
    """
    return min(100, round(transfer_contexts / 3 * 100))


def calc_independence(hint_count: int, total_attempts: int) -> int:
    """
    1 − hint_dependency, where hint_dependency = hints / attempts.
    Defaults to 100 (fully independent) before any data.
    """
    if total_attempts == 0:
        return 100
    hint_rate = min(1.0, hint_count / total_attempts)
    return max(0, min(100, round((1.0 - hint_rate) * 100)))


def calc_mastery_score(
    bloom_progress: int,
    retention:      int,
    confidence:     int,
    transfer:       int,
    independence:   int,
) -> int:
    """
    Weighted composite mastery score (0–100).

    Weights:
        40%  Bloom Progress   (curriculum coverage)
        25%  Retention        (long-term memory)
        15%  Confidence       (accuracy / self-efficacy)
        10%  Transfer         (cross-context application)
        10%  Independence     (1 − hint dependency)
    """
    return round(
        bloom_progress * 0.40
        + retention    * 0.25
        + confidence   * 0.15
        + transfer     * 0.10
        + independence * 0.10
    )


def recompute_all(row: dict) -> dict:
    """
    Given a raw subconcept_mastery row (or partial dict with defaults),
    recompute all five dimensions and the composite mastery_score.
    Returns a dict of computed fields ready to merge back into the row.
    """
    bloom_achieved_at_raw = row.get("bloom_achieved_at")
    bloom_achieved_at: Optional[datetime] = None
    if bloom_achieved_at_raw:
        try:
            dt = datetime.fromisoformat(str(bloom_achieved_at_raw))
            bloom_achieved_at = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    last_active_raw = row.get("last_active") or datetime.now(timezone.utc).isoformat()
    try:
        la = datetime.fromisoformat(str(last_active_raw))
        last_active = la if la.tzinfo else la.replace(tzinfo=timezone.utc)
    except Exception:
        last_active = datetime.now(timezone.utc)

    bp  = calc_bloom_progress(row.get("bloom_level", "remember"), row.get("bloom_target", "apply"))
    ret = calc_retention(bloom_achieved_at, last_active)
    con = calc_confidence(row.get("correct_count", 0), row.get("total_attempts", 0))
    trn = calc_transfer(row.get("transfer_contexts", 0))
    ind = calc_independence(row.get("hint_count", 0), row.get("total_attempts", 0))
    ms  = calc_mastery_score(bp, ret, con, trn, ind)

    return {
        "bloom_progress":    bp,
        "retention_score":   ret,
        "confidence_score":  con,
        "transfer_score":    trn,
        "independence_score": ind,
        "mastery_score":     ms,
    }


# ── Supabase CRUD ─────────────────────────────────────────────────────────────

async def get_mastery_for_chapter(student_id: str, chapter_id: str) -> dict[str, dict]:
    """
    Returns { subconcept_id: mastery_row } for all subconcepts the student
    has any engagement record for in this chapter.
    """
    def _fetch():
        return (
            _supabase()
            .table("subconcept_mastery")
            .select("*")
            .eq("student_id", student_id)
            .eq("chapter_id", chapter_id)
            .execute()
        )

    res = await asyncio.to_thread(_fetch)
    return {row["subconcept_id"]: row for row in (res.data or [])}


async def get_mastered_subconcept_ids(student_id: str) -> set[str]:
    """
    Returns the set of subconcept_ids where mastery_score >= MASTERY_DONE_THRESHOLD.
    Used by the GPS routing algorithm.
    """
    def _fetch():
        return (
            _supabase()
            .table("subconcept_mastery")
            .select("subconcept_id")
            .eq("student_id", student_id)
            .gte("mastery_score", MASTERY_DONE_THRESHOLD)
            .execute()
        )

    res = await asyncio.to_thread(_fetch)
    return {row["subconcept_id"] for row in (res.data or [])}


async def upsert_after_session(
    *,
    student_id:        str,
    subconcept_id:     str,
    chapter_id:        str,
    new_bloom_level:   str,        # bloom level reached (or current) after this session
    bloom_target:      str,        # the subconcept node's target bloom level (from Neo4j)
    hints_used:        int,        # hints given THIS turn (delta, not cumulative)
    correct:           bool,       # did the student answer correctly this turn?
    xp_earned:         int,
    transfer_context:  Optional[str] = None,   # e.g. "market_shopping" — new context tested
) -> dict:
    """
    Fetch existing mastery row (or start from defaults), apply session signals,
    recompute all five dimensions, persist to Supabase.

    Returns the updated mastery row including all dimension scores.

    Rules:
    - bloom_level only ever advances, never goes backward
    - bloom_achieved_at is set the first time bloom_target level is reached
    - Retention resets to 100 at bloom_achieved_at, then decays over idle days
    """
    sb  = _supabase()
    now = datetime.now(timezone.utc)

    # ── Fetch existing row ──────────────────────────────────────────────────
    def _fetch_existing():
        return (
            sb.table("subconcept_mastery")
            .select("*")
            .eq("student_id", student_id)
            .eq("subconcept_id", subconcept_id)
            .execute()
        )

    res      = await asyncio.to_thread(_fetch_existing)
    existing = res.data[0] if res.data else {}

    # ── Update raw signals ──────────────────────────────────────────────────
    # Bloom level: only advance, never retreat
    prev_bloom  = existing.get("bloom_level", "remember")
    prev_idx    = bloom_idx(prev_bloom)
    new_idx     = bloom_idx(new_bloom_level)
    final_bloom = new_bloom_level if new_idx > prev_idx else prev_bloom

    # Check if bloom_target was just achieved for the first time
    prev_achieved       = existing.get("bloom_achieved_at")
    target_idx          = bloom_idx(bloom_target)
    final_bloom_idx     = bloom_idx(final_bloom)
    bloom_achieved_at   = prev_achieved
    if bloom_achieved_at is None and final_bloom_idx >= target_idx:
        bloom_achieved_at = now.isoformat()

    # Accumulate signals
    hint_count      = existing.get("hint_count",      0) + hints_used
    session_count   = existing.get("session_count",   0) + 1
    correct_count   = existing.get("correct_count",   0) + (1 if correct else 0)
    total_attempts  = existing.get("total_attempts",  0) + 1
    transfer_n      = existing.get("transfer_contexts", 0)
    xp_total        = existing.get("xp_total",        0) + xp_earned

    if transfer_context:
        transfer_n += 1   # TODO: deduplicate by storing a JSONB array of context IDs

    # ── Recompute dimensions ────────────────────────────────────────────────
    achieved_dt: Optional[datetime] = None
    if bloom_achieved_at:
        try:
            dt = datetime.fromisoformat(bloom_achieved_at)
            achieved_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    bp  = calc_bloom_progress(final_bloom, bloom_target)
    ret = calc_retention(achieved_dt, now)
    con = calc_confidence(correct_count, total_attempts)
    trn = calc_transfer(transfer_n)
    ind = calc_independence(hint_count, total_attempts)
    ms  = calc_mastery_score(bp, ret, con, trn, ind)

    # ── Upsert to Supabase ──────────────────────────────────────────────────
    row = {
        "student_id":         student_id,
        "subconcept_id":      subconcept_id,
        "chapter_id":         chapter_id,

        # Bloom
        "bloom_level":        final_bloom,
        "bloom_target":       bloom_target,
        "bloom_progress":     bp,

        # Mastery dimensions
        "retention_score":    ret,
        "confidence_score":   con,
        "transfer_score":     trn,
        "independence_score": ind,

        # Composite
        "mastery_score":      ms,

        # Raw signals
        "hint_count":         hint_count,
        "session_count":      session_count,
        "correct_count":      correct_count,
        "total_attempts":     total_attempts,
        "transfer_contexts":  transfer_n,

        # Timestamps
        "bloom_achieved_at":  bloom_achieved_at,
        "last_active":        now.isoformat(),
        "updated_at":         now.isoformat(),

        # XP
        "xp_total":           xp_total,
    }

    def _upsert():
        sb.table("subconcept_mastery").upsert(row).execute()

    await asyncio.to_thread(_upsert)
    return row


async def get_chapter_mastery_summary(student_id: str, chapter_id: str) -> dict:
    """
    Returns a chapter-level summary with:
      - mastery_pct       : mean mastery_score across all engaged subconcepts
      - bloom_pct         : mean bloom_progress
      - subconcepts       : per-subconcept breakdown
    """
    rows = await get_mastery_for_chapter(student_id, chapter_id)
    if not rows:
        return {
            "mastery_pct": 0,
            "bloom_pct":   0,
            "subconcepts": {},
        }

    values = list(rows.values())
    mastery_pct = round(sum(r["mastery_score"]   for r in values) / len(values))
    bloom_pct   = round(sum(r["bloom_progress"]  for r in values) / len(values))

    return {
        "mastery_pct": mastery_pct,
        "bloom_pct":   bloom_pct,
        "subconcepts": rows,
    }
