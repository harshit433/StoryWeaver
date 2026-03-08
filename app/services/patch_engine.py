"""
Patch engine: execute scoped edits. System assembles context from the graph;
LLM only produces content for the target scope (one paragraph).
"""

from typing import Dict, Optional

from app.models.node_model import create_paragraph_node
from app.services.graph_service import get_node, update_node, create_node, delete_node, insert_child_after
from app.services.propagation_service import propagate_from_paragraph, propagate_from_chapter
from app.services.embedding_service import create_node_embedding, update_node_embedding, remove_node_embedding
from app.services.context_scope import get_rewrite_scope, get_add_paragraph_scope
from app.llm.groq_client import generate_text


# -----------------------------------
# Rewrite: scope = paragraph + chapter summary + prev/next
# -----------------------------------

def _build_rewrite_prompt(scope: Dict, instruction: str) -> str:
    chapter_summary = scope.get("chapter_summary") or "(no summary)"
    prev_text = scope.get("prev_paragraph_text") or ""
    next_text = scope.get("next_paragraph_text") or ""
    target_text = scope.get("paragraph_text") or ""

    parts = [
        "You are editing a single paragraph in a story. Keep the edit consistent with the surrounding context.",
        "",
        f"Chapter summary: {chapter_summary}",
    ]
    if prev_text:
        parts += ["", "Previous paragraph:", prev_text]
    parts += ["", "Paragraph to edit:", target_text]
    if next_text:
        parts += ["", "Next paragraph:", next_text]
    parts += ["", f"User instruction: {instruction}", "", "Rewrite only the target paragraph. Return ONLY the new paragraph text, no explanation."]
    return "\n".join(parts)


def rewrite_paragraph(node_id: str, instruction: str) -> bool:
    """
    Rewrite one paragraph with scope-aware context (prev/next + chapter summary).
    Returns True if done, False if skipped.
    """
    scope = get_rewrite_scope(node_id)
    if not scope:
        return False
    prompt = _build_rewrite_prompt(scope, instruction)
    new_text = generate_text(prompt, temperature=0.4).strip()
    if not new_text:
        return False
    update_node(node_id, {"text": new_text})
    propagate_from_paragraph(node_id)
    update_node_embedding(node_id)
    return True


# -----------------------------------
# Add paragraph: scope = chapter summary + last N paragraphs (content so far)
# -----------------------------------

def _build_add_paragraph_prompt(scope: Dict, instruction: str) -> str:
    title = scope.get("chapter_title") or "Untitled"
    summary = scope.get("chapter_summary") or "No summary yet."
    content_so_far = scope.get("content_so_far", "").strip()
    count = scope.get("paragraph_count", 0)

    parts = [
        "You are writing the next paragraph of a story. Continue from the existing content; do not repeat it.",
        "",
        f"Chapter: {title}",
        f"Chapter summary: {summary}",
    ]
    if content_so_far:
        parts += ["", "Content so far (in order):", content_so_far]
    else:
        parts += ["", "This chapter has no content yet. Write the first paragraph."]
    parts += ["", f"User instruction: {instruction}", "", "Write the NEXT paragraph that continues the story. Return ONLY the new paragraph text, no title or explanation."]
    return "\n".join(parts)


def add_paragraph(chapter_id: str, instruction: str, after_paragraph_id: Optional[str] = None) -> bool:
    """
    Add a new paragraph to a chapter. Scope = chapter summary + content so far
    (re-fetched from graph so sequential adds see the previous new paragraph).
    If after_paragraph_id is set, insert after that paragraph; else append at end.
    """
    scope = get_add_paragraph_scope(chapter_id, after_paragraph_id)
    if scope is None:
        return False
    prompt = _build_add_paragraph_prompt(scope, instruction)
    new_text = generate_text(prompt, temperature=0.4).strip()
    if not new_text:
        return False
    node = create_paragraph_node(text=new_text, parent_id=chapter_id)
    paragraph_id = create_node(node)
    if after_paragraph_id:
        insert_child_after(chapter_id, paragraph_id, after_paragraph_id)
    propagate_from_paragraph(paragraph_id)
    create_node_embedding(paragraph_id)
    return True


# -----------------------------------
# Delete: no LLM; update graph and propagate
# -----------------------------------

def delete_paragraph(node_id: str) -> bool:
    """Delete a paragraph and update hierarchy. Returns True if done."""
    node = get_node(node_id)
    if not node or node.get("type") != "paragraph":
        return False
    chapter_id = node.get("parent_id")
    remove_node_embedding(node_id)
    delete_node(node_id)
    if chapter_id:
        propagate_from_chapter(chapter_id)
    return True


# -----------------------------------
# Direct execution with provided data (for chapter agent: no LLM, use agent output)
# -----------------------------------

def rewrite_paragraph_with_text(paragraph_id: str, new_text: str) -> bool:
    """Replace paragraph text with the given string; propagate and re-embed."""
    node = get_node(paragraph_id)
    if not node or node.get("type") != "paragraph":
        return False
    if not (new_text or new_text.strip()):
        return False
    update_node(paragraph_id, {"text": new_text.strip()})
    propagate_from_paragraph(paragraph_id)
    update_node_embedding(paragraph_id)
    return True


def add_paragraph_with_text(
    chapter_id: str,
    text: str,
    after_paragraph_id: Optional[str] = None,
) -> bool:
    """Create a new paragraph with the given text; insert after after_paragraph_id or at end."""
    chapter = get_node(chapter_id)
    if not chapter or chapter.get("type") != "chapter":
        return False
    if not (text or text.strip()):
        return False
    node = create_paragraph_node(text=text.strip(), parent_id=chapter_id)
    paragraph_id = create_node(node)
    if after_paragraph_id:
        insert_child_after(chapter_id, paragraph_id, after_paragraph_id)
    propagate_from_paragraph(paragraph_id)
    create_node_embedding(paragraph_id)
    return True


# -----------------------------------
# Apply edit plan (sequential; each add sees updated graph)
# -----------------------------------

def apply_edit_plan(edit_plan: Dict, instruction: str) -> None:
    """
    Execute the edit plan. Operations are run in order. For multiple
    add_paragraph to the same chapter, each call re-fetches chapter content
    so the next paragraph continues from the previous.
    """
    targets = edit_plan.get("target_nodes") or []
    for target in targets:
        node_id = (target.get("node_id") or "").strip()
        operation = (target.get("operation") or "").strip().lower()
        after_paragraph_id = (target.get("after_paragraph_id") or "").strip() or None
        if not node_id:
            continue
        if operation == "rewrite":
            rewrite_paragraph(node_id, instruction)
        elif operation == "add_paragraph":
            add_paragraph(node_id, instruction, after_paragraph_id=after_paragraph_id)
        elif operation == "delete":
            delete_paragraph(node_id)
