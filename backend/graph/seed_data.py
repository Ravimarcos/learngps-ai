"""
Seed Data — Grade 8 Science: Force & Pressure
=============================================
Run this ONCE (or re-run safely) after setting up Neo4j Aura.

Graph loaded:
    1 Chapter  →  2 Concepts  →  10 SubConcepts
    10 SubConcepts -[:BUILDS]-> 3 Abilities
    3 Abilities    -[:MAPS_TO]-> 2 CareerFamilies
    2 CareerFamilies -[:LEADS_TO]-> 4 CareerPaths
    PREREQUISITE edges forming the learning DAG

map_x / map_y are stored on each SubConcept in Neo4j so the frontend
can render the 2D knowledge graph without any hardcoded layout.
SVG viewBox is "0 0 340 510" — positions are in those units.

Usage:
    python -m backend.graph.seed_data
"""

import asyncio
from neo4j import AsyncGraphDatabase
from backend.config.settings import get_settings
from backend.graph.schema import create_constraints


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------
CHAPTERS = [
    {
        "id":               "ch_force_pressure",
        "name":             "Force & Pressure",
        "grade":            8,
        "subject":          "Science",
        "ncert_chapter_num": 11,
        # Overview-map display properties (stored in Neo4j, never hardcoded in frontend)
        # ov_x / ov_y → position on overview SVG canvas (viewBox "0 0 760 590")
        # ov_radius    → orb radius in SVG units
        # color        → hex accent colour for this chapter's orb + ring
        # eta          → human-readable estimated time to complete
        "color":     "#2979ff",
        "ov_x":      380.0,
        "ov_y":      295.0,
        "ov_radius": 52.0,
        "eta":       "~8 sessions",
    }
]

# Cross-chapter dependency edges shown in the overview map.
# Format: (from_chapter_id, to_chapter_id, edge_label)
# Only creates the relationship if BOTH chapters exist in Neo4j — safe to
# add future links here before the target chapter is seeded.
CHAPTER_LINKS: list[tuple[str, str, str]] = [
    # Examples for when more chapters are seeded:
    # ("ch_force_pressure", "ch_mensuration", "P = F/Area"),
    # ("ch_force_pressure", "ch_sound",        "Vibrations"),
]

# ---------------------------------------------------------------------------
# Concepts
# ---------------------------------------------------------------------------
CONCEPTS = [
    {"id": "con_force",    "name": "Force",    "weight": 0.60},
    {"id": "con_pressure", "name": "Pressure", "weight": 0.40},
]

# ---------------------------------------------------------------------------
# SubConcepts
# map_x / map_y → position on SVG canvas (viewBox "0 0 340 510")
# Topology matches knowledge-map-v2.html:
#   Muscular Force (root, top-centre)
#     → Contact Force (left)  →  Normal Force (far-left)
#     → Non-Contact Force (right) → Gravity (far-right)
#   Normal Force + Gravity → Friction (centre)
#   Friction → Resultant Force → Pressure → Liquid / Atmospheric
# ---------------------------------------------------------------------------
SUBCONCEPTS = [
    # ── Force concept ────────────────────────────────────────────────────────
    ("con_force", {
        "id": "sc_muscular_force",
        "name": "Muscular Force",
        "bloom_target": "Remember",
        "vark_hint": "K",
        "map_x": 170.0,
        "map_y":  52.0,
    }),
    ("con_force", {
        "id": "sc_contact_force",
        "name": "Contact Force",
        "bloom_target": "Understand",
        "vark_hint": "K",
        "map_x":  88.0,
        "map_y": 132.0,
    }),
    ("con_force", {
        "id": "sc_non_contact",
        "name": "Non-Contact Force",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 252.0,
        "map_y": 132.0,
    }),
    ("con_force", {
        "id": "sc_normal_force",
        "name": "Normal Force",
        "bloom_target": "Apply",
        "vark_hint": "V",
        "map_x":  52.0,
        "map_y": 218.0,
    }),
    ("con_force", {
        "id": "sc_gravity",
        "name": "Gravity",
        "bloom_target": "Understand",
        "vark_hint": "V",
        "map_x": 288.0,
        "map_y": 218.0,
    }),
    ("con_force", {
        "id": "sc_friction",
        "name": "Friction",
        "bloom_target": "Analyse",
        "vark_hint": "K",
        "map_x": 170.0,
        "map_y": 282.0,
    }),
    ("con_force", {
        "id": "sc_resultant_force",
        "name": "Resultant Force",
        "bloom_target": "Apply",
        "vark_hint": "V",
        "map_x": 170.0,
        "map_y": 340.0,
    }),
    # ── Pressure concept ─────────────────────────────────────────────────────
    ("con_pressure", {
        "id": "sc_pressure_def",
        "name": "Pressure",
        "bloom_target": "Understand",
        "vark_hint": "R",
        "map_x": 170.0,
        "map_y": 392.0,
    }),
    ("con_pressure", {
        "id": "sc_liquid_pressure",
        "name": "Liquid Pressure",
        "bloom_target": "Apply",
        "vark_hint": "V",
        "map_x":  88.0,
        "map_y": 458.0,
    }),
    ("con_pressure", {
        "id": "sc_atm_pressure",
        "name": "Atmospheric Pressure",
        "bloom_target": "Analyse",
        "vark_hint": "R",
        "map_x": 252.0,
        "map_y": 458.0,
    }),
]

