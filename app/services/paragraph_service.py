from typing import List

from app.models.node_model import create_paragraph_node
from app.services.graph_service import create_node, get_children, update_node, delete_node
from app.services.propagation_service import propagate_from_paragraph, propagate_from_chapter
from app.services.embedding_service import (
    create_node_embedding,
    update_node_embedding,
    remove_node_embedding,
)


# -----------------------------------
# Get chapter content (paragraphs joined for user-facing view)
# -----------------------------------

def get_chapter_content(chapter_id: str) -> str:
    """
    Return full chapter text: paragraphs in order, joined by double newline.
    Used so the user sees/edits the chapter as one unit.
    """
    existing_nodes = get_children(chapter_id)
    paragraphs = [n for n in existing_nodes if n.get("type") == "paragraph"]
    texts = [(p.get("text") or "").strip() for p in paragraphs]
    return "\n\n".join(texts)


# -----------------------------------
# Split Paragraphs
# -----------------------------------

def split_paragraphs(text: str) -> List[str]:
    """
    Split raw text into paragraphs.
    """

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    return paragraphs


# -----------------------------------
# Sync Paragraphs With Chapter
# -----------------------------------

def sync_paragraphs(chapter_id: str, chapter_text: str):
    """
    Sync paragraph nodes with the chapter text.

    Handles:
    - new paragraphs
    - updated paragraphs
    - deleted paragraphs
    """

    paragraphs = split_paragraphs(chapter_text)

    existing_nodes = get_children(chapter_id)

    existing_nodes = [n for n in existing_nodes if n["type"] == "paragraph"]

    existing_count = len(existing_nodes)
    new_count = len(paragraphs)

    min_count = min(existing_count, new_count)

    # -----------------------------------
    # Update existing paragraphs
    # -----------------------------------

    for i in range(min_count):

        node = existing_nodes[i]

        if node["text"] != paragraphs[i]:

            update_node(
                node["id"],
                {
                    "text": paragraphs[i]
                }
            )
            propagate_from_paragraph(node["id"])
            update_node_embedding(node["id"])

    # -----------------------------------
    # Add new paragraphs
    # -----------------------------------

    if new_count > existing_count:

        for i in range(existing_count, new_count):

            new_node = create_paragraph_node(
                text=paragraphs[i],
                parent_id=chapter_id
            )

            paragraph_id = create_node(new_node)
            propagate_from_paragraph(paragraph_id)
            create_node_embedding(paragraph_id)

    # -----------------------------------
    # Remove extra paragraphs
    # -----------------------------------

    if existing_count > new_count:

        for i in range(new_count, existing_count):

            node_id = existing_nodes[i]["id"]
            remove_node_embedding(node_id)
            delete_node(node_id)
        propagate_from_chapter(chapter_id)