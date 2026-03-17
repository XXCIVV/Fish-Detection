import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from databases import Database
from sqlalchemy import MetaData
from config import config

database = Database(config.DATABASE_URL)
metadata = MetaData()  # lowercase — was shadowing the imported class

# --- Lifespan (use this in main.py instead of connect/disconnect functions) ---

@asynccontextmanager
async def lifespan(app):
    await database.connect()
    yield
    await database.disconnect()

# --- Sessions ---

async def create_session(device_info: str = "Unknown Device") -> str:
    session_id = str(uuid.uuid4())
    query = """
        INSERT INTO sessions (id, device_info)
        VALUES (:id, :device_info)
    """
    try:
        await database.execute(query=query, values={"id": session_id, "device_info": device_info})
    except Exception as e:
        raise RuntimeError(f"Failed to create session: {e}")
    return session_id

async def close_session(session_id: str):
    query = """
        UPDATE sessions
        SET end_time = :end_time
        WHERE id = :id
    """
    try:
        await database.execute(
            query=query,
            values={"end_time": datetime.now(), "id": session_id}
        )
    except Exception as e:
        raise RuntimeError(f"Failed to close session {session_id}: {e}")

# --- Detections ---

async def save_detection(
    session_id: str,
    species: str,
    confidence: float,
    bbox: list,
    image_path: str = None
):
    query = """
        INSERT INTO detections (session_id, species, confidence, bbox, image_path)
        VALUES (:session_id, :species, :confidence, :bbox, :image_path)
    """
    # key names now match the query placeholders exactly
    values = {
        "session_id": session_id,
        "species": species,
        "confidence": confidence,       # was "conf" — mismatch fixed
        "bbox": json.dumps(bbox),
        "image_path": image_path,       # was "path" — mismatch fixed
    }
    try:
        await database.execute(query=query, values=values)
    except Exception as e:
        raise RuntimeError(f"Failed to save detection: {e}")

async def get_session_history(session_id: str) -> list[dict]:
    query = """
        SELECT * FROM detections
        WHERE session_id = :session_id
        ORDER BY create_at DESC
    """
    try:
        rows = await database.fetch_all(query=query, values={"session_id": session_id})
    except Exception as e:
        raise RuntimeError(f"Failed to fetch history for session {session_id}: {e}")

    # parse bbox back to list before returning — don't make callers do this
    return [
        {**dict(row), "bbox": json.loads(row["bbox"])}
        for row in rows
    ]

async def get_all_history(limit: int = 50, offset: int = 0) -> list[dict]:
    query = """
        SELECT * FROM detections
        ORDER BY create_at DESC
        LIMIT :limit OFFSET :offset
    """
    try:
        rows = await database.fetch_all(query=query, values={"limit": limit, "offset": offset})
    except Exception as e:
        raise RuntimeError(f"Failed to fetch detection history: {e}")

    return [
        {**dict(row), "bbox": json.loads(row["bbox"])}
        for row in rows
    ]