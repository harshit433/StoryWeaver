import logging

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from app.database.mongodb import connect_mongo, close_mongo
from app.database.chroma import init_chroma

from app.routes import project_routes, reasoning_routes
from app.services.request_settings import reset_current_groq_api_key, set_current_groq_api_key

# Orchestrator logs (Phase 1/2/3 and execution)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("writer.orchestrator")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(h)


app = FastAPI(
    title="Story Reasoning Engine",
    description="Backend reasoning engine for AI powered writing system",
    version="0.1.0"
)


# -----------------------------
# CORS
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def inject_request_settings(request: Request, call_next):
    token = set_current_groq_api_key(request.headers.get("X-Groq-Api-Key", ""))
    try:
        response = await call_next(request)
        return response
    finally:
        reset_current_groq_api_key(token)


# -----------------------------
# Startup / Shutdown Events
# -----------------------------

@app.on_event("startup")
async def startup_event():
    """
    Initialize database connections.
    """
    connect_mongo()
    init_chroma()
    print("System initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Close database connections.
    """
    close_mongo()
    print("System shutdown complete")


# -----------------------------
# Routers
# -----------------------------

app.include_router(project_routes.router)
app.include_router(reasoning_routes.router)


# -----------------------------
# Health Check
# -----------------------------

@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "story-reasoning-engine"
    }