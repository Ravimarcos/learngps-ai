"""
Tutor Agent — Gyaan (Day 12 upgrade)
======================================
Full pedagogical intelligence upgrade based on Learning GPS rules:

1. Hint Ladder       — 4 levels: guide → hint → worked example → full explanation
2. Question Format   — MCQ for Remember/Understand/Apply; Open-ended for Analyse/Evaluate/Create
3. Misconception     — name it, give analogy, ask student to restate before moving on
4. Activity Trigger  — hands-on challenge once per Apply+ Bloom level
5. Video/Sim Links   — PhET + YouTube, only when student asks
6. Learning Modes    — learning | revision | quick_test | concept_clarity | exam_prep | feynman
7. Mastery Criteria  — Bloom≥Apply + confidence≥0.8 + 2 consecutive correct + self-explained
"""

import anthropic
import asyncio
from backend.config.models import get_model, TaskType
from backend.config.settings import get_settings
from backend.content.question_bank import get_questions_for_subconcept, get_bloom_style_guide
from backend.rag.retriever import retrieve, format_for_prompt

settings = get_settings()
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

BLOOM_ORDER = ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"]

# ── MCQ vs Open-ended rule ─────────────────────────────────────────────────────
MCQ_BLOOMS = {"Remember", "Understand", "Apply"}


# ── Video/sim resources by topic keyword ──────────────────────────────────────
RESOURCES = {
    "pressure": [
        {"type": "simulation", "title": "Under Pressure (PhET)",
         "url": "https://phet.colorado.edu/sims/html/under-pressure/latest/under-pressure_all.html"},
        {"type": "video", "title": "Force & Pressure Concepts",
         "url": "https://www.youtube.com/watch?v=30KW69TViHI"},
    ],
    "atmospheric": [
        {"type": "video", "title": "Atmospheric Pressure Explained",
         "url": "https://www.youtube.com/watch?v=63jnANXFsqc"},
    ],
    "friction": [
        {"type": "simulation", "title": "Forces & Motion Basics (PhET)",
         "url": "https://phet.colorado.edu/en/simulations/forces-and-motion-basics"},
    ],
    "gravity": [
        {"type": "simulation", "title": "Gravity & Orbits (PhET)",
         "url": "https://phet.colorado.edu/en/simulations/gravity-and-orbits"},
    ],
    "force": [
        {"type": "simulation", "title": "Forces & Motion Basics (PhET)",
         "url": "https://phet.colorado.edu/en/simulations/forces-and-motion-basics"},
        {"type": "video", "title": "Force & Pressure Concepts",
         "url": "https://www.youtube.com/watch?v=30KW69TViHI"},
    ],
}


def _get_resources(subconcept_name: str) -> list[dict]:
    """Return relevant video/sim resources for a subconcept."""
    name_lower = subconcept_name.lower()
    for keyword, resources in RESOURCES.items():
        if keyword in name_lower:
            return resources
    return RESOURCES["force"]  # default


def _hint_guidance(hint_count: int) -> str:
    if hint_count == 0:
        return (
            "First attempt — if the student is wrong, ask a GUIDING QUESTION only. "
            "Do NOT reveal the answer."
        )
    elif hint_count == 1:
        return (
            "Student has failed once. Give a SMALL HINT or real-world analogy "
            "(e.g. 'Think about sliding a book on a rough vs smooth surface...'). "
            "Still do NOT give the answer."
        )
    elif hint_count == 2:
        return (
            "Student has failed twice. Show a WORKED EXAMPLE in this format:\n"
            "  📖 **Worked Example** — [a similar question]\n"
            "  **Solution:** [step-by-step]\n"
            "Then ask: 'Now try the original question again.' Use your own knowledge — no tool call."
        )
    else:
        return (
            "Student has failed 3+ times. Give the FULL EXPLANATION step by step. "
            "Then ask: 'Can you restate the KEY IDEA in your own words?' "
            "Only move on once they restate it correctly."
        )


