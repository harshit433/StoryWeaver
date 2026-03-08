from dataclasses import dataclass


@dataclass
class ModelServiceError(Exception):
    message: str
    status_code: int = 503

    def __str__(self) -> str:
        return self.message


def normalize_model_error(exc: Exception) -> ModelServiceError:
    text = str(exc or "").strip()
    lowered = text.lower()

    if (
        "rate limit reached" in lowered
        or "rate_limit_exceeded" in lowered
        or "429" in lowered
        or "tokens per day" in lowered
    ):
        return ModelServiceError(
            "Groq rate limit reached. Please wait and try again later, or switch to a higher quota tier.",
            status_code=429,
        )

    if "api key" in lowered or "authentication" in lowered or "unauthorized" in lowered:
        return ModelServiceError(
            "The Groq API credentials are invalid or missing. Check the backend configuration.",
            status_code=401,
        )

    return ModelServiceError(
        text or "The language model request failed. Please try again.",
        status_code=503,
    )


def raise_if_model_error_text(text: str) -> None:
    lowered = (text or "").lower()
    if (
        "rate limit reached" in lowered
        or "rate_limit_exceeded" in lowered
        or "\"error\"" in lowered
        or "'error'" in lowered
    ):
        raise normalize_model_error(Exception(text))
