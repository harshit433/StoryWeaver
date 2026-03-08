from datetime import datetime
from math import sqrt
from typing import Dict, List, Optional

from app.database.mongodb import get_doc_indexes_collection
from app.llm.groq_client import generate_embedding
from app.services.graph_service import get_document_chapters, get_node


def _safe_summary(chapter: dict) -> str:
    return (
        chapter.get("summary")
        or chapter.get("title")
        or ""
    ).strip()


def build_doc_index(document_id: str) -> Dict:
    document = get_node(document_id)
    if not document or document.get("type") != "document":
        return {"document_id": document_id, "chapters": []}

    chapters = get_document_chapters(document_id)
    entries = []
    for order, chapter in enumerate(chapters, 1):
        detailed_summary = _safe_summary(chapter)
        embedding = generate_embedding(detailed_summary) if detailed_summary else []
        entries.append(
            {
                "chapter_id": chapter["id"],
                "order": order,
                "title": chapter.get("title") or f"Chapter {order}",
                "detailed_summary": detailed_summary,
                "embedding": embedding,
            }
        )

    return {
        "document_id": document_id,
        "updated_at": datetime.utcnow(),
        "chapters": entries,
    }


def update_doc_index(document_id: str) -> Dict:
    collection = get_doc_indexes_collection()
    payload = build_doc_index(document_id)
    collection.update_one(
        {"document_id": document_id},
        {"$set": payload},
        upsert=True,
    )
    return payload


def get_doc_index(document_id: str) -> Dict:
    collection = get_doc_indexes_collection()
    index = collection.find_one({"document_id": document_id}) or {}
    index.pop("_id", None)
    if not index:
        return update_doc_index(document_id)
    return index


def delete_doc_index(document_id: str) -> None:
    collection = get_doc_indexes_collection()
    collection.delete_one({"document_id": document_id})


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def find_relevant_chapters(
    document_id: str,
    query: str,
    limit: int = 5,
) -> List[Dict]:
    """
    Search a document's chapter summaries and return the best chapter matches.
    """
    doc_index = get_doc_index(document_id)
    chapters = doc_index.get("chapters") or []
    if not chapters:
        return []

    query_embedding = generate_embedding(query)
    scored = []
    for chapter in chapters:
        score = _cosine_similarity(query_embedding, chapter.get("embedding") or [])
        scored.append(
            {
                "chapter_id": chapter["chapter_id"],
                "order": chapter["order"],
                "title": chapter.get("title") or f"Chapter {chapter['order']}",
                "detailed_summary": chapter.get("detailed_summary") or "",
                "score": score,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[: max(1, limit)]


def get_chapter_index_entry(document_id: str, chapter_number: int) -> Optional[Dict]:
    chapters = (get_doc_index(document_id).get("chapters") or [])
    for chapter in chapters:
        if chapter.get("order") == chapter_number:
            return chapter
    return None
