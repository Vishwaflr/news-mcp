from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session
from app.models import Feed

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates", auto_reload=True)


@router.get("/feeds-v2", response_class=HTMLResponse)
def feeds_management_v2(request: Request, session: Session = Depends(get_session)):
    """New feed management page with 2-column layout"""
    # Load feeds for initial render
    feeds = session.exec(
        select(Feed).order_by(Feed.health_score.desc().nulls_last())
    ).all()

    return templates.TemplateResponse(
        "admin/feeds_v2.html",
        {"request": request, "feeds": feeds}
    )
