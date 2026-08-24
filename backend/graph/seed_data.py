"""
Seed Data — Grade 8 Science: Force & Pressure
=============================================
Run this ONCE after setting up Neo4j Aura to populate the initial graph.

Usage:
    python -m backend.graph.seed_data

Graph loaded:
    1 Chapter  →  2 Concepts  →  8 SubConcepts
    8 SubConcepts -[:BUILDS]-> 3 Abilities
    3 Abilities   -[:MAPS_TO]-> 2 CareerFamilies
    2 CareerFamilies -[:LEADS_TO]-> 4 CareerPaths
    PREREQUISITE edges between SubConcepts
"""

import asyncio
from neo4j import AsyncGraphDatabase
from backend.config.settings import get_settings
from backend.graph.schema import create_constraints


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

CHAPTERS = [
    {
        "id": "ch_force_pressure",
        "name": "Force & Pressure",
        "grade": 8,
        "subject": "Science",
        "ncert_chapter_num": 11,
    }
]

CONCEPTS = [
    {"id": "con_force",    "name": "Force",    "weight": 0.60},
    {"id": "con_pressure", "name": "Pressure", "weight": 0.40},
]

# (concept_id, subconcept)
SUBCONCEPTS = [
    # Force concept
    ("con_force", {"id": "sc_contact_force",    "name": "Contact Force",    "bloom_target": "Understand", "vark_hint": "K"}),
    ("con_force", {"id": "sc_non_contact",      "name": "Non-Contact Force","bloom_target": "Understand", "vark_hint": "V"}),
    ("con_force", {"id": "sc_muscular_force",   "name": "Muscular Force",   "bloom_target": "Apply",      "vark_hint": "K"}),
    ("con_force", {"id": "sc_normal_force",     "name": "Normal Force",     "bloom_target": "Apply",      "vark_hint": "V"}),
    ("con_force", {"id": "sc_friction",         "name": "Friction",         "bloom_target": "Analyse",    "vark_hint": "K"}),
    # Pressure concept
    ("con_pressure", {"id": "sc_pressure_def",  "name": "Pressure Definition","bloom_target": "Understand","vark_hint": "R"}),
    ("con_pressure", {"id": "sc_liquid_pressure","name": "Liquid Pressure",   "bloom_target": "Apply",     "vark_hint": "V"}),
    ("con_pressure", {"id": "sc_atm_pressure",  "name": "Atmospheric Pressure","bloom_target": "Analyse",  "vark_hint": "R"}),
]

# PREREQUISITE edges: (from_id, to_id) — must master 'from' before unlocking 'to'
PREREQUISITES = [
    ("sc_contact_force",  "sc_muscular_force"),
    ("sc_contact_force",  "sc_normal_force"),
    ("sc_non_contact",    "sc_friction"),       # magnetic / gravity context
    ("sc_muscular_force", "sc_friction"),
    ("sc_normal_force",   "sc_friction"),
    ("sc_pressure_def",   "sc_liquid_pressure"),
    ("sc_liquid_pressure","sc_atm_pressure"),
]

ABILITIES = [
    {"id": "ab_analytical_reasoning", "name": "Analytical Reasoning",
     "description": "Break complex problems into components and reason systematically"},
    {"id": "ab_spatial_reasoning",    "name": "Spatial Reasoning",
     "description": "Visualise forces, vectors, and 3-D structures"},
    {"id": "ab_quantitative_thinking","name": "Quantitative Thinking",
     "description": "Apply formulae and work with numerical relationships"},
]

# (subconcept_id, ability_id)
BUILDS_EDGES = [
    ("sc_normal_force",    "ab_analytical_reasoning"),
    ("sc_friction",        "ab_analytical_reasoning"),
    ("sc_atm_pressure",    "ab_analytical_reasoning"),
    ("sc_contact_force",   "ab_spatial_reasoning"),
    ("sc_muscular_force",  "ab_spatial_reasoning"),
    ("sc_liquid_pressure", "ab_spatial_reasoning"),
    ("sc_pressure_def",    "ab_quantitative_thinking"),
    ("sc_atm_pressure",    "ab_quantitative_thinking"),
]

