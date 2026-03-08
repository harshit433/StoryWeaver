from datetime import datetime
from typing import List, Optional

from app.database.mongodb import get_nodes_collection
from app.models.node_model import Node


# -----------------------------------
# Create Node
# -----------------------------------

def create_node(node: Node) -> str:
    """
    Insert a node into MongoDB and link it with parent.
    """

    collection = get_nodes_collection()

    node_dict = node.dict()

    collection.insert_one(node_dict)

    node_id = node_dict["id"]

    # Link to parent
    if node.parent_id:

        collection.update_one(
            {"id": node.parent_id},
            {"$push": {"children_ids": node_id}}
        )

    return node_id


# -----------------------------------
# Get Node
# -----------------------------------

def get_node(node_id: str) -> Optional[dict]:

    collection = get_nodes_collection()

    node = collection.find_one({"id": node_id})

    if node:
        node.pop("_id", None)

    return node


# -----------------------------------
# Get Children
# -----------------------------------

def get_children(node_id: str) -> List[dict]:

    collection = get_nodes_collection()

    parent = collection.find_one({"id": node_id})

    if not parent:
        return []

    children = []

    for child_id in parent.get("children_ids", []):
        child = collection.find_one({"id": child_id})

        if child:
            child.pop("_id", None)
            children.append(child)

    return children


def get_document_chapters(document_id: str) -> List[dict]:
    """
    Return chapters for a document in display order.

    New data is stored as document -> chapter. Older data may still have
    document -> act -> chapter, so we flatten that away at read time.
    """
    children = get_children(document_id)
    direct_chapters = [child for child in children if child.get("type") == "chapter"]
    if direct_chapters:
        return direct_chapters

    chapters: List[dict] = []
    for child in children:
        if child.get("type") != "act":
            continue
        for grandchild in get_children(child["id"]):
            if grandchild.get("type") == "chapter":
                chapters.append(grandchild)
    return chapters


# -----------------------------------
# Get Parent
# -----------------------------------

def get_parent(node_id: str) -> Optional[dict]:

    collection = get_nodes_collection()

    node = collection.find_one({"id": node_id})

    if not node:
        return None

    parent_id = node.get("parent_id")

    if not parent_id:
        return None

    parent = collection.find_one({"id": parent_id})

    if parent:
        parent.pop("_id", None)

    return parent


# -----------------------------------
# Update Node
# -----------------------------------

def update_node(node_id: str, updates: dict):

    collection = get_nodes_collection()

    updates["updated_at"] = datetime.utcnow()

    collection.update_one(
        {"id": node_id},
        {"$set": updates}
    )


def set_children_order(parent_id: str, children_ids: List[str]) -> bool:
    collection = get_nodes_collection()
    result = collection.update_one(
        {"id": parent_id},
        {"$set": {"children_ids": children_ids, "updated_at": datetime.utcnow()}},
    )
    return result.matched_count > 0


# -----------------------------------
# Insert child after sibling (for ordered add)
# -----------------------------------

def insert_child_after(parent_id: str, new_child_id: str, after_sibling_id: str) -> bool:
    """
    Place new_child_id immediately after after_sibling_id in parent's children_ids.
    Call after create_node if the new node was appended but should be mid-list.
    """
    collection = get_nodes_collection()
    parent = collection.find_one({"id": parent_id})
    if not parent:
        return False
    children_ids = list(parent.get("children_ids") or [])
    if new_child_id not in children_ids or after_sibling_id not in children_ids:
        return False
    # Remove new_child_id and build new order: ... after_sibling_id, new_child_id, ...
    children_ids = [c for c in children_ids if c != new_child_id]
    try:
        idx = children_ids.index(after_sibling_id)
    except ValueError:
        return False
    new_order = children_ids[: idx + 1] + [new_child_id] + children_ids[idx + 1 :]
    collection.update_one(
        {"id": parent_id},
        {"$set": {"children_ids": new_order, "updated_at": datetime.utcnow()}}
    )
    return True


def insert_child_before(parent_id: str, new_child_id: str, before_sibling_id: str) -> bool:
    collection = get_nodes_collection()
    parent = collection.find_one({"id": parent_id})
    if not parent:
        return False
    children_ids = list(parent.get("children_ids") or [])
    if new_child_id not in children_ids or before_sibling_id not in children_ids:
        return False
    children_ids = [c for c in children_ids if c != new_child_id]
    try:
        idx = children_ids.index(before_sibling_id)
    except ValueError:
        return False
    new_order = children_ids[:idx] + [new_child_id] + children_ids[idx:]
    collection.update_one(
        {"id": parent_id},
        {"$set": {"children_ids": new_order, "updated_at": datetime.utcnow()}},
    )
    return True


def insert_child_at_index(parent_id: str, new_child_id: str, index: int) -> bool:
    collection = get_nodes_collection()
    parent = collection.find_one({"id": parent_id})
    if not parent:
        return False
    children_ids = list(parent.get("children_ids") or [])
    if new_child_id not in children_ids:
        return False
    children_ids = [c for c in children_ids if c != new_child_id]
    safe_index = max(0, min(index, len(children_ids)))
    new_order = children_ids[:safe_index] + [new_child_id] + children_ids[safe_index:]
    collection.update_one(
        {"id": parent_id},
        {"$set": {"children_ids": new_order, "updated_at": datetime.utcnow()}},
    )
    return True


# -----------------------------------
# Delete Node
# -----------------------------------

def delete_node(node_id: str):

    collection = get_nodes_collection()

    node = collection.find_one({"id": node_id})

    if not node:
        return

    parent_id = node.get("parent_id")

    # remove reference from parent
    if parent_id:

        collection.update_one(
            {"id": parent_id},
            {"$pull": {"children_ids": node_id}}
        )

    # delete children recursively
    for child_id in node.get("children_ids", []):
        delete_node(child_id)

    # delete the node
    collection.delete_one({"id": node_id})


# -----------------------------------
# Get Documents (root nodes)
# -----------------------------------

def get_documents() -> List[dict]:
    """
    Return all document nodes (root of the hierarchy).
    """
    collection = get_nodes_collection()
    cursor = collection.find({"type": "document"})
    docs = []
    for node in cursor:
        node.pop("_id", None)
        docs.append(node)
    return docs


# -----------------------------------
# Get Subtree
# -----------------------------------

def get_subtree(node_id: str) -> dict:
    """
    Recursively retrieve node and all children.
    """

    node = get_node(node_id)

    if not node:
        return {}

    children = []

    for child_id in node.get("children_ids", []):
        child_tree = get_subtree(child_id)
        children.append(child_tree)

    node["children"] = children

    return node


def get_document_id_for_node(node_id: str) -> Optional[str]:
    current = get_node(node_id)
    while current:
        if current.get("type") == "document":
            return current["id"]
        parent_id = current.get("parent_id")
        if not parent_id:
            return None
        current = get_node(parent_id)
    return None