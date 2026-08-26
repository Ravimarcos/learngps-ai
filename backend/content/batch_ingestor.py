"""
LearnGPS Batch Content Ingestor
================================
Fetches DIKSHA content for all Grade 8 Science + Maths chapters,
extracts text from PDFs where available, and indexes everything
into ChromaDB for Gyaan's RAG retrieval.

Sources (priority order per chapter):
  1. DIKSHA PDF resources   — full text extraction via PyMuPDF
  2. DIKSHA activity/video  — title + description as context chunk
  3. Fallback summary       — chapter name + keywords as minimal chunk

Run once to build the full index:
    python -m backend.content.batch_ingestor

Rebuild (wipe + re-index):
    python -m backend.content.batch_ingestor --rebuild
"""

import asyncio
import io
import re
import sys
import time
from pathlib import Path
from typing import Iterator

import httpx

# ── Chapter registry — all 34 Grade 8 Science + Maths chapters ─────────────

CHAPTERS = [
    # ── Science ──────────────────────────────────────────────────────────────
    {"id": "ch_crop_production",   "name": "Crop Production and Management",      "subject": "Science",     "num": 1},
    {"id": "ch_microorganisms",    "name": "Microorganisms Friend and Foe",       "subject": "Science",     "num": 2},
    {"id": "ch_synthetic_fibres",  "name": "Synthetic Fibres and Plastics",       "subject": "Science",     "num": 3},
    {"id": "ch_metals_nonmetals",  "name": "Materials Metals and Non-Metals",     "subject": "Science",     "num": 4},
    {"id": "ch_coal_petroleum",    "name": "Coal and Petroleum",                  "subject": "Science",     "num": 5},
    {"id": "ch_combustion",        "name": "Combustion and Flame",                "subject": "Science",     "num": 6},
    {"id": "ch_conservation",      "name": "Conservation of Plants and Animals",  "subject": "Science",     "num": 7},
    {"id": "ch_cell",              "name": "Cell Structure and Functions",         "subject": "Science",     "num": 8},
    {"id": "ch_reproduction",      "name": "Reproduction in Animals",             "subject": "Science",     "num": 9},
    {"id": "ch_adolescence",       "name": "Reaching the Age of Adolescence",     "subject": "Science",     "num": 10},
    {"id": "ch_force_pressure",    "name": "Force and Pressure",                  "subject": "Science",     "num": 11},
    {"id": "ch_friction",          "name": "Friction",                            "subject": "Science",     "num": 12},
    {"id": "ch_sound",             "name": "Sound",                               "subject": "Science",     "num": 13},
    {"id": "ch_chemical_effects",  "name": "Chemical Effects of Electric Current","subject": "Science",     "num": 14},
    {"id": "ch_natural_phenomena", "name": "Some Natural Phenomena",              "subject": "Science",     "num": 15},
    {"id": "ch_light",             "name": "Light",                               "subject": "Science",     "num": 16},
    {"id": "ch_stars_solar",       "name": "Stars and the Solar System",          "subject": "Science",     "num": 17},
    {"id": "ch_pollution",         "name": "Pollution of Air and Water",          "subject": "Science",     "num": 18},
    # ── Mathematics ──────────────────────────────────────────────────────────
    {"id": "ch_rational_numbers",  "name": "Rational Numbers",                    "subject": "Mathematics", "num": 1},
    {"id": "ch_linear_equations",  "name": "Linear Equations in One Variable",    "subject": "Mathematics", "num": 2},
    {"id": "ch_quadrilaterals",    "name": "Understanding Quadrilaterals",        "subject": "Mathematics", "num": 3},
    {"id": "ch_practical_geometry","name": "Practical Geometry",                  "subject": "Mathematics", "num": 4},
    {"id": "ch_data_handling",     "name": "Data Handling",                       "subject": "Mathematics", "num": 5},
    {"id": "ch_squares_roots",     "name": "Squares and Square Roots",            "subject": "Mathematics", "num": 6},
    {"id": "ch_cubes_roots",       "name": "Cubes and Cube Roots",                "subject": "Mathematics", "num": 7},
    {"id": "ch_comparing_quantities","name": "Comparing Quantities",              "subject": "Mathematics", "num": 8},
    {"id": "ch_algebraic_expr",    "name": "Algebraic Expressions and Identities","subject": "Mathematics", "num": 9},
    {"id": "ch_solid_shapes",      "name": "Visualising Solid Shapes",            "subject": "Mathematics", "num": 10},
    {"id": "ch_mensuration",       "name": "Mensuration",                         "subject": "Mathematics", "num": 11},
    {"id": "ch_exponents",         "name": "Exponents and Powers",                "subject": "Mathematics", "num": 12},
    {"id": "ch_direct_inverse",    "name": "Direct and Inverse Proportions",      "subject": "Mathematics", "num": 13},
    {"id": "ch_factorisation",     "name": "Factorisation",                       "subject": "Mathematics", "num": 14},
    {"id": "ch_intro_graphs",      "name": "Introduction to Graphs",              "subject": "Mathematics", "num": 15},
    {"id": "ch_playing_numbers",   "name": "Playing with Numbers",                "subject": "Mathematics", "num": 16},
]

