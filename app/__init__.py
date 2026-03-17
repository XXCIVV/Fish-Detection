from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import config
from app.database.db import lifespan
from app.routes.predict import router as predict_router
from app.routes.history import router as history_router

def create_app() -> FastAPI:
    app = FastAPI(
        title=config.APP_NAME,
        description="Web application for Bengal Bay's Fish species detection.",
        version="1.1.0",
        lifespan=lifespan,      # DB connects/disconnects cleanly on startup/shutdown
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.APP_ENV == "development" else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(predict_router, tags=["Detection"])
    app.include_router(history_router, prefix="/history", tags=["History"])

    config.init_dirs()

    return app