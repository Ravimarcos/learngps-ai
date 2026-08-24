"""
Photo Question Solver — Multimodal Gyaan
=========================================
Student takes a photo of a question from their textbook or homework.
Gyaan either:
  - Guides them to solve it (Socratic mode)
  - Evaluates their handwritten answer (Check mode)

Uses Claude's vision capability (multimodal).
Model: Haiku (vision) — fast and supports images.
"""

import anthropic
import asyncio
import base64
from pathlib import Path
from backend.config.settings import get_settings

settings = get_settings()
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

GUIDE_PROMPT = """You are Gyaan, a warm AI tutor for Indian Class 8-10 students.
A student has sent you a photo of a question from their textbook or homework.

Your job: Help them THINK through it, not solve it for them.
- Ask ONE guiding question to get them started
- Use a relatable Indian example if helpful
- Keep it to 3-4 sentences maximum
- End with a question that moves them forward

Do NOT give the answer directly. Guide them step by step."""

CHECK_PROMPT = """You are Gyaan, a warm AI tutor for Indian Class 8-10 students.
A student has sent you a photo of a question AND their attempted answer.

Your job: Evaluate their answer.
- If correct: Celebrate clearly, explain WHY it's correct, give XP signal (say "XP: 20")
- If partially correct: Acknowledge what's right, point to ONE specific thing to fix
- If incorrect: Don't say "wrong" — say "interesting approach, but..." and give a hint

Keep it to 4-5 sentences. End with encouragement."""


async def solve_from_photo(
    image_data: bytes,
    image_media_type: str,
    student_name: str,
    mode: str = "guide",           # "guide" | "check"
    student_answer: str = "",      # filled for "check" mode
    vark_style: str = "K",
) -> dict:
    """
    Process a photo of a question and return Gyaan's response.

    Args:
        image_data: raw image bytes (JPEG or PNG)
        image_media_type: "image/jpeg" or "image/png"
        student_name: student's name
        mode: "guide" (help solve) or "check" (evaluate answer)
        student_answer: student's written answer (check mode only)
        vark_style: VARK learning style

    Returns:
        {"reply": str, "xp_earned": int, "mode": str}
    """

    # Base64 encode the image for Claude's vision API
    image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

    # Choose system prompt based on mode
    system = GUIDE_PROMPT if mode == "guide" else CHECK_PROMPT

    # Build user message with image
    if mode == "guide":
        user_text = f"Hi Gyaan! I'm {student_name}. Can you help me understand how to solve this question?"
    else:
        user_text = (
            f"Hi Gyaan! I'm {student_name}. Here's the question and my answer:\n\n"
            f"My answer: {student_answer}\n\n"
            f"Is my answer correct? What did I get right or wrong?"
        )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": user_text,
                },
            ],
        }
    ]

    # Call Claude with vision — run in thread so it doesn't block the async event loop
    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=system,
        messages=messages,
    )

    reply = response.content[0].text

    # Detect XP from check mode
    xp_earned = 0
    if mode == "check":
        lower = reply.lower()
        if "xp: 20" in lower or any(w in lower for w in ["correct", "perfect", "exactly right"]):
            xp_earned = 20
        elif any(w in lower for w in ["partially", "almost", "close"]):
            xp_earned = 10

    return {
        "reply":      reply,
        "xp_earned":  xp_earned,
        "mode":       mode,
        "model_used": "claude-haiku-4-5-20251001",
    }
