"""
MCP Server: learning-tools
===========================
Exposed to the Tutor Agent (Gyaan) only.
Tools the student-facing agent needs during a session.

TODO (Day 5): Implement with Claude Agent SDK MCP server pattern.

Tools planned:
- get_subconcept_content(sc_id, vark_style) → explanation + activity + questions
- evaluate_answer(question, student_answer, sc_id) → {correct, feedback, xp}
- get_hint(sc_id, attempt_number) → hint string (escalates with each attempt)
- award_xp(student_id, amount, reason) → new total XP
- get_student_context(student_id) → last session note, VARK style, streak
"""

LEARNING_TOOLS_SCHEMA = [
    {
        "name": "get_subconcept_content",
        "description": "Retrieve explanation, activity, and quiz questions for a SubConcept, adapted to the student's VARK learning style",
        "input_schema": {
            "type": "object",
            "properties": {
                "sc_id": {"type": "string", "description": "SubConcept ID from Neo4j"},
                "vark_style": {"type": "string", "enum": ["V", "A", "R", "K"]},
            },
            "required": ["sc_id", "vark_style"],
        },
    },
    {
        "name": "evaluate_answer",
        "description": "Evaluate a student's answer and return correctness, feedback, and XP earned",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "student_answer": {"type": "string"},
                "sc_id": {"type": "string"},
            },
            "required": ["question", "student_answer", "sc_id"],
        },
    },
    {
        "name": "get_hint",
        "description": "Get an escalating hint for a SubConcept question",
        "input_schema": {
            "type": "object",
            "properties": {
                "sc_id": {"type": "string"},
                "attempt_number": {"type": "integer", "minimum": 1, "maximum": 3},
            },
            "required": ["sc_id", "attempt_number"],
        },
    },
]
