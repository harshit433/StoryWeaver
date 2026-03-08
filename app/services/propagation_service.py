from app.services.doc_index_service import update_doc_index
from app.services.graph_service import (
    get_children,
    get_document_chapters,
    get_document_id_for_node,
    get_node,
    update_node,
)
from app.services.summarizer_service import (
    summarize_paragraph,
    summarize_chapter,
    summarize_document,
)


# -----------------------------------
# Update Paragraph Summary
# -----------------------------------

def update_paragraph_summary(paragraph_id: str):

    paragraph = get_node(paragraph_id)

    if not paragraph:
        return

    text = paragraph.get("text")

    if not text:
        return

    summary = summarize_paragraph(text)

    update_node(
        paragraph_id,
        {
            "summary": summary
        }
    )


# -----------------------------------
# Update Chapter Summary
# -----------------------------------

def update_chapter_summary(chapter_id: str):

    children = get_children(chapter_id)

    paragraph_summaries = []

    for child in children:

        if child["type"] == "paragraph" and child.get("summary"):
            paragraph_summaries.append(child["summary"])

    if not paragraph_summaries:
        summary = ""
    else:
        summary = summarize_chapter(paragraph_summaries)

    update_node(
        chapter_id,
        {
            "summary": summary
        }
    )


# -----------------------------------
# Update Act Summary
# -----------------------------------

def update_act_summary(act_id: str):

    children = get_children(act_id)

    chapter_summaries = []

    for child in children:

        if child["type"] == "chapter" and child.get("summary"):
            chapter_summaries.append(child["summary"])

    if not chapter_summaries:
        return

    summary = summarize_act(chapter_summaries)

    update_node(
        act_id,
        {
            "summary": summary
        }
    )


# -----------------------------------
# Update Document Summary
# -----------------------------------

def update_document_summary(document_id: str):
    chapters = get_document_chapters(document_id)
    chapter_summaries = [
        child["summary"]
        for child in chapters
        if child.get("type") == "chapter" and child.get("summary")
    ]

    summary = summarize_document(chapter_summaries) if chapter_summaries else ""

    update_node(
        document_id,
        {
            "summary": summary
        }
    )


# -----------------------------------
# Propagate from Chapter (e.g. after paragraph deleted)
# -----------------------------------

def propagate_from_chapter(chapter_id: str):
    """
    Recompute chapter summary, document summary, and doc index.
    Call after deleting a paragraph or when chapter structure changes.
    """
    update_chapter_summary(chapter_id)
    document_id = get_document_id_for_node(chapter_id)
    if not document_id:
        return
    update_document_summary(document_id)
    update_doc_index(document_id)


# -----------------------------------
# Propagate Changes Upward
# -----------------------------------

def propagate_from_paragraph(paragraph_id: str):
    """
    Called when paragraph text changes.
    """

    paragraph = get_node(paragraph_id)

    if not paragraph:
        return

    chapter_id = paragraph["parent_id"]

    if not chapter_id:
        return

    update_paragraph_summary(paragraph_id)

    update_chapter_summary(chapter_id)
    document_id = get_document_id_for_node(chapter_id)
    if not document_id:
        return
    update_document_summary(document_id)
    update_doc_index(document_id)