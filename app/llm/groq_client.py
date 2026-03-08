from typing import List

from groq import Groq
from sentence_transformers import SentenceTransformer

from app.services.llm_errors import normalize_model_error
from app.services.request_settings import get_required_groq_api_key


client: Groq | None = None
client_api_key: str | None = None


def _get_groq_client() -> Groq:
    global client, client_api_key
    api_key = get_required_groq_api_key()
    if client is None or client_api_key != api_key:
        client = Groq(api_key=api_key)
        client_api_key = api_key
    return client


# -----------------------------------
# Embedding Model Initialization
# -----------------------------------

# Load once globally (important for performance)
embedding_model = SentenceTransformer("BAAI/bge-m3")


# -----------------------------------
# Text Generation
# -----------------------------------

def generate_text(prompt: str, temperature: float = 0.7) -> str:
    """
    Generate text using Groq LLM.
    """

    print(prompt)

    try:
        response = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature
        )
    except Exception as exc:
        raise normalize_model_error(exc) from exc

    text = response.choices[0].message.content

    print(text)

    return text.strip()


# -----------------------------------
# Embedding Generation
# -----------------------------------

def generate_embedding(text: str) -> List[float]:
    """
    Generate embeddings using SentenceTransformer.
    """

    embedding = embedding_model.encode(text)

    # Convert numpy array to python list
    return embedding.tolist()