# ---------------------------------------------------------------------------
# PREREQUISITE edges  (from_id → to_id means: master 'from' to unlock 'to')
# Matches the DAG in knowledge-map-v2.html
# ---------------------------------------------------------------------------
PREREQUISITES = [
    # Muscular Force is the root — no prerequisites
    ("sc_muscular_force",  "sc_contact_force"),     # learn contact types
    ("sc_muscular_force",  "sc_non_contact"),        # learn non-contact types
    ("sc_contact_force",   "sc_normal_force"),       # normal is a contact force
    ("sc_non_contact",     "sc_gravity"),            # gravity is non-contact
    ("sc_normal_force",    "sc_friction"),           # need both to understand friction
    ("sc_gravity",         "sc_friction"),
    ("sc_friction",        "sc_resultant_force"),    # net force concept
    ("sc_resultant_force", "sc_pressure_def"),       # pressure = force / area
    ("sc_pressure_def",    "sc_liquid_pressure"),
    ("sc_pressure_def",    "sc_atm_pressure"),
]

# ---------------------------------------------------------------------------
# Abilities, Career graph (unchanged)
# ---------------------------------------------------------------------------
ABILITIES = [
    {
        "id": "ab_analytical_reasoning",
        "name": "Analytical Reasoning",
        "description": "Break complex problems into components and reason systematically",
    },
    {
        "id": "ab_spatial_reasoning",
        "name": "Spatial Reasoning",
        "description": "Visualise forces, vectors, and 3-D structures",
    },
    {
        "id": "ab_quantitative_thinking",
        "name": "Quantitative Thinking",
        "description": "Apply formulae and work with numerical relationships",
    },
]

BUILDS_EDGES = [
    ("sc_normal_force",     "ab_analytical_reasoning"),
    ("sc_friction",         "ab_analytical_reasoning"),
    ("sc_atm_pressure",     "ab_analytical_reasoning"),
    ("sc_contact_force",    "ab_spatial_reasoning"),
    ("sc_muscular_force",   "ab_spatial_reasoning"),
    ("sc_liquid_pressure",  "ab_spatial_reasoning"),
    ("sc_pressure_def",     "ab_quantitative_thinking"),
    ("sc_atm_pressure",     "ab_quantitative_thinking"),
    ("sc_resultant_force",  "ab_quantitative_thinking"),
]

CAREER_FAMILIES = [
    {"id": "cf_engineering", "name": "Engineering"},
    {"id": "cf_science",     "name": "Pure Science"},
]

MAPS_TO_EDGES = [
    ("ab_analytical_reasoning",  "cf_engineering"),
    ("ab_spatial_reasoning",     "cf_engineering"),
    ("ab_quantitative_thinking", "cf_engineering"),
    ("ab_analytical_reasoning",  "cf_science"),
    ("ab_quantitative_thinking", "cf_science"),
]

CAREER_PATHS = [
    {"id": "cp_mechanical_engineer", "name": "Mechanical Engineer", "family": "cf_engineering"},
    {"id": "cp_civil_engineer",      "name": "Civil Engineer",      "family": "cf_engineering"},
    {"id": "cp_physicist",           "name": "Physicist",           "family": "cf_science"},
    {"id": "cp_research_scientist",  "name": "Research Scientist",  "family": "cf_science"},
]

LEARNING_STYLES = [
    {"id": "V", "name": "Visual"},
    {"id": "A", "name": "Auditory"},
    {"id": "R", "name": "Read/Write"},
    {"id": "K", "name": "Kinesthetic"},
]


