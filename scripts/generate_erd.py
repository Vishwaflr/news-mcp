#!/usr/bin/env python3
"""
Generate Entity Relationship Diagram for News MCP Database.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import graphviz
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'news_db',
    'user': 'news_user',
    'password': 'news_password'
}

def get_database_structure():
    """Get complete database structure with relationships."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all tables and their relationships
    cur.execute("""
        SELECT DISTINCT
            tc.table_name,
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
            AND tc.table_schema = 'public'
        ORDER BY tc.table_name
    """)
    
    relationships = cur.fetchall()
    
    # Get all tables with columns
    cur.execute("""
        SELECT 
            t.table_name,
            array_agg(
                c.column_name || ' ' || c.data_type || 
                CASE WHEN c.is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END
                ORDER BY c.ordinal_position
            ) as columns
        FROM information_schema.tables t
        JOIN information_schema.columns c 
            ON t.table_name = c.table_name 
            AND t.table_schema = c.table_schema
        WHERE t.table_schema = 'public' 
            AND t.table_type = 'BASE TABLE'
        GROUP BY t.table_name
        ORDER BY t.table_name
    """)
    
    tables = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return tables, relationships

def generate_erd():
    """Generate ERD using Graphviz."""
    tables, relationships = get_database_structure()
    
    # Create Graphviz diagram
    dot = graphviz.Digraph('ERD', comment='News MCP Database ERD')
    dot.attr(rankdir='TB')
    dot.attr('node', shape='record', style='filled', fillcolor='lightblue')
    dot.attr('edge', arrowhead='crow')
    
    # Define color scheme for different table types
    table_colors = {
        'feeds': '#FFE5B4',  # Peach for core entities
        'items': '#FFE5B4',
        'categories': '#FFE5B4',
        'sources': '#FFE5B4',
        
        'item_analysis': '#B4E5FF',  # Light blue for analysis
        'analysis_runs': '#B4E5FF',
        'analysis_run_items': '#B4E5FF',
        'analysis_presets': '#B4E5FF',
        
        'fetch_log': '#D4FFB4',  # Light green for operational
        'feed_health': '#D4FFB4',
        'feed_metrics': '#D4FFB4',
        'queue_metrics': '#D4FFB4',
        
        'dynamic_feed_templates': '#FFB4E5',  # Pink for configuration
        'feed_template_assignments': '#FFB4E5',
        'feed_processor_configs': '#FFB4E5',
        'user_settings': '#FFB4E5',
    }
    
    # Add tables as nodes
    for table in tables:
        table_name = table['table_name']
        columns = table['columns'][:10]  # Limit to first 10 columns for readability
        
        # Determine color
        color = 'lightblue'
        for key, col in table_colors.items():
            if key in table_name:
                color = col
                break
        
        # Create label with table name and key columns
        label = f"{{<b>{table_name}</b>|"
        for col in columns:
            col_parts = col.split(' ')
            col_name = col_parts[0]
            col_type = ' '.join(col_parts[1:2]) if len(col_parts) > 1 else ''
            
            # Highlight primary keys
            if col_name == 'id':
                label += f"<font color='red'>• {col_name}</font> {col_type}\\l"
            else:
                label += f"• {col_name} {col_type}\\l"
        
        if len(table['columns']) > 10:
            label += f"... +{len(table['columns']) - 10} more\\l"
        label += "}"
        
        dot.node(table_name, label, fillcolor=color, shape='record')
    
    # Add relationships as edges
    for rel in relationships:
        dot.edge(
            rel['table_name'],
            rel['foreign_table'],
            label=f"{rel['column_name']}→{rel['foreign_column']}",
            fontsize='10'
        )
    
    return dot

def generate_mermaid():
    """Generate Mermaid diagram code."""
    tables, relationships = get_database_structure()
    
    mermaid = "```mermaid\n"
    mermaid += "erDiagram\n"
    
    # Add relationships
    for rel in relationships:
        mermaid += f"    {rel['table_name']} ||--o{{ {rel['foreign_table']} : has\n"
    
    # Add table definitions
    mermaid += "\n"
    for table in tables:
        table_name = table['table_name']
        mermaid += f"    {table_name} {{\n"
        
        # Add first 5 columns
        for col in table['columns'][:5]:
            col_parts = col.split(' ')
            col_name = col_parts[0]
            col_type = col_parts[1] if len(col_parts) > 1 else 'text'
            mermaid += f"        {col_type} {col_name}\n"
        
        if len(table['columns']) > 5:
            mermaid += f"        string more_columns\n"
        
        mermaid += "    }\n\n"
    
    mermaid += "```\n"
    return mermaid

def main():
    print("Generating Entity Relationship Diagram...")
    
    # Generate Graphviz ERD
    try:
        dot = generate_erd()
        
        # Save as different formats
        dot.render('/home/cytrex/news-mcp/docs/erd_diagram', format='png', cleanup=True)
        dot.render('/home/cytrex/news-mcp/docs/erd_diagram', format='svg', cleanup=True)
        
        print("ERD saved as:")
        print("  - /home/cytrex/news-mcp/docs/erd_diagram.png")
        print("  - /home/cytrex/news-mcp/docs/erd_diagram.svg")
    except Exception as e:
        print(f"Could not generate Graphviz diagram: {e}")
    
    # Generate Mermaid diagram
    mermaid_code = generate_mermaid()
    
    # Save Mermaid diagram
    with open('/home/cytrex/news-mcp/docs/ERD_MERMAID.md', 'w') as f:
        f.write("# Entity Relationship Diagram (Mermaid)\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(mermaid_code)
    
    print("Mermaid diagram saved to: /home/cytrex/news-mcp/docs/ERD_MERMAID.md")
    
    # Generate summary statistics
    tables, relationships = get_database_structure()
    
    print(f"\nDatabase Statistics:")
    print(f"  - Total Tables: {len(tables)}")
    print(f"  - Total Relationships: {len(relationships)}")
    print(f"\nMain Entities:")
    
    for table in ['feeds', 'items', 'categories', 'item_analysis', 'analysis_runs']:
        table_info = next((t for t in tables if t['table_name'] == table), None)
        if table_info:
            print(f"  - {table}: {len(table_info['columns'])} columns")

if __name__ == '__main__':
    main()