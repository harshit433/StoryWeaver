"""
Edit pipeline: (1) Read whole book → select chapters to edit + reasoning.
(2) For each chapter, go to paragraph level: visit each paragraph in order; for each,
    the agent gets paragraph-level context (prev/this/next) and outputs one operation
    (skip | rewrite | add_after | delete) → execute → update → continue to next paragraph.
Paragraph order is explicit (position 1, 2, 3...) so the system respects structure.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.graph_service import get_node, get_children, get_document_chapters
from app.services.context_scope import get_paragraphs_ordered, get_rewrite_scope
from app.services.patch_engine import (
    rewrite_paragraph_with_text,
    add_paragraph_with_text,
    delete_paragraph,
)
from app.llm.groq_client import generate_text

logger = logging.getLogger("writer.orchestrator")

MAX_AGENT_ITERATIONS_PER_CHAPTER = 25
MAX_PARAGRAPH_VISITS_PER_CHAPTER = 100  # safety cap for paragraph-level loop


# -----------------------------------
# Phase 1: Read book, get chapters to edit + reasoning
# -----------------------------------

def _collect_node_summary(node: dict) -> str:
    ntype = node.get("type", "")
    title = (node.get("title") or "").strip()
    summary = (node.get("summary") or node.get("text") or "").strip()
    parts = [f"[{ntype}] id={node.get('id')}"]
    if title:
        parts.append(f" title={title}")
    if summary:
        parts.append(f" summary={summary}")
    return " ".join(parts)


def _traverse_and_collect_summaries(document_id: str) -> Tuple[List[dict], str]:
    doc = get_node(document_id)
    if not doc:
        return [], ""
    nodes_flat: List[dict] = []
    lines: List[str] = []

    def walk(n: dict, depth: int) -> None:
        nodes_flat.append(n)
        indent = "  " * depth
        lines.append(indent + _collect_node_summary(n))
        for child in get_children(n["id"]):
            walk(child, depth + 1)

    walk(doc, 0)
    return nodes_flat, "\n".join(lines)


def _get_all_chapters_under_document(document_id: str) -> List[dict]:
    return get_document_chapters(document_id)


def phase1_select_chapters_with_reasoning(
    document_id: str, instruction: str
) -> Tuple[List[dict], str]:
    """
    Traverse full document, then LLM returns which chapters to edit and why.
    Returns (list of chapter nodes, reasoning string).
    """
    logger.info("Phase 1: Reading whole document and selecting chapters to edit")
    nodes, context_text = _traverse_and_collect_summaries(document_id)
    logger.info("Phase 1: Traversed %d nodes", len(nodes))
    if not nodes:
        return [], ""

    chapters = _get_all_chapters_under_document(document_id)
    if not chapters:
        logger.info("Phase 1: No chapters in document")
        return [], ""

    chapter_lines = "\n".join(
        f"  - id: {c['id']}, title: {c.get('title') or 'Untitled'}, summary: {c.get('summary') or ''}"
        for c in chapters
    )
    prompt = f"""You are analyzing a book/document to decide where to apply the user's editing instruction.

Document structure (summary of full tree):
{context_text}

Chapters in this document:
{chapter_lines}

User instruction: {instruction}

Which chapters must be edited to fulfill this instruction? Also give brief reasoning.
Return a JSON object with exactly two keys:
- "chapter_ids": array of chapter IDs (use the exact ids from the list above)
- "reasoning": string explaining why these chapters were selected

