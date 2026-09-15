"""
DIKSHA API Client — Day 6
==========================
DIKSHA (Digital Infrastructure for Knowledge Sharing) is India's national
education platform. Free public REST API — no key required.

What we fetch:
  - Videos, explanations, and activities mapped to NCERT chapters
  - Filtered by subject=Science, grade level, and keyword

API: POST https://diksha.gov.in/api/content/v1/search
Docs: https://dock.diksha.gov.in/api-docs

Usage:
    resources = await fetch_diksha_content("sc_friction")
    # Returns list of {title, content_type, url, description}
"""

import httpx
import asyncio
from functools import lru_cache

DIKSHA_SEARCH_URL = "https://diksha.gov.in/api/content/v1/search"

# Map our Neo4j SubConcept IDs → DIKSHA search keywords + grade
SUBCONCEPT_TO_DIKSHA = {
    "sc_contact_force":    {"keywords": ["contact force", "force"],         "grade": "Class 8"},
    "sc_muscular_force":   {"keywords": ["muscular force", "muscle force"],  "grade": "Class 8"},
    "sc_non_contact":      {"keywords": ["non-contact force", "magnetic force", "gravity"], "grade": "Class 8"},
    "sc_normal_force":     {"keywords": ["normal force", "reaction force"],  "grade": "Class 8"},
    "sc_friction":         {"keywords": ["friction", "sliding friction"],    "grade": "Class 8"},
    "sc_pressure_def":     {"keywords": ["pressure", "force area"],          "grade": "Class 8"},
    "sc_liquid_pressure":  {"keywords": ["liquid pressure", "water pressure","fluid pressure"], "grade": "Class 8"},
    "sc_atm_pressure":     {"keywords": ["atmospheric pressure", "air pressure"], "grade": "Class 8"},
}

# MIME type → friendly content type label
MIME_LABELS = {
    "video/mp4":                          "video",
    "video/x-youtube":                    "video",
    "application/pdf":                    "pdf",
    "application/vnd.ekstep.ecml-archive":"activity",
    "application/vnd.ekstep.h5p-archive": "activity",
    "application/vnd.ekstep.html-archive":"activity",
}


def _build_request_body(keywords: list[str], grade: str, limit: int = 5, subject: str = "Science") -> dict:
    """Build DIKSHA search request body."""
    # DIKSHA uses "Mathematics" not "Maths"
    diksha_subject = "Mathematics" if subject.lower() in ("maths", "math", "mathematics") else subject
    return {
        "request": {
            "filters": {
                "subject":      [diksha_subject],
                "gradeLevel":   [grade],
                "medium":       ["English"],
                "status":       ["Live"],
                "contentType":  ["Resource", "ExplanationResource", "PracticeResource"],
            },
            "query": " ".join(keywords[:2]),   # use first 2 keywords as query
            "limit": limit,
            "fields": [
                "name",
                "description",
                "contentType",
                "mimeType",
                "artifactUrl",
                "streamingUrl",
                "downloadUrl",
                "subject",
                "gradeLevel",
                "identifier",
                "pkgVersion",
            ],
        }
    }


def _parse_content_item(item: dict) -> dict | None:
    """Parse one DIKSHA content item into our format."""
    # Pick best URL: streaming > artifact > download
    url = (
        item.get("streamingUrl")
        or item.get("artifactUrl")
        or item.get("downloadUrl")
        or ""
    )
    if not url:
        return None

    mime = item.get("mimeType", "")
    content_type = MIME_LABELS.get(mime, "resource")

    return {
        "title":        item.get("name", "Untitled"),
        "description":  item.get("description", "")[:200],   # cap at 200 chars
        "content_type": content_type,
        "url":          url,
        "identifier":   item.get("identifier", ""),
        "source":       "diksha",
    }


async def fetch_diksha_content(
    subconcept_id: str,
    limit: int = 5,
    timeout: float = 8.0,
    name: str | None = None,
    grade: int | None = None,
    subject: str | None = None,
) -> list[dict]:
    """
    Fetch NCERT content from DIKSHA for a SubConcept.

    Priority:
      1. Hardcoded mapping (SUBCONCEPT_TO_DIKSHA) — curated keywords
      2. Dynamic search using `name` + `grade` + `subject` params (for all other subconcepts)

    Args:
        subconcept_id: e.g. "sc_friction"
        limit: max results to return
        timeout: seconds before giving up
        name: subconcept display name e.g. "Production of Sound"
        grade: NCERT grade number e.g. 9
        subject: "Science" or "Maths"

    Returns:
        List of {title, description, content_type, url, identifier, source}
        Empty list if DIKSHA is unreachable.
    """
    mapping = SUBCONCEPT_TO_DIKSHA.get(subconcept_id)

    if not mapping:
        # Dynamic fallback: build keywords from the subconcept name
        if not name:
            return []
        grade_label = f"Class {grade}" if grade else "Class 8"
        # Use the subconcept name words as keywords (drop short words)
        words = [w for w in name.lower().split() if len(w) > 2]
        keywords = [name] + words[:2]
        mapping = {"keywords": keywords, "grade": grade_label}

    # Override subject filter if provided
    diksha_subject = subject if subject else "Science"
    body = _build_request_body(mapping["keywords"], mapping["grade"], limit, diksha_subject)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                DIKSHA_SEARCH_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept":       "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Navigate to content list
        content_list = data.get("result", {}).get("content", [])
        if not content_list:
            return []

        # Parse and filter out items with no URL
        results = []
        for item in content_list:
            parsed = _parse_content_item(item)
            if parsed:
                results.append(parsed)

        return results[:limit]

    except httpx.TimeoutException:
        print(f"⚠️  DIKSHA timeout for {subconcept_id}")
        return []
    except httpx.HTTPStatusError as e:
        print(f"⚠️  DIKSHA HTTP error {e.response.status_code} for {subconcept_id}")
        return []
    except Exception as e:
        print(f"⚠️  DIKSHA error for {subconcept_id}: {e}")
        return []


# ---------------------------------------------------------------------------
# Quick test (run directly: python -m backend.content.diksha_client)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    async def _test():
        print("Testing DIKSHA client...\n")
        for sc_id in ["sc_friction", "sc_atm_pressure", "sc_contact_force"]:
            results = await fetch_diksha_content(sc_id, limit=3)
            print(f"\n📚 {sc_id} → {len(results)} results")
            for r in results:
                print(f"  [{r['content_type']}] {r['title']}")
                print(f"   {r['url'][:80]}...")

    asyncio.run(_test())
