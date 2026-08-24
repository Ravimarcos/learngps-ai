"""
VARK Inference Agent — Day 7
==============================
Detects a student's learning style (Visual / Auditory / Read-Write / Kinesthetic)
from their chat messages and updates their profile using Bayesian inference.

How it works:
  1. Student sends a message: "can you show me a diagram of friction?"
  2. We scan for VARK signal keywords → Visual signal detected
  3. Bayesian update: V score increases, others decrease slightly
  4. New VARK profile saved to Supabase (student_vark table)
  5. Next session, Gyaan automatically uses Visual teaching style

Bayesian update rule (simple):
  new_score = (old_score * session_weight + signal_strength) / (session_weight + 1)

  session_weight grows with experience — early sessions shift style fast,
  later sessions need stronger evidence to change it.

Run directly to test detection:
    python -m backend.agents.vark_agent
"""

import re
import asyncio
from supabase import create_client
from backend.config.settings import get_settings

settings = get_settings()

# ── VARK signal keyword banks ──────────────────────────────────────────────
# Each keyword gets a weight (0.0-1.0) based on how strongly it signals that style

VARK_SIGNALS: dict[str, dict[str, float]] = {
    "V": {   # Visual — wants to SEE it
        "show me":       1.0,
        "diagram":       1.0,
        "picture":       1.0,
        "draw":          0.9,
        "visualise":     0.9,
        "visualize":     0.9,
        "what does it look like": 1.0,
        "image":         0.8,
        "graph":         0.8,
        "chart":         0.8,
        "colour":        0.7,
        "color":         0.7,
        "map":           0.7,
        "see":           0.5,
        "look":          0.5,
    },
    "A": {   # Auditory — wants to HEAR / discuss it
        "explain":       0.8,
        "tell me":       0.9,
        "talk":          0.8,
        "discuss":       0.9,
        "sounds like":   1.0,
        "i hear":        0.9,
        "say it":        0.9,
        "repeat":        0.7,
        "listen":        0.8,
        "pronunciation": 0.7,
        "read aloud":    1.0,
        "can you say":   0.9,
    },
    "R": {   # Read/Write — wants TEXT, lists, definitions
        "write":         0.8,
        "list":          0.9,
        "define":        1.0,
        "definition":    1.0,
        "steps":         0.9,
        "notes":         0.9,
        "summarise":     0.9,
        "summarize":     0.9,
        "textbook":      0.8,
        "read":          0.7,
        "formula":       0.8,
        "equation":      0.8,
        "write down":    1.0,
        "point by point":1.0,
    },
    "K": {   # Kinesthetic — wants to DO it / real examples
        "try":           0.8,
        "do it":         0.9,
        "experiment":    1.0,
        "hands-on":      1.0,
        "activity":      0.9,
        "practice":      0.9,
        "real life":     0.9,
        "example":       0.7,
        "feel":          0.8,
        "touch":         0.8,
        "build":         0.8,
        "make":          0.7,
        "physically":    0.9,
        "at home":       0.8,
        "chapati":       0.7,   # Indian kinesthetic context :)
        "cricket":       0.7,
    },
}


def detect_vark_signals(text: str) -> dict[str, float]:
    """
    Scan a student message for VARK signal keywords.

    Returns:
        Dict of style → signal strength (0.0 if no signal detected)
        e.g. {"V": 0.0, "A": 0.0, "R": 0.0, "K": 0.9}
    """
    text_lower = text.lower()
    signals = {"V": 0.0, "A": 0.0, "R": 0.0, "K": 0.0}

    for style, keywords in VARK_SIGNALS.items():
        for keyword, weight in keywords.items():
            if keyword in text_lower:
                # Take the strongest signal per style
                signals[style] = max(signals[style], weight)

    return signals


def bayesian_update(
    current_scores: dict[str, float],
    signals: dict[str, float],
    session_count: int,
) -> dict[str, float]:
    """
    Update VARK scores using Bayesian-style weighted averaging.

    Early sessions (low session_count) → signals have more impact
    Later sessions (high session_count) → profile is more stable

    Args:
        current_scores: {"V": 0.25, "A": 0.25, "R": 0.25, "K": 0.25}
        signals:        {"V": 0.0, "A": 0.0, "R": 0.0, "K": 0.9}
        session_count:  how many sessions this student has had

    Returns:
        Updated scores that sum to 1.0
    """
    # No signal detected — return unchanged
    if not any(signals.values()):
        return current_scores

    # Session weight: starts low (easy to change), grows with experience
    session_weight = min(session_count + 1, 10)   # cap at 10

    # Weighted update
    updated = {}
    for style in ["V", "A", "R", "K"]:
        signal = signals.get(style, 0.0)
        old    = current_scores.get(f"{style.lower()}_score", 0.25)
        # Blend old score with new signal
        updated[f"{style.lower()}_score"] = (
            (old * session_weight + signal) / (session_weight + 1)
        )

    # Normalise so scores sum to 1.0
    total = sum(updated.values())
    if total > 0:
        updated = {k: round(v / total, 4) for k, v in updated.items()}

    return updated


