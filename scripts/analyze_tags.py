#!/usr/bin/env python3
"""Analyze semantic tags quality across analyzed items"""
import sys
import os
import json
from collections import Counter

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, text
from app.database import engine

def analyze_tags():
    """Analyze semantic tags distribution and quality"""

    with Session(engine) as session:
        # Get all items with semantic tags
        stmt = text("""
            SELECT
                i.id,
                LEFT(i.title, 60) as title,
                a.sentiment_json::jsonb->>'category' as category,
                a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                a.sentiment_json::jsonb->'semantic_tags'->>'region' as region
            FROM items i
            JOIN item_analysis a ON a.item_id = i.id
            WHERE a.sentiment_json::jsonb->>'category' IS NOT NULL
                AND a.sentiment_json::jsonb->>'category' != 'panorama'
                AND a.sentiment_json::jsonb->'semantic_tags'->>'actor' != 'Unknown'
            ORDER BY i.created_at DESC
            LIMIT 50
        """)
        results = session.execute(stmt).fetchall()

        if not results:
            print("❌ No items found with semantic tags")
            return

        print(f"📊 Semantic Tag Analysis ({len(results)} items)")
        print("=" * 80)

        # Collect statistics
        categories = Counter()
        actors = Counter()
        themes = Counter()
        regions = Counter()

        print("\n📰 Sample Items:")
        print("-" * 80)
        for i, row in enumerate(results[:10], 1):
            item_id, title, category, actor, theme, region = row
            print(f"{i}. [{item_id}] {title}")
            print(f"   Category: {category}")
            print(f"   Tags: {actor} | {theme} | {region}")
            print()

            categories[category] += 1
            actors[actor] += 1
            themes[theme] += 1
            regions[region] += 1

        # Category distribution
        print("\n📂 Category Distribution:")
        print("-" * 80)
        for cat, count in categories.most_common():
            pct = (count / len(results)) * 100
            bar = "█" * int(pct / 2)
            print(f"{cat:30} {count:3} ({pct:5.1f}%) {bar}")

        # Top actors
        print("\n👤 Top Actors (Who?):")
        print("-" * 80)
        for actor, count in actors.most_common(15):
            print(f"{actor:40} {count:3}")

        # Top themes
        print("\n🎯 Top Themes (What?):")
        print("-" * 80)
        for theme, count in themes.most_common(15):
            print(f"{theme:40} {count:3}")

        # Top regions
        print("\n🌍 Top Regions (Where?):")
        print("-" * 80)
        for region, count in regions.most_common(15):
            print(f"{region:40} {count:3}")

        # Quality metrics
        print("\n🔍 Quality Metrics:")
        print("-" * 80)
        print(f"Total analyzed items: {len(results)}")
        print(f"Unique actors: {len(actors)}")
        print(f"Unique themes: {len(themes)}")
        print(f"Unique regions: {len(regions)}")
        print(f"Unique categories: {len(categories)}")

        # Check for potential duplicates (case variations, hyphen vs underscore)
        print("\n⚠️  Potential Tag Duplicates:")
        print("-" * 80)

        # Actor duplicates (case-insensitive)
        actor_lower = {}
        for actor in actors.keys():
            lower = actor.lower()
            if lower not in actor_lower:
                actor_lower[lower] = []
            actor_lower[lower].append(actor)

        dupes = {k: v for k, v in actor_lower.items() if len(v) > 1}
        if dupes:
            print("Actors:")
            for variants in dupes.values():
                print(f"  - {', '.join(variants)}")
        else:
            print("Actors: None found")

        # Theme duplicates
        theme_normalized = {}
        for theme in themes.keys():
            # Normalize: lowercase, replace _ and - with space
            normalized = theme.lower().replace('_', ' ').replace('-', ' ')
            if normalized not in theme_normalized:
                theme_normalized[normalized] = []
            theme_normalized[normalized].append(theme)

        dupes = {k: v for k, v in theme_normalized.items() if len(v) > 1}
        if dupes:
            print("Themes:")
            for variants in dupes.values():
                print(f"  - {', '.join(variants)}")
        else:
            print("Themes: None found")

        # Check for multi-value actors (comma-separated)
        print("\n⚠️  Multi-Value Actors (should be single entity):")
        print("-" * 80)
        multi_actors = [a for a in actors.keys() if ',' in a or ' and ' in a.lower()]
        if multi_actors:
            for actor in multi_actors[:10]:
                print(f"  - {actor} (count: {actors[actor]})")
        else:
            print("None found ✅")

if __name__ == "__main__":
    analyze_tags()
