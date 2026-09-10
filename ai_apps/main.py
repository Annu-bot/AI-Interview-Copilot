from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from config.logging_config import logger
from ai_apps.core.database import init_db
from ai_apps.views import router as views_router

# Project root directories
ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("📦 SQLite Database initialized.")
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}] started.")
    logger.info(f"Active Provider: {'Local Open-Source LLM' if settings.USE_OPEN_SOURCE else 'Google Gemini Cloud API'}")
    yield


# Initialize FastAPI Application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Interview Copilot - V1: Resume vs JD Analysis, Gap-Targeted Questions & Staff-Level Answer Evaluation.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files from root static/
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register Views Router
app.include_router(views_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ai_apps.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