def _mode_block(mode: str) -> str:
    modes = {
        "revision": """
📚 REVISION MODE — Student wants to revise previously learned topics.
- Start with their weakest concept (lowest confidence).
- Ask 2-3 questions per concept, then move to the next weak one.
- Keep it brisk: after each concept say "✅ [Topic] — looking solid! Moving on."
- Use spaced-repetition pacing.
""",
        "quick_test": """
⚡ QUICK TEST MODE — Rapid-fire, 10 MCQ questions, no teaching, no hints.
- One line of feedback per answer: ✅ Correct! or ❌ Wrong — answer is [X].
- Immediately ask the next question after feedback.
- Vary concepts: don't repeat same topic more than twice in a row.
- After Q10 show scorecard: "📊 Score: X/10 | Bloom reached: [level] | Strong: [topics] | Weak: [topics]"
""",
        "concept_clarity": """
💡 CONCEPT CLARITY MODE — Student is confused, needs deep explanation.
For each concept use this structure:
  1. Simple definition (1 sentence, plain language)
  2. Real-life analogy ("It's like...")
  3. Concrete example from daily life (Indian context: cricket, chapati, auto-rickshaw)
  4. Visual description ("Imagine you can see...")
  5. One MCQ to confirm understanding
""",
        "exam_prep": """
🎯 EXAM PREP MODE — Hard questions only, strict CBSE marking.
Question rotation (in order):
  1. Assertion-Reason (A is true, R is true and R explains A — pick a/b/c/d)
  2. Numerical (calculate pressure / force / area given values)
  3. Match the Column
  4. HOTS (Higher Order Thinking — scenario-based, no options)
No hints unless student has made 3 attempts. Show marks per question.
Running total: "📊 Score: X/Y marks"
""",
        "feynman": """
🗣️ FEYNMAN (EXPLAIN IT BACK) MODE — Student explains; Gyaan evaluates.
  Step 1: Name the concept ("Explain Friction to me as if I'm 10 years old.")
  Step 2: Wait for their explanation. Do NOT interrupt.
  Step 3: Evaluate:
    ✅ What they got right (be specific)
    ❌ What was missing or incorrect
    🔁 Ask them to try again on the weak parts only
  Step 4: "Feynman Score: X/5" with one-line summary.
  Step 5: Ask if they want to explain another concept.
Pure dialogue — NO MCQ in this mode.
""",
    }
    return modes.get(mode, "")


def _activity_trigger(bloom_level: str, already_shown: bool) -> str:
    """Return a one-sentence hands-on challenge for Apply+ Bloom levels (fires once per level)."""
    if bloom_level not in ("Apply", "Analyse", "Evaluate", "Create") or already_shown:
        return ""
    challenges = {
        "Apply": (
            "🎯 **Try this:** Push a heavy schoolbag, then an empty one — "
            "notice how much more force you need? That's Newton's law in action!"
        ),
        "Analyse": (
            "🎯 **Compare this:** Press your finger on a table, then on a pin — "
            "same force, but the pin hurts more. Why? Think about area and pressure."
        ),
        "Evaluate": (
            "🎯 **Judge this:** A camel walks on sand easily, but a person in heels sinks — "
            "which design is better for sandy terrain and why?"
        ),
        "Create": (
            "🎯 **Design this:** How would you design a shoe sole for walking on snow? "
            "Think about force, area, and pressure — sketch your idea mentally."
        ),
    }
    return challenges.get(bloom_level, "")


# ── System prompt ──────────────────────────────────────────────────────────────

