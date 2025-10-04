#!/usr/bin/env python3
"""Batch test analysis for semantic tags - save to DB"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.llm_client import LLMClient
from app.repositories.analysis import AnalysisRepo
from app.domain.analysis.schema import AnalysisResult, SentimentPayload, ImpactPayload, SemanticTags, GeopoliticalPayload
from sqlmodel import Session, select, text
from app.database import engine
from app.models.core import Item

def batch_analyze(limit: int = 15):
    """Analyze a batch of unanalyzed items and save to DB"""

    # Get unanalyzed items
    with Session(engine) as session:
        stmt = text("""
            SELECT i.id, i.title, i.description, i.content
            FROM items i
            LEFT JOIN item_analysis a ON a.item_id = i.id
            WHERE a.item_id IS NULL
            ORDER BY i.created_at DESC
            LIMIT :limit
        """)
        results = session.execute(stmt, {"limit": limit}).fetchall()

        if not results:
            print("❌ No unanalyzed items found")
            return

        print(f"📊 Analyzing {len(results)} items...")
        print("=" * 80)

        llm_client = LLMClient(model="gpt-4.1-nano", rate_per_sec=3.0)

        for i, (item_id, title, description, content) in enumerate(results, 1):
            try:
                print(f"\n[{i}/{len(results)}] Item {item_id}: {title[:60]}...")

                # Prepare summary
                summary = description or (content[:800] if content else "")

                # Call LLM
                llm_data = llm_client.classify(title=title, summary=summary)

                # Extract fields
                category = llm_data.get("category", "panorama")
                semantic_tags_data = llm_data.get("semantic_tags", {
                    "actor": "Unknown",
                    "theme": "General",
                    "region": "Global"
                })
                semantic_tags = SemanticTags(**semantic_tags_data)

                # Build AnalysisResult
                from app.domain.analysis.schema import Overall, Market

                sentiment = SentimentPayload(
                    overall=Overall(**llm_data["overall"]),
                    market=Market(**llm_data["market"]),
                    urgency=float(llm_data["urgency"])
                )

                impact = ImpactPayload(**llm_data["impact"])

                # Geopolitical (optional)
                geopolitical = None
                if "geopolitical" in llm_data:
                    try:
                        geopolitical = GeopoliticalPayload(**llm_data["geopolitical"])
                    except Exception as e:
                        print(f"   ⚠️  Geopolitical parsing failed: {e}")

                result = AnalysisResult(
                    category=category,
                    semantic_tags=semantic_tags,
                    sentiment=sentiment,
                    impact=impact,
                    geopolitical=geopolitical,
                    model_tag="gpt-4.1-nano"
                )

                # Save to DB
                AnalysisRepo.upsert(item_id, result)

                print(f"   ✅ Category: {category}")
                print(f"   📌 Tags: {semantic_tags.actor} | {semantic_tags.theme} | {semantic_tags.region}")
                print(f"   💭 Sentiment: {sentiment.overall.label} ({sentiment.overall.score:.2f})")

            except Exception as e:
                print(f"   ❌ Failed: {e}")
                continue

        print(f"\n✅ Batch analysis complete!")

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    batch_analyze(limit)