Example: {{"chapter_ids": ["uuid-1", "uuid-2"], "reasoning": "Chapter 1 sets up the storm; Chapter 3 contains the climax."}}
If no chapters need changes, return {{"chapter_ids": [], "reasoning": "..."}}"""

    response = generate_text(prompt, temperature=0.2)
    raw = _extract_json_object(response)
    try:
        data = json.loads(raw)
        ids = data.get("chapter_ids") or []
        reasoning = (data.get("reasoning") or "").strip()
    except Exception:
        ids = []
        reasoning = ""
    valid_ids = {c["id"] for c in chapters}
    target_ids = [i for i in ids if i in valid_ids]
    target_chapters = [c for c in chapters if c["id"] in target_ids]
    logger.info("Phase 1: Selected %d chapters. Reasoning: %s", len(target_chapters), reasoning[:200] if reasoning else "—")
    return target_chapters, reasoning


def _extract_json_object(text: str) -> str:
    text = text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    start = text.find("{")
    if start < 0:
        return "{}"
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return "{}"


# -----------------------------------
# Chapter state: ordered paragraphs (position 1, 2, 3...)
# -----------------------------------

def _build_chapter_state(chapter_id: str) -> str:
    """Return a string describing the chapter's paragraphs in order (position, id, content)."""
    chapter = get_node(chapter_id)
    if not chapter:
        return ""
    paras = get_paragraphs_ordered(chapter_id)
    lines = [
        f"Chapter: {chapter.get('title') or 'Untitled'} (id={chapter_id})",
        f"Summary: {chapter.get('summary') or ''}",
        "",
        "Paragraphs in order:",
    ]
    for i, p in enumerate(paras, 1):
        content = (p.get("text") or p.get("summary") or "").strip()
        lines.append(f"  {i}. id={p['id']}")
        lines.append(f"     content: {content}")
    if not paras:
        lines.append("  (no paragraphs yet)")
    return "\n".join(lines)


# -----------------------------------
# Paragraph-level: one operation per paragraph (skip | rewrite | add_after | delete)
# -----------------------------------

def _build_paragraph_level_prompt(
    paragraph_id: str,
    position: int,
    instruction: str,
    document_reasoning: str,
    chapter_title: str,
) -> str:
    """Build prompt for one paragraph with prev/this/next scope."""
    scope = get_rewrite_scope(paragraph_id)
    if not scope:
        return ""
    prev = (scope.get("prev_paragraph_text") or "").strip()
    this = (scope.get("paragraph_text") or "").strip()
    next_ = (scope.get("next_paragraph_text") or "").strip()
    parts = [
        f"You are editing chapter \"{chapter_title}\". You are at paragraph position {position} (id={paragraph_id}).",
        "",
        "User instruction: " + instruction,
        "",
        "Why this chapter was selected: " + document_reasoning,
        "",
        "Context for this paragraph:",
    ]
    if prev:
        parts += ["", "Previous paragraph:", prev]
    parts += ["", "Current paragraph (to possibly rewrite or delete):", this]
    if next_:
        parts += ["", "Next paragraph:", next_]
    parts += [
        "",
        "What do you want to do for this paragraph? Return exactly one JSON object:",
        "1. {\"op\": \"skip\"} — no change.",
        "2. {\"op\": \"rewrite\", \"new_text\": \"<full new paragraph text>\"}",
        "3. {\"op\": \"add_after\", \"text\": \"<full paragraph text>\"} — insert new paragraph after this one.",
        "4. {\"op\": \"delete\"} — remove this paragraph.",
        "",
        "Use the paragraph id above only to identify position; for rewrite/delete you are acting on this paragraph. Return only the JSON object.",
    ]
    return "\n".join(parts)


def _parse_paragraph_level_operation(response: str, paragraph_id: str) -> Optional[Dict]:
    """Parse agent response for one paragraph: skip | rewrite | add_after | delete."""
    raw = _extract_json_object(response)
    try:
        data = json.loads(raw)
    except Exception:
        return None
    op = (data.get("op") or "").strip().lower()
    if op == "skip":
        return {"op": "skip"}
    if op == "rewrite":
        new_text = data.get("new_text")
        if new_text is not None:
            return {"op": "rewrite", "paragraph_id": paragraph_id, "new_text": str(new_text)}
    if op == "add_after":
        text = data.get("text")
        if text is not None:
            return {"op": "add_paragraph", "text": str(text), "after_paragraph_id": paragraph_id}
    if op == "delete":
        return {"op": "delete", "paragraph_id": paragraph_id}
    return None


# -----------------------------------
# Chapter agent: one operation at a time until done
# -----------------------------------