def build_system_prompt(context: dict) -> str:
    student_name   = context.get("student_name", "Student")
    vark_style     = context.get("vark_style", "K")
    bloom_level    = context.get("bloom_level", "Remember")
    subconcept     = context.get("subconcept_name", "this topic")
    chapter        = context.get("chapter_name", "Force & Pressure")
    last_note      = context.get("last_session_note", "")
    questions_ctx  = context.get("questions_context", "")
    rag_ctx        = context.get("rag_context", "")
    hint_count     = context.get("hint_count", 0)
    mode           = context.get("mode", "learning")
    activity_shown = context.get("activity_shown", False)
    subconcept_id  = context.get("subconcept_id", "")

    vark_instructions = {
        "V": "Use diagrams described in words, spatial metaphors. Say 'picture this...' or 'imagine a diagram where...'",
        "A": "Use verbal explanations and discussion. Ask student to explain back out loud.",
        "R": "Use definitions, written lists, step-by-step text. Reference textbook language.",
        "K": "Use hands-on examples, physical experiments, real-world activities. Say 'try this at home...'",
    }
    vark_tip = vark_instructions.get(vark_style, "Adapt to what works for this student.")

    use_mcq = bloom_level in MCQ_BLOOMS
    question_format = (
        "MCQ with 4 options (A/B/C/D). Wrong options MUST be real misconceptions students commonly hold. "
        "End with: *Please type A, B, C, or D*"
        if use_mcq else
        "Open-ended scenario question — no options. Ask student to explain their reasoning."
    )

    hint_block   = _hint_guidance(hint_count)
    mode_block   = _mode_block(mode)
    activity_tip = _activity_trigger(bloom_level, activity_shown)

    # Resources for this subconcept
    resources = _get_resources(subconcept)
    resource_lines = "\n".join(
        f"  {'🔬' if r['type']=='simulation' else '▶️'} [{r['title']}]({r['url']})"
        for r in resources
    )

    memory_line = f"\nYou remember from last session: {last_note}" if last_note else ""

    prompt = f"""You are Gyaan, a warm and encouraging AI tutor for Indian Class 8-10 students.
You are tutoring {student_name} right now.{memory_line}

CURRENT FOCUS:
- Chapter: {chapter}
- Topic: {subconcept}
- Student's Bloom level: {bloom_level}
- Target: help them reach the NEXT Bloom level

TEACHING STYLE:
- NEVER give the answer directly — use the Socratic method
- Use relatable Indian examples: cricket bat, chapati, auto-rickshaw, dosa, chai, trains
- {vark_tip}
- Celebrate correct reasoning with genuine enthusiasm
- When student is wrong, say "interesting, but what if..." — never say "wrong"
- Max 4 sentences per response
- End every response with ONE question to keep the student thinking

QUESTION FORMAT (follow this every time you ask a question):
- Format: {question_format}
- Always show the Bloom level tag before the question: 🟢 L1 (Remember) · 🔵 L2 (Understand) · 🟡 L3 (Apply) · 🟠 L4 (Analyse) · 🔴 L5 (Evaluate)
- If question is from NCERT Exemplar, add ⭐ after the level tag
{mode_block}
HINT LADDER (current hint_count = {hint_count}):
{hint_block}

MISCONCEPTION PROTOCOL (when student is wrong):
1. Name the misconception clearly: "Many students think [X] — but actually [Y]"
2. Give a simple analogy to make the correction concrete
3. Ask the student to restate the correct idea in THEIR OWN WORDS
4. Only ask the next question AFTER they restate it correctly
5. Repeat the SAME question — do NOT move to a new question after a wrong answer

{f'ACTIVITY CHALLENGE (mention this once in your next response):{chr(10)}{activity_tip}' if activity_tip else ''}

VIDEO & SIMULATION RESOURCES (share ONLY when student explicitly asks for a video or simulation):
{resource_lines}
Format: 🔬 **Try this sim:** [title](url)  or  ▶️ **Watch this:** [title](url)

MASTERY CRITERIA (all 5 needed before moving to next topic):
✅ Bloom level ≥ Apply
✅ 2 consecutive correct answers
✅ No unresolved misconception
✅ Student can explain it in their own words

AVAILABLE QUESTIONS FOR THIS TOPIC (use as inspiration — do NOT repeat the same question twice):
{questions_ctx}

NCERT SOURCE CONTENT (use this to generate FRESH questions when bank is exhausted):
{rag_ctx}

QUESTION GENERATION RULE: If you have asked a question from the bank before in this session, generate a NEW one using the NCERT content above. Vary the format: mix MCQ, fill-in-the-blank, assertion-reason, case-based, and short-answer across turns.

RULES:
- Short responses only (3-5 sentences max)
- One question per response — never ask multiple questions at once
- After 3 failed attempts → give full explanation, ask them to restate key idea
- If student asks for a video/sim → share from the resources above
- STRICT TOPIC RESTRICTION: You can ONLY teach topics from "{chapter}". If asked about ANY other subject or chapter (Simple Machines, Heat, Light, Sound, etc.) say: "I'm your guide for {chapter} right now! Let's master this first — I don't have study material for other chapters yet. Shall we continue?" Do NOT explain or teach any other topic.
- Never reveal you are an AI unless directly asked
""".strip()

    return prompt


