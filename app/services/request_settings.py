from contextvars import ContextVar, Token

from app.services.llm_errors import ModelServiceError


_current_groq_api_key: ContextVar[str] = ContextVar("current_groq_api_key", default="")


def set_current_groq_api_key(api_key: str) -> Token:
    return _current_groq_api_key.set((api_key or "").strip())


def reset_current_groq_api_key(token: Token) -> None:
    _current_groq_api_key.reset(token)


def get_required_groq_api_key() -> str:
    api_key = _current_groq_api_key.get().strip()
    if not api_key:
        raise ModelServiceError(
            "No Groq API key configured for this browser. Add your API key in Settings on this device to use AI features.",
            status_code=400,
        )
    return api_key
