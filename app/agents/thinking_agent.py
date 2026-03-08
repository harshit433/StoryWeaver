import json
import re
from typing import Dict, List

from app.services.llm_errors import normalize_model_error, raise_if_model_error_text
from app.services.doc_index_service import find_relevant_chapters
from app.services.numbered_content import get_numbered_chapter
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


def search_chapter_summaries(document_id: str, query: str, top_k: int = 5) -> str:
    """
    Search the doc index and return the most relevant chapter summaries.
    """
    matches = find_relevant_chapters(document_id, query, limit=top_k)
    return json.dumps(matches, indent=2)


def read_chapter(document_id: str, chapter_number: int) -> str:
    """
    Read a complete chapter with full content.
    """
    chapter = get_numbered_chapter(document_id, chapter_number)
    if not chapter:
        return json.dumps({"error": "chapter not found"})
    return json.dumps(
        {
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "summary": chapter["summary"],
            "content": chapter["content"],
        },
        indent=2,
    )


def _build_thinking_agent() -> "Agent":
    if Agent is None or AgnoGroq is None:
        raise RuntimeError(
            "Agno is not installed. Add the 'agno' dependency and install project requirements."
        )
    return Agent(
        model=AgnoGroq(
            id="llama-3.3-70b-versatile",
            api_key=get_required_groq_api_key(),
        ),
        tools=[search_chapter_summaries, read_chapter],
        instructions="""
You are the thinking agent for a writing assistant.

Your job is to decide which chapters are relevant to the user's request.
Start from the chapter summaries tool. If the summaries are not enough, use the read_chapter tool
to inspect the full content of one or more chapters before deciding.

Always return one JSON object with this exact shape:
{
  "relevant_chapters": [1, 2],
  "reasoning": "Short explanation of why these chapters matter."
}

Rules:
- Prefer the smallest chapter set that fully satisfies the request.
- If the instruction explicitly names chapter numbers, include them.
- Return chapter numbers, not UUIDs.
- Return only JSON.
""".strip(),
        markdown=False,
    )


def think_relevant_chapters(document_id: str, instruction: str) -> Dict:
    agent = _build_thinking_agent()
    try:
        response = agent.run(
            f"Document ID: {document_id}\nUser instruction: {instruction}"
        )
    except Exception as exc:
        raise normalize_model_error(exc) from exc
    response_text = str(getattr(response, "content", "") or "")
    raise_if_model_error_text(response_text)
    payload = _extract_json_object(response_text)
    relevant = payload.get("relevant_chapters") or []
    reasoning = (payload.get("reasoning") or "").strip()
    return {
        "relevant_chapters": [
            int(chapter_number)
            for chapter_number in relevant
            if isinstance(chapter_number, int) or str(chapter_number).isdigit()
        ],
        "reasoning": reasoning,
    }
