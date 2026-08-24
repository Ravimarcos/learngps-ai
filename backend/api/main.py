"""
LearnGPS FastAPI Application
=============================
Entry point. Run with:
    uvicorn backend.api.main:app --reload

Routes:
    GET  /health          — liveness check
    POST /chat            — Gyaan tutor session (Day 5)
    GET  /gps/{student_id}/{chapter_id} — GPS route for student (Day 3)
    GET  /career/{student_id} — Career Compass recommendations (Day 5)
"""

import asyncio
import time
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase
from backend.config.settings import get_settings
from backend.graph.schema import create_constraints

# Langfuse — observability (initialised once at startup)
try:
    from langfuse import Langfuse
    _lf = Langfuse()          # reads LANGFUSE_PUBLIC_KEY / SECRET_KEY / HOST from env
    LANGFUSE_ENABLED = True
except Exception:
    _lf = None
    LANGFUSE_ENABLED = False

settings = get_settings()
_driver = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect Neo4j, build RAG index, apply constraints. Shutdown: close driver."""
    global _driver

    # Build ChromaDB RAG index in background — don't block server startup
    async def _build_rag_background():
        try:
            from backend.rag.embedder import build_index
            await asyncio.to_thread(build_index, False)
            print("✅ RAG index ready")
        except Exception as e:
            print(f"⚠️  RAG index build failed (non-fatal): {e}")
    asyncio.create_task(_build_rag_background())

    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    await create_constraints(_driver)
    print("✅ LearnGPS API started")
    yield
    await _driver.close()


app = FastAPI(
    title="LearnGPS API",
    version="0.1.0",
    description="AI tutoring platform — GPS-style learning for Indian students",
    lifespan=lifespan,
)

# Allow browser requests from Next.js dev server and production Vercel URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # wildcard subdomains not supported — open for now
    allow_credentials=False,      # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/photo")
async def photo_solve(
    image: UploadFile = File(...),
    student_name: str = Form(default="Student"),
    mode: str = Form(default="guide"),          # "guide" | "check"
    student_answer: str = Form(default=""),
    vark_style: str = Form(default="K"),
):
    """
    Multimodal endpoint — student uploads a photo of a question.
    Gyaan guides them to solve it or checks their answer.

    mode=guide  → Gyaan asks guiding questions (Socratic)
    mode=check  → Gyaan evaluates the student's answer
    """
    from backend.agents.photo_solver import solve_from_photo

    image_data = await image.read()
    media_type = image.content_type or "image/jpeg"

    return await solve_from_photo(
        image_data      = image_data,
        image_media_type= media_type,
        student_name    = student_name,
        mode            = mode,
        student_answer  = student_answer,
        vark_style      = vark_style,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# GPS route endpoint (wired after Day 2)
# ---------------------------------------------------------------------------
@app.get("/gps/{student_id}/{chapter_id}")
async def get_gps(student_id: str, chapter_id: str):
    """Returns the student's GPS route through a chapter."""
    from backend.graph.traversal import get_gps_route
    from backend.config.settings import get_settings
    from supabase import create_client

    cfg = get_settings()

    # Fetch mastered subconcepts for this student from Supabase
    sb = create_client(cfg.supabase_url, cfg.supabase_service_key)
    result = sb.table("student_progress") \
               .select("subconcept_id") \
               .eq("student_id", student_id) \
               .eq("mastered", True) \
               .execute()
    mastered_ids = {row["subconcept_id"] for row in result.data}

    # Get GPS route from Neo4j
    gps = await get_gps_route(_driver, chapter_id, mastered_ids)

    return {
        "student_id": student_id,
        "chapter_id": chapter_id,
        "current": gps["current"],
        "route": gps["route"],
        "completed": gps["completed"],
        "locked_count": len(gps["locked"]),
        "progress_pct": round(
            len(gps["completed"]) / max(len(gps["completed"]) + len(gps["route"]) + len(gps["locked"]), 1) * 100
        ),
    }


# ---------------------------------------------------------------------------
# DIKSHA content endpoint (Day 6)
# ---------------------------------------------------------------------------
@app.get("/diksha/{subconcept_id}")
async def get_diksha_content(subconcept_id: str, limit: int = 5):
    """
    Fetch NCERT learning resources from DIKSHA for a SubConcept.

    Returns list of {title, description, content_type, url, source}
    content_type: "video" | "pdf" | "activity" | "resource"
    """
    from backend.content.diksha_client import fetch_diksha_content

    results = await fetch_diksha_content(subconcept_id, limit=limit)
    return {
        "subconcept_id": subconcept_id,
        "count":         len(results),
        "resources":     results,
    }


