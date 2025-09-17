from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import logging

from app.config import settings
from app.database import create_db_and_tables
from app.api import feeds, items, health, categories, sources, htmx, processors, statistics, database
from app.routes import templates as template_routes

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="News MCP API",
    description="MCP-compatible newsreader API",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(feeds.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(processors.router, prefix="/api")
app.include_router(statistics.router)
app.include_router(database.router)
app.include_router(htmx.router)
app.include_router(template_routes.router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("News MCP API started")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin/feeds", response_class=HTMLResponse)
async def admin_feeds(request: Request):
    return templates.TemplateResponse("admin/feeds.html", {"request": request})

@app.get("/admin/items", response_class=HTMLResponse)
async def admin_items(request: Request):
    return templates.TemplateResponse("admin/items.html", {"request": request})

@app.get("/admin/health", response_class=HTMLResponse)
async def admin_health(request: Request):
    return templates.TemplateResponse("admin/health.html", {"request": request})

@app.get("/admin/processors", response_class=HTMLResponse)
async def admin_processors(request: Request):
    return templates.TemplateResponse("admin/processors.html", {"request": request})

@app.get("/admin/statistics", response_class=HTMLResponse)
async def admin_statistics(request: Request):
    return templates.TemplateResponse("admin/statistics.html", {"request": request})

@app.get("/admin/database", response_class=HTMLResponse)
async def admin_database(request: Request):
    return templates.TemplateResponse("admin/database.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)