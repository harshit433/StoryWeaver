import json
import re
from typing import Dict, List, Optional

from app.services.retrieval_service import build_context
from app.llm.groq_client import generate_text


# -----------------------------------
# Build Reasoning Prompt
# -----------------------------------

def build_reasoning_prompt(instruction: str, context_nodes: List[dict]) -> str:
    """
    Build prompt so the LLM returns an edit plan with supported operations.
    For paragraphs we include full text so the LLM can choose what to rewrite/delete.
    """

    context_text = ""
    for node in context_nodes:
        node_type = node.get("type")
        node_id = node.get("id")
        title = node.get("title") or ""
        # For paragraphs, always include full text so we can decide rewrite/delete
        content = node.get("text") or node.get("summary") or ""
        if node_type == "paragraph" and not content and node.get("summary"):
            content = node.get("summary")
        content = (content or "").strip()

        context_text += f"""
Node ID: {node_id}
Node Type: {node_type}
Title: {title}
Content:
{content if content else "(empty)"}
"""

    prompt = f"""You are an AI edit planner for a structured book/document.

Structure: document → chapter → paragraph.
Only paragraphs have editable "Content" (body text). Chapters have titles and summaries.

Relevant context from the document:

{context_text}

User instruction: {instruction}

Decide what edits to make. You can use these operations:

1. **rewrite** – Change existing paragraph text. node_id must be a PARAGRAPH id. Use when the user wants to modify existing content (e.g. "make it scarier", "shorten this").

2. **add_paragraph** – Add a new paragraph. node_id must be a CHAPTER id (the new paragraph will be added to that chapter). Use when the user wants new content (e.g. "write an opening", "add a scene with..."). For "write in chapter X" or "add to chapter X", use add_paragraph with that chapter's id.

3. **delete** – Remove a paragraph. node_id must be a PARAGRAPH id. Use when the user wants to remove or cut content.

Rules:
- For rewrite or delete, node_id must be a paragraph (type paragraph) — use the exact Node ID from the context above.
- For add_paragraph, node_id must be a chapter (type chapter) — use the exact Node ID from the context above.
- If a chapter has no paragraphs yet and the user asks to "write" or "add" something there, use add_paragraph with that chapter's id.
- For goals like "make this chapter 2000 words" or "expand this chapter", you may output multiple add_paragraph operations for the same chapter; they will be executed in order and each new paragraph will continue from the previous.
- Return only valid node_ids from the context above (exact IDs listed).

Return a single JSON object with this exact shape (no markdown, no extra text):

{{"target_nodes": [
  {{"node_id": "<paragraph_id>", "operation": "rewrite"}},
  {{"node_id": "<chapter_id>", "operation": "add_paragraph"}},
  {{"node_id": "<chapter_id>", "operation": "add_paragraph", "after_paragraph_id": "<id>"}},
  {{"node_id": "<paragraph_id>", "operation": "delete"}}
]}}

Optional: for add_paragraph, include "after_paragraph_id" (a paragraph id from context) only when the new paragraph must be inserted after a specific paragraph; otherwise omit it (new paragraph is added at end of chapter).

Use only operations: rewrite, add_paragraph, delete. If nothing to do, return {{"target_nodes": []}}."""

    return prompt


# -----------------------------------
# Parse Edit Plan
# -----------------------------------

def _extract_json(text: str) -> str:
    """Strip markdown code blocks and return JSON string."""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
    # Find first { ... } block
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return text


def parse_edit_plan(response: str) -> Dict:
    """
    Convert LLM output into a structured edit plan. Validates operations.
    """
    try:
        raw = _extract_json(response)
        plan = json.loads(raw)
        nodes = plan.get("target_nodes") or []
        allowed = {"rewrite", "add_paragraph", "delete"}
        validated = []
        for t in nodes:
            if not isinstance(t, dict):
                continue
            node_id = t.get("node_id")
            op = (t.get("operation") or "").strip().lower()
            if node_id and op in allowed:
                entry = {"node_id": str(node_id), "operation": op}
                if op == "add_paragraph" and t.get("after_paragraph_id"):
                    entry["after_paragraph_id"] = str(t.get("after_paragraph_id"))
                validated.append(entry)
        plan["target_nodes"] = validated
        return plan
    except Exception:
        return {"target_nodes": []}


# -----------------------------------
# Main Reasoning Function
# -----------------------------------

def generate_edit_plan(instruction: str, document_id: Optional[str] = None) -> Dict:
    """
    Main reasoning pipeline.

    When document_id is provided, context is retrieved via top-down LLM traversal
    (document → chapters → paragraphs). Otherwise uses embedding similarity.
    """

    # Step 1: Retrieve context (traversal if document_id, else embedding)
    context_nodes = build_context(instruction, document_id=document_id)

    # Step 2: Build reasoning prompt
    prompt = build_reasoning_prompt(instruction, context_nodes)

    # Step 3: Ask LLM
    response = generate_text(prompt)

    # Step 4: Parse plan
    edit_plan = parse_edit_plan(response)

    return edit_plan