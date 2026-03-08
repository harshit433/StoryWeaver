from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Dict

from app.services.reasoning_engine import generate_edit_plan
from app.services.patch_engine import apply_edit_plan
from app.agents.planning_agent import create_edit_plan
from app.agents.thinking_agent import think_relevant_chapters
from app.schemas.edit_plan import dump_edit_plan
from app.services.agno_pipeline import run_agno_edit_pipeline
from app.services.llm_errors import ModelServiceError
from app.services.numbered_content import build_numbered_document_view


router = APIRouter(
    prefix="/reasoning",
    tags=["Reasoning"]
)


# -----------------------------------
# Generate Edit Plan
# -----------------------------------

@router.post("/plan")
def generate_plan(payload: Dict):
    """
    Generate an edit plan for a user instruction.
    Uses the Agno thinking + planning pipeline when document_id is provided.
    """

    instruction = payload.get("instruction")
    document_id = payload.get("document_id")

    if not instruction:
        return {"error": "instruction required"}

    try:
        if document_id:
            thinking = think_relevant_chapters(document_id, instruction)
            numbered = build_numbered_document_view(
                document_id,
                thinking.get("relevant_chapters") or [],
            )
            plan = create_edit_plan(
                document_id=document_id,
                instruction=instruction,
                relevant_chapters=thinking.get("relevant_chapters") or [],
                numbered_chapters=numbered,
                reasoning=thinking.get("reasoning") or "",
            )
            return {"edit_plan": dump_edit_plan(plan)}
    except ModelServiceError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    plan = generate_edit_plan(instruction, document_id=document_id)

    return {
        "edit_plan": plan
    }


# -----------------------------------
# Apply Edit Plan
# -----------------------------------

@router.post("/apply")
def apply_plan(payload: Dict):
    """
    Apply edit plan to the document.
    """

    instruction = payload.get("instruction")
    edit_plan = payload.get("edit_plan")

    if not instruction or not edit_plan:
        return {"error": "instruction and edit_plan required"}

    apply_edit_plan(edit_plan, instruction)

    return {
        "status": "edits applied"
    }


# -----------------------------------
# Reason + Apply in One Step
# -----------------------------------

@router.post("/execute")
def execute_reasoning(payload: Dict):
    """
    Full pipeline: when document_id is provided, use Agno thinking -> planning -> execute.
    Otherwise use the legacy fallback path.
    """

    instruction = payload.get("instruction")
    document_id = payload.get("document_id")

    if not instruction:
        return {"error": "instruction required"}

    try:
        if document_id:
            result = run_agno_edit_pipeline(document_id, instruction)
            return result
    except ModelServiceError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message},
        )

    edit_plan = generate_edit_plan(instruction, document_id=None)
    apply_edit_plan(edit_plan, instruction)
    return {"edit_plan": edit_plan, "status": "edits applied"}