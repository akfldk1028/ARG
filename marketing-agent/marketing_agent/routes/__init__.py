"""FastAPI app factory."""

from fastapi import FastAPI

from .agent_card import router as meta_router
from .content import router as content_router
from .output import router as output_router
from .pipeline import router as pipeline_router


def create_app() -> FastAPI:
    app = FastAPI(title="Marketing Agent A2A", version="2.0.0")
    app.include_router(meta_router)
    app.include_router(content_router)
    app.include_router(output_router)
    app.include_router(pipeline_router)
    return app
