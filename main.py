import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import config
from app.database.db import database
from app.model.detector import detector
from app.routes.history import router as history_router
from app.routes.predict import router as predict_router
from app.routes.library import router as library_router

# --- Logging setup — do this first so all modules inherit the config ---
logging.basicConfig(
    level=logging.DEBUG if config.APP_ENV == "development" else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# --- Lifespan: startup + shutdown in one place ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    logger.info("Starting up — env: %s", config.APP_ENV)

    # 1. ensure upload/output dirs exist
    config.init_dirs()

    # 2. initialise DB schema
    try:
        await database.connect()
        logger.info("Database connected: %s", config.DATABASE_URL)
    except Exception as e:
        logger.critical("Database failed to connect: %s", e)
        raise  # abort startup — no point running without a DB

    # 3. verify model loaded (detector is None if it failed)
    if detector is None:
        logger.critical(
            "YOLO model failed to load from %s — "
            "predictions will return 503 until fixed.",
            config.MODEL_PATH,
        )
    else:
        logger.info("YOLO model ready on %s", detector.device)

    yield  # app runs here

    # ---- shutdown ----
    logger.info("Shutting down...")
    await database.disconnect()
    logger.info("Database disconnected.")


# --- App factory ---

def create_app() -> FastAPI:
    app = FastAPI(
        title=config.APP_NAME,
        description="Bengal Bay fish species detection — FastAPI + YOLOv11",
        version="1.1.0",
        lifespan=lifespan,
        # hide /docs and /redoc in production
        docs_url="/docs" if config.APP_ENV == "development" else None,
        redoc_url="/redoc" if config.APP_ENV == "development" else None,
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.APP_ENV == "development" else [config.ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Static files & templates ---
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    templates = Jinja2Templates(directory="app/templates")
    templates.env.filters["basename"] = os.path.basename

    # --- Routers ---
    app.include_router(predict_router, tags=["Detection"])
    app.include_router(history_router, prefix="/history", tags=["History"])
    app.include_router(library_router, prefix="/library", tags=["Library"])

    # --- Root route ---
    @app.get("/", response_class=HTMLResponse)
    async def index_page(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        favicon_path = "app/static/favicon.ico"
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        # Return 204 No Content if favicon doesn't exist (prevents 500 error)
        from fastapi.responses import Response
        return Response(status_code=204)
    
    @app.get("/result", response_class=HTMLResponse)
    async def result_page(request: Request):
        return templates.TemplateResponse("result.html", {"request": request})

    # --- Global exception handlers ---
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=404, content={"detail": "Not found."})
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        logger.exception("Unhandled server error: %s", exc)
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=500, content={"detail": "Internal server error."})
        return templates.TemplateResponse(
            "500.html", {"request": request}, status_code=500
        )

    return app


app = create_app()