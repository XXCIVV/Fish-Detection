import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

from app.database.db import get_session_history, get_all_history

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- 1. History page (HTML) ---

@router.get("/", response_class=HTMLResponse)
async def history_page(request: Request):
    """Render the history page with all past detections."""
    try:
        detections = await get_all_history(limit=50, offset=0)
    except Exception as e:
        logger.exception("Failed to load history page: %s", e)
        raise HTTPException(status_code=500, detail="Could not load history.")

    return templates.TemplateResponse("history.html", {
        "request": request,
        "detections": detections,
    })


# --- 2. History API (JSON) — for JS pagination or future mobile client ---

@router.get("/api")
async def history_api(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    Return paginated detection history as JSON.
    Useful for dynamic frontend pagination without full page reload.
    """
    try:
        detections = await get_all_history(limit=limit, offset=offset)
    except Exception as e:
        logger.exception("Failed to fetch history API: %s", e)
        raise HTTPException(status_code=500, detail="Could not fetch history.")

    return {
        "status": "success",
        "count": len(detections),
        "offset": offset,
        "limit": limit,
        "detections": detections,
    }


# --- 3. Single session history ---

@router.get("/session/{session_id}")
async def session_history(session_id: str):
    """Return all detections for a specific session."""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")
    try:
        detections = await get_session_history(session_id)
    except Exception as e:
        logger.exception("Failed to fetch session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail="Could not fetch session history.")

    if not detections:
        raise HTTPException(status_code=404, detail=f"No detections found for session {session_id}.")

    return {
        "status": "success",
        "session_id": session_id,
        "count": len(detections),
        "detections": detections,
    }