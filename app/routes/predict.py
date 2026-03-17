import logging
import time
import uuid
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.model.detector import detector
from app.database.db import create_session, save_detection, close_session
from app.utils.draw_boxes import draw_detections, save_image
from config import config

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _check_detector():
    """Return 503 if model failed to load at startup."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Model not available — check server logs.")


# --- 1. HTTP upload endpoint ---

@router.post("/predict")
async def predict_image(file: UploadFile = File(...)):
    _check_detector()

    # validate MIME type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    contents = await file.read()

    # validate file size
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    session_id = await create_session(device_info="Single Upload")

    try:
        # run detection — predict() returns plain list after detector.py fix
        detections = await run_in_threadpool(detector.predict, contents)

        # draw and save annotated image
        output_filename = f"{uuid.uuid4().hex}.jpg"
        processed_img = draw_detections(contents, detections)
        saved_path = save_image(processed_img, filename=output_filename)
        image_path = str(saved_path) if config.SAVE_DETECTIONS_IMAGES else None

        # persist each detection
        for det in detections:
            await save_detection(
                session_id=session_id,
                species=det["species"],
                confidence=det["confidence"],
                bbox=det["bbox"],
                image_path=image_path,
            )

    except ValueError as e:
        # bad image bytes from draw_detections
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        raise HTTPException(status_code=500, detail="Detection failed — see server logs.")
    finally:
        # always close session, even if something above raised
        await close_session(session_id)

    logger.info("predict_image: %d detection(s) for session %s", len(detections), session_id)

    return {
        "status": "success",
        "session_id": session_id,
        "output_image": f"/static/outputs/{output_filename}",
        "detections": detections,
    }


# --- 2. WebSocket real-time stream ---

@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    _check_detector()
    await websocket.accept()

    session_id = await create_session(device_info="Real-time Web Stream")
    logger.info("WebSocket session started: %s", session_id)

    # cooldown: track last saved time per species to avoid DB bloat
    last_saved: dict[str, float] = {}
    SAVE_COOLDOWN_SEC = 3.0

    try:
        while True:
            data = await websocket.receive_bytes()
            detections = await run_in_threadpool(detector.predict, data)

            await websocket.send_json({
                "session_id": session_id,
                "detections": detections,
            })

            now = time.monotonic()
            for det in detections:
                species = det["species"]
                # only save if cooldown has passed for this species
                if now - last_saved.get(species, 0) >= SAVE_COOLDOWN_SEC:
                    await save_detection(
                        session_id=session_id,
                        species=species,
                        confidence=det["confidence"],
                        bbox=det["bbox"],
                    )
                    last_saved[species] = now

    except WebSocketDisconnect:
        logger.info("WebSocket session closed: %s", session_id)
    except Exception as e:
        logger.exception("WebSocket error on session %s: %s", session_id, e)
        await websocket.close(code=1011)  # 1011 = internal error
    finally:
        # guaranteed cleanup whether disconnect or error
        await close_session(session_id)