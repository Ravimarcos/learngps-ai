"""
GPS Traversal Algorithm
========================
Given a chapter and a student's mastered SubConcept IDs, compute:

  current   — first SubConcept whose prerequisites are all mastered
  route     — remaining reachable SubConcepts (not yet mastered, not current)
  completed — all mastered SubConcepts
  locked    — SubConcepts whose prerequisites are NOT yet fully mastered (ghost nodes)
  nodes     — ALL SubConcepts in the chapter with map_x / map_y positions
  edges     — ALL PREREQUISITE edges in the chapter (from_id → to_id)

nodes + edges let the frontend render a fully data-driven 2D graph.
No layout data lives in the frontend.
"""

from typing import Optional
from neo4j import AsyncDriver


async def get_gps_route(
    driver: AsyncDriver,
    chapter_id: str,
    mastered_sc_ids: set[str],
) -> dict:
    """
    Returns the full GPS state for a chapter.

    Return shape:
    {
        "current":   {id, name, x, y, bloom_target, vark_hint} | None,
        "route":     [{id, name, x, y, ...}, ...],   # reachable, not yet started
        "completed": [{id, name, x, y, ...}, ...],
        "locked":    [{id, name, x, y, ...}, ...],   # prereqs not yet met (ghost nodes)
        "nodes":     [{id, name, x, y, ...}, ...],   # EVERY node in chapter
        "edges":     [{"from_id": str, "to_id": str}, ...],  # all PREREQUISITE edges
    }
    """
    async with driver.session() as session:

        # ── 1. All SubConcepts in this chapter with positions ─────────────────
        node_result = await session.run(
            """
            MATCH (sc:SubConcept)-[:PART_OF]->(:Concept)-[:PART_OF]->(ch:Chapter {id:$chapter_id})
            OPTIONAL MATCH (prereq:SubConcept)-[:PREREQUISITE]->(sc)
            RETURN sc.id          AS id,
                   sc.name        AS name,
                   sc.bloom_target AS bloom_target,
                   sc.vark_hint   AS vark_hint,
                   coalesce(sc.map_x, 170.0) AS x,
                   coalesce(sc.map_y, 250.0) AS y,
                   collect(prereq.id) AS prerequisite_ids
            """,
            chapter_id=chapter_id,
        )
        records = await node_result.data()

        # ── 2. All PREREQUISITE edges in this chapter ─────────────────────────
        edge_result = await session.run(
            """
            MATCH (a:SubConcept)-[:PART_OF]->(:Concept)-[:PART_OF]->(ch:Chapter {id:$chapter_id})
            MATCH (b:SubConcept)-[:PART_OF]->(:Concept)-[:PART_OF]->(ch)
            MATCH (a)-[:PREREQUISITE]->(b)
            RETURN a.id AS from_id, b.id AS to_id
            """,
            chapter_id=chapter_id,
        )
        edges = [{"from_id": r["from_id"], "to_id": r["to_id"]}
                 for r in await edge_result.data()]

        # ── 3. Classify each node ─────────────────────────────────────────────
        completed  = []
        current    = None
        route      = []
        locked     = []
        all_nodes  = []

        for r in records:
            sc = {
                "id":           r["id"],
                "name":         r["name"],
                "bloom_target": r["bloom_target"],
                "vark_hint":    r["vark_hint"],
                "x":            r["x"],
                "y":            r["y"],
            }
            all_nodes.append(sc)

            prereqs = set(r["prerequisite_ids"]) if r["prerequisite_ids"] else set()

            if r["id"] in mastered_sc_ids:
                completed.append(sc)
            elif prereqs.issubset(mastered_sc_ids):
                # All prerequisites met — node is reachable
                if current is None:
                    current = sc          # first reachable = GPS position
                else:
                    route.append(sc)      # others are "ready" (not started)
            else:
                locked.append(sc)         # ghost nodes — visible but prereqs pending

        return {
            "current":   current,
            "route":     route,           # does NOT include current (bug fixed)
            "completed": completed,
            "locked":    locked,
            "nodes":     all_nodes,       # all nodes with x,y for 2D rendering
            "edges":     edges,           # all prerequisite edges for drawing lines
        }


