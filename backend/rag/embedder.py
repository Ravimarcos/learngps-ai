"""
RAG Embedder — Qdrant Cloud
============================
Converts text chunks into vector embeddings and stores them in Qdrant Cloud.

Model: all-MiniLM-L6-v2 (sentence-transformers)
  - Free, runs locally — no API key needed
  - 384-dimensional vectors

Qdrant Cloud: hosted persistent vector store
  - No local disk needed — survives Railway redeploys
  - Web UI at cloud.qdrant.io

Run to build the index:
    python -m backend.rag.embedder

Run again to rebuild (clears + re-indexes):
    python -m backend.rag.embedder --rebuild
"""

import sys
import time
import uuid

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False

from backend.rag.chunker import get_all_chunks
from backend.config.settings import get_settings

# ── Config ─────────────────────────────────────────────────────────────────
COLLECTION  = "learngps_ncert"
EMBED_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384

# ── Lazy singletons ────────────────────────────────────────────────────────
_qdrant_client  = None
_embed_model    = None


def get_qdrant_client() -> "QdrantClient":
    global _qdrant_client
    if _qdrant_client is None:
        if not HAS_QDRANT:
            raise RuntimeError("qdrant-client not installed. Run: pip install qdrant-client")
        cfg = get_settings()
        _qdrant_client = QdrantClient(
            url=cfg.qdrant_url,
            api_key=cfg.qdrant_api_key,
        )
    return _qdrant_client


def get_embed_model() -> "SentenceTransformer":
    global _embed_model
    if _embed_model is None:
        if not HAS_ST:
            raise RuntimeError("sentence-transformers not installed.")
        print(f"🔄 Loading embedding model {EMBED_MODEL}...")
        _embed_model = SentenceTransformer(EMBED_MODEL)
        print("✅ Embedding model ready")
    return _embed_model


def get_collection():
    """Ensure the Qdrant collection exists and return its name."""
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"✅ Created Qdrant collection '{COLLECTION}'")
    return COLLECTION


# ── Index builder ───────────────────────────────────────────────────────────

def build_index(rebuild: bool = False) -> int:
    client = get_qdrant_client()
    model  = get_embed_model()

    if rebuild:
        try:
            client.delete_collection(COLLECTION)
            print(f"🗑️  Deleted old collection '{COLLECTION}'")
        except Exception:
            pass

    get_collection()

    # Check if already indexed
    info = client.get_collection(COLLECTION)
    existing = info.points_count or 0
    if existing > 0 and not rebuild:
        print(f"✅ Index already has {existing} chunks. Use --rebuild to re-index.")
        return existing

    print("📦 Chunking NCERT content...")
    chunks = get_all_chunks()
    print(f"   {len(chunks)} chunks ready")

    if not chunks:
        print("⚠️  No chunks found — check source files exist")
        return 0

    print("🔢 Embedding chunks...")
    batch_size = 64
    total = 0
    start = time.time()

    for i in range(0, len(chunks), batch_size):
        batch  = chunks[i : i + batch_size]
        texts  = [c["text"] for c in batch]
        embs   = model.encode(texts, show_progress_bar=False).tolist()

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={
                    "text":          c.get("text", ""),
                    "chapter_id":    c.get("chapter_id", ""),
                    "subject":       c.get("subject", ""),
                    "source":        c.get("source", "unknown"),
                    "subconcept_id": c.get("subconcept_id", ""),
                    "bloom_level":   c.get("bloom_level", ""),
                },
            )
            for c, emb in zip(batch, embs)
        ]
        client.upsert(collection_name=COLLECTION, points=points)
        total += len(batch)
        print(f"   Indexed {total}/{len(chunks)} chunks...", end="\r")

    elapsed = time.time() - start
    print(f"\n✅ Indexed {total} chunks in {elapsed:.1f}s → Qdrant Cloud")
    return total


def is_index_ready() -> bool:
    if not HAS_QDRANT:
        return False
    try:
        client = get_qdrant_client()
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION not in existing:
            return False
        info = client.get_collection(COLLECTION)
        return (info.points_count or 0) > 0
    except Exception:
        return False


# ── CLI entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    rebuild = "--rebuild" in sys.argv
    print(f"\n{'Rebuilding' if rebuild else 'Building'} RAG index in Qdrant Cloud...\n")
    count = build_index(rebuild=rebuild)
    print(f"\n🎉 Done! {count} chunks indexed and ready for Gyaan.\n")
