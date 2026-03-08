from typing import Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.llm_errors import ModelServiceError
from app.services.settings_service import (
    clear_groq_api_key,
    get_app_settings,
    set_groq_api_key,
)


router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)


@router.get("")
def get_settings():
    return get_app_settings()


@router.put("/groq-key")
def update_groq_key(payload: Dict):
    api_key = payload.get("api_key")
    if api_key is None:
        return {"error": "api_key required"}
    try:
        return set_groq_api_key(str(api_key))
    except ModelServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@router.delete("/groq-key")
def delete_groq_key():
    return clear_groq_api_key()
