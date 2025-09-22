"""System management HTMX components."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session, text
from datetime import datetime, timedelta

from app.database import get_session
from .base_component import BaseComponent

router = APIRouter(tags=["htmx-system"])


class SystemComponent(BaseComponent):
    """Component for system-related HTMX endpoints."""

    @staticmethod
    def build_status_card(title: str, value: int, color: str = "primary") -> str:
        """Build HTML for a status card."""
        return f'''
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="text-{color}">{value}</h2>
                    <p class="card-text">{title}</p>
                </div>
            </div>
        </div>
        '''

    @staticmethod
    def build_health_alert(health_pct: float) -> str:
        """Build system health alert box."""
        if health_pct >= 90:
            status_color = "success"
            status_text = "Excellent"
        elif health_pct >= 70:
            status_color = "warning"
            status_text = "Good"
        else:
            status_color = "danger"
            status_text = "Needs Attention"

        return f'''
        <div class="row mt-3">
            <div class="col-12">
                <div class="alert alert-{status_color}">
                    <h5>System Health: {health_pct:.1f}%</h5>
                    <p class="mb-0">Status: {status_text}</p>
                </div>
            </div>
        </div>
        '''


@router.get("/system-status", response_class=HTMLResponse)
def get_system_status(session: Session = Depends(get_session)):
    """Get system status overview with key metrics."""
    # Get feed statistics - Use raw SQL to avoid SQLModel issues
    total_feeds = session.exec(text("SELECT COUNT(*) FROM feeds")).one()[0]
    active_feeds = session.exec(text("SELECT COUNT(*) FROM feeds WHERE status = 'ACTIVE'")).one()[0]
    error_feeds = session.exec(text("SELECT COUNT(*) FROM feeds WHERE status = 'ERROR'")).one()[0]

    # Get recent items (last 24 hours)
    recent_items = session.exec(text("""
        SELECT COUNT(*) FROM items
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """)).one()[0]

    # Calculate system health percentage
    health_pct = (active_feeds / total_feeds * 100) if total_feeds > 0 else 100

    # Build status cards
    html = '<div class="row">'
    html += SystemComponent.build_status_card("Total Feeds", total_feeds, "primary")
    html += SystemComponent.build_status_card("Active Feeds", active_feeds, "success")
    html += SystemComponent.build_status_card("Error Feeds", error_feeds, "danger")
    html += SystemComponent.build_status_card("Items (24h)", recent_items, "info")
    html += '</div>'

    # Add health status
    html += SystemComponent.build_health_alert(health_pct)

    return html