"""
Neo4j Knowledge Graph Schema
=============================
Navigation layer (student-visible GPS map):
    Chapter → Concept → SubConcept

Derived layer (invisible, powers Career Compass):
    SubConcept -[:BUILDS]-> Ability -[:MAPS_TO]-> CareerFamily -[:LEADS_TO]-> CareerPath

VARK layer:
    LearningStyle node — inferred per student, updated each session

Run create_constraints() once when setting up a fresh Neo4j instance.
"""

from neo4j import AsyncDriver


CONSTRAINTS = [
    # Uniqueness constraints (also create indexes automatically)
    "CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (n:Chapter) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT subconcept_id IF NOT EXISTS FOR (n:SubConcept) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ability_id IF NOT EXISTS FOR (n:Ability) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT careerfamily_id IF NOT EXISTS FOR (n:CareerFamily) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT careerpath_id IF NOT EXISTS FOR (n:CareerPath) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT learningstyle_id IF NOT EXISTS FOR (n:LearningStyle) REQUIRE n.id IS UNIQUE",
]


async def create_constraints(driver: AsyncDriver) -> None:
    """Apply schema constraints — idempotent, safe to run on every boot."""
    async with driver.session() as session:
        for cypher in CONSTRAINTS:
            await session.run(cypher)
    print("✅ Neo4j constraints applied")


# ---------------------------------------------------------------------------
# Node property reference (documentation — not enforced by Neo4j)
# ---------------------------------------------------------------------------
# Chapter
#   id: str          e.g. "ch_force_pressure"
#   name: str        e.g. "Force & Pressure"
#   grade: int       8 | 9 | 10
#   subject: str     "Science" | "Maths"
#   ncert_chapter_num: int
#
# Concept
#   id: str          e.g. "con_force"
#   name: str        e.g. "Force"
#   weight: float    importance within chapter (sum = 1.0 per chapter)
#
# SubConcept
#   id: str          e.g. "sc_muscular_force"
#   name: str        e.g. "Muscular Force"
#   bloom_target: str  "Remember"|"Understand"|"Apply"|"Analyse"|"Evaluate"|"Create"
#   vark_hint: str   "V"|"A"|"R"|"K"  (primary modality for content)
#
# Ability
#   id: str          e.g. "ab_analytical_reasoning"
#   name: str        e.g. "Analytical Reasoning"
#   description: str
#
# CareerFamily
#   id: str          e.g. "cf_engineering"
#   name: str        e.g. "Engineering"
#
# CareerPath
#   id: str          e.g. "cp_mechanical_engineer"
#   name: str        e.g. "Mechanical Engineer"
#   description: str
#
# LearningStyle
#   id: str          "V"|"A"|"R"|"K"
#   name: str        "Visual"|"Auditory"|"Read/Write"|"Kinesthetic"

# ---------------------------------------------------------------------------
# Edge reference
# ---------------------------------------------------------------------------
# [:PART_OF]        SubConcept → Concept,  Concept → Chapter
# [:PREREQUISITE]   SubConcept → SubConcept  (must master before unlocking)
# [:REINFORCES]     SubConcept → SubConcept  (cross-concept reinforcement)
# [:UNLOCKS]        Chapter → Chapter  (chapter gate)
# [:BUILDS]         SubConcept → Ability  (mastering sc contributes to ability)
# [:MAPS_TO]        Ability → CareerFamily
# [:LEADS_TO]       CareerFamily → CareerPath