# ---------------------------------------------------------------------------
# VARK profile endpoint (Day 7)
# ---------------------------------------------------------------------------
@app.get("/vark/{student_id}")
async def get_vark(student_id: str):
    """
    Get a student's current VARK learning style profile.

    Returns: {v_score, a_score, r_score, k_score, dominant, session_count}
    dominant: "V" | "A" | "R" | "K"
    """
    from backend.agents.vark_agent import get_vark_profile
    return await get_vark_profile(student_id)


# ---------------------------------------------------------------------------
# Chat endpoint (wired after Day 5, VARK update added Day 7)
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(body: dict):
    """
    Gyaan tutor conversation turn.

    Request body:
    {
        "student_id": "uuid",
        "student_name": "Dhwani",
        "message": "I think muscular force is when muscles push",
        "conversation_history": [{"role": "assistant", "content": "..."}],
        "subconcept_id": "sc_muscular_force",
        "subconcept_name": "Muscular Force",
        "chapter_name": "Force & Pressure",
        "bloom_level": "Remember",
        "vark_style": "K",
        "last_session_note": "",
        "distress_count": 0     ← frontend tracks this across turns
    }
    """
    from backend.agents.tutor_agent import chat as gyaan_chat
    from backend.agents.vark_agent import update_vark_profile
    from backend.agents.guardrails import check_guardrails, ADULT_WARNING

    student_id      = body.get("student_id", "")
    student_name    = body.get("student_name", "Student")
    student_message = body.get("message", "")
    subconcept_name = body.get("subconcept_name", "Contact Force")
    chapter_name    = body.get("chapter_name", "Force & Pressure")
    distress_count  = body.get("distress_count", 0)
    _t_start        = time.monotonic()

    try:
        # ── GUARDRAILS ────────────────────────────────────────────────────
        guard = await check_guardrails(
            message         = student_message,
            student_name    = student_name,
            subconcept_name = subconcept_name,
            chapter_name    = chapter_name,
            distress_count  = distress_count,
        )

        # Parent flag → write to Supabase (fire-and-forget)
        if guard.get("flag_parent") and student_id:
            try:
                from backend.config.settings import get_settings
                from supabase import create_client
                cfg = get_settings()
                sb  = create_client(cfg.supabase_url, cfg.supabase_service_key)
                sb.table("student_vark").upsert(
                    {"student_id": student_id, "distress_flag": True},
                    on_conflict="student_id",
                ).execute()
            except Exception:
                pass

        # Blocked → return guardrail reply directly, skip Gyaan
        if guard["blocked"]:
            return {
                "reply":          guard["reply"],
                "xp_earned":      0,
                "bloom_level":    body.get("bloom_level", "Remember"),
                "session_note":   "",
                "guardrail_rule": guard["rule"],
                "distress_count": guard["distress_count"],
            }

        # ── GYAAN AGENT + VARK UPDATE (concurrent) ───────────────────────
        common_kwargs = dict(
            student_name         = student_name,
            student_message      = student_message,
            conversation_history = body.get("conversation_history", []),
            subconcept_id        = body.get("subconcept_id", "sc_contact_force"),
            subconcept_name      = subconcept_name,
            chapter_name         = chapter_name,
            bloom_level          = body.get("bloom_level", "Remember"),
            vark_style           = body.get("vark_style", "K"),
            last_session_note    = body.get("last_session_note", ""),
        )

        if student_id:
            # gather with return_exceptions so VARK failure never kills Gyaan
            results = await asyncio.gather(
                gyaan_chat(**common_kwargs),
                update_vark_profile(student_id, student_message),
                return_exceptions=True,
            )
            result = results[0]
            if isinstance(result, Exception):
                raise result   # Gyaan failure is a real error
            vark = results[1]
            if not isinstance(vark, Exception):
                result["vark_updated"] = vark.get("dominant", "K")
        else:
            result = await gyaan_chat(**common_kwargs)

        # Append adult safety warning if experiment keyword detected
        if guard.get("add_adult_warning"):
            result["reply"] = result.get("reply", "") + ADULT_WARNING

        result["guardrail_rule"] = guard["rule"]
        result["distress_count"] = guard["distress_count"]

        # ── Langfuse trace ────────────────────────────────────────────────
        if LANGFUSE_ENABLED:
            try:
                latency_ms = int((time.monotonic() - _t_start) * 1000)
                _lf.trace(
                    name     = "gyaan_chat",
                    user_id  = student_id or "anonymous",
                    input    = {"message": student_message, "subconcept": subconcept_name},
                    output   = {"reply": result.get("reply", "")[:200]},
                    metadata = {
                        "guardrail_rule": guard["rule"],
                        "bloom_level":    body.get("bloom_level", "Remember"),
                        "vark_style":     body.get("vark_style", "K"),
                        "xp_earned":      result.get("xp_earned", 0),
                        "latency_ms":     latency_ms,
                        "chapter":        chapter_name,
                    },
                )
            except Exception:
                pass

        return result

    except Exception as exc:
        import traceback
        print(f"❌ /chat error: {exc}\n{traceback.format_exc()}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(exc))
