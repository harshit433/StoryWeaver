import json
import re
from typing import Dict, List

from app.schemas.edit_plan import EditPlan, parse_edit_plan_payload
from app.services.llm_errors import normalize_model_error, raise_if_model_error_text
from app.services.request_settings import get_required_groq_api_key

try:
    from agno.agent import Agent
    from agno.models.groq import Groq as AgnoGroq
except ImportError:  # pragma: no cover - runtime dependency
    Agent = None
    AgnoGroq = None


def _extract_json_object(text: str) -> Dict:
    text = (text or "").strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

    start = text.find("{")
    if start < 0:
        return {}
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : index + 1])
                except Exception:
                    return {}
    return {}


def _build_planning_agent() -> "Agent":
    if Agent is None or AgnoGroq is None:
        raise RuntimeError(
            "Agno is not installed. Add the 'agno' dependency and install project requirements."
        )
    return Agent(
        model=AgnoGroq(
            id="llama-3.3-70b-versatile",
            api_key=get_required_groq_api_key(),
        ),
        instructions="""
You are the planning agent for a writing assistant.

You will receive:
- the user instruction
- the relevant chapter numbers
- a numbered chapter/paragraph/line view of those chapters

Return only JSON with this exact shape:
{
  "relevant_chapters": [1, 2],
  "reasoning": "Short explanation",
  "operations": [
    {"operation": "create_chapter", "number": 4, "content": "full chapter text", "title": "optional title"},
    {"operation": "delete_chapter", "number": 2},
    {"operation": "update_chapter", "number": 3, "new_complete_chapter_content": "full chapter text"},
    {"operation": "update_paragraph", "chapter_number": 3, "paragraph_number": 2, "new_text": "full paragraph text"},
    {"operation": "update_line", "chapter_number": 3, "paragraph_number": 2, "line_number": 1, "new_line_text": "full line text"},
    {"operation": "add_paragraph", "chapter_number": 3, "before_paragraph_number": 2, "text": "full paragraph text"},
    {"operation": "add_line", "chapter_number": 3, "paragraph_number": 2, "after_line_number": 1, "text": "full line text"}
  ]
}

Rules:
- Use chapter_number, paragraph_number, and line_number from the numbered input.
- Use the most localized operation possible.
- Use update_chapter only when the whole chapter should be replaced.
- Use create_chapter and delete_chapter only when the request changes chapter structure.
- Return only JSON.
""".strip(),
        markdown=False,
    )


def create_edit_plan(
    document_id: str,
    instruction: str,
    relevant_chapters: List[int],
    numbered_chapters: List[Dict],
    reasoning: str,
) -> EditPlan:
    agent = _build_planning_agent()
    try:
        response = agent.run(
            "\n".join(
                [
                    f"Document ID: {document_id}",
                    f"User instruction: {instruction}",
                    f"Relevant chapters: {relevant_chapters}",
                    f"Thinking step reasoning: {reasoning}",
                    "Numbered chapter view:",
                    json.dumps(numbered_chapters, indent=2),
                ]
            )
        )
    except Exception as exc:
        raise normalize_model_error(exc) from exc
    response_text = str(getattr(response, "content", "") or "")
    raise_if_model_error_text(response_text)
    payload = _extract_json_object(response_text)
    if "relevant_chapters" not in payload:
        payload["relevant_chapters"] = relevant_chapters
    if "reasoning" not in payload:
        payload["reasoning"] = reasoning
    return parse_edit_plan_payload(payload)
