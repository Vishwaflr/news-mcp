from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.config import settings
from app.database import create_db_and_tables, get_session

# API imports
from app.api import (
    feeds, items, health, categories, sources, htmx, processors,
    statistics, database, analysis_control, user_settings,
    feature_flags_admin, templates as api_templates, scheduler,
    analysis_management, metrics, feed_limits, system,
    analysis_selection, auto_analysis_monitoring,
    feeds_simple, analysis_jobs, websocket_endpoint, config
)
from app.api.v1 import analysis as analysis_v1, health as health_v1

# View imports
from app.routes import templates as template_routes, processors_htmx
from app.web.views import analysis, auto_analysis_views, manager_views

# Core imports
from app.core.logging_config import setup_logging, get_logger
from app.core.error_handlers import register_exception_handlers
from app.core.health import create_health_router, register_default_health_checks

# Setup structured logging
setup_logging(log_level=settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title="News MCP - Enterprise RSS Management System",
    description="""
    🚀 **Enterprise-Ready RSS Management & Content Processing System**

    ## 🏗️ **Modern Repository Architecture**
    - **Repository Pattern**: Type-safe data access with SQLAlchemy Core
    - **Feature Flags**: Safe gradual rollout with automatic fallback
    - **Shadow Comparison**: A/B testing between old and new implementations
    - **Performance Monitoring**: P50/P95/P99 metrics with alerting

    ## 🎛️ **Advanced Features**
    - **Dynamic Templates**: Hot-reload configuration without restart
    - **Sentiment Analysis**: AI-powered content analysis with OpenAI integration
    - **MCP Integration**: Complete Model Context Protocol implementation
    - **HTMX Interface**: Modern progressive enhancement

    ## 🔧 **Production Ready**
    - **Circuit Breaker**: Auto-disable on >5% error rate or >30% latency increase
    - **Index Optimization**: Automated performance monitoring and optimization
    - **Alembic Migrations**: Schema-first with drop protection
    - **Health Monitoring**: Comprehensive system health checks
    """,
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "News MCP Development Team",
        "url": "https://github.com/your-repo/news-mcp",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    tags_metadata=[
        {
            "name": "feeds",
            "description": "RSS feed management operations",
        },
        {
            "name": "items",
            "description": "Article/item operations with Repository pattern",
        },
        {
            "name": "admin",
            "description": "Administrative operations and feature flags",
        },
        {
            "name": "feature-flags",
            "description": "Feature flag management and monitoring",
        },
        {
            "name": "htmx",
            "description": "HTMX-powered web interface endpoints",
        },
        {
            "name": "analysis",
            "description": "AI-powered content analysis operations",
        },
        {
            "name": "health",
            "description": "System health monitoring and diagnostics",
        }
    ]
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

# Include new v1 API first (takes precedence)
app.include_router(analysis_v1.router)
app.include_router(health_v1.router)

app.include_router(feeds.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(feeds_simple.router)
app.include_router(health.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(processors.router, prefix="/api")
app.include_router(statistics.router)
app.include_router(database.router)
app.include_router(htmx.router, prefix="/htmx")
app.include_router(processors_htmx.router)
app.include_router(template_routes.router)
app.include_router(analysis_control.router, prefix="/api")
app.include_router(user_settings.router, prefix="/api")
app.include_router(feature_flags_admin.router)
app.include_router(analysis.router)
app.include_router(auto_analysis_views.router, prefix="/htmx")
app.include_router(manager_views.router)

app.include_router(analysis_jobs.router, prefix="/api")
app.include_router(websocket_endpoint.router)
# MCP v2 API endpoints
app.include_router(api_templates.router, prefix="/api")
app.include_router(scheduler.router, prefix="/api")
app.include_router(analysis_management.router)
app.include_router(metrics.router)
app.include_router(feed_limits.router)
app.include_router(system.router, prefix="/api")
app.include_router(analysis_selection.router)
app.include_router(auto_analysis_monitoring.router)
app.include_router(config.router)

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

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin/feeds", response_class=HTMLResponse)
async def admin_feeds(request: Request, session: Session = Depends(get_session)):
    from sqlmodel import select
    from app.models.feeds import Source, Category

    sources = session.exec(select(Source).order_by(Source.name)).all()
    categories = session.exec(select(Category).order_by(Category.name)).all()

    return templates.TemplateResponse("admin/feeds.html", {
        "request": request,
        "sources": sources,
        "categories": categories
    })

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
    # Use the v4 clean unified Alpine.js template
    return templates.TemplateResponse("analysis_cockpit_v4.html", {"request": request})

@app.get("/admin/auto-analysis", response_class=HTMLResponse)
async def admin_auto_analysis(request: Request):
    from app.services.auto_analysis_config import auto_analysis_config
    config = auto_analysis_config.get_all()
    return templates.TemplateResponse("auto_analysis.html", {
        "request": request,
        "config": config
    })

@app.get("/admin/manager", response_class=HTMLResponse)
async def admin_manager(request: Request):
    return templates.TemplateResponse("admin/analysis_manager.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True)