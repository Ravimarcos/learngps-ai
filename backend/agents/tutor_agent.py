"""
Tutor Agent — Gyaan
====================
Student-facing conversational AI. Uses Claude (Haiku for speed)
with a Socratic teaching style.

Flow per turn:
  1. Build context (GPS position, VARK style, last session note)
  2. Fetch relevant questions from question bank
  3. Call Claude with system prompt + conversation history
  4. Return response + any XP events

MAX_TOOL_ROUNDS = 3 (enforced by config)
"""

import anthropic
import asyncio
from backend.config.models import get_model, TaskType
from backend.config.settings import get_settings
from backend.content.question_bank import get_questions_for_subconcept, get_activities_for_subconcept
from backend.rag.retriever import retrieve, format_for_prompt

settings = get_settings()
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ── System prompt ──────────────────────────────────────────────────────────

def build_system_prompt(context: dict) -> str:
    """Build Gyaan's system prompt from student context."""

    student_name   = context.get("student_name", "Student")
    vark_style     = context.get("vark_style", "unknown")
    bloom_level    = context.get("bloom_level", "Remember")
    subconcept     = context.get("subconcept_name", "this topic")
    chapter        = context.get("chapter_name", "Science")
    last_note      = context.get("last_session_note", "")
    questions_ctx  = context.get("questions_context", "")
    rag_ctx        = context.get("rag_context", "")

    vark_instructions = {
        "V": "Use diagrams described in words, spatial metaphors, and visual comparisons. Say things like 'picture this...' or 'imagine a diagram where...'",
        "A": "Use verbal explanations, rhythm, and discussion. Ask the student to explain back to you out loud.",
        "R": "Use definitions, written lists, and step-by-step text explanations. Reference textbook language.",
        "K": "Use hands-on examples, physical experiments, and real-world activities. Ask 'try this at home...'",
    }
    vark_tip = vark_instructions.get(vark_style, "Adapt to what seems to work for this student.")

    memory_line = f"\nYou remember from last session: {last_note}" if last_note else ""

    return f"""You are Gyaan, a warm and encouraging AI tutor for Indian Class 8-10 students.
You are tutoring {student_name} right now.{memory_line}

CURRENT FOCUS:
- Chapter: {chapter}
- Topic (SubConcept): {subconcept}
- Student's current Bloom level: {bloom_level}
- Target: help them reach the NEXT Bloom level

TEACHING STYLE:
- NEVER give the answer directly — ask guiding questions (Socratic method)
- Use relatable Indian examples: cricket, chapati, auto-rickshaw, dosa, chai, trains
- {vark_tip}
- Celebrate correct reasoning with genuine enthusiasm ("That's it! You just got it!")
- When student is wrong, don't say "wrong" — say "interesting, but what if..."
- Use short sentences. Max 3-4 sentences per response.
- End every response with ONE question to keep the student thinking

BLOOM LEVEL GUIDE (push student to next level):
- Remember → ask them to recall a definition
- Understand → ask them to explain in their own words
- Apply → give a scenario, ask them to solve it
- Analyse → ask them to compare two forces or find the odd one out
- Evaluate → ask them to judge which approach is better and why

AVAILABLE QUESTIONS FOR THIS TOPIC:
{questions_ctx}

{rag_ctx}

RULES:
- Keep responses SHORT (3-5 sentences max)
- One question per response — never multiple questions at once
- If student is stuck after 3 attempts → offer a hint, then the next step
- If student answers correctly → say so clearly, award XP in response
- Never reveal you are an AI unless directly asked
- Respond in English unless student writes in another language
""".strip()


# ── Main chat function ────────────────────────────────────────────────────

async def chat(
    student_name: str,
    student_message: str,
    conversation_history: list[dict],
    subconcept_id: str,
    subconcept_name: str,
    chapter_name: str,
    bloom_level: str = "Remember",
    vark_style: str = "K",
    last_session_note: str = "",
) -> dict:
    """
    One turn of Gyaan's conversation.

    Returns:
        {
            "reply": str,
            "xp_earned": int,
            "bloom_advance": bool,
        }
    """

    # Fetch relevant questions for context
    questions = get_questions_for_subconcept(subconcept_id, bloom_level, limit=2)
    questions_ctx = ""
    if questions:
        q = questions[0]
        questions_ctx = (
            f"Sample question: {q['question']}\n"
            f"Options: {q.get('options', {})}\n"
            f"Answer: {q['answer']} — {q.get('explanation', '')}"
        )
    else:
        questions_ctx = f"No pre-loaded questions for {subconcept_name}. Generate one appropriate for {bloom_level} level."

    # RAG — retrieve relevant NCERT chunks for this subconcept + student message
    rag_chunks  = await retrieve(
        query          = student_message or subconcept_name,
        subconcept_id  = subconcept_id,
        k              = 3,
    )
    rag_context = format_for_prompt(rag_chunks)

    # Build context dict
    context = {
        "student_name":      student_name,
        "vark_style":        vark_style,
        "bloom_level":       bloom_level,
        "subconcept_name":   subconcept_name,
        "chapter_name":      chapter_name,
        "last_session_note": last_session_note,
        "questions_context": questions_ctx,
        "rag_context":       rag_context,
    }

    system_prompt = build_system_prompt(context)

    # Build messages list
    messages = conversation_history + [
        {"role": "user", "content": student_message}
    ]

    # Call Claude Haiku — run in thread so it doesn't block the async event loop
    response = await asyncio.to_thread(
        client.messages.create,
        model=get_model(TaskType.DIALOGUE),
        max_tokens=300,
        system=system_prompt,
        messages=messages,
    )

    reply = response.content[0].text

    # Simple XP detection (upgrade to LLM-as-Judge on Day 10)
    xp_earned = 0
    bloom_advance = False
    lower_reply = reply.lower()
    if any(word in lower_reply for word in ["correct", "exactly", "perfect", "well done", "that's it", "you got it"]):
        xp_earned = 20
    elif any(word in lower_reply for word in ["good", "right", "yes", "great"]):
        xp_earned = 10

    return {
        "reply":         reply,
        "xp_earned":     xp_earned,
        "bloom_advance": bloom_advance,
        "model_used":    get_model(TaskType.DIALOGUE),
    }
