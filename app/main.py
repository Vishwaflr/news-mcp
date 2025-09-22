from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import logging

from app.config import settings
from app.database import create_db_and_tables
from app.api import feeds, items, health, categories, sources, htmx, processors, statistics, database, analysis_control, user_settings
from app.routes import templates as template_routes
from app.web.views import analysis_control as analysis_htmx

# Import monitoring and error handling components (simplified)
from app.core.logging_config import setup_logging, get_logger
from app.core.error_handlers import register_exception_handlers
from app.core.health import register_default_health_checks

# Setup basic logging (structured logging temporarily disabled)
import logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="News MCP API",
    description="MCP-compatible newsreader API",
    version="1.0.0"
)

# Register global exception handlers
register_exception_handlers(app)

# Add monitoring middleware (schrittweise aktiviert)
# from app.core.tracing import TracingMiddleware
# app.add_middleware(TracingMiddleware)  # Temporär deaktiviert für Debugging
# from app.core.metrics import MetricsMiddleware
# app.add_middleware(MetricsMiddleware)  # Problem mit ASGI interface

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
app.include_router(htmx.router, prefix="/htmx")
app.include_router(template_routes.router)
app.include_router(analysis_control.router, prefix="/api")
app.include_router(user_settings.router, prefix="/api")
app.include_router(analysis_htmx.router)

# Include monitoring routers (schrittweise aktiviert)
from app.core.health import create_health_router
app.include_router(create_health_router())
# app.include_router(create_metrics_router())  # Als nächstes
# app.include_router(create_tracing_router())
# app.include_router(create_resilience_router())

@app.on_event("startup")
def on_startup():
    # Initialize database
    create_db_and_tables()

    # Register default health checks
    register_default_health_checks()

    logger.info("News MCP API started with monitoring enabled")

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

@app.get("/admin/analysis", response_class=HTMLResponse)
async def admin_analysis(request: Request):
    return templates.TemplateResponse("analysis_control.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)