import re
from typing import Any, Dict, List

from app.agents.planning_agent import create_edit_plan
from app.agents.thinking_agent import think_relevant_chapters
from app.schemas.edit_plan import EditPlan, dump_edit_plan
from app.services.doc_index_service import get_doc_index
from app.services.numbered_content import build_numbered_document_view
from app.services.plan_executor import execute_edit_plan


def _extract_explicit_chapter_numbers(instruction: str) -> List[int]:
    matches = re.findall(r"\bchapter\s+(\d+)\b", instruction, flags=re.IGNORECASE)
    seen = []
    for match in matches:
        number = int(match)
        if number not in seen:
            seen.append(number)
    return seen


def run_agno_edit_pipeline(document_id: str, instruction: str) -> Dict[str, Any]:
    doc_index = get_doc_index(document_id)
    if not (doc_index.get("chapters") or []):
        empty_plan = EditPlan(relevant_chapters=[], reasoning="", operations=[])
        return {
            "relevant_chapters": [],
            "reasoning": "This document has no chapters yet.",
            "edit_plan": dump_edit_plan(empty_plan),
            "execution_results": [],
            "status": "no chapters to edit",
        }

    thinking = think_relevant_chapters(document_id, instruction)
    relevant_chapters = thinking.get("relevant_chapters") or []
    for chapter_number in _extract_explicit_chapter_numbers(instruction):
        if chapter_number not in relevant_chapters:
            relevant_chapters.append(chapter_number)
    relevant_chapters = sorted(
        {
            chapter_number
            for chapter_number in relevant_chapters
            if 1 <= chapter_number <= len(doc_index.get("chapters") or [])
        }
    )

    if not relevant_chapters and instruction.strip():
        top_hit = (doc_index.get("chapters") or [])[:1]
        if top_hit:
            relevant_chapters = [top_hit[0]["order"]]

    numbered_chapters = build_numbered_document_view(document_id, relevant_chapters)
    edit_plan = create_edit_plan(
        document_id=document_id,
        instruction=instruction,
        relevant_chapters=relevant_chapters,
        numbered_chapters=numbered_chapters,
        reasoning=thinking.get("reasoning") or "",
    )
    execution_results = execute_edit_plan(document_id, edit_plan)

    return {
        "relevant_chapters": edit_plan.relevant_chapters,
        "reasoning": edit_plan.reasoning,
        "edit_plan": dump_edit_plan(edit_plan),
        "execution_results": execution_results,
        "operations_performed": sum(1 for result in execution_results if result.get("success")),
        "status": "edits applied" if execution_results else "no edits planned",
    }