CAREER_FAMILIES = [
    {"id": "cf_engineering", "name": "Engineering"},
    {"id": "cf_science",     "name": "Pure Science"},
]

# (ability_id, career_family_id)
MAPS_TO_EDGES = [
    ("ab_analytical_reasoning", "cf_engineering"),
    ("ab_spatial_reasoning",    "cf_engineering"),
    ("ab_quantitative_thinking","cf_engineering"),
    ("ab_analytical_reasoning", "cf_science"),
    ("ab_quantitative_thinking","cf_science"),
]

CAREER_PATHS = [
    {"id": "cp_mechanical_engineer",  "name": "Mechanical Engineer",   "family": "cf_engineering"},
    {"id": "cp_civil_engineer",       "name": "Civil Engineer",         "family": "cf_engineering"},
    {"id": "cp_physicist",            "name": "Physicist",              "family": "cf_science"},
    {"id": "cp_research_scientist",   "name": "Research Scientist",     "family": "cf_science"},
]

LEARNING_STYLES = [
    {"id": "V", "name": "Visual"},
    {"id": "A", "name": "Auditory"},
    {"id": "R", "name": "Read/Write"},
    {"id": "K", "name": "Kinesthetic"},
]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

async def seed(driver):
    async with driver.session() as session:

        # Chapters
        for ch in CHAPTERS:
            await session.run(
                "MERGE (n:Chapter {id:$id}) SET n += $props",
                id=ch["id"], props=ch
            )

        # Concepts + PART_OF Chapter
        for c in CONCEPTS:
            await session.run(
                "MERGE (n:Concept {id:$id}) SET n += $props",
                id=c["id"], props=c
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
                id=sc["id"], props=sc
            )
            await session.run(
                """
                MATCH (sc:SubConcept {id:$sc_id}), (c:Concept {id:$c_id})
                MERGE (sc)-[:PART_OF]->(c)
                """,
                sc_id=sc["id"], c_id=concept_id
            )

        # PREREQUISITE edges
        for from_id, to_id in PREREQUISITES:
            await session.run(
                """
                MATCH (a:SubConcept {id:$from_id}), (b:SubConcept {id:$to_id})
                MERGE (a)-[:PREREQUISITE]->(b)
                """,
                from_id=from_id, to_id=to_id
            )

        # Abilities
        for ab in ABILITIES:
            await session.run(
                "MERGE (n:Ability {id:$id}) SET n += $props",
                id=ab["id"], props=ab
            )

        # BUILDS edges
        for sc_id, ab_id in BUILDS_EDGES:
            await session.run(
                """
                MATCH (sc:SubConcept {id:$sc_id}), (ab:Ability {id:$ab_id})
                MERGE (sc)-[:BUILDS]->(ab)
                """,
                sc_id=sc_id, ab_id=ab_id
            )

        # CareerFamilies
        for cf in CAREER_FAMILIES:
            await session.run(
                "MERGE (n:CareerFamily {id:$id}) SET n += $props",
                id=cf["id"], props=cf
            )

        # MAPS_TO edges
        for ab_id, cf_id in MAPS_TO_EDGES:
            await session.run(
                """
                MATCH (ab:Ability {id:$ab_id}), (cf:CareerFamily {id:$cf_id})
                MERGE (ab)-[:MAPS_TO]->(cf)
                """,
                ab_id=ab_id, cf_id=cf_id
            )

        # CareerPaths + LEADS_TO
        for cp in CAREER_PATHS:
            await session.run(
                "MERGE (n:CareerPath {id:$id}) SET n += $props",
                id=cp["id"], props={"id": cp["id"], "name": cp["name"]}
            )
            await session.run(
                """
                MATCH (cf:CareerFamily {id:$cf_id}), (cp:CareerPath {id:$cp_id})
                MERGE (cf)-[:LEADS_TO]->(cp)
                """,
                cf_id=cp["family"], cp_id=cp["id"]
            )

        # LearningStyles
        for ls in LEARNING_STYLES:
            await session.run(
                "MERGE (n:LearningStyle {id:$id}) SET n += $props",
                id=ls["id"], props=ls
            )

    print("✅ Seed data loaded — Force & Pressure graph ready")


async def main():
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    await create_constraints(driver)
    await seed(driver)
    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
