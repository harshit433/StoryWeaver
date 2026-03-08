from typing import List

from app.database.chroma import (
    add_embedding,
    update_embedding,
    delete_embedding,
    query_similar
)

from app.services.graph_service import get_node
from app.llm.groq_client import generate_embedding


# -----------------------------------
# Create Embedding
# -----------------------------------

def create_node_embedding(node_id: str):
    """
    Generate and store embedding for a node summary.
    """

    node = get_node(node_id)

    if not node:
        return

    text = node.get("summary") or node.get("text")

    if not text:
        return

    embedding = generate_embedding(text)

    add_embedding(node_id, text, embedding)


# -----------------------------------
# Update Embedding
# -----------------------------------

def update_node_embedding(node_id: str):
    """
    Update embedding when node text or summary changes.
    """

    node = get_node(node_id)

    if not node:
        return

    text = node.get("summary") or node.get("text")

    if not text:
        return

    embedding = generate_embedding(text)

    update_embedding(node_id, text, embedding)


# -----------------------------------
# Delete Embedding
# -----------------------------------

def remove_node_embedding(node_id: str):
    """
    Remove embedding from Chroma.
    """

    delete_embedding(node_id)


# -----------------------------------
# Semantic Search
# -----------------------------------

def search_similar_nodes(query: str, n_results: int = 5) -> List[str]:
    """
    Return node_ids of semantically similar nodes.
    """

    embedding = generate_embedding(query)

    results = query_similar(embedding, n_results)

    ids = []

    if results and "ids" in results:
        ids = results["ids"][0]

    return ids