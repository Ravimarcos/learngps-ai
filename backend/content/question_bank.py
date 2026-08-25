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

# Map our Neo4j SubConcept IDs → question bank concept_ids
SUBCONCEPT_TO_CONCEPT = {
    "sc_muscular_force":   "muscular_force",
    "sc_contact_force":    "contact_force",
    "sc_non_contact":      "non_contact_force",
    "sc_normal_force":     "normal_force",
    "sc_friction":         "friction",
    "sc_pressure_def":     "pressure",
    "sc_liquid_pressure":  "liquid_pressure",
    "sc_atm_pressure":     "atmospheric_pressure",
}

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
    limit: int = 3,
) -> list[dict]:
    """
    Return questions matching a SubConcept and Bloom level.
    Falls back to lower Bloom levels if no match found.
    """
    bank = load_question_bank()
    if not bank:
        return []

    concept_id = SUBCONCEPT_TO_CONCEPT.get(subconcept_id)
    if not concept_id:
        return []

    bloom_key = BLOOM_TO_KEY.get(bloom_level, "remember")
    questions = bank.get("questions", {})

    # Try target bloom level first, then fall back down
    bloom_order = ["remember", "understand", "apply", "analyse", "evaluate"]
    target_idx = bloom_order.index(bloom_key) if bloom_key in bloom_order else 0

    for idx in range(target_idx, -1, -1):
        level_qs = questions.get(bloom_order[idx], [])
        matched = [q for q in level_qs if q.get("concept_id") == concept_id]
        if matched:
            random.shuffle(matched)   # randomise so same question isn't repeated every turn
            return matched[:limit]

    return []


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
