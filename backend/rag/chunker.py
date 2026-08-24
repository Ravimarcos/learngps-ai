"""
RAG Chunker — Day 6b
=====================
Splits NCERT textbook PDF and levelwise_questions.json into
text chunks suitable for embedding.

Each chunk gets metadata so we know which SubConcept it belongs to
and can filter during retrieval.

Chunk types:
  - "textbook"  : paragraph from NCERT PDF
  - "question"  : Q&A pair from levelwise_questions.json
  - "activity"  : hands-on activity description

Run directly to preview chunks:
    python -m backend.rag.chunker
"""

import json
import re
from pathlib import Path
from typing import Iterator

try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("⚠️  PyPDF2 not installed — PDF chunking disabled")

# ── Paths ──────────────────────────────────────────────────────────────────

BASE = Path(__file__).parents[2]   # learngps/ root (backend/rag/chunker.py → 2 levels up)

NCERT_PDF      = BASE / "data" / "sources" / "8-Sci-NCERT-Book-Force-Pressure.pdf"
QUESTIONS_JSON = BASE / "data" / "sources" / "levelwise_questions.json"

# ── Keyword → SubConcept mapping (for tagging chunks) ─────────────────────

KEYWORD_TO_SC = {
    "muscular force":       "sc_muscular_force",
    "muscle":               "sc_muscular_force",
    "contact force":        "sc_contact_force",
    "non-contact":          "sc_non_contact",
    "magnetic":             "sc_non_contact",
    "gravity":              "sc_non_contact",
    "electrostatic":        "sc_non_contact",
    "normal force":         "sc_normal_force",
    "reaction force":       "sc_normal_force",
    "friction":             "sc_friction",
    "pressure":             "sc_pressure_def",
    "liquid pressure":      "sc_liquid_pressure",
    "fluid":                "sc_liquid_pressure",
    "atmospheric pressure": "sc_atm_pressure",
    "air pressure":         "sc_atm_pressure",
}

BLOOM_ORDER = ["remember", "understand", "apply", "analyse", "evaluate"]


def _tag_subconcept(text: str) -> str:
    """Guess the SubConcept ID from keywords in the text."""
    lower = text.lower()
    for keyword, sc_id in KEYWORD_TO_SC.items():
        if keyword in lower:
            return sc_id
    return "sc_contact_force"   # default fallback


def _clean(text: str) -> str:
    """Remove extra whitespace and page artefacts."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)   # strip non-ASCII (page numbers etc.)
    return text.strip()


# ── PDF chunker ─────────────────────────────────────────────────────────────

def chunk_ncert_pdf(chunk_size: int = 400) -> Iterator[dict]:
    """
    Split the NCERT Force & Pressure PDF into overlapping text chunks.

    Yields dicts:
        {
            "text": str,
            "source": "textbook",
            "subconcept_id": str,
            "page": int,
        }
    """
    if not HAS_PDF:
        return
    if not NCERT_PDF.exists():
        print(f"⚠️  NCERT PDF not found: {NCERT_PDF}")
        return

    with open(NCERT_PDF, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        full_text = ""
        page_map = []   # (char_start, page_num)

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            page_map.append((len(full_text), page_num))
            full_text += page_text + " "

    # Split into sentences then group into chunks
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    buffer = ""
    buffer_page = 1

    for sentence in sentences:
        sentence = _clean(sentence)
        if len(sentence) < 20:     # skip very short fragments
            continue
        buffer += " " + sentence

        if len(buffer) >= chunk_size:
            chunk_text = buffer.strip()
            # Find page for this chunk
            chunk_start = full_text.find(chunk_text[:50])
            page = 1
            for char_start, pg in page_map:
                if char_start <= chunk_start:
                    page = pg

            yield {
                "text":          chunk_text[:600],   # hard cap
                "source":        "textbook",
                "subconcept_id": _tag_subconcept(chunk_text),
                "page":          page,
            }
            # 50% overlap — keep last half of buffer
            buffer = buffer[len(buffer)//2:]

    # Yield remaining
    if buffer.strip():
        yield {
            "text":          buffer.strip()[:600],
            "source":        "textbook",
            "subconcept_id": _tag_subconcept(buffer),
            "page":          page_map[-1][1] if page_map else 1,
        }


# ── Questions JSON chunker ──────────────────────────────────────────────────

def chunk_questions_json() -> Iterator[dict]:
    """
    Convert levelwise_questions.json Q&A pairs into chunks.

    Yields dicts:
        {
            "text": str,       # "Q: ... A: ... Explanation: ..."
            "source": "question",
            "subconcept_id": str,
            "bloom_level": str,
        }
    """
    if not QUESTIONS_JSON.exists():
        print(f"⚠️  Questions JSON not found: {QUESTIONS_JSON}")
        return

    with open(QUESTIONS_JSON) as f:
        bank = json.load(f)

    questions = bank.get("questions", {})

    for bloom_level in BLOOM_ORDER:
        for q in questions.get(bloom_level, []):
            question_text = q.get("question", "").strip()
            answer        = q.get("answer", "").strip()
            explanation   = q.get("explanation", "").strip()
            concept_id    = q.get("concept_id", "")

            if not question_text or not answer:
                continue

            # Build a self-contained chunk
            chunk = f"Question: {question_text}\nAnswer: {answer}"
            if explanation:
                chunk += f"\nExplanation: {explanation}"

            # Map concept_id → subconcept_id
            sc_id = f"sc_{concept_id}" if concept_id else _tag_subconcept(question_text)

            yield {
                "text":          chunk,
                "source":        "question",
                "subconcept_id": sc_id,
                "bloom_level":   bloom_level,
            }


def chunk_activities_json() -> Iterator[dict]:
    """Convert activity descriptions into chunks."""
    if not QUESTIONS_JSON.exists():
        return

    with open(QUESTIONS_JSON) as f:
        bank = json.load(f)

    for activity in bank.get("activities", []):
        title       = activity.get("title", "")
        description = activity.get("description", "")
        concept_id  = activity.get("concept_id", "")

        if not description:
            continue

        chunk = f"Activity: {title}\n{description}"
        sc_id = f"sc_{concept_id}" if concept_id else _tag_subconcept(chunk)

        yield {
            "text":          chunk[:600],
            "source":        "activity",
            "subconcept_id": sc_id,
        }


def get_all_chunks() -> list[dict]:
    """Return all chunks from all sources."""
    chunks = []
    chunks.extend(chunk_ncert_pdf())
    chunks.extend(chunk_questions_json())
    chunks.extend(chunk_activities_json())
    return chunks


# ── Quick preview ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_chunks = get_all_chunks()
    print(f"\n📦 Total chunks: {len(all_chunks)}\n")

    by_source = {}
    for c in all_chunks:
        by_source.setdefault(c["source"], []).append(c)

    for source, chunks in by_source.items():
        print(f"  {source}: {len(chunks)} chunks")
        # Print first chunk as sample
        print(f"  Sample: {chunks[0]['text'][:150]}...\n")