def dominant_style(scores: dict) -> str:
    """Return the VARK style with highest score."""
    style_map = {
        "v_score": "V",
        "a_score": "A",
        "r_score": "R",
        "k_score": "K",
    }
    best = max(["v_score", "a_score", "r_score", "k_score"],
               key=lambda k: scores.get(k, 0))
    return style_map[best]


# ── Supabase read/write ────────────────────────────────────────────────────

def _get_supabase():
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def get_vark_profile(student_id: str) -> dict:
    """
    Fetch student's VARK profile from Supabase.
    Returns default equal profile if not found.
    """
    sb = _get_supabase()

    result = await asyncio.to_thread(
        lambda: sb.table("student_vark")
                  .select("*")
                  .eq("student_id", student_id)
                  .execute()
    )

    if result.data:
        profile = result.data[0]
        return {
            "student_id":    student_id,
            "v_score":       profile["v_score"],
            "a_score":       profile["a_score"],
            "r_score":       profile["r_score"],
            "k_score":       profile["k_score"],
            "session_count": profile["session_count"],
            "dominant":      dominant_style(profile),
        }

    # Default: equal distribution
    return {
        "student_id":    student_id,
        "v_score":       0.25,
        "a_score":       0.25,
        "r_score":       0.25,
        "k_score":       0.25,
        "session_count": 0,
        "dominant":      "K",   # default to Kinesthetic for Indian students
    }


async def update_vark_profile(student_id: str, student_message: str) -> dict:
    """
    Detect VARK signals in a student message and update their profile.

    Args:
        student_id:      UUID of student
        student_message: what the student just said

    Returns:
        Updated VARK profile with dominant style
    """
    sb = _get_supabase()

    # 1. Get current profile
    profile = await get_vark_profile(student_id)
    current_scores = {
        "v_score": profile["v_score"],
        "a_score": profile["a_score"],
        "r_score": profile["r_score"],
        "k_score": profile["k_score"],
    }

    # 2. Detect signals in student message
    signals = detect_vark_signals(student_message)

    # 3. Bayesian update
    new_scores = bayesian_update(current_scores, signals, profile["session_count"])
    new_count  = profile["session_count"] + 1
    new_dominant = dominant_style(new_scores)

    # 4. Upsert to Supabase (insert if new, update if exists)
    upsert_data = {
        "student_id":    student_id,
        "v_score":       new_scores["v_score"],
        "a_score":       new_scores["a_score"],
        "r_score":       new_scores["r_score"],
        "k_score":       new_scores["k_score"],
        "session_count": new_count,
        "updated_at":    "now()",
    }

    try:
        await asyncio.to_thread(
            lambda: sb.table("student_vark")
                      .upsert(upsert_data, on_conflict="student_id")
                      .execute()
        )
    except Exception as e:
        # VARK update should never crash the main chat
        print(f"⚠️  VARK upsert skipped: {e}")

    return {
        "student_id":    student_id,
        "v_score":       new_scores["v_score"],
        "a_score":       new_scores["a_score"],
        "r_score":       new_scores["r_score"],
        "k_score":       new_scores["k_score"],
        "session_count": new_count,
        "dominant":      new_dominant,
        "signals_detected": {k: v for k, v in signals.items() if v > 0},
    }


# ── Quick test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_messages = [
        "Can you show me a diagram of how friction works?",
        "Let me try the chapati experiment at home!",
        "Please give me a list of all the types of force",
        "Can you explain it to me again?",
        "I don't understand anything",   # no signal
    ]

    print("VARK Signal Detection Test\n" + "=" * 40)
    for msg in test_messages:
        signals = detect_vark_signals(msg)
        detected = {k: v for k, v in signals.items() if v > 0}
        dominant = max(signals, key=signals.get) if any(signals.values()) else "none"
        print(f"\nMessage: {msg[:60]}")
        print(f"Signals: {detected}")
        print(f"Dominant signal: {dominant}")
