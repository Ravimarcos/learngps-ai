"""
RAG Embedder — Day 6b
======================
Converts text chunks into vector embeddings and stores them in ChromaDB.

Model: all-MiniLM-L6-v2 (sentence-transformers)
  - Free, runs locally — no API key needed
  - 384-dimensional vectors
  - Fast: ~10ms per chunk on CPU

ChromaDB: local persistent store
  - Saved to learngps/data/chroma_db/
  - Survives server restarts
  - No cloud account needed

Run to build the index:
    python -m backend.rag.embedder

Run again to rebuild (it clears + re-indexes):
    python -m backend.rag.embedder --rebuild
"""

import sys
import time
from pathlib import Path

# ChromaDB + sentence-transformers are optional — fail gracefully if missing
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except ImportError:
    HAS_ST = False

from backend.rag.chunker import get_all_chunks

# ── Config ─────────────────────────────────────────────────────────────────

CHROMA_DIR  = Path(__file__).parents[3] / "data" / "chroma_db"
COLLECTION  = "learngps_ncert"
EMBED_MODEL = "all-MiniLM-L6-v2"   # ~90MB download on first run

# ── Lazy singletons (loaded once per process) ──────────────────────────────

_chroma_client     = None
_embed_model       = None
_collection        = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        if not HAS_CHROMA:
            raise RuntimeError("chromadb not installed. Run: pip install chromadb")
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        if not HAS_ST:
            raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers")
        print(f"🔄 Loading embedding model {EMBED_MODEL}...")
        _embed_model = SentenceTransformer(EMBED_MODEL)
        print("✅ Embedding model ready")
    return _embed_model


def get_collection():
    """Get or create the ChromaDB collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},   # cosine similarity
        )
    return _collection


# ── Index builder ───────────────────────────────────────────────────────────

def build_index(rebuild: bool = False) -> int:
    """
    Build (or rebuild) the ChromaDB index from all chunks.

    Args:
        rebuild: if True, delete and recreate the collection first

    Returns:
        Number of chunks indexed
    """
    client = get_chroma_client()
    model  = get_embed_model()

    if rebuild:
        try:
            client.delete_collection(COLLECTION)
            print(f"🗑️  Deleted old collection '{COLLECTION}'")
        except Exception:
            pass
        global _collection
        _collection = None

    collection = get_collection()

    # Check if already indexed
    existing = collection.count()
    if existing > 0 and not rebuild:
        print(f"✅ Index already has {existing} chunks. Use --rebuild to re-index.")
        return existing

    # Get all chunks
    print("📦 Chunking NCERT content...")
    chunks = get_all_chunks()
    print(f"   {len(chunks)} chunks ready")

    if not chunks:
        print("⚠️  No chunks found — check source files exist")
        return 0

    # Embed in batches of 32
    print("🔢 Embedding chunks...")
    batch_size = 32
    total = 0
    start = time.time()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]

        # Generate embeddings
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        # Build IDs and metadata
        ids       = [f"chunk_{i + j}" for j in range(len(batch))]
        metadatas = [
            {
                "source":        c.get("source", "unknown"),
                "subconcept_id": c.get("subconcept_id", ""),
                "bloom_level":   c.get("bloom_level", ""),
                "page":          str(c.get("page", "")),
            }
            for c in batch
        ]

        collection.add(
            ids        = ids,
            embeddings = embeddings,
            documents  = texts,
            metadatas  = metadatas,
        )
        total += len(batch)
        print(f"   Indexed {total}/{len(chunks)} chunks...", end="\r")

    elapsed = time.time() - start
    print(f"\n✅ Indexed {total} chunks in {elapsed:.1f}s")
    print(f"   Stored at: {CHROMA_DIR}")
    return total


def is_index_ready() -> bool:
    """Check if the ChromaDB index has been built."""
    if not HAS_CHROMA or not CHROMA_DIR.exists():
        return False
    try:
        collection = get_collection()
        return collection.count() > 0
    except Exception:
        return False


# ── CLI entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    rebuild = "--rebuild" in sys.argv
    print(f"\n{'Rebuilding' if rebuild else 'Building'} RAG index...\n")
    count = build_index(rebuild=rebuild)
    print(f"\n🎉 Done! {count} chunks indexed and ready for retrieval.\n")
