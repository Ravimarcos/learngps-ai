"""
Question Bank — loads levelwise_questions.json
================================================
Indexes questions by concept_id + bloom level so the Tutor Agent
can fetch the right question for a student's current GPS position.

The source file lives in the ai-learning-platform data folder.
On Day 6 (DIKSHA), we'll add video/simulation links alongside.
"""

import json
import random
from pathlib import Path
from functools import lru_cache
from typing import Optional

# Path to the extracted question bank from daughter's worksheets
QUESTION_BANK_PATH = Path(__file__).parents[2] / "data" / "sources" / "levelwise_questions.json"

# Map our Neo4j SubConcept IDs → question bank concept_ids (list = pull from multiple)
SUBCONCEPT_TO_CONCEPTS: dict[str, list[str]] = {
    "sc_muscular_force":   ["muscular_force"],
    "sc_contact_force":    ["contact_force", "force"],        # force general covers contact too
    "sc_non_contact":      ["electrostatic_force", "magnetic_force"],  # both non-contact types
    "sc_normal_force":     ["force"],                         # general force questions
    "sc_gravity":          ["gravity"],
    "sc_friction":         ["friction"],
    "sc_resultant_force":  ["resultant_force", "force"],
    "sc_pressure_def":     ["pressure"],
    "sc_liquid_pressure":  ["liquid_pressure"],
    "sc_atm_pressure":     ["atmospheric_pressure"],
}

# Legacy single-value alias for any code still using SUBCONCEPT_TO_CONCEPT
SUBCONCEPT_TO_CONCEPT = {k: v[0] for k, v in SUBCONCEPT_TO_CONCEPTS.items()}

# Map Bloom levels to question bank keys
BLOOM_TO_KEY = {
    "Remember":  "remember",
    "Understand":"understand",
    "Apply":     "apply",
    "Analyse":   "analyse",
    "Evaluate":  "evaluate",
    "Create":    "evaluate",  # fallback
}


@lru_cache(maxsize=1)
def load_question_bank() -> dict:
    """Load and cache the full question bank."""
    if not QUESTION_BANK_PATH.exists():
        print(f"⚠️  Question bank not found at {QUESTION_BANK_PATH}")
        return {}
    with open(QUESTION_BANK_PATH) as f:
        return json.load(f)


def get_questions_for_subconcept(
    subconcept_id: str,
    bloom_level: str = "Remember",
    limit: int = 5,
) -> list[dict]:
    """
    Return questions matching a SubConcept and Bloom level.
    Pulls from all question types (bloom levels + NCERT, case-based, assertion-reason, etc.)
    so Claude always has variety. Falls back to lower Bloom levels if no match found.
    """
    bank = load_question_bank()
    if not bank:
        return []

    concept_ids = SUBCONCEPT_TO_CONCEPTS.get(subconcept_id)
    if not concept_ids:
        return []

    def _matches(q: dict) -> bool:
        return q.get("concept_id") in concept_ids

    bloom_key = BLOOM_TO_KEY.get(bloom_level, "remember")
    questions = bank.get("questions", {})

    # 1. Bloom-level questions (target level first, fall back down)
    bloom_order = ["remember", "understand", "apply", "analyse", "evaluate"]
    target_idx = bloom_order.index(bloom_key) if bloom_key in bloom_order else 0
    bloom_qs: list[dict] = []
    for idx in range(target_idx, -1, -1):
        level_qs = questions.get(bloom_order[idx], [])
        bloom_qs += [q for q in level_qs if _matches(q)]
        if bloom_qs:
            break

    # 2. Rich question types — always pull these for variety
    EXTRA_TYPES = [
        "ncert_section", "case_based", "assertion_reason",
        "true_false", "fill_blanks", "short_answer",
        "long_answer", "numerical",
    ]
    extra_qs: list[dict] = []
    for qtype in EXTRA_TYPES:
        pool = questions.get(qtype, [])
        extra_qs += [q for q in pool if _matches(q)]

    # Combine: bloom-level first, then extras. Shuffle each group independently.
    random.shuffle(bloom_qs)
    random.shuffle(extra_qs)
    combined = bloom_qs + extra_qs

    return combined[:limit] if combined else []


BLOOM_STYLE_GUIDE = {
    "Remember": (
        "L1 — Basic recall. Format: MCQ with 4 options. Wrong options must be common misconceptions. "
        "Test: definitions, examples vs non-examples, naming forces. "
        "Example style: 'Which of the following is NOT an example of [X]?'"
    ),
    "Understand": (
        "L2 — Explain why/how. Mix of short-answer and MCQ. "
        "Test: cause-effect, reasoning behind everyday observations. "
        "Example style: 'Why do school bags have broad straps?' or "
        "'Which statement CORRECTLY explains why [observation]?'"
    ),
    "Apply": (
        "L3 — Use concept in new situation. Numerical or scenario MCQ. "
        "Test: calculations (P=F/A, F=ma), real-world application. "
        "Example style: 'A person weighs 600N with shoe area 0.02m². What pressure on floor?' "
        "or 'A camel walks on sand. Why does it not sink?'"
    ),
    "Analyse": (
        "L4 — Break down and compare. Multi-statement MCQ or assertion-reason. "
        "Test: identify correct explanation among plausible options, compare scenarios. "
        "Example style: 'Statement 1: X. Statement 2: Y. Which is correct and why?' "
        "or 'Which TWO of the following statements explain [phenomenon]?'"
    ),
    "Evaluate": (
        "L5 — Judge and justify. Case-based or HOTS open-ended. "
        "Test: evaluate a design/claim/experiment, justify with reasoning. "
        "Example style: Case study with 3-4 sub-questions, or "
        "'Assertion: X. Reason: Y. Choose A/B/C/D' where student must verify both."
    ),
    "Create": (
        "L6 — Design/propose. Open-ended only. "
        "Test: design an experiment, propose a solution, create an analogy. "
        "Example style: 'Design a shoe sole for walking on snow. Justify using force and pressure.' "
        "or 'Propose an experiment to show friction depends on surface roughness.'"
    ),
}


def get_bloom_style_guide(bloom_level: str) -> str:
    """Return question style instructions for a given Bloom level."""
    return BLOOM_STYLE_GUIDE.get(bloom_level, BLOOM_STYLE_GUIDE["Remember"])


def get_activities_for_subconcept(subconcept_id: str) -> list[dict]:
    """Return hands-on activities for a SubConcept."""
    bank = load_question_bank()
    concept_id = SUBCONCEPT_TO_CONCEPT.get(subconcept_id)
    if not concept_id or not bank:
        return []

    activities = bank.get("activities", [])
    if isinstance(activities, list):
        return [a for a in activities if a.get("concept_id") == concept_id]
    return []


def get_solved_examples(subconcept_id: str) -> list[dict]:
    """Return solved examples for a SubConcept."""
    bank = load_question_bank()
    concept_id = SUBCONCEPT_TO_CONCEPT.get(subconcept_id)
    if not concept_id or not bank:
        return []

    examples = bank.get("solved_examples", [])
    if isinstance(examples, list):
        return [e for e in examples if e.get("concept_id") == concept_id]
    return []