# ── DIKSHA API ──────────────────────────────────────────────────────────────

DIKSHA_SEARCH_URL = "https://diksha.gov.in/api/content/v1/search"
CHUNK_SIZE = 500   # characters per chunk, with 50% overlap

MIME_LABELS = {
    "video/mp4":                           "video",
    "video/x-youtube":                     "video",
    "application/pdf":                     "pdf",
    "application/vnd.ekstep.ecml-archive": "activity",
    "application/vnd.ekstep.h5p-archive":  "activity",
    "application/vnd.ekstep.html-archive": "activity",
}


def _search_body(chapter_name: str, subject: str, limit: int = 10) -> dict:
    return {
        "request": {
            "filters": {
                "subject":     [subject],
                "gradeLevel":  ["Class 8"],
                "medium":      ["English"],
                "status":      ["Live"],
                "contentType": ["Resource", "ExplanationResource",
                                "PracticeResource", "TextBookUnit"],
            },
            "query": chapter_name,
            "limit": limit,
            "fields": [
                "name", "description", "contentType", "mimeType",
                "artifactUrl", "streamingUrl", "downloadUrl",
                "subject", "gradeLevel", "identifier",
            ],
        }
    }


async def _search_diksha(chapter: dict, client: httpx.AsyncClient) -> list[dict]:
    """Search DIKSHA for resources related to this chapter."""
    try:
        r = await client.post(
            DIKSHA_SEARCH_URL,
            json=_search_body(chapter["name"], chapter["subject"]),
            headers={"Content-Type": "application/json"},
            timeout=12.0,
        )
        r.raise_for_status()
        return r.json().get("result", {}).get("content", []) or []
    except Exception as e:
        print(f"  ⚠️  DIKSHA search failed for {chapter['name']}: {e}")
        return []


