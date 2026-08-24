"""
Model Router — maps task types to the right Claude model.
Haiku for fast dialogue, Sonnet for planning and curriculum decisions.
"""

from enum import Enum

class TaskType(str, Enum):
    DIALOGUE = "dialogue"          # Gyaan chat responses
    HINT = "hint"                  # Hint generation
    QUIZ_EVAL = "quiz_eval"        # Evaluate student quiz answer
    CURRICULUM = "curriculum"      # Curriculum planning (Curriculum Agent)
    VARK_INFER = "vark_infer"      # VARK style inference
    CAREER_MAP = "career_map"      # Career path recommendation
    JUDGE = "judge"                # LLM-as-Judge scoring
    SUMMARY = "summary"           # Session summary


MODEL_ROUTER: dict[TaskType, str] = {
    TaskType.DIALOGUE:   "claude-haiku-4-5-20251001",   # Fast, cheap, student-facing
    TaskType.HINT:       "claude-haiku-4-5-20251001",
    TaskType.QUIZ_EVAL:  "claude-haiku-4-5-20251001",
    TaskType.JUDGE:      "claude-haiku-4-5-20251001",   # Silent scorer
    TaskType.CURRICULUM: "claude-sonnet-5",             # Heavier reasoning
    TaskType.VARK_INFER: "claude-sonnet-5",
    TaskType.CAREER_MAP: "claude-sonnet-5",
    TaskType.SUMMARY:    "claude-haiku-4-5-20251001",
}


def get_model(task: TaskType) -> str:
    """Return the model string for a given task type."""
    return MODEL_ROUTER[task]
