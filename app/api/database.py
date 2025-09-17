from fastapi import APIRouter, Depends, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, text
from typing import Optional, List, Dict, Any
from app.database import get_session
import json
import re

router = APIRouter(prefix="/api/database", tags=["database"])

# Security: Allowed table prefixes for read-only operations
ALLOWED_TABLE_PATTERNS = [
    r'^feeds$', r'^items$', r'^sources$', r'^categories$', r'^feed_health$',
    r'^feed_categories$', r'^dynamic_feed_templates$', r'^feed_template_assignments$',
    r'^feed_configuration_changes$', r'^fetch_logs$', r'^content_processing_logs$'
]

def is_safe_query(query: str) -> bool:
    """Check if query is safe (read-only operations only)"""
    query_lower = query.lower().strip()

    # Only allow SELECT statements
    if not query_lower.startswith('select'):
        return False

    # Block dangerous keywords
    dangerous_keywords = [
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'truncate', 'exec', 'execute', 'sp_', 'xp_', '--', '/*', '*/',
        'union', 'information_schema', 'pg_', 'mysql', 'sqlite_master'
    ]

    for keyword in dangerous_keywords:
        if keyword in query_lower:
            return False

    return True

def is_table_allowed(table_name: str) -> bool:
    """Check if table access is allowed"""
    for pattern in ALLOWED_TABLE_PATTERNS:
        if re.match(pattern, table_name.lower()):
            return True
    return False

@router.get("/tables")
def list_tables(session: Session = Depends(get_session)):
    """Get list of available tables"""

    # Get table list from PostgreSQL
    result = session.exec(text("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)).fetchall()

    tables = []
    for table_name, table_type in result:
        if is_table_allowed(table_name):
            # Get row count
            try:
                count_result = session.exec(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                tables.append({
                    "name": table_name,
                    "type": table_type,
                    "row_count": count_result
                })
            except Exception:
                tables.append({
                    "name": table_name,
                    "type": table_type,
                    "row_count": 0
                })

    return {"tables": tables}

@router.get("/schema/{table_name}")
def get_table_schema(table_name: str, session: Session = Depends(get_session)):
    """Get table schema information"""

    if not is_table_allowed(table_name):
        raise HTTPException(status_code=403, detail="Table access not allowed")

    # Get column information
    result = session.exec(text("""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name = :table_name
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """), {"table_name": table_name}).fetchall()

    columns = []
    for row in result:
        columns.append({
            "name": row[0],
            "type": row[1],
            "nullable": row[2] == "YES",
            "default": row[3],
            "max_length": row[4]
        })

    return {
        "table_name": table_name,
        "columns": columns
    }

@router.post("/query")
def execute_query(
    query: str = Form(...),
    limit: int = Form(100),
    session: Session = Depends(get_session)
):
    """Execute a read-only SQL query"""

    # Security checks
    if not is_safe_query(query):
        raise HTTPException(status_code=403, detail="Query contains forbidden operations")

    # Add LIMIT if not present
    query_lower = query.lower().strip()
    if 'limit' not in query_lower:
        if query.rstrip().endswith(';'):
            query = query.rstrip()[:-1] + f' LIMIT {limit};'
        else:
            query = query.rstrip() + f' LIMIT {limit}'

    try:
        result = session.exec(text(query)).fetchall()

        # Convert to list of dictionaries
        if result:
            # Get column names from first row
            columns = list(result[0]._mapping.keys()) if hasattr(result[0], '_mapping') else list(range(len(result[0])))

            data = []
            for row in result:
                if hasattr(row, '_mapping'):
                    data.append(dict(row._mapping))
                else:
                    data.append({f"col_{i}": val for i, val in enumerate(row)})
        else:
            columns = []
            data = []

        return {
            "success": True,
            "columns": columns,
            "data": data,
            "row_count": len(data),
            "query": query
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

@router.get("/quick-queries")
def get_quick_queries():
    """Get predefined quick queries"""

    queries = [
        {
            "name": "All Feeds Overview",
            "description": "Show all feeds with basic info",
            "query": "SELECT f.id, f.title, f.url, s.name as source, f.status, f.fetch_interval_minutes FROM feeds f LEFT JOIN sources s ON f.source_id = s.id"
        },
        {
            "name": "Recent Items (24h)",
            "description": "Latest items from last 24 hours",
            "query": "SELECT i.title, f.title as feed, i.created_at, i.published FROM items i LEFT JOIN feeds f ON i.feed_id = f.id WHERE i.created_at > NOW() - INTERVAL '24 hours' ORDER BY i.created_at DESC"
        },
        {
            "name": "Feed Performance",
            "description": "Feeds with item counts and latest activity",
            "query": "SELECT f.title, COUNT(i.id) as total_items, MAX(i.created_at) as latest_item, f.fetch_interval_minutes FROM feeds f LEFT JOIN items i ON f.id = i.feed_id GROUP BY f.id, f.title, f.fetch_interval_minutes ORDER BY total_items DESC"
        },
        {
            "name": "Health Status",
            "description": "Feed health metrics",
            "query": "SELECT f.title, fh.success_rate, fh.avg_response_time_ms, fh.last_successful_fetch, fh.last_error_message FROM feeds f LEFT JOIN feed_health fh ON f.id = fh.feed_id"
        },
        {
            "name": "Template Assignments",
            "description": "Which templates are assigned to which feeds",
            "query": "SELECT f.title as feed_title, t.name as template_name, fta.assigned_by, fta.created_at FROM feed_template_assignments fta LEFT JOIN feeds f ON fta.feed_id = f.id LEFT JOIN dynamic_feed_templates t ON fta.template_id = t.id WHERE fta.is_active = true"
        },
        {
            "name": "Processing Logs",
            "description": "Recent content processing activity",
            "query": "SELECT cpl.created_at, f.title as feed, i.title as item_title, cpl.processor_type, cpl.processing_status, cpl.error_message FROM content_processing_logs cpl LEFT JOIN items i ON cpl.item_id = i.id LEFT JOIN feeds f ON cpl.feed_id = f.id ORDER BY cpl.created_at DESC"
        },
        {
            "name": "Fetch Statistics",
            "description": "Recent fetch activity and results",
            "query": "SELECT fl.created_at, f.title as feed, fl.status, fl.items_found, fl.items_new, fl.response_time_ms, fl.error_message FROM fetch_logs fl LEFT JOIN feeds f ON fl.feed_id = f.id ORDER BY fl.created_at DESC"
        }
    ]

    return {"queries": queries}