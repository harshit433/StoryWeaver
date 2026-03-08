"""
Top-down, LLM-guided traversal for context retrieval.

Starts at document root → selects relevant chapters → paragraphs
using structured LLM calls at each level. Does not rely on embeddings.
"""

import json
import re
from typing import List, Optional

from app.services.graph_service import get_document_chapters, get_node, get_children, get_parent
from app.llm.groq_client import generate_text


# -----------------------------------
# Parse LLM response for IDs
# -----------------------------------

def _parse_id_list(response: str, valid_ids: List[str]) -> List[str]:
    """Extract list of IDs from LLM response; only return IDs that are in valid_ids."""
    response = response.strip()
    # Strip markdown code block if present
    if "```" in response:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if match:
            response = match.group(1).strip()
    # Try JSON array
    try:
        parsed = json.loads(response)
        if isinstance(parsed, list):
            ids = [str(x).strip() for x in parsed if x]
        elif isinstance(parsed, dict):
            for key in ("ids", "chapter_ids", "paragraph_ids"):
                if key in parsed and isinstance(parsed[key], list):
                    ids = [str(x).strip() for x in parsed[key] if x]
                    break
            else:
                ids = []
        else:
            ids = []
    except json.JSONDecodeError:
        # Comma-separated or newline-separated
        ids = re.split(r"[\s,]+", response)
        ids = [x.strip() for x in ids if x.strip()]
    valid_set = set(valid_ids)
    return [i for i in ids if i in valid_set]


# -----------------------------------
# Step 1: Select relevant chapters
# -----------------------------------

def _select_chapter_ids(instruction: str, document_id: str) -> List[str]:
    chapters = get_document_chapters(document_id)
    if not chapters:
        return []

    lines = []
    for chapter in chapters:
        summary = (chapter.get("summary") or chapter.get("title") or "(no summary)").strip()
        lines.append(
            f"  - id: {chapter['id']}, title: {chapter.get('title') or 'Untitled'}, summary: {summary}"
        )

    prompt = f"""You are selecting which parts of a document are relevant to a user's editing instruction.

User instruction: {instruction}

The document has the following chapters. Each has an id, title, and summary.

{chr(10).join(lines)}

Which chapter IDs are relevant to this instruction? Return a JSON array of those IDs only, e.g. ["id1", "id2"]. If none are relevant, return []."""

    response = generate_text(prompt, temperature=0.2)
    valid_ids = [chapter["id"] for chapter in chapters]
    return _parse_id_list(response, valid_ids)


# -----------------------------------
# Step 3: Select relevant paragraphs (within selected chapters)
# -----------------------------------

def _select_paragraph_ids(instruction: str, chapter_id: str) -> List[str]:
    children = get_children(chapter_id)
    paragraphs = [c for c in children if c.get("type") == "paragraph"]
    if not paragraphs:
        return []

    lines = []
    for p in paragraphs:
        content = (p.get("summary") or p.get("text") or "(empty)").strip()
        lines.append(f"  - id: {p['id']}, content: {content}")

    prompt = f"""You are selecting which paragraphs are relevant to a user's editing instruction.

User instruction: {instruction}

This chapter has the following paragraphs:

{chr(10).join(lines)}

Which paragraph IDs are relevant for editing (or creating new content nearby)? Return a JSON array of those IDs only. If none, return []."""

    response = generate_text(prompt, temperature=0.2)
    valid_ids = [p["id"] for p in paragraphs]
    return _parse_id_list(response, valid_ids)


# -----------------------------------
# Build context: selected nodes + parents
# -----------------------------------

def _expand_with_parents(node_ids: List[str]) -> List[dict]:
    """For each node id, add the node and its parent chain; dedupe and return."""
    seen = set()
    result = []
    for nid in node_ids:
        current = get_node(nid)
        while current:
            if current["id"] not in seen:
                seen.add(current["id"])
                result.append(current)
            current = get_parent(current["id"]) if current.get("parent_id") else None
    return result


# -----------------------------------
# Main: top-down traversal
# -----------------------------------

def build_context_by_traversal(instruction: str, document_id: str) -> List[dict]:
    """
    Top-down, multi-step LLM traversal:
    document → select chapters → select paragraphs → build context with parents.
    """
    document = get_node(document_id)
    if not document:
        return []

    chapter_ids = _select_chapter_ids(instruction, document_id)
    if not chapter_ids:
        return [document]

    paragraph_ids = []
    for chapter_id in chapter_ids:
        paragraph_ids.extend(_select_paragraph_ids(instruction, chapter_id))

    if not paragraph_ids:
        return _expand_with_parents(chapter_ids)

    return _expand_with_parents(paragraph_ids)
