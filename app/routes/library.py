from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database.db import database

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def library_page(request: Request):
    query = """
        SELECT 
            species,
            MAX(confidence) as max_conf,
            COUNT(id) as total_detections,
            MAX(create_at) as last_seen
        FROM detections
        GROUP BY species
        ORDER BY species ASC
    """
    try:
        species_rows = await database.fetch_all(query=query)
        library_data = [dict(row) for row in species_rows]
    except Exception as e:
        library_data = []
        print(f"Error fetching library: {e}")
        
    return templates.TemplateResponse(
        "library.html", 
        {"request": request, "library": library_data}
    )