def _parse_one_operation(response: str) -> Optional[Dict]:
    """Parse agent response into one op: done | rewrite | add_paragraph | delete."""
    raw = _extract_json_object(response)
    try:
        data = json.loads(raw)
    except Exception:
        return None
    op = (data.get("op") or "").strip().lower()
    if op == "done":
        return {"op": "done"}
    if op == "rewrite":
        pid = data.get("paragraph_id")
        new_text = data.get("new_text")
        if pid and new_text is not None:
            return {"op": "rewrite", "paragraph_id": str(pid), "new_text": str(new_text)}
    if op == "add_paragraph":
        text = data.get("text")
        if text is not None:
            after = data.get("after_paragraph_id")
            return {
                "op": "add_paragraph",
                "text": str(text),
                "after_paragraph_id": str(after).strip() or None,
            }
    if op == "delete":
        pid = data.get("paragraph_id")
        if pid:
            return {"op": "delete", "paragraph_id": str(pid)}
    return None


def _execute_one_operation(
    chapter_id: str,
    op_spec: Dict,
) -> bool:
    """Execute a single operation (rewrite/add_paragraph/delete) with agent-provided data."""
    op = op_spec.get("op")
    if op == "done":
        return True
    if op == "rewrite":
        return rewrite_paragraph_with_text(
            op_spec["paragraph_id"],
            op_spec.get("new_text", ""),
        )
    if op == "add_paragraph":
        return add_paragraph_with_text(
            chapter_id,
            op_spec.get("text", ""),
            op_spec.get("after_paragraph_id"),
        )
    if op == "delete":
        return delete_paragraph(op_spec["paragraph_id"])
    return False


def run_chapter_paragraph_level_loop(
    chapter_id: str,
    chapter_title: str,
    instruction: str,
    document_reasoning: str,
) -> int:
    """
    For one chapter: go to paragraph level. Visit each paragraph in order; for each,
    ask the agent what to do (skip | rewrite | add_after | delete) with paragraph-level
    context (prev/this/next). Execute the operation and continue. After delete, re-fetch
    and stay at same index; after add_after, re-fetch and advance so the new paragraph
    is visited next.
    Returns number of operations performed.
    """
    logger.info("Chapter paragraph-level: starting for chapter '%s'", chapter_title)
    count = 0
    visit_count = 0
    while visit_count < MAX_PARAGRAPH_VISITS_PER_CHAPTER:
        paragraphs = get_paragraphs_ordered(chapter_id)
        if not paragraphs:
            # No paragraphs: one shot to add at start
            prompt = f"""You are editing chapter "{chapter_title}". The chapter has no paragraphs yet.

User instruction: {instruction}
Why this chapter was selected: {document_reasoning}

Do you want to add the first paragraph? Return JSON: {{"op": "add_after", "text": "<full paragraph>"}} or {{"op": "skip"}}."""
            response = generate_text(prompt, temperature=0.3)
            raw = _extract_json_object(response)
            try:
                data = json.loads(raw)
                op = (data.get("op") or "").strip().lower()
                if op == "add_after" and data.get("text") is not None:
                    if add_paragraph_with_text(chapter_id, str(data.get("text")), None):
                        count += 1
            except Exception:
                pass
            return count

        i = 0
        while i < len(paragraphs) and visit_count < MAX_PARAGRAPH_VISITS_PER_CHAPTER:
            p = paragraphs[i]
            pid = p["id"]
            position = i + 1
            visit_count += 1
            prompt = _build_paragraph_level_prompt(
                pid, position, instruction, document_reasoning, chapter_title
            )
            if not prompt:
                i += 1
                continue
            response = generate_text(prompt, temperature=0.3)
            spec = _parse_paragraph_level_operation(response, pid)
            if not spec:
                logger.warning("Paragraph-level: could not parse at position %d", position)
                i += 1
                continue
            if spec.get("op") == "skip":
                i += 1
                continue
            logger.info("Paragraph-level: position %d executing %s", position, spec.get("op"))
            if spec.get("op") == "rewrite":
                if rewrite_paragraph_with_text(pid, spec.get("new_text", "")):
                    count += 1
                i += 1
            elif spec.get("op") == "add_paragraph":
                if add_paragraph_with_text(
                    chapter_id, spec.get("text", ""), spec.get("after_paragraph_id")
                ):
                    count += 1
                # Re-fetch so next iteration we see the new paragraph at i+1
                paragraphs = get_paragraphs_ordered(chapter_id)
                i += 1
            elif spec.get("op") == "delete":
                if delete_paragraph(pid):
                    count += 1
                # Re-fetch; same index i now points to the next paragraph
                paragraphs = get_paragraphs_ordered(chapter_id)
                # do not increment i
        else:
            break
    logger.info("Chapter paragraph-level: completed with %d operations", count)
    return count