# ── Main chat function ────────────────────────────────────────────────────────

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
    hint_count: int = 0,
    mode: str = "learning",
    activity_shown: bool = False,
) -> dict:
    """
    One turn of Gyaan's conversation.

    Returns:
        {
            "reply": str,
            "xp_earned": int,
            "bloom_advance": bool,
            "hint_count": int,       ← incremented on wrong, reset on correct
            "activity_shown": bool,  ← True once the activity challenge has fired
        }
    """

    # Fetch relevant questions for context — pass 5 so Claude picks a different one each turn
    questions = get_questions_for_subconcept(subconcept_id, bloom_level, limit=5)
    style_guide = get_bloom_style_guide(bloom_level)

    if questions:
        lines = []
        for q in questions:
            # Handle different question formats (regular, case_based, ncert_section)
            question_text = q.get("question") or q.get("title") or ""
            if not question_text:
                continue
            # For case_based, append context and sub-questions
            if q.get("context"):
                question_text = f"{question_text}\nContext: {q['context']}"
            if q.get("questions"):  # case_based sub-questions
                sub_qs = q["questions"]
                question_text += "\n" + "\n".join(
                    f"  ({i+1}) {sq.get('q', '')} — Ans: {sq.get('answer', '')}"
                    for i, sq in enumerate(sub_qs[:2])  # show first 2 sub-questions
                )
            opts = q.get("options", {})
            opt_str = "  ".join(f"{k}) {v}" for k, v in opts.items()) if opts else ""
            exemplar_tag = " ⭐ NCERT Exemplar" if q.get("ncert_exemplar") else ""
            lines.append(
                f"[{q.get('id', '')}]{exemplar_tag}\n"
                f"Q: {question_text}\n"
                + (f"Options: {opt_str}\n" if opt_str else "")
                + f"Answer: {q.get('answer', q.get('answers', ''))} — {q.get('explanation', q.get('solution', ''))}"
            )
        questions_ctx = (
            f"BLOOM LEVEL STYLE GUIDE ({bloom_level}):\n{style_guide}\n\n"
            f"SAMPLE QUESTIONS FROM QUESTION BANK (use as style reference — do NOT repeat verbatim; generate fresh variations):\n\n"
            + "\n\n".join(lines)
        )
    else:
        questions_ctx = (
            f"BLOOM LEVEL STYLE GUIDE ({bloom_level}):\n{style_guide}\n\n"
            f"No pre-loaded questions found for {subconcept_name} at this level. "
            f"Generate a FRESH question following the style guide above using the NCERT content provided. "
            f"Use Indian context examples (cricket, chapati, auto-rickshaw, etc.)."
        )

    # RAG — retrieve relevant NCERT chunks
    rag_chunks  = await retrieve(
        query         = student_message or subconcept_name,
        subconcept_id = subconcept_id,
        k             = 3,
    )
    rag_context = format_for_prompt(rag_chunks)

    # Check if activity should fire this turn
    should_show_activity = (
        bloom_level in ("Apply", "Analyse", "Evaluate", "Create")
        and not activity_shown
    )

    context = {
        "student_name":      student_name,
        "vark_style":        vark_style,
        "bloom_level":       bloom_level,
        "subconcept_name":   subconcept_name,
        "subconcept_id":     subconcept_id,
        "chapter_name":      chapter_name,
        "last_session_note": last_session_note,
        "questions_context": questions_ctx,
        "rag_context":       rag_context,
        "hint_count":        hint_count,
        "mode":              mode,
        "activity_shown":    activity_shown,
    }

    system_prompt = build_system_prompt(context)

    messages = conversation_history + [
        {"role": "user", "content": student_message}
    ]

    # Call Claude — run in thread so it doesn't block event loop
    response = await asyncio.to_thread(
        client.messages.create,
        model     = get_model(TaskType.DIALOGUE),
        max_tokens= 400,
        system    = system_prompt,
        messages  = messages,
    )

    reply = response.content[0].text

    # XP detection — keyword match in Gyaan's reply
    # Only run XP detection after the student has sent at least one message
    # (conversation_history has prior turns), to avoid false positives on Gyaan's opener
    xp_earned = 0
    bloom_advance = False
    lower_reply = reply.lower()

    student_turns = [m for m in conversation_history if m.get("role") == "user"]
    has_prior_student_turn = len(student_turns) > 0

    correct_signals = ["correct", "exactly", "perfect", "well done", "that's it",
                       "you got it", "spot on", "nailed it", "brilliant"]
    good_signals    = ["good", "right", "yes", "great", "nice", "good thinking",
                       "good attempt", "almost"]

    is_correct = has_prior_student_turn and any(w in lower_reply for w in correct_signals)
    is_good    = has_prior_student_turn and any(w in lower_reply for w in good_signals)

    if is_correct:
        xp_earned = 20
        bloom_advance = True
    elif is_good:
        xp_earned = 10

    # Update hint_count: reset on correct, increment on wrong (0 XP)
    new_hint_count = 0 if is_correct else (hint_count + 1 if xp_earned == 0 else hint_count)

    # Activity shown flag: mark True once fired
    new_activity_shown = activity_shown or should_show_activity

    return {
        "reply":          reply,
        "xp_earned":      xp_earned,
        "bloom_advance":  bloom_advance,
        "model_used":     get_model(TaskType.DIALOGUE),
        "hint_count":     new_hint_count,
        "activity_shown": new_activity_shown,
        "token_usage": {
            "input_tokens":  response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
