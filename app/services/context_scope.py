"""
Scope assembly for Cursor-for-writers: system chooses minimal context from the graph
so the LLM gets a bounded window, not the whole book.
"""

from typing import Dict, List, Optional

from app.services.graph_service import get_node, get_children


# -----------------------------------
# Helpers: ordered paragraphs in a chapter
# -----------------------------------

def get_paragraphs_ordered(chapter_id: str) -> List[dict]:
    """Return paragraph nodes in chapter order (children_ids order)."""
    children = get_children(chapter_id)
    return [c for c in children if c.get("type") == "paragraph"]


def _find_paragraph_index(paragraphs: List[dict], paragraph_id: str) -> int:
    for i, p in enumerate(paragraphs):
        if p.get("id") == paragraph_id:
            return i
    return -1


# -----------------------------------
# Rewrite scope: target paragraph + surrounding context
# -----------------------------------

def get_rewrite_scope(paragraph_id: str) -> Optional[Dict]:
    """
    Assemble scope for rewriting one paragraph.
    Returns: chapter_summary, paragraph_text, prev_paragraph_text, next_paragraph_text.
    Bounded: only immediate prev/next + chapter summary (no full chapter).
    """
    node = get_node(paragraph_id)
    if not node or node.get("type") != "paragraph":
        return None
    chapter_id = node.get("parent_id")
    if not chapter_id:
        return None
    chapter = get_node(chapter_id)
    if not chapter:
        return None
    paragraphs = get_paragraphs_ordered(chapter_id)
    idx = _find_paragraph_index(paragraphs, paragraph_id)
    if idx < 0:
        return None
    prev_text = ""
    if idx > 0:
        prev_text = (paragraphs[idx - 1].get("text") or "").strip()
    next_text = ""
    if idx + 1 < len(paragraphs):
        next_text = (paragraphs[idx + 1].get("text") or "").strip()
    return {
        "chapter_title": chapter.get("title") or "",
        "chapter_summary": (chapter.get("summary") or "").strip(),
        "paragraph_text": (node.get("text") or "").strip(),
        "prev_paragraph_text": prev_text,
        "next_paragraph_text": next_text,
    }


# -----------------------------------
# Add-paragraph scope: chapter summary + "content so far"
# -----------------------------------

# Max paragraphs of full text to send for add_paragraph (context budget)
ADD_PARAGRAPH_CONTEXT_MAX = 3


def get_add_paragraph_scope(
    chapter_id: str,
    after_paragraph_id: Optional[str] = None,
) -> Optional[Dict]:
    """
    Assemble scope for adding a new paragraph.
    - If after_paragraph_id is None: add at end; content_so_far = last N paragraphs.
    - If after_paragraph_id is set: insert after that paragraph; content_so_far = from start up to and including that paragraph.
    Re-fetch from graph each time so sequential adds see the newly added paragraph.
    """
    chapter = get_node(chapter_id)
    if not chapter or chapter.get("type") != "chapter":
        return None
    paragraphs = get_paragraphs_ordered(chapter_id)
    if after_paragraph_id:
        idx = _find_paragraph_index(paragraphs, after_paragraph_id)
        if idx < 0:
            # Fallback: use last N
            n = min(ADD_PARAGRAPH_CONTEXT_MAX, len(paragraphs))
            recent = paragraphs[-n:] if n else []
        else:
            # Content from start through after_paragraph_id (cap length for context)
            recent = paragraphs[: idx + 1]
            if len(recent) > ADD_PARAGRAPH_CONTEXT_MAX:
                recent = recent[-ADD_PARAGRAPH_CONTEXT_MAX:]
    else:
        n = min(ADD_PARAGRAPH_CONTEXT_MAX, len(paragraphs))
        recent = paragraphs[-n:] if n else []
    content_so_far = "\n\n".join(
        (p.get("text") or "").strip() for p in recent if (p.get("text") or "").strip()
    )
    return {
        "chapter_title": chapter.get("title") or "",
        "chapter_summary": (chapter.get("summary") or "").strip(),
        "content_so_far": content_so_far,
        "paragraph_count": len(paragraphs),
    }
