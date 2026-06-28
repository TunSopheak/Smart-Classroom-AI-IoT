from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.dashboard_service import get_dashboard_stats

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    stats = get_dashboard_stats(db)
    return templates.TemplateResponse(request, "dashboard.html", {"stats": stats})
