import chromadb
from chromadb.config import Settings
from typing import Optional


# -----------------------------------
# Chroma Configuration
# -----------------------------------

CHROMA_COLLECTION_NAME = "node_embeddings"

# Global references
chroma_client: Optional[chromadb.Client] = None
embedding_collection = None


# -----------------------------------
# Initialize Chroma
# -----------------------------------

def init_chroma():
    """
    Initialize ChromaDB client and collection.
    """

    global chroma_client, embedding_collection

    chroma_client = chromadb.Client(
        Settings(
            persist_directory="./chroma_data",
            anonymized_telemetry=False
        )
    )

    embedding_collection = chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME
    )

    print("ChromaDB initialized")


# -----------------------------------
# Helper Getter
# -----------------------------------

def get_collection():
    if embedding_collection is None:
        raise Exception("ChromaDB not initialized")
    return embedding_collection


# -----------------------------------
# Embedding Operations
# -----------------------------------

def add_embedding(node_id: str, text: str, embedding: list):
    """
    Store embedding for a node.
    """

    collection = get_collection()

    collection.add(
        ids=[node_id],
        documents=[text],
        embeddings=[embedding]
    )


def update_embedding(node_id: str, text: str, embedding: list):
    """
    Update an existing embedding.
    """

    collection = get_collection()

    collection.update(
        ids=[node_id],
        documents=[text],
        embeddings=[embedding]
    )


def delete_embedding(node_id: str):
    """
    Remove embedding for a node.
    """

    collection = get_collection()

    collection.delete(ids=[node_id])


def query_similar(text_embedding: list, n_results: int = 5):
    """
    Find similar nodes using embeddings.
    """

    collection = get_collection()

    results = collection.query(
        query_embeddings=[text_embedding],
        n_results=n_results
    )

    return results