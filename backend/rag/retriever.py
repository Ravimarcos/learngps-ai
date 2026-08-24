"""
RAG Retriever — Day 6b
=======================
Given a student's question, finds the most relevant NCERT chunks
from ChromaDB and returns them as context for Gyaan.

This is the "R" in RAG — Retrieval Augmented Generation.

Flow:
  student question
       ↓
  embed with same model (all-MiniLM-L6-v2)
       ↓
  cosine similarity search in ChromaDB
       ↓
  top-k chunks returned
       ↓
  injected into Gyaan's system prompt
       ↓
  Claude answers using NCERT content

Usage:
    from backend.rag.retriever import retrieve

    chunks = await retrieve(
        query="what is friction",
        subconcept_id="sc_friction",
        k=3,
    )
    # chunks = [{"text": "...", "source": "textbook", ...}, ...]
"""

import asyncio
from backend.rag.embedder import get_embed_model, get_collection, is_index_ready


async def retrieve(
    query: str,
    subconcept_id: str | None = None,
    k: int = 3,
    source_filter: str | None = None,   # "textbook" | "question" | "activity" | None
) -> list[dict]:
    """
    Retrieve top-k relevant NCERT chunks for a query.

    Args:
        query:         student's question or Gyaan's current topic
        subconcept_id: filter to chunks from this SubConcept only
        k:             number of chunks to return
        source_filter: optionally limit to one source type

    Returns:
        List of {text, source, subconcept_id, score}
        Empty list if index not ready or error.
    """
    if not is_index_ready():
        return []

    try:
        # Embed the query (run in thread — CPU-bound)
        model  = get_embed_model()
        q_vec  = await asyncio.to_thread(
            model.encode, [query], show_progress_bar=False
        )
        q_vec  = q_vec[0].tolist()

        # Build ChromaDB where filter
        where = {}
        if subconcept_id and source_filter:
            where = {"$and": [
                {"subconcept_id": {"$eq": subconcept_id}},
                {"source": {"$eq": source_filter}},
            ]}
        elif subconcept_id:
            where = {"subconcept_id": {"$eq": subconcept_id}}
        elif source_filter:
            where = {"source": {"$eq": source_filter}}

        collection = get_collection()

        # Query ChromaDB
        results = collection.query(
            query_embeddings = [q_vec],
            n_results        = k,
            where            = where if where else None,
            include          = ["documents", "metadatas", "distances"],
        )

        # Parse results
        chunks = []
        docs      = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metadatas, distances):
            score = 1 - dist   # convert cosine distance → similarity
            if score < 0.2:    # skip very low relevance
                continue
            chunks.append({
                "text":          doc,
                "source":        meta.get("source", ""),
                "subconcept_id": meta.get("subconcept_id", ""),
                "bloom_level":   meta.get("bloom_level", ""),
                "score":         round(score, 3),
            })

        return chunks

    except Exception as e:
        print(f"⚠️  RAG retrieval error: {e}")
        return []


def format_for_prompt(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a string for Gyaan's system prompt.

    Example output:
        [From NCERT textbook]
        Friction is the force that opposes motion...

        [From Q&A bank — Apply level]
        Question: A book is pushed on a table...
        Answer: The friction force acts opposite...
    """
    if not chunks:
        return ""

    lines = ["RELEVANT NCERT CONTENT (use this to ground your answer):"]
    for chunk in chunks:
        source = chunk.get("source", "")
        bloom  = chunk.get("bloom_level", "")

        if source == "textbook":
            label = "[From NCERT textbook]"
        elif source == "question" and bloom:
            label = f"[From Q&A bank — {bloom.title()} level]"
        elif source == "activity":
            label = "[Hands-on activity]"
        else:
            label = "[Reference]"

        lines.append(f"\n{label}\n{chunk['text']}")

    return "\n".join(lines)
