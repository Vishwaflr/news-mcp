from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Feed

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates", auto_reload=True)


@router.get("/feeds", response_class=HTMLResponse)
def feeds_management(request: Request, session: Session = Depends(get_session)):
    """Feed management page with 2-column layout"""
    # Load feeds for initial render
    feeds = session.exec(
        select(Feed).order_by(Feed.health_score.desc().nulls_last())
    ).all()

    return templates.TemplateResponse(
        "admin/feeds.html",
        {"request": request, "feeds": feeds}
    )


@router.get("/research", response_class=HTMLResponse)
def research_templates(request: Request):
    """Research templates page with article filter UI"""
    return templates.TemplateResponse(
        "admin/research_templates.html",
        {"request": request}
    )
