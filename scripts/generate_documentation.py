#!/usr/bin/env python3
"""
Generate comprehensive documentation for News MCP system.
"""

import json
import subprocess
import os
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'news_db',
    'user': 'news_user',
    'password': 'news_password'
}

def get_database_schema():
    """Get complete database schema information."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all tables with their columns
    schema_info = {}
    
    # Get tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    
    for table in tables:
        table_name = table['table_name']
        
        # Get columns for each table
        cur.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = cur.fetchall()
        
        # Get indexes
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = %s
        """, (table_name,))
        
        indexes = cur.fetchall()
        
        # Get foreign keys
        cur.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = %s
        """, (table_name,))
        
        foreign_keys = cur.fetchall()
        
        # Get row count
        cur.execute(f'SELECT COUNT(*) as count FROM {table_name}')
        row_count = cur.fetchone()['count']
        
        schema_info[table_name] = {
            'columns': columns,
            'indexes': indexes,
            'foreign_keys': foreign_keys,
            'row_count': row_count
        }
    
    cur.close()
    conn.close()
    
    return schema_info

def get_api_endpoints():
    """Get all API endpoints from the running application."""
    try:
        import requests
        response = requests.get('http://localhost:8000/openapi.json')
        openapi_spec = response.json()
        
        endpoints = {}
        for path, methods in openapi_spec.get('paths', {}).items():
            endpoints[path] = {
                'methods': list(methods.keys()),
                'details': methods
            }
        
        return endpoints, openapi_spec
    except Exception as e:
        print(f"Error fetching API endpoints: {e}")
        return {}, {}

def generate_markdown_documentation(schema_info, endpoints, openapi_spec):
    """Generate comprehensive markdown documentation."""
    
    # API Documentation
    api_doc = "# News MCP API Documentation\n\n"
    api_doc += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    api_doc += f"## Overview\n\n"
    api_doc += f"Base URL: `http://localhost:8000`\n\n"
    api_doc += f"OpenAPI Version: {openapi_spec.get('openapi', 'N/A')}\n\n"
    
    # Group endpoints by tag
    endpoints_by_tag = {}
    for path, info in endpoints.items():
        for method, details in info.get('details', {}).items():
            tags = details.get('tags', ['Other'])
            for tag in tags:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append({
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', ''),
                    'description': details.get('description', ''),
                    'parameters': details.get('parameters', []),
                    'responses': details.get('responses', {})
                })
    
    # Write endpoints by category
    for tag in sorted(endpoints_by_tag.keys()):
        api_doc += f"\n## {tag}\n\n"
        for endpoint in sorted(endpoints_by_tag[tag], key=lambda x: x['path']):
            api_doc += f"### {endpoint['method']} {endpoint['path']}\n"
            if endpoint['summary']:
                api_doc += f"**{endpoint['summary']}**\n\n"
            if endpoint['description']:
                api_doc += f"{endpoint['description']}\n\n"
            
            # Parameters
            if endpoint['parameters']:
                api_doc += "**Parameters:**\n\n"
                api_doc += "| Name | Type | Required | Description |\n"
                api_doc += "|------|------|----------|-------------|\n"
                for param in endpoint['parameters']:
                    api_doc += f"| {param.get('name', '')} | {param.get('in', '')} | {param.get('required', False)} | {param.get('description', '')} |\n"
                api_doc += "\n"
            
            # Responses
            if endpoint['responses']:
                api_doc += "**Responses:**\n\n"
                for code, response in endpoint['responses'].items():
                    api_doc += f"- `{code}`: {response.get('description', '')}\n"
                api_doc += "\n"
    
    # Database Documentation
    db_doc = "# News MCP Database Schema\n\n"
    db_doc += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    db_doc += f"## Database Overview\n\n"
    db_doc += f"Total Tables: {len(schema_info)}\n\n"
    
    # Statistics
    total_rows = sum(info['row_count'] for info in schema_info.values())
    db_doc += f"Total Rows: {total_rows:,}\n\n"
    
    # Table of Contents
    db_doc += "## Tables\n\n"
    for table_name in sorted(schema_info.keys()):
        row_count = schema_info[table_name]['row_count']
        db_doc += f"- [{table_name}](#{table_name.replace('_', '-')}) ({row_count:,} rows)\n"
    
    db_doc += "\n## Table Details\n\n"
    
    # Detailed table documentation
    for table_name in sorted(schema_info.keys()):
        info = schema_info[table_name]
        db_doc += f"### {table_name}\n\n"
        db_doc += f"**Rows:** {info['row_count']:,}\n\n"
        
        # Columns
        db_doc += "**Columns:**\n\n"
        db_doc += "| Column | Type | Nullable | Default |\n"
        db_doc += "|--------|------|----------|---------|\n"
        for col in info['columns']:
            db_doc += f"| {col['column_name']} | {col['data_type']} | {col['is_nullable']} | {col['column_default'] or 'None'} |\n"
        
        # Foreign Keys
        if info['foreign_keys']:
            db_doc += "\n**Foreign Keys:**\n\n"
            for fk in info['foreign_keys']:
                db_doc += f"- `{fk['column_name']}` → `{fk['foreign_table']}.{fk['foreign_column']}`\n"
        
        # Indexes
        if info['indexes']:
            db_doc += "\n**Indexes:**\n\n"
            for idx in info['indexes']:
                db_doc += f"- `{idx['indexname']}`\n"
        
        db_doc += "\n---\n\n"
    
    return api_doc, db_doc

def main():
    print("Generating comprehensive documentation...")
    
    # Get database schema
    print("Fetching database schema...")
    schema_info = get_database_schema()
    
    # Get API endpoints
    print("Fetching API endpoints...")
    endpoints, openapi_spec = get_api_endpoints()
    
    # Generate documentation
    print("Generating markdown documentation...")
    api_doc, db_doc = generate_markdown_documentation(schema_info, endpoints, openapi_spec)
    
    # Save documentation
    docs_dir = Path('/home/cytrex/news-mcp/docs')
    docs_dir.mkdir(exist_ok=True)
    
    # Save API documentation
    api_file = docs_dir / 'API_DOCUMENTATION.md'
    with open(api_file, 'w') as f:
        f.write(api_doc)
    print(f"API documentation saved to {api_file}")
    
    # Save database documentation
    db_file = docs_dir / 'DATABASE_SCHEMA.md'
    with open(db_file, 'w') as f:
        f.write(db_doc)
    print(f"Database documentation saved to {db_file}")
    
    print("Documentation generation complete!")

if __name__ == '__main__':
    main()