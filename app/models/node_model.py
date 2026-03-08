from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# -----------------------------------
# Node Type Enum
# -----------------------------------

class NodeType(str, Enum):
    document = "document"
    chapter = "chapter"
    paragraph = "paragraph"
    event = "event"


# -----------------------------------
# Node Model
# -----------------------------------

class Node(BaseModel):

    id: str = Field(default_factory=lambda: str(uuid4()))

    type: NodeType

    title: Optional[str] = None
    text: Optional[str] = None

    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)

    summary: Optional[str] = None
    description: Optional[str] = None

    timeline: Optional[Dict] = None

    embedding_id: Optional[str] = None

    metadata: Dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------
# Node Creation Helpers
# -----------------------------------

def create_document_node(title: str) -> Node:
    return Node(
        type=NodeType.document,
        title=title,
        summary=title,
        parent_id=None
    )


def create_chapter_node(title: str, parent_id: str) -> Node:
    return Node(
        type=NodeType.chapter,
        title=title,
        summary=title,
        parent_id=parent_id
    )


def create_paragraph_node(text: str, parent_id: str) -> Node:
    return Node(
        type=NodeType.paragraph,
        text=text,
        parent_id=parent_id
    )