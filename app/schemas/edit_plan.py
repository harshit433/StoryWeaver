from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class CreateChapterOperation(BaseModel):
    operation: Literal["create_chapter"]
    number: int = Field(ge=1)
    content: str
    title: Optional[str] = None


class DeleteChapterOperation(BaseModel):
    operation: Literal["delete_chapter"]
    number: int = Field(ge=1)


class UpdateChapterOperation(BaseModel):
    operation: Literal["update_chapter"]
    number: int = Field(ge=1)
    new_complete_chapter_content: str


class UpdateParagraphOperation(BaseModel):
    operation: Literal["update_paragraph"]
    chapter_number: int = Field(ge=1)
    paragraph_number: int = Field(ge=1)
    new_text: str


class UpdateLineOperation(BaseModel):
    operation: Literal["update_line"]
    chapter_number: int = Field(ge=1)
    paragraph_number: int = Field(ge=1)
    line_number: int = Field(ge=1)
    new_line_text: str


class AddParagraphOperation(BaseModel):
    operation: Literal["add_paragraph"]
    chapter_number: int = Field(ge=1)
    before_paragraph_number: Optional[int] = Field(default=None, ge=1)
    text: str


class AddLineOperation(BaseModel):
    operation: Literal["add_line"]
    chapter_number: int = Field(ge=1)
    paragraph_number: int = Field(ge=1)
    after_line_number: Optional[int] = Field(default=None, ge=0)
    text: str


EditOperation = Union[
    CreateChapterOperation,
    DeleteChapterOperation,
    UpdateChapterOperation,
    UpdateParagraphOperation,
    UpdateLineOperation,
    AddParagraphOperation,
    AddLineOperation,
]


class EditPlan(BaseModel):
    relevant_chapters: List[int] = Field(default_factory=list)
    reasoning: str = ""
    operations: List[EditOperation] = Field(default_factory=list)


def dump_edit_plan(plan: EditPlan) -> Dict[str, Any]:
    if hasattr(plan, "model_dump"):
        return plan.model_dump()
    return plan.dict()


def parse_edit_plan_payload(payload: Dict[str, Any]) -> EditPlan:
    raw_operations = payload.get("operations") or []
    parsed_operations: List[EditOperation] = []

    operation_map = {
        "create_chapter": CreateChapterOperation,
        "delete_chapter": DeleteChapterOperation,
        "update_chapter": UpdateChapterOperation,
        "update_paragraph": UpdateParagraphOperation,
        "update_line": UpdateLineOperation,
        "add_paragraph": AddParagraphOperation,
        "add_line": AddLineOperation,
    }

    for raw in raw_operations:
        if not isinstance(raw, dict):
            continue
        op_name = raw.get("operation")
        model = operation_map.get(op_name)
        if not model:
            continue
        try:
            parsed_operations.append(model(**raw))
        except Exception:
            continue

    return EditPlan(
        relevant_chapters=payload.get("relevant_chapters") or [],
        reasoning=(payload.get("reasoning") or "").strip(),
        operations=parsed_operations,
    )
