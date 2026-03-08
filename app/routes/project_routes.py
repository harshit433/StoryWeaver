from fastapi import APIRouter
from typing import Dict

from app.models.node_model import (
    create_document_node,
    create_chapter_node,
    create_paragraph_node,
)

from app.services.graph_service import (
    create_node,
    delete_node,
    get_children,
    get_documents,
    get_document_chapters,
    get_node,
    update_node,
)
from app.services.embedding_service import (
    create_node_embedding,
    remove_node_embedding,
    update_node_embedding,
)
from app.services.doc_index_service import delete_doc_index, update_doc_index
from app.services.propagation_service import (
    propagate_from_paragraph,
    update_document_summary,
)
from app.services.paragraph_service import get_chapter_content, sync_paragraphs


router = APIRouter(
    prefix="/project",
    tags=["Project"]
)


def _remove_subtree_embeddings(node_id: str) -> None:
    node = get_node(node_id)
    if not node:
        return
    remove_node_embedding(node_id)
    for child in get_children(node_id):
        _remove_subtree_embeddings(child["id"])


# -----------------------------------
# Create Project (Document Node)
# -----------------------------------

@router.post("/create")
def create_project(payload: Dict):

    title = payload.get("title")

    if not title:
        return {"error": "title required"}

    node = create_document_node(title)

    node_id = create_node(node)

    create_node_embedding(node_id)
    update_doc_index(node_id)

    return {
        "project_id": node_id,
        "title": title
    }


# -----------------------------------
# Create Chapter
# -----------------------------------

@router.post("/chapter")
def create_chapter(payload: Dict):

    title = payload.get("title")
    document_id = payload.get("document_id")

    if not title or not document_id:
        return {"error": "title and document_id required"}

    node = create_chapter_node(title, document_id)

    chapter_id = create_node(node)

    create_node_embedding(chapter_id)
    update_document_summary(document_id)
    update_doc_index(document_id)

    return {
        "chapter_id": chapter_id,
        "title": title
    }


# -----------------------------------
# List Documents
# -----------------------------------

@router.get("/documents")
def list_documents():
    """
    Return all document nodes (for tree navigation).
    """
    documents = get_documents()
    return {"documents": documents}


@router.delete("/{document_id}")
def delete_project(document_id: str):
    document = get_node(document_id)
    if not document or document.get("type") != "document":
        return {"error": "document not found"}

    _remove_subtree_embeddings(document_id)
    delete_doc_index(document_id)
    delete_node(document_id)
    return {"status": "deleted", "document_id": document_id}


# -----------------------------------
# Get / Update chapter content (user-facing: one blob, backend: paragraphs)
# -----------------------------------

@router.get("/chapter/{chapter_id}/content")
def get_chapter_content_route(chapter_id: str):
    """Return full chapter text for editing (paragraphs joined by \\n\\n)."""
    chapter = get_node(chapter_id)
    if not chapter or chapter.get("type") != "chapter":
        return {"error": "chapter not found"}
    text = get_chapter_content(chapter_id)
    return {"chapter_id": chapter_id, "text": text}


@router.patch("/chapter/{chapter_id}/content")
def update_chapter_content(chapter_id: str, payload: Dict):
    """Set full chapter text; backend splits into paragraphs and syncs."""
    chapter = get_node(chapter_id)
    if not chapter or chapter.get("type") != "chapter":
        return {"error": "chapter not found"}
    text = payload.get("text")
    if text is None:
        return {"error": "text required"}
    sync_paragraphs(chapter_id, text)
    return {"chapter_id": chapter_id, "text": get_chapter_content(chapter_id)}


# -----------------------------------
# Get Full Document Tree
# -----------------------------------

@router.get("/tree/{document_id}")
def get_document_tree(document_id: str):
    """
    Return full hierarchy: document → chapters → paragraphs.
    Legacy act nodes are flattened away.
    """
    document = get_node(document_id)
    if not document or document.get("type") != "document":
        return {"error": "document not found"}

    chapters = get_document_chapters(document_id)
    chapter_trees = []
    for chapter in chapters:
        paragraphs = [
            child
            for child in (get_node(pid) for pid in chapter.get("children_ids", []))
            if child and child.get("type") == "paragraph"
        ]
        chapter_copy = dict(chapter)
        chapter_copy["children"] = paragraphs
        chapter_trees.append(chapter_copy)

    document_copy = dict(document)
    document_copy["children"] = chapter_trees
    return document_copy


# -----------------------------------
# Create Paragraph
# -----------------------------------

@router.post("/paragraph")
def create_paragraph(payload: Dict):

    text = payload.get("text")
    chapter_id = payload.get("chapter_id")

    if not text or not chapter_id:
        return {"error": "text and chapter_id required"}

    node = create_paragraph_node(text=text, parent_id=chapter_id)

    paragraph_id = create_node(node)

    propagate_from_paragraph(paragraph_id)

    create_node_embedding(paragraph_id)

    created = get_node(paragraph_id)

    return {
        "paragraph_id": paragraph_id,
        "text": text,
        "summary": created.get("summary"),
    }


# -----------------------------------
# Update Paragraph (editor save)
# -----------------------------------

@router.patch("/paragraph/{paragraph_id}")
def update_paragraph(paragraph_id: str, payload: Dict):

    text = payload.get("text")

    if text is None:
        return {"error": "text required"}

    node = get_node(paragraph_id)

    if not node or node.get("type") != "paragraph":
        return {"error": "paragraph not found"}

    update_node(paragraph_id, {"text": text})
    propagate_from_paragraph(paragraph_id)
    update_node_embedding(paragraph_id)

    updated = get_node(paragraph_id)

    return {
        "paragraph_id": paragraph_id,
        "text": updated.get("text"),
        "summary": updated.get("summary"),
    }