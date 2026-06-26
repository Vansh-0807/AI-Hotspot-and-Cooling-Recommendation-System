import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, hotspots, locations, priority, recommendations, settings, simulator, chat
from app.config import get_settings
from app.db.database import check_db_connection, init_db, SessionLocal
from app.db.models import GridCell
from app.models.schemas import HealthResponse
from app.services.bootstrap_service import keys_configured

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not check_db_connection():
        logger.error("Cannot connect to Database. Check DATABASE_URL.")
        raise RuntimeError("Database connection failed — check DATABASE_URL")
    init_db()
    logger.info("Database initialized. Live data will be fetched on-demand for any city.")
    yield


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(
        title="Urban Heat Platform API",
        description="ISRO Hackathon — Urban heat hotspot detection for any Indian city (live OpenWeather + OSM + ML)",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origin_list + ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(hotspots.router, prefix="/api/v1")
    app.include_router(analysis.router, prefix="/api/v1")
    app.include_router(recommendations.router, prefix="/api/v1")
    app.include_router(simulator.router, prefix="/api/v1")
    app.include_router(priority.router, prefix="/api/v1")
    app.include_router(locations.router, prefix="/api/v1")
    app.include_router(settings.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")

    @app.get("/health", response_model=HealthResponse)
    def health():
        db = SessionLocal()
        try:
            cells = db.query(GridCell).count()
        finally:
            db.close()
        db_ok = check_db_connection()
        keys_ok = keys_configured()
        return HealthResponse(
            status="ok" if db_ok else "degraded",
            city=config.target_city,
            database="connected" if db_ok else "disconnected",
            data_ready=cells > 0,
            keys_configured=keys_ok,
            cell_count=cells,
        )

    return app


app = create_app()