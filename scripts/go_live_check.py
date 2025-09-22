#!/usr/bin/env python3
"""
Go-Live Readiness Check for ItemsRepo Cutover

Simplified validation script that checks all go-live prerequisites
without complex async operations.
"""

import sys
import json
import time
import requests
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, '/home/cytrex/news-mcp')

from app.config import settings

class GoLiveChecker:
    """Validates all go-live prerequisites for ItemsRepo cutover."""

    def __init__(self):
        self.engine = create_engine(settings.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.api_base = f"http://{settings.api_host}:{settings.api_port}"

    def check_database_connection(self) -> bool:
        """Check database connectivity."""
        try:
            with self.SessionLocal() as session:
                result = session.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def check_required_indexes(self) -> dict:
        """Check if critical indexes exist."""
        required_indexes = [
            'items_feed_timeline_idx',
            'items_published_idx',
            'items_content_hash_idx',
            'item_analysis_item_id_idx',
            'item_analysis_sentiment_idx'
        ]

        results = {"missing": [], "existing": []}

        try:
            with self.SessionLocal() as session:
                for index_name in required_indexes:
                    query = text("""
                        SELECT indexname FROM pg_indexes
                        WHERE schemaname = 'public'
                        AND indexname LIKE :pattern
                    """)
                    result = session.execute(query, {"pattern": f"%{index_name}%"}).fetchall()

                    if result:
                        results["existing"].append(index_name)
                    else:
                        results["missing"].append(index_name)

        except Exception as e:
            print(f"❌ Index check failed: {e}")
            results["error"] = str(e)

        return results

    def check_table_stats(self) -> dict:
        """Get basic table statistics."""
        try:
            with self.SessionLocal() as session:
                # Items count
                items_count = session.execute(text("SELECT COUNT(*) FROM items")).scalar()

                # Recent items (last 24h)
                recent_items = session.execute(text("""
                    SELECT COUNT(*) FROM items
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)).scalar()

                # Analysis coverage
                analyzed_items = session.execute(text("""
                    SELECT COUNT(DISTINCT item_id) FROM item_analysis
                """)).scalar()

                return {
                    "total_items": items_count,
                    "recent_items_24h": recent_items,
                    "analyzed_items": analyzed_items,
                    "analysis_coverage": round(analyzed_items / items_count * 100, 1) if items_count > 0 else 0
                }

        except Exception as e:
            print(f"❌ Table stats check failed: {e}")
            return {"error": str(e)}

    def check_api_health(self) -> dict:
        """Check API server health."""
        try:
            # Test basic API
            response = requests.get(f"{self.api_base}/docs", timeout=5)
            api_healthy = response.status_code == 200

            # Test items endpoint (legacy)
            items_response = requests.get(f"{self.api_base}/api/items?limit=1", timeout=5)
            items_working = items_response.status_code == 200

            # Try feature flags API (might not be available yet)
            try:
                flags_response = requests.get(f"{self.api_base}/api/admin/feature-flags/", timeout=5)
                feature_flags_available = flags_response.status_code == 200
                if feature_flags_available:
                    feature_flags_data = flags_response.json()
                else:
                    feature_flags_data = None
            except:
                feature_flags_available = False
                feature_flags_data = None

            return {
                "api_healthy": api_healthy,
                "items_endpoint_working": items_working,
                "feature_flags_available": feature_flags_available,
                "feature_flags_data": feature_flags_data
            }

        except Exception as e:
            print(f"❌ API health check failed: {e}")
            return {"error": str(e)}

    def check_repository_implementation(self) -> dict:
        """Check if repository implementation is available."""
        try:
            from app.repositories.items_repo import ItemsRepository
            from app.schemas.items import ItemQuery
            from app.db.session import db_session

            # Basic import test
            repo_available = True

            # Test repository instantiation
            try:
                repo = ItemsRepository(db_session)
                repo_instantiable = True
            except Exception as e:
                repo_instantiable = False
                repo_error = str(e)

            return {
                "repository_available": repo_available,
                "repository_instantiable": repo_instantiable,
                "error": repo_error if not repo_instantiable else None
            }

        except Exception as e:
            return {
                "repository_available": False,
                "error": str(e)
            }

    def run_comprehensive_check(self) -> dict:
        """Run all go-live checks and return comprehensive report."""
        print("🚀 Running Go-Live Readiness Check for ItemsRepo Cutover")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_ready": True,
            "checks": {}
        }

        # 1. Database connectivity
        print("\n1️⃣ Database Connectivity")
        db_ok = self.check_database_connection()
        results["checks"]["database"] = {"status": "✅" if db_ok else "❌", "ready": db_ok}
        if not db_ok:
            results["overall_ready"] = False
        print(f"   Database: {'✅' if db_ok else '❌'}")

        # 2. Required indexes
        print("\n2️⃣ Required Indexes")
        indexes = self.check_required_indexes()
        indexes_ok = len(indexes.get("missing", [])) == 0
        results["checks"]["indexes"] = {
            "status": "✅" if indexes_ok else "❌",
            "ready": indexes_ok,
            "details": indexes
        }
        if not indexes_ok:
            results["overall_ready"] = False
        print(f"   Existing: {len(indexes.get('existing', []))}")
        print(f"   Missing: {len(indexes.get('missing', []))}")
        if indexes.get("missing"):
            print(f"   ⚠️ Missing: {', '.join(indexes['missing'])}")

        # 3. Table statistics
        print("\n3️⃣ Table Statistics")
        stats = self.check_table_stats()
        stats_ok = "error" not in stats and stats.get("total_items", 0) > 0
        results["checks"]["table_stats"] = {
            "status": "✅" if stats_ok else "❌",
            "ready": stats_ok,
            "details": stats
        }
        if stats_ok:
            print(f"   Total items: {stats['total_items']:,}")
            print(f"   Recent (24h): {stats['recent_items_24h']:,}")
            print(f"   Analysis coverage: {stats['analysis_coverage']}%")
        else:
            print(f"   ❌ {stats.get('error', 'Unknown error')}")

        # 4. API Health
        print("\n4️⃣ API Health")
        api = self.check_api_health()
        api_ok = api.get("api_healthy", False) and api.get("items_endpoint_working", False)
        results["checks"]["api"] = {
            "status": "✅" if api_ok else "❌",
            "ready": api_ok,
            "details": api
        }
        if not api_ok:
            results["overall_ready"] = False
        print(f"   API Server: {'✅' if api.get('api_healthy') else '❌'}")
        print(f"   Items Endpoint: {'✅' if api.get('items_endpoint_working') else '❌'}")
        print(f"   Feature Flags: {'✅' if api.get('feature_flags_available') else '⚠️ Not configured'}")

        # 5. Repository Implementation
        print("\n5️⃣ Repository Implementation")
        repo = self.check_repository_implementation()
        repo_ok = repo.get("repository_available", False) and repo.get("repository_instantiable", False)
        results["checks"]["repository"] = {
            "status": "✅" if repo_ok else "❌",
            "ready": repo_ok,
            "details": repo
        }
        if not repo_ok:
            results["overall_ready"] = False
        print(f"   Available: {'✅' if repo.get('repository_available') else '❌'}")
        print(f"   Instantiable: {'✅' if repo.get('repository_instantiable') else '❌'}")
        if repo.get("error"):
            print(f"   ⚠️ Error: {repo['error']}")

        # Overall assessment
        print("\n" + "=" * 60)
        if results["overall_ready"]:
            print("🎯 GO-LIVE STATUS: ✅ READY")
            print("✅ All prerequisite checks passed")
            print("🚀 ItemsRepo cutover can proceed")
        else:
            print("🎯 GO-LIVE STATUS: ❌ NOT READY")
            print("❌ Some prerequisite checks failed")
            print("🔧 Address issues before proceeding with cutover")

        return results

def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Go-Live Readiness Check")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--create-missing-indexes", action="store_true",
                       help="Create missing indexes")

    args = parser.parse_args()

    checker = GoLiveChecker()

    if args.create_missing_indexes:
        print("🔧 Creating missing indexes...")
        indexes = checker.check_required_indexes()

        if indexes.get("missing"):
            index_queries = {
                "items_feed_timeline_idx": "CREATE INDEX CONCURRENTLY items_feed_timeline_idx ON items (feed_id, created_at DESC);",
                "items_published_idx": "CREATE INDEX CONCURRENTLY items_published_idx ON items (published DESC NULLS LAST);",
                "items_content_hash_idx": "CREATE UNIQUE INDEX CONCURRENTLY items_content_hash_idx ON items (content_hash);",
                "item_analysis_item_id_idx": "CREATE INDEX CONCURRENTLY item_analysis_item_id_idx ON item_analysis (item_id);",
                "item_analysis_sentiment_idx": "CREATE INDEX CONCURRENTLY item_analysis_sentiment_idx ON item_analysis (sentiment_label);"
            }

            try:
                # Use autocommit for CONCURRENTLY indexes
                with checker.engine.connect() as conn:
                    conn.execute(text("COMMIT"))  # End any existing transaction
                    for missing_index in indexes["missing"]:
                        if missing_index in index_queries:
                            print(f"Creating {missing_index}...")
                            conn.execute(text(index_queries[missing_index]))
                            print(f"✅ Created {missing_index}")
            except Exception as e:
                print(f"❌ Failed to create indexes: {e}")
        else:
            print("✅ All required indexes already exist")

        return

    results = checker.run_comprehensive_check()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary already printed in run_comprehensive_check
        pass

if __name__ == "__main__":
    main()