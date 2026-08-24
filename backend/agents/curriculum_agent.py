"""
Curriculum Agent — invisible planner, never student-facing
==========================================================
Responsibilities:
- Decide next SubConcept after student masters current one
- Infer VARK learning style from session evidence (Bayesian update)
- Check Career Compass trigger conditions (90 sessions, Analyse level, etc.)
- Schedule spaced repetition reviews

TODO (Day 5): Implement full agent loop with MCP tools
"""

# Career Compass trigger conditions
CAREER_COMPASS_TRIGGERS = {
    "min_sessions": 90,
    "min_subjects": 2,
    "min_bloom_level": "Analyse",
    "min_style_confidence": 0.75,
}

CURRICULUM_SYSTEM_PROMPT = """
You are the Curriculum Agent for LearnGPS — an invisible planner that operates
silently behind the scenes. You are never shown to the student.

Your job each session:
1. Review the student's mastered SubConcepts and Bloom level
2. Decide the optimal next SubConcept using the Neo4j traversal algorithm
3. Update VARK style confidence based on session evidence
4. Check if Career Compass trigger conditions are met
5. Schedule spaced repetition for SubConcepts at risk of forgetting

INPUT (from Supabase + Neo4j):
- student_id: {student_id}
- mastered_subconcepts: {mastered_subconcepts}
- session_count: {session_count}
- vark_state: {vark_state}
- bloom_peak: {bloom_peak}

OUTPUT: JSON decision object for the Tutor Agent to consume.
""".strip()
