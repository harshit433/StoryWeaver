from typing import List, Optional

from app.services.embedding_service import search_similar_nodes
from app.services.graph_service import get_node, get_parent
from app.services.traversal_service import build_context_by_traversal


# -----------------------------------
# Retrieve Relevant Nodes (embedding-based fallback)
# -----------------------------------

def retrieve_relevant_nodes(query: str, limit: int = 5) -> List[dict]:
    """
    Retrieve nodes relevant to the user query using semantic search.
    """
    node_ids = search_similar_nodes(query, limit)
    nodes = []
    for node_id in node_ids:
        node = get_node(node_id)
        if node:
            nodes.append(node)
    return nodes


# -----------------------------------
# Expand Context
# -----------------------------------

def expand_context(nodes: List[dict]) -> List[dict]:
    """
    Add parent nodes to provide hierarchical context.
    """
    context_nodes = []
    visited = set()
    for node in nodes:
        if node["id"] not in visited:
            context_nodes.append(node)
            visited.add(node["id"])
        parent = get_parent(node["id"])
        while parent:
            if parent["id"] not in visited:
                context_nodes.append(parent)
                visited.add(parent["id"])
            parent = get_parent(parent["id"])
    return context_nodes


# -----------------------------------
# Build Context Package
# -----------------------------------

def build_context(
    query: str,
    limit: int = 5,
    document_id: Optional[str] = None,
) -> List[dict]:
    """
    Build reasoning context.

    - If document_id is provided: use top-down LLM-guided traversal
      (document → chapters → paragraphs) for accurate, summary-based selection.
    - Otherwise: use embedding similarity (legacy fallback).
    """
    if document_id:
        return build_context_by_traversal(query, document_id)
    relevant_nodes = retrieve_relevant_nodes(query, limit)
    return expand_context(relevant_nodes)