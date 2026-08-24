"""
GPS Traversal Algorithm
========================
Given a student's current SubConcept, compute:
  1. next_subconcept  — what to learn next on the GPS route
  2. gps_route        — full ordered list of SubConcepts from current to chapter end
  3. unlocked_chapters — Chapters unlocked after mastering prerequisites

The algorithm honours PREREQUISITE edges — a SubConcept is only reachable
if all its prerequisites are mastered by the student.

Student mastery state lives in Supabase (student_progress table),
but is passed in as a set here to keep graph logic pure.
"""

from typing import Optional
from neo4j import AsyncDriver


async def get_gps_route(
    driver: AsyncDriver,
    chapter_id: str,
    mastered_sc_ids: set[str],
) -> dict:
    """
    Returns the GPS route for a chapter.

    Returns:
        {
            "current": SubConcept node dict or None,
            "route": [ordered SubConcept dicts from current to end],
            "completed": [mastered SubConcept dicts],
            "locked": [SubConcept dicts not yet reachable],
        }
    """
    async with driver.session() as session:

        # Step 1: Get all SubConcepts in this chapter (ordered by depth / prereq chain)
        result = await session.run(
            """
            MATCH (sc:SubConcept)-[:PART_OF]->(:Concept)-[:PART_OF]->(ch:Chapter {id:$chapter_id})
            OPTIONAL MATCH (prereq:SubConcept)-[:PREREQUISITE]->(sc)
            RETURN sc.id AS id, sc.name AS name,
                   sc.bloom_target AS bloom_target, sc.vark_hint AS vark_hint,
                   collect(prereq.id) AS prerequisite_ids
            """,
            chapter_id=chapter_id
        )
        records = await result.data()

        # Step 2: Classify each SubConcept
        completed = []
        current = None
        route = []
        locked = []

        for r in records:
            sc = {
                "id": r["id"],
                "name": r["name"],
                "bloom_target": r["bloom_target"],
                "vark_hint": r["vark_hint"],
            }
            prereqs = set(r["prerequisite_ids"]) if r["prerequisite_ids"] else set()

            if r["id"] in mastered_sc_ids:
                completed.append(sc)
            elif prereqs.issubset(mastered_sc_ids):
                # All prerequisites satisfied → reachable
                if current is None:
                    current = sc   # First reachable = current GPS position
                else:
                    route.append(sc)
            else:
                locked.append(sc)

        # Route = current + what comes after (still locked due to future prereqs)
        full_route = ([current] if current else []) + route

        return {
            "current": current,
            "route": full_route,
            "completed": completed,
            "locked": locked,
        }


async def get_next_subconcept(
    driver: AsyncDriver,
    chapter_id: str,
    mastered_sc_ids: set[str],
) -> Optional[dict]:
    """Returns just the next SubConcept to study (current GPS position)."""
    gps = await get_gps_route(driver, chapter_id, mastered_sc_ids)
    return gps["current"]


async def get_ability_scores(
    driver: AsyncDriver,
    mastered_sc_ids: set[str],
) -> list[dict]:
    """
    Derive Ability scores from mastered SubConcepts.
    Used by Curriculum Agent to check Career Compass trigger conditions.

    Returns:
        [{"ability_id": str, "ability_name": str, "score": float (0-1)}, ...]
    """
    if not mastered_sc_ids:
        return []

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (sc:SubConcept)-[:BUILDS]->(ab:Ability)
            WHERE sc.id IN $mastered_ids
            WITH ab, count(sc) AS mastered_count
            MATCH (any_sc:SubConcept)-[:BUILDS]->(ab)
            WITH ab, mastered_count, count(any_sc) AS total_count
            RETURN ab.id AS ability_id, ab.name AS ability_name,
                   toFloat(mastered_count) / total_count AS score
            ORDER BY score DESC
            """,
            mastered_ids=list(mastered_sc_ids)
        )
        return await result.data()


async def get_career_recommendations(
    driver: AsyncDriver,
    ability_scores: list[dict],
    min_ability_score: float = 0.6,
) -> list[dict]:
    """
    Map high-scoring Abilities to CareerFamilies and CareerPaths.
    Called only after Career Compass trigger conditions are met.

    Returns:
        [{"career_family": str, "career_paths": [str], "confidence": float}, ...]
    """
    strong_abilities = [
        a["ability_id"] for a in ability_scores
        if a["score"] >= min_ability_score
    ]
    if not strong_abilities:
        return []

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (ab:Ability)-[:MAPS_TO]->(cf:CareerFamily)-[:LEADS_TO]->(cp:CareerPath)
            WHERE ab.id IN $ability_ids
            WITH cf, collect(DISTINCT cp.name) AS paths, avg(1.0) AS confidence
            RETURN cf.name AS career_family, paths AS career_paths, confidence
            ORDER BY career_family
            """,
            ability_ids=strong_abilities
        )
        return await result.data()
