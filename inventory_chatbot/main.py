# inventory_chatbot/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from inventory_chatbot.api.endpoints import router  
from inventory_chatbot.config import settings


def create_app():
    """Create and configure FastAPI app."""
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(router, prefix=settings.API_PREFIX)

    return app


app = create_app()
