from typing import Iterable, List, Optional

from app.models.node_model import create_chapter_node, create_paragraph_node
from app.schemas.edit_plan import (
    AddLineOperation,
    AddParagraphOperation,
    CreateChapterOperation,
    DeleteChapterOperation,
    EditPlan,
    UpdateChapterOperation,
    UpdateLineOperation,
    UpdateParagraphOperation,
)
from app.services.doc_index_service import update_doc_index
from app.services.embedding_service import (
    create_node_embedding,
    remove_node_embedding,
    update_node_embedding,
)
from app.services.graph_service import (
    create_node,
    delete_node,
    get_children,
    get_document_chapters,
    get_document_id_for_node,
    get_node,
    insert_child_at_index,
    insert_child_before,
    update_node,
)
from app.services.paragraph_service import sync_paragraphs
from app.services.propagation_service import (
    propagate_from_chapter,
    propagate_from_paragraph,
    update_document_summary,
)


def _get_chapter_by_number(document_id: str, chapter_number: int) -> Optional[dict]:
    chapters = get_document_chapters(document_id)
    if chapter_number < 1 or chapter_number > len(chapters):
        return None
    return chapters[chapter_number - 1]


def _get_paragraph_by_number(chapter_id: str, paragraph_number: int) -> Optional[dict]:
    paragraphs = [child for child in get_children(chapter_id) if child.get("type") == "paragraph"]
    if paragraph_number < 1 or paragraph_number > len(paragraphs):
        return None
    return paragraphs[paragraph_number - 1]


def _remove_subtree_embeddings(node_id: str) -> None:
    node = get_node(node_id)
    if not node:
        return
    remove_node_embedding(node_id)
    for child in get_children(node_id):
        _remove_subtree_embeddings(child["id"])


def _replace_line(text: str, line_number: int, new_line_text: str) -> Optional[str]:
    lines = text.split("\n")
    if line_number < 1 or line_number > len(lines):
        return None
    lines[line_number - 1] = new_line_text
    return "\n".join(lines)


def _insert_line(text: str, after_line_number: Optional[int], line_text: str) -> str:
    lines = text.split("\n")
    if after_line_number is None:
        return line_text if not text else f"{line_text}\n{text}"
    index = max(0, min(after_line_number, len(lines)))
    new_lines = lines[:index] + [line_text] + lines[index:]
    return "\n".join(new_lines)


def _execute_create_chapter(document_id: str, op: CreateChapterOperation) -> bool:
    title = op.title or f"Chapter {op.number}"
    node = create_chapter_node(title=title, parent_id=document_id)
    chapter_id = create_node(node)
    insert_child_at_index(document_id, chapter_id, op.number - 1)
    sync_paragraphs(chapter_id, op.content)
    create_node_embedding(chapter_id)
    update_document_summary(document_id)
    update_doc_index(document_id)
    return True


def _execute_delete_chapter(document_id: str, op: DeleteChapterOperation) -> bool:
    chapter = _get_chapter_by_number(document_id, op.number)
    if not chapter:
        return False
    _remove_subtree_embeddings(chapter["id"])
    delete_node(chapter["id"])
    update_document_summary(document_id)
    update_doc_index(document_id)
    return True


def _execute_update_chapter(document_id: str, op: UpdateChapterOperation) -> bool:
    chapter = _get_chapter_by_number(document_id, op.number)
    if not chapter:
        return False
    sync_paragraphs(chapter["id"], op.new_complete_chapter_content)
    update_node_embedding(chapter["id"])
    update_doc_index(document_id)
    return True


def _execute_update_paragraph(document_id: str, op: UpdateParagraphOperation) -> bool:
    chapter = _get_chapter_by_number(document_id, op.chapter_number)
    if not chapter:
        return False
    paragraph = _get_paragraph_by_number(chapter["id"], op.paragraph_number)
    if not paragraph:
        return False
    update_node(paragraph["id"], {"text": op.new_text})
    propagate_from_paragraph(paragraph["id"])
    update_node_embedding(paragraph["id"])
    return True


def _execute_update_line(document_id: str, op: UpdateLineOperation) -> bool:
    chapter = _get_chapter_by_number(document_id, op.chapter_number)
    if not chapter:
        return False
    paragraph = _get_paragraph_by_number(chapter["id"], op.paragraph_number)
    if not paragraph:
        return False
    updated_text = _replace_line(paragraph.get("text") or "", op.line_number, op.new_line_text)
    if updated_text is None:
        return False
    update_node(paragraph["id"], {"text": updated_text})
    propagate_from_paragraph(paragraph["id"])
    update_node_embedding(paragraph["id"])
    return True


def _execute_add_paragraph(document_id: str, op: AddParagraphOperation) -> bool:
    chapter = _get_chapter_by_number(document_id, op.chapter_number)
    if not chapter:
        return False

    node = create_paragraph_node(text=op.text, parent_id=chapter["id"])
    paragraph_id = create_node(node)
    if op.before_paragraph_number is not None:
        before_paragraph = _get_paragraph_by_number(chapter["id"], op.before_paragraph_number)
        if before_paragraph:
            insert_child_before(chapter["id"], paragraph_id, before_paragraph["id"])
    propagate_from_paragraph(paragraph_id)
    create_node_embedding(paragraph_id)
    return True


def _execute_add_line(document_id: str, op: AddLineOperation) -> bool:
    chapter = _get_chapter_by_number(document_id, op.chapter_number)
    if not chapter:
        return False
    paragraph = _get_paragraph_by_number(chapter["id"], op.paragraph_number)
    if not paragraph:
        return False
    updated_text = _insert_line(paragraph.get("text") or "", op.after_line_number, op.text)
    update_node(paragraph["id"], {"text": updated_text})
    propagate_from_paragraph(paragraph["id"])
    update_node_embedding(paragraph["id"])
    return True


def execute_edit_plan(document_id: str, edit_plan: EditPlan) -> List[dict]:
    results = []
    for operation in edit_plan.operations:
        success = False
        if isinstance(operation, CreateChapterOperation):
            success = _execute_create_chapter(document_id, operation)
        elif isinstance(operation, DeleteChapterOperation):
            success = _execute_delete_chapter(document_id, operation)
        elif isinstance(operation, UpdateChapterOperation):
            success = _execute_update_chapter(document_id, operation)
        elif isinstance(operation, UpdateParagraphOperation):
            success = _execute_update_paragraph(document_id, operation)
        elif isinstance(operation, UpdateLineOperation):
            success = _execute_update_line(document_id, operation)
        elif isinstance(operation, AddParagraphOperation):
            success = _execute_add_paragraph(document_id, operation)
        elif isinstance(operation, AddLineOperation):
            success = _execute_add_line(document_id, operation)

        results.append({"operation": operation.operation, "success": success})

    update_doc_index(document_id)
    return results
