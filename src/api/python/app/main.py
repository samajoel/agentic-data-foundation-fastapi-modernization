"""
FastAPI application factory for the Agentic Applications for Unified Data Foundation Solution Accelerator.
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.logging import configure_logging
from app.core.middleware import attach_trace_attributes
from app.api.routers.chat import router as chat_router
from app.api.routers.history import router as history_router
from app.api.routers.history_sql import router as history_sql_router

load_dotenv()

configure_logging()


def build_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    fastapi_app = FastAPI(
        title="Agentic Applications for Unified Data Foundation Solution Accelerator",
        version="1.0.0"
    )

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.middleware("http")(attach_trace_attributes)

    fastapi_app.include_router(chat_router, prefix="/api", tags=["chat"])
    fastapi_app.include_router(history_router, prefix="/history", tags=["history"])
    fastapi_app.include_router(history_sql_router, prefix="/historyfab", tags=["historyfab"])

    @fastapi_app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}

    return fastapi_app


app = build_app()
FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