# ---------------------------------------------------------------------------
# Seeder — safe to re-run (idempotent)
# ---------------------------------------------------------------------------
async def seed(driver):
    async with driver.session() as session:

        # Chapters
        for ch in CHAPTERS:
            await session.run(
                "MERGE (n:Chapter {id:$id}) SET n += $props",
                id=ch["id"], props=ch,
            )

        # Concepts + PART_OF Chapter
        for c in CONCEPTS:
            await session.run(
                "MERGE (n:Concept {id:$id}) SET n += $props",
                id=c["id"], props=c,
            )
        await session.run(
            """
            MATCH (c:Concept), (ch:Chapter {id:'ch_force_pressure'})
            WHERE c.id IN ['con_force','con_pressure']
            MERGE (c)-[:PART_OF]->(ch)
            """
        )

        # SubConcepts + PART_OF Concept
        for concept_id, sc in SUBCONCEPTS:
            await session.run(
                "MERGE (n:SubConcept {id:$id}) SET n += $props",
                id=sc["id"], props=sc,
            )
            await session.run(
                """
                MATCH (sc:SubConcept {id:$sc_id}), (c:Concept {id:$c_id})
                MERGE (sc)-[:PART_OF]->(c)
                """,
                sc_id=sc["id"], c_id=concept_id,
            )

        # ── CHAPTER_LINK edges (cross-chapter conceptual bridges) ────────────
        # Delete stale links from this chapter first, then recreate
        await session.run(
            """
            MATCH (a:Chapter {id:'ch_force_pressure'})-[r:CHAPTER_LINK]->()
            DELETE r
            """
        )
        for from_id, to_id, label in CHAPTER_LINKS:
            await session.run(
                """
                MATCH (a:Chapter {id:$from_id}), (b:Chapter {id:$to_id})
                MERGE (a)-[:CHAPTER_LINK {label:$label}]->(b)
                """,
                from_id=from_id, to_id=to_id, label=label,
            )

        # ── Reset PREREQUISITE edges for this chapter (clean slate) ──────────
        # Delete old edges so stale/incorrect ones don't linger on re-seed
        await session.run(
            """
            MATCH (a:SubConcept)-[r:PREREQUISITE]->(b:SubConcept)
            WHERE (a)-[:PART_OF]->(:Concept)-[:PART_OF]->(:Chapter {id:'ch_force_pressure'})
            DELETE r
            """
        )
        for from_id, to_id in PREREQUISITES:
            await session.run(
                """
                MATCH (a:SubConcept {id:$from_id}), (b:SubConcept {id:$to_id})
                MERGE (a)-[:PREREQUISITE]->(b)
                """,
                from_id=from_id, to_id=to_id,
            )

        # Abilities
        for ab in ABILITIES:
            await session.run(
                "MERGE (n:Ability {id:$id}) SET n += $props",
                id=ab["id"], props=ab,
            )
        for sc_id, ab_id in BUILDS_EDGES:
            await session.run(
                """
                MATCH (sc:SubConcept {id:$sc_id}), (ab:Ability {id:$ab_id})
                MERGE (sc)-[:BUILDS]->(ab)
                """,
                sc_id=sc_id, ab_id=ab_id,
            )

        # Career graph
        for cf in CAREER_FAMILIES:
            await session.run(
                "MERGE (n:CareerFamily {id:$id}) SET n += $props",
                id=cf["id"], props=cf,
            )
        for ab_id, cf_id in MAPS_TO_EDGES:
            await session.run(
                """
                MATCH (ab:Ability {id:$ab_id}), (cf:CareerFamily {id:$cf_id})
                MERGE (ab)-[:MAPS_TO]->(cf)
                """,
                ab_id=ab_id, cf_id=cf_id,
            )
        for cp in CAREER_PATHS:
            await session.run(
                "MERGE (n:CareerPath {id:$id}) SET n += $props",
                id=cp["id"], props={"id": cp["id"], "name": cp["name"]},
            )
            await session.run(
                """
                MATCH (cf:CareerFamily {id:$cf_id}), (cp:CareerPath {id:$cp_id})
                MERGE (cf)-[:LEADS_TO]->(cp)
                """,
                cf_id=cp["family"], cp_id=cp["id"],
            )

        # Learning Styles
        for ls in LEARNING_STYLES:
            await session.run(
                "MERGE (n:LearningStyle {id:$id}) SET n += $props",
                id=ls["id"], props=ls,
            )

    print("✅ Seed data loaded — Force & Pressure (10 nodes, map_x/map_y set)")


async def main():
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    await create_constraints(driver)
    await seed(driver)
    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
