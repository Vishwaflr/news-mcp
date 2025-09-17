from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select, text, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.database import get_session
from app.models import Feed, Item, FeedHealth, Source, Category, FeedCategory
import json

router = APIRouter(prefix="/api/statistics", tags=["statistics"])

@router.get("/dashboard")
def get_dashboard_stats(session: Session = Depends(get_session)):
    """Get comprehensive dashboard statistics"""

    # Total counts
    total_feeds = session.exec(select(func.count(Feed.id))).one()
    total_items = session.exec(select(func.count(Item.id))).one()
    total_sources = session.exec(select(func.count(Source.id))).one()

    # Recent activity (last 24h)
    yesterday = datetime.utcnow() - timedelta(days=1)
    items_24h = session.exec(
        select(func.count(Item.id)).where(Item.created_at > yesterday)
    ).one()

    # Items per hour for last 24h
    hourly_stats = session.exec(text("""
        SELECT
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as items_count
        FROM items
        WHERE created_at > NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC
        LIMIT 24
    """)).fetchall()

    # Feed performance
    feed_stats = session.exec(text("""
        SELECT
            f.id,
            f.title,
            f.url,
            s.name as source_name,
            COUNT(i.id) as total_items,
            COUNT(CASE WHEN i.created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as items_24h,
            COUNT(CASE WHEN i.created_at > NOW() - INTERVAL '1 hour' THEN 1 END) as items_1h,
            MAX(i.created_at) as latest_item,
            f.fetch_interval_minutes,
            f.status
        FROM feeds f
        LEFT JOIN items i ON f.id = i.feed_id
        LEFT JOIN sources s ON f.source_id = s.id
        GROUP BY f.id, f.title, f.url, s.name, f.fetch_interval_minutes, f.status
        ORDER BY total_items DESC
    """)).fetchall()

    # Top categories
    category_stats = session.exec(text("""
        SELECT
            c.name as category_name,
            COUNT(DISTINCT f.id) as feed_count,
            COUNT(i.id) as total_items,
            COUNT(CASE WHEN i.created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as items_24h
        FROM categories c
        LEFT JOIN feed_categories fc ON c.id = fc.category_id
        LEFT JOIN feeds f ON fc.feed_id = f.id
        LEFT JOIN items i ON f.id = i.feed_id
        GROUP BY c.id, c.name
        ORDER BY total_items DESC
    """)).fetchall()

    # Health overview
    health_stats = session.exec(text("""
        SELECT
            f.status,
            COUNT(*) as feed_count,
            AVG(fh.ok_ratio) as avg_success_rate,
            AVG(fh.avg_response_time_ms) as avg_response_time
        FROM feeds f
        LEFT JOIN feed_health fh ON f.id = fh.feed_id
        GROUP BY f.status
    """)).fetchall()

    return {
        "overview": {
            "total_feeds": total_feeds,
            "total_items": total_items,
            "total_sources": total_sources,
            "items_24h": items_24h
        },
        "hourly_activity": [
            {"hour": str(row[0]), "items": row[1]} for row in hourly_stats
        ],
        "feed_performance": [
            {
                "id": row[0],
                "title": row[1] or row[2][:50] + "...",
                "url": row[2],
                "source": row[3],
                "total_items": row[4],
                "items_24h": row[5],
                "items_1h": row[6],
                "latest_item": str(row[7]) if row[7] else None,
                "interval_minutes": row[8],
                "status": row[9]
            } for row in feed_stats
        ],
        "category_stats": [
            {
                "category": row[0] or "Uncategorized",
                "feed_count": row[1],
                "total_items": row[2],
                "items_24h": row[3]
            } for row in category_stats
        ],
        "health_overview": [
            {
                "status": row[0],
                "feed_count": row[1],
                "avg_success_rate": float(row[2] or 0),
                "avg_response_time": float(row[3] or 0)
            } for row in health_stats
        ]
    }

@router.get("/feed/{feed_id}")
def get_feed_details(feed_id: int, session: Session = Depends(get_session)):
    """Get detailed statistics for a specific feed"""

    feed = session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Daily item counts for last 30 days
    daily_stats = session.exec(text("""
        SELECT
            DATE(created_at) as date,
            COUNT(*) as items_count
        FROM items
        WHERE feed_id = :feed_id
        AND created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """), {"feed_id": feed_id}).fetchall()

    # Recent items
    recent_items = session.exec(
        select(Item.title, Item.created_at, Item.published)
        .where(Item.feed_id == feed_id)
        .order_by(Item.created_at.desc())
        .limit(10)
    ).fetchall()

    # Health metrics
    health = session.exec(
        select(FeedHealth).where(FeedHealth.feed_id == feed_id)
    ).first()

    return {
        "feed": {
            "id": feed.id,
            "title": feed.title,
            "url": feed.url,
            "status": feed.status,
            "interval_minutes": feed.fetch_interval_minutes
        },
        "daily_activity": [
            {"date": str(row[0]), "items": row[1]} for row in daily_stats
        ],
        "recent_items": [
            {
                "title": row[0],
                "created_at": str(row[1]),
                "published": str(row[2]) if row[2] else None
            } for row in recent_items
        ],
        "health": {
            "success_rate": health.ok_ratio if health else 0,
            "avg_response_time": health.avg_response_time_ms if health else 0,
            "last_success": str(health.last_success) if health and health.last_success else None,
            "last_failure": str(health.last_failure) if health and health.last_failure else None,
            "uptime_24h": health.uptime_24h if health else 0,
            "consecutive_failures": health.consecutive_failures if health else 0
        } if health else None
    }

@router.get("/export/csv")
def export_statistics_csv(
    table: str = Query(..., description="Table to export (feeds, items, etc.)"),
    session: Session = Depends(get_session)
):
    """Export statistics as CSV"""

    # Security: only allow specific tables
    allowed_tables = ["feeds", "items", "sources", "categories"]
    if table not in allowed_tables:
        raise HTTPException(status_code=400, detail="Table not allowed")

    # Simple CSV export
    if table == "feeds":
        results = session.exec(text("""
            SELECT f.id, f.title, f.url, s.name as source, f.status,
                   f.fetch_interval_minutes, COUNT(i.id) as total_items
            FROM feeds f
            LEFT JOIN sources s ON f.source_id = s.id
            LEFT JOIN items i ON f.id = i.feed_id
            GROUP BY f.id, f.title, f.url, s.name, f.status, f.fetch_interval_minutes
        """)).fetchall()

        csv_content = "ID,Title,URL,Source,Status,Interval,Total Items\n"
        for row in results:
            csv_content += f'"{row[0]}","{row[1] or ""}","{row[2]}","{row[3] or ""}","{row[4]}","{row[5]}","{row[6]}"\n'

    elif table == "items":
        results = session.exec(text("""
            SELECT i.id, i.title, f.title as feed_title, i.created_at, i.published
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
            ORDER BY i.created_at DESC
            LIMIT 1000
        """)).fetchall()

        csv_content = "ID,Title,Feed,Created,Published\n"
        for row in results:
            csv_content += f'"{row[0]}","{row[1] or ""}","{row[2] or ""}","{row[3]}","{row[4] or ""}"\n'

    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table}_export.csv"}
    )