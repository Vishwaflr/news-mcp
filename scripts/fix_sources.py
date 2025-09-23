#!/usr/bin/env python3
"""
Source Assignment Fix Script

Automatically creates proper sources for all feeds based on their URLs
and reassigns feeds to the correct sources.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, select, text
from app.database import engine
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL to Source mapping based on domain patterns
SOURCE_MAPPING = {
    # News Organizations
    'nytimes.com': {'name': 'New York Times', 'type': 'RSS', 'description': 'American newspaper of record'},
    'cnn.com': {'name': 'CNN', 'type': 'RSS', 'description': 'Cable News Network'},
    'bbc.co.uk': {'name': 'BBC', 'type': 'RSS', 'description': 'British Broadcasting Corporation'},
    'theguardian.com': {'name': 'The Guardian', 'type': 'RSS', 'description': 'British daily newspaper'},
    'reuters.com': {'name': 'Reuters', 'type': 'RSS', 'description': 'International news agency'},
    'bloomberg.com': {'name': 'Bloomberg', 'type': 'RSS', 'description': 'Business and financial news'},
    'wsj.com': {'name': 'Wall Street Journal', 'type': 'RSS', 'description': 'Business-focused newspaper'},
    'washingtonpost.com': {'name': 'Washington Post', 'type': 'RSS', 'description': 'American daily newspaper'},
    'spiegel.de': {'name': 'Der Spiegel', 'type': 'RSS', 'description': 'German news magazine'},
    'dw.com': {'name': 'Deutsche Welle', 'type': 'RSS', 'description': 'German international broadcaster'},
    'independent.co.uk': {'name': 'The Independent', 'type': 'RSS', 'description': 'British online newspaper'},

    # Technology & Science
    'wired.com': {'name': 'Wired', 'type': 'RSS', 'description': 'Technology and culture magazine'},
    'techcrunch.com': {'name': 'TechCrunch', 'type': 'RSS', 'description': 'Technology startup news'},
    'arstechnica.com': {'name': 'Ars Technica', 'type': 'RSS', 'description': 'Technology news and analysis'},
    'heise.de': {'name': 'Heise Online', 'type': 'RSS', 'description': 'Technology news from Heise.de'},
    'artificialintelligence-news.com': {'name': 'AI News', 'type': 'RSS', 'description': 'Artificial Intelligence news'},
    'techmeme.com': {'name': 'TechMeme', 'type': 'RSS', 'description': 'Technology news aggregator'},

    # Business & Finance
    'cnbc.com': {'name': 'CNBC', 'type': 'RSS', 'description': 'Business news network'},
    'forbes.com': {'name': 'Forbes', 'type': 'RSS', 'description': 'Business magazine'},
    'axios.com': {'name': 'Axios', 'type': 'API', 'description': 'News and information company'},

    # Defense & Security
    'defensenews.com': {'name': 'Defense News', 'type': 'RSS', 'description': 'Defense industry news'},
    'justsecurity.org': {'name': 'Just Security', 'type': 'RSS', 'description': 'Security and law analysis'},

    # International Organizations
    'ecfr.eu': {'name': 'European Council on Foreign Relations', 'type': 'RSS', 'description': 'European foreign policy think tank'},
    'crisisgroup.org': {'name': 'International Crisis Group', 'type': 'RSS', 'description': 'Conflict prevention organization'},

    # Broadcasting
    'abcnews.com': {'name': 'ABC News', 'type': 'RSS', 'description': 'American television news network'},
    'abcnews.go.com': {'name': 'ABC News', 'type': 'RSS', 'description': 'American television news network'},
}

def extract_domain(url):
    """Extract domain from URL for source mapping"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return None

def get_or_create_source(session, domain, url):
    """Get existing source or create new one based on domain"""
    # Check if we have a mapping for this domain
    if domain in SOURCE_MAPPING:
        source_info = SOURCE_MAPPING[domain]

        # Check if source already exists
        existing = session.execute(
            text("SELECT id FROM sources WHERE name = :name"),
            {"name": source_info['name']}
        ).fetchone()

        if existing:
            return existing[0]

        # Create new source
        logger.info(f"Creating new source: {source_info['name']}")
        result = session.execute(
            text("""
                INSERT INTO sources (name, type, description, created_at)
                VALUES (:name, :type, :description, NOW())
                RETURNING id
            """),
            {
                "name": source_info['name'],
                "type": source_info['type'],
                "description": source_info['description']
            }
        )
        session.commit()
        return result.fetchone()[0]

    else:
        # Create generic source based on domain
        source_name = domain.replace('.com', '').replace('.org', '').replace('.net', '').title()
        logger.info(f"Creating generic source for unknown domain: {source_name}")

        existing = session.execute(
            text("SELECT id FROM sources WHERE name = :name"),
            {"name": source_name}
        ).fetchone()

        if existing:
            return existing[0]

        result = session.execute(
            text("""
                INSERT INTO sources (name, type, description, created_at)
                VALUES (:name, :type, :description, NOW())
                RETURNING id
            """),
            {
                "name": source_name,
                "type": "RSS",
                "description": f"News source from {domain}"
            }
        )
        session.commit()
        return result.fetchone()[0]

def fix_feed_sources():
    """Main function to fix all feed source assignments"""
    with Session(engine) as session:
        # Get all feeds with their current source assignments
        feeds = session.execute(
            text("SELECT id, title, url, source_id FROM feeds ORDER BY title")
        ).fetchall()

        logger.info(f"Processing {len(feeds)} feeds...")

        updates_made = 0
        for feed_id, title, url, current_source_id in feeds:
            domain = extract_domain(url)
            if not domain:
                logger.warning(f"Could not extract domain from URL: {url}")
                continue

            # Get correct source ID
            correct_source_id = get_or_create_source(session, domain, url)

            # Update feed if source is different
            if current_source_id != correct_source_id:
                logger.info(f"Updating feed '{title}' from source_id {current_source_id} to {correct_source_id}")
                session.execute(
                    text("UPDATE feeds SET source_id = :source_id WHERE id = :feed_id"),
                    {"source_id": correct_source_id, "feed_id": feed_id}
                )
                updates_made += 1

        session.commit()
        logger.info(f"Completed! Made {updates_made} source assignment updates.")

def show_results():
    """Show the results after fixing"""
    with Session(engine) as session:
        result = session.execute(
            text("""
                SELECT s.name, s.type, COUNT(f.id) as feed_count, s.description
                FROM sources s
                LEFT JOIN feeds f ON s.id = f.source_id
                GROUP BY s.id, s.name, s.type, s.description
                ORDER BY feed_count DESC, s.name
            """)
        ).fetchall()

        print("\n=== Source Distribution After Fix ===")
        for name, type_val, count, description in result:
            print(f"{name:30} | {type_val:6} | {count:2} feeds | {description}")

if __name__ == "__main__":
    print("=== News-MCP Source Assignment Fix ===")
    print("This script will automatically create proper sources for all feeds")
    print("and reassign feeds to the correct sources based on their URLs.\n")

    try:
        fix_feed_sources()
        show_results()
        print("\n✅ Source assignment fix completed successfully!")

    except Exception as e:
        logger.error(f"Error during source fix: {e}")
        sys.exit(1)