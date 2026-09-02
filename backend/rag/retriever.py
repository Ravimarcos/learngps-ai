"""
RAG Retriever — Qdrant Cloud
=============================
Given a student's question, finds the most relevant NCERT chunks
from Qdrant and returns them as context for Gyaan.

Flow:
  student question
       ↓
  embed with all-MiniLM-L6-v2
       ↓
  cosine similarity search in Qdrant Cloud
       ↓
  top-k chunks returned
       ↓
  injected into Gyaan's system prompt
"""

import asyncio
from backend.rag.embedder import get_embed_model, get_qdrant_client, is_index_ready, COLLECTION


async def retrieve(
    query: str,
    chapter_id: str | None = None,
    subconcept_id: str | None = None,
    k: int = 3,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Retrieve top-k relevant NCERT chunks for a query.

    Args:
        query:         student's question or Gyaan's current topic
        chapter_id:    filter to chunks from this chapter only
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
        model  = get_embed_model()
        q_vec  = await asyncio.to_thread(
            model.encode, [query], show_progress_bar=False
        )
        q_vec = q_vec[0].tolist()

        # Build Qdrant filter
        from qdrant_client.models import Filter, FieldCondition, MatchValue, AndCondition

        conditions = []
        if chapter_id:
            conditions.append(FieldCondition(key="chapter_id", match=MatchValue(value=chapter_id)))
        if subconcept_id:
            conditions.append(FieldCondition(key="subconcept_id", match=MatchValue(value=subconcept_id)))
        if source_filter:
            conditions.append(FieldCondition(key="source", match=MatchValue(value=source_filter)))

        qdrant_filter = Filter(must=conditions) if conditions else None

        client  = get_qdrant_client()
        results = await asyncio.to_thread(
            client.search,
            collection_name = COLLECTION,
            query_vector    = q_vec,
            limit           = k,
            query_filter    = qdrant_filter,
            with_payload    = True,
        )

        chunks = []
        for hit in results:
            score = hit.score   # already cosine similarity (0–1)
            if score < 0.2:
                continue
            payload = hit.payload or {}
            chunks.append({
                "text":          payload.get("text", ""),
                "source":        payload.get("source", ""),
                "subconcept_id": payload.get("subconcept_id", ""),
                "bloom_level":   payload.get("bloom_level", ""),
                "score":         round(score, 3),
            })

        return chunks

    except Exception as e:
        print(f"⚠️  RAG retrieval error: {e}")
        return []


def format_for_prompt(chunks: list[dict]) -> str:
    if not chunks:
        return ""

    lines = ["RELEVANT NCERT CONTENT (use this to ground your answer):"]
    for chunk in chunks:
        source = chunk.get("source", "")
        bloom  = chunk.get("bloom_level", "")

        if source == "textbook":
            label = "[From NCERT textbook]"
        elif source == "diksha_pdf":
            label = "[From NCERT textbook]"
        elif source == "question" and bloom:
            label = f"[From Q&A bank — {bloom.title()} level]"
        elif source == "activity":
            label = "[Hands-on activity]"
        else:
            label = "[Reference]"

        lines.append(f"\n{label}\n{chunk['text']}")

    return "\n".join(lines)
