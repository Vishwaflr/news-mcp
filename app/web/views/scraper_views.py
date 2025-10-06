"""
Scraper Test Views
Admin interface for testing the web scraper
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.services.scraper_service import ScraperService
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/scraper", tags=["scraper"])
templates = Jinja2Templates(directory="templates")


@router.get("/test", response_class=HTMLResponse)
async def scraper_test_page(request: Request):
    """Display scraper test page"""
    return templates.TemplateResponse(
        "admin/scraper_test.html",
        {"request": request}
    )


@router.post("/test", response_class=HTMLResponse)
async def test_scraper(
    request: Request,
    url: str = Form(...),
    method: str = Form(default="auto"),
    extract_metadata: Optional[str] = Form(default=None),
    extract_images: Optional[str] = Form(default=None)
):
    """
    Test scraper with given URL and return results via HTMX
    """
    # Convert form checkboxes to booleans
    extract_metadata_bool = extract_metadata == "on"
    extract_images_bool = extract_images == "on"

    logger.info(f"Testing scraper: url={url}, method={method}, metadata={extract_metadata_bool}, images={extract_images_bool}")

    # Initialize scraper
    scraper = ScraperService()

    # Scrape the URL
    result = await scraper.scrape_article(
        url=url,
        extract_images=extract_images_bool,
        extract_metadata=extract_metadata_bool
    )

    logger.info(f"Scrape result: status={result['scrape_status']}, word_count={result['word_count']}")

    # Render result partial
    return templates.TemplateResponse(
        "admin/partials/scraper_result.html",
        {
            "request": request,
            "result": result
        }
    )