async def _download_pdf(url: str, client: httpx.AsyncClient) -> bytes | None:
    """Download a PDF and return its bytes, or None on failure."""
    try:
        r = await client.get(url, timeout=20.0, follow_redirects=True)
        r.raise_for_status()
        if "pdf" in r.headers.get("content-type", "").lower() or url.endswith(".pdf"):
            return r.content
    except Exception:
        pass
    return None


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF (preferred) or PyPDF2 fallback."""
    # Try PyMuPDF first (much better quality)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = [page.get_text() for page in doc]
        doc.close()
        return " ".join(texts)
    except ImportError:
        pass

    # Fallback: PyPDF2
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        return " ".join(p.extract_text() or "" for p in reader.pages)
    except Exception:
        return ""


def _clean(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _text_to_chunks(
    text: str,
    chapter_id: str,
    subject: str,
    source: str,
    chunk_size: int = CHUNK_SIZE,
) -> list[dict]:
    """Split text into overlapping chunks, tagged with chapter metadata."""
    text = _clean(text)
    if len(text) < 80:
        return []

    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    buffer = ""

    for sentence in sentences:
        sentence = _clean(sentence)
        if len(sentence) < 20:
            continue
        buffer += " " + sentence
        if len(buffer) >= chunk_size:
            chunks.append({
                "text":       buffer.strip()[:800],
                "chapter_id": chapter_id,
                "subject":    subject,
                "source":     source,
                "bloom_level": "",
                "subconcept_id": "",
            })
            buffer = buffer[len(buffer) // 2:]   # 50% overlap

    if buffer.strip():
        chunks.append({
            "text":       buffer.strip()[:800],
            "chapter_id": chapter_id,
            "subject":    subject,
            "source":     source,
            "bloom_level": "",
            "subconcept_id": "",
        })

    return chunks


async def ingest_chapter(chapter: dict, client: httpx.AsyncClient) -> list[dict]:
    """
    Fetch all DIKSHA content for one chapter and return text chunks.
    PDF resources are downloaded + text-extracted.
    Non-PDF resources contribute title + description.
    """
    chunks: list[dict] = []
    items = await _search_diksha(chapter, client)

    pdf_count = 0
    meta_count = 0

    for item in items:
        mime  = item.get("mimeType", "")
        title = item.get("name", "")
        desc  = item.get("description", "") or ""
        url   = (item.get("artifactUrl") or item.get("downloadUrl") or "")

        if mime == "application/pdf" and url:
            pdf_bytes = await _download_pdf(url, client)
            if pdf_bytes:
                pdf_text = _extract_pdf_text(pdf_bytes)
                if pdf_text and len(pdf_text) > 100:
                    new_chunks = _text_to_chunks(
                        pdf_text, chapter["id"], chapter["subject"], "diksha_pdf"
                    )
                    chunks.extend(new_chunks)
                    pdf_count += 1
                    continue   # don't double-add as metadata

        # Non-PDF or PDF with no text: use title + description
        combined = f"{title}. {desc}".strip()
        if combined and len(combined) > 30:
            chunks.append({
                "text":          _clean(combined)[:800],
                "chapter_id":    chapter["id"],
                "subject":       chapter["subject"],
                "source":        "diksha_meta",
                "bloom_level":   "",
                "subconcept_id": "",
            })
            meta_count += 1

    # Minimum fallback: chapter name + subject so RAG always returns something
    if not chunks:
        chunks.append({
            "text":          f"NCERT Class 8 {chapter['subject']} Chapter {chapter['num']}: {chapter['name']}.",
            "chapter_id":    chapter["id"],
            "subject":       chapter["subject"],
            "source":        "fallback",
            "bloom_level":   "",
            "subconcept_id": "",
        })

    print(f"  ✅ {chapter['name'][:40]:<40} → {len(chunks):>3} chunks "
          f"({pdf_count} PDFs + {meta_count} meta)")
    return chunks


async def fetch_all_chapters(concurrency: int = 4) -> list[dict]:
    """
    Fetch all chapters concurrently (limited to `concurrency` at a time
    to avoid hammering DIKSHA).
    """
    all_chunks: list[dict] = []
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(chapter):
        async with sem:
            return await ingest_chapter(chapter, client)

    async with httpx.AsyncClient() as client:
        tasks = [_bounded(ch) for ch in CHAPTERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for ch, result in zip(CHAPTERS, results):
        if isinstance(result, Exception):
            print(f"  ❌ {ch['name']}: {result}")
        else:
            all_chunks.extend(result)

    return all_chunks


def index_chunks(chunks: list[dict], rebuild: bool = False) -> int:
    """Embed chunks and upsert into ChromaDB."""
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Run: pip install chromadb sentence-transformers --break-system-packages")
        return 0

    CHROMA_DIR = Path(__file__).parents[3] / "data" / "chroma_db"
    COLLECTION  = "learngps_ncert"
    EMBED_MODEL = "all-MiniLM-L6-v2"

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    db = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if rebuild:
        try:
            db.delete_collection(COLLECTION)
            print("🗑️  Deleted old collection")
        except Exception:
            pass

    col = db.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    print(f"\n🔢 Embedding {len(chunks)} chunks with {EMBED_MODEL}...")
    model  = SentenceTransformer(EMBED_MODEL)
    batch  = 32
    total  = 0
    t0     = time.time()

    for i in range(0, len(chunks), batch):
        b    = chunks[i : i + batch]
        texts = [c["text"] for c in b]
        embs  = model.encode(texts, show_progress_bar=False).tolist()
        ids   = [f"ch_{c['chapter_id']}_{i+j}" for j, c in enumerate(b)]
        metas = [{
            "chapter_id":    c.get("chapter_id", ""),
            "subject":       c.get("subject", ""),
            "source":        c.get("source", ""),
            "subconcept_id": c.get("subconcept_id", ""),
            "bloom_level":   c.get("bloom_level", ""),
        } for c in b]

        col.upsert(ids=ids, embeddings=embs, documents=texts, metadatas=metas)
        total += len(b)
        print(f"   {total}/{len(chunks)} indexed...", end="\r")

    print(f"\n✅ {total} chunks indexed in {time.time()-t0:.1f}s → {CHROMA_DIR}")
    return total


async def run(rebuild: bool = False):
    print("\n🚀 LearnGPS Batch DIKSHA Ingestor")
    print(f"   Chapters: {len(CHAPTERS)} ({sum(1 for c in CHAPTERS if c['subject']=='Science')} Science + "
          f"{sum(1 for c in CHAPTERS if c['subject']=='Mathematics')} Maths)\n")

    print("📡 Fetching from DIKSHA...")
    t0 = time.time()
    chunks = await fetch_all_chapters(concurrency=4)
    print(f"\n   Total chunks collected: {len(chunks)} in {time.time()-t0:.1f}s")

    # Save raw chunks to JSON for inspection / reuse
    import json
    out_path = Path(__file__).parents[2] / "data" / "diksha_chunks.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(chunks, f, indent=2)
    print(f"   Raw chunks saved → {out_path}")

    # Index into ChromaDB
    count = index_chunks(chunks, rebuild=rebuild)
    print(f"\n🎉 Done! {count} chunks ready for Gyaan RAG.\n")


if __name__ == "__main__":
    rebuild    = "--rebuild"    in sys.argv
    index_only = "--index-only" in sys.argv

    if index_only:
        import json
        cache_path = Path(__file__).parents[2] / "data" / "diksha_chunks.json"
        if not cache_path.exists():
            print(f"❌ Cache not found: {cache_path}\n   Run without --index-only first.")
            sys.exit(1)
        with open(cache_path) as f:
            chunks = json.load(f)
        print(f"\n📦 Loaded {len(chunks)} chunks from cache → indexing...\n")
        count = index_chunks(chunks, rebuild=True)
        print(f"\n🎉 Done! {count} chunks indexed.\n")
    else:
        asyncio.run(run(rebuild=rebuild))
