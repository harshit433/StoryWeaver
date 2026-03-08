from typing import Dict

from app.database.mongodb import get_settings_collection
from app.services.llm_errors import ModelServiceError


SETTINGS_ID = "global"


def _mask_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def get_app_settings() -> Dict:
    collection = get_settings_collection()
    settings = collection.find_one({"_id": SETTINGS_ID}) or {"_id": SETTINGS_ID}
    settings.pop("_id", None)
    api_key = (settings.get("groq_api_key") or "").strip()
    return {
        "has_groq_api_key": bool(api_key),
        "groq_api_key_preview": _mask_key(api_key) if api_key else None,
    }


def set_groq_api_key(api_key: str) -> Dict:
    cleaned = (api_key or "").strip()
    if not cleaned:
        raise ModelServiceError("Groq API key is required.", status_code=400)
    collection = get_settings_collection()
    collection.update_one(
        {"_id": SETTINGS_ID},
        {"$set": {"groq_api_key": cleaned}},
        upsert=True,
    )
    return get_app_settings()


def clear_groq_api_key() -> Dict:
    collection = get_settings_collection()
    collection.update_one(
        {"_id": SETTINGS_ID},
        {"$unset": {"groq_api_key": ""}},
        upsert=True,
    )
    return get_app_settings()


def get_required_groq_api_key() -> str:
    collection = get_settings_collection()
    settings = collection.find_one({"_id": SETTINGS_ID}) or {}
    api_key = (settings.get("groq_api_key") or "").strip()
    if not api_key:
        raise ModelServiceError(
            "No Groq API key configured. Add your API key in Settings to use AI features.",
            status_code=400,
        )
    return api_key