def run_chapter_agent_loop(
    chapter_id: str,
    chapter_title: str,
    instruction: str,
    document_reasoning: str,
) -> int:
    """
    For one chapter: repeatedly ask the agent for one operation, execute it, update state, until done.
    Returns number of operations performed.
    """
    logger.info("Chapter agent: starting for chapter '%s'", chapter_title)
    count = 0
    for step in range(MAX_AGENT_ITERATIONS_PER_CHAPTER):
        state = _build_chapter_state(chapter_id)
        prompt = f"""You are editing a single chapter of a book. The user has given an instruction. You must output exactly ONE immediate operation to perform.

User instruction: {instruction}

Why this chapter was selected: {document_reasoning}

Current state of this chapter (paragraphs are in strict order; position matters):
{state}

Output exactly one operation as JSON. Choose one:
1. {{"op": "done"}} — the instruction is fully satisfied for this chapter; no more edits needed.
2. {{"op": "rewrite", "paragraph_id": "<id from list above>", "new_text": "<full new paragraph text>"}}
3. {{"op": "add_paragraph", "text": "<full paragraph text>", "after_paragraph_id": "<id> or null for end"}}
4. {{"op": "delete", "paragraph_id": "<id from list above>"}}

Use the exact paragraph ids from the current state. For add_paragraph, use after_paragraph_id to preserve order (null = append at end). Return only the JSON object."""

        response = generate_text(prompt, temperature=0.3)
        spec = _parse_one_operation(response)
        if not spec:
            logger.warning("Chapter agent: could not parse response at step %d", step + 1)
            continue
        if spec.get("op") == "done":
            logger.info("Chapter agent: done after %d operations", count)
            return count
        logger.info("Chapter agent: step %d executing %s", step + 1, spec.get("op"))
        ok = _execute_one_operation(chapter_id, spec)
        if ok:
            count += 1
        else:
            logger.warning("Chapter agent: operation failed at step %d", step + 1)
    logger.info("Chapter agent: max iterations reached (%d ops)", count)
    return count


# -----------------------------------
# Full pipeline
# -----------------------------------

def run_edit_pipeline(instruction: str, document_id: str) -> Dict[str, Any]:
    """
    1. Read whole book → select chapters to edit + reasoning.
    2. For each chapter: agent loop (one op → execute → update → repeat until done).
    """
    logger.info("=== Edit pipeline started: document_id=%s instruction=%s", document_id[:8], instruction[:80])
    target_chapters, reasoning = phase1_select_chapters_with_reasoning(document_id, instruction)
    if not target_chapters:
        logger.info("Phase 1: No chapters to edit")
        return {
            "chapters_selected": [],
            "reasoning": reasoning,
            "status": "no chapters to edit",
        }

    total_ops = 0
    for ch in target_chapters:
        n = run_chapter_paragraph_level_loop(
            ch["id"],
            ch.get("title") or ch["id"],
            instruction,
            reasoning,
        )
        total_ops += n

    logger.info("=== Edit pipeline completed: %d chapters, %d total operations ===", len(target_chapters), total_ops)
    return {
        "chapters_selected": [c["id"] for c in target_chapters],
        "reasoning": reasoning,
        "status": "edits applied",
        "operations_performed": total_ops,
    }