async def get_chapters(
    driver: AsyncDriver,
    mastered_sc_ids: set[str] | None = None,
    grade: int | None = None,
    subject: str | None = None,
) -> dict:
    """
    Returns all Chapter nodes visible in the overview map, with mastery_pct
    calculated from the student's mastered subconcepts (if provided).

    Also returns CHAPTER_LINK edges for the cross-chapter overlay.

    Return shape:
    {
        "chapters": [
            {
                "id", "name", "grade", "subject",
                "color", "ov_x", "ov_y", "ov_radius", "eta",
                "ncert_chapter_num", "subconcept_count", "mastery_pct"
            },
            ...
        ],
        "edges": [{"from_id": str, "to_id": str, "label": str}, ...]
    }
    """
    mastered_ids = list(mastered_sc_ids) if mastered_sc_ids else []

    async with driver.session() as session:
        # ── 1. Chapters with subconcept count + per-chapter mastery ──────────
        chapter_result = await session.run(
            """
            MATCH (ch:Chapter)
            WHERE ($grade   IS NULL OR ch.grade   = $grade)
              AND ($subject IS NULL OR ch.subject = $subject)
            OPTIONAL MATCH (sc:SubConcept)-[:PART_OF]->(:Concept)-[:PART_OF]->(ch)
            WITH ch, collect(sc.id) AS all_sc_ids, count(sc) AS total
            RETURN
                ch.id               AS id,
                ch.name             AS name,
                ch.grade            AS grade,
                ch.subject          AS subject,
                coalesce(ch.color,     '#4338ca')    AS color,
                coalesce(ch.ov_x,      380.0)        AS ov_x,
                coalesce(ch.ov_y,      295.0)        AS ov_y,
                coalesce(ch.ov_radius, 46.0)         AS ov_radius,
                coalesce(ch.eta,       '~8 sessions') AS eta,
                ch.ncert_chapter_num  AS ncert_chapter_num,
                total,
                [x IN all_sc_ids WHERE x IN $mastered_ids | x] AS mastered_in_ch
            ORDER BY ch.grade, ch.subject, ch.ncert_chapter_num
            """,
            grade=grade, subject=subject, mastered_ids=mastered_ids,
        )
        records = await chapter_result.data()

        chapters = []
        for r in records:
            mastered_count = len(r["mastered_in_ch"]) if r["mastered_in_ch"] else 0
            total          = r["total"] or 0
            chapters.append({
                "id":                r["id"],
                "name":              r["name"],
                "grade":             r["grade"],
                "subject":           r["subject"],
                "color":             r["color"],
                "ov_x":              float(r["ov_x"]),
                "ov_y":              float(r["ov_y"]),
                "ov_radius":         float(r["ov_radius"]),
                "eta":               r["eta"],
                "ncert_chapter_num": r["ncert_chapter_num"],
                "subconcept_count":  total,
                "mastery_pct":       round(mastered_count / max(total, 1) * 100),
            })

        # ── 2. CHAPTER_LINK edges ─────────────────────────────────────────────
        edge_result = await session.run(
            """
            MATCH (a:Chapter)-[r:CHAPTER_LINK]->(b:Chapter)
            RETURN a.id AS from_id, b.id AS to_id, r.label AS label
            """
        )
        edges = [
            {"from_id": r["from_id"], "to_id": r["to_id"], "label": r["label"]}
            for r in await edge_result.data()
        ]

        return {"chapters": chapters, "edges": edges}


async def get_next_subconcept(
    driver: AsyncDriver,
    chapter_id: str,
    mastered_sc_ids: set[str],
) -> Optional[dict]:
    """Returns just the current GPS position (next SubConcept to study)."""
    gps = await get_gps_route(driver, chapter_id, mastered_sc_ids)
    return gps["current"]


async def get_ability_scores(
    driver: AsyncDriver,
    mastered_sc_ids: set[str],
) -> list[dict]:
    """
    Derive Ability scores from mastered SubConcepts.
    Used by Curriculum Agent for Career Compass trigger conditions.
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
            mastered_ids=list(mastered_sc_ids),
        )
        return await result.data()


async def get_career_recommendations(
    driver: AsyncDriver,
    ability_scores: list[dict],
    min_ability_score: float = 0.6,
) -> list[dict]:
    """Map high-scoring Abilities to CareerFamilies and CareerPaths."""
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
            ability_ids=strong_abilities,
        )
        return await result.data()
