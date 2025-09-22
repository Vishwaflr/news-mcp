#!/usr/bin/env python3
"""
Go-Live Readiness Check for FeedsRepo Cutover

Validates all go-live prerequisites for feeds repository migration.
Focuses on CRUD operations, health monitoring, and UI consistency.
"""

import sys
import json
import time
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, '/home/cytrex/news-mcp')

from app.config import settings

class FeedsGoLiveChecker:
    """Validates all go-live prerequisites for FeedsRepo cutover."""

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

    def check_feeds_repo_implementation(self) -> dict:
        """Check if FeedsRepository implementation is available."""
        try:
            from app.repositories.feeds_repo import FeedsRepository
            from app.db.session import db_session

            # Basic import test
            repo_available = True

            # Test repository instantiation
            try:
                repo = FeedsRepository(db_session)
                repo_instantiable = True

                # Test if key methods exist
                required_methods = [
                    'get_by_id', 'list', 'create', 'update', 'delete',
                    'get_health', 'list_health_summary', 'get_status_counts'
                ]
                missing_methods = []

                for method in required_methods:
                    if not hasattr(repo, method):
                        missing_methods.append(method)

                methods_complete = len(missing_methods) == 0

            except Exception as e:
                repo_instantiable = False
                methods_complete = False
                repo_error = str(e)
                missing_methods = []

            return {
                "repository_available": repo_available,
                "repository_instantiable": repo_instantiable,
                "methods_complete": methods_complete,
                "missing_methods": missing_methods,
                "error": repo_error if not repo_instantiable else None
            }

        except Exception as e:
            return {
                "repository_available": False,
                "error": str(e)
            }

    def check_feeds_indexes(self) -> dict:
        """Check feeds-specific indexes."""
        required_indexes = [
            'feeds_pkey',  # Primary key
            'feeds_url_unique',  # URL uniqueness
            'feed_health_feed_id_created_at_idx',  # Health lookups
            'feeds_active_created_at_idx',  # Active feeds lists
            'feed_categories_feed_id_idx'  # Category lookups (if used)
        ]

        results = {"missing": [], "existing": [], "optional_missing": []}

        try:
            with self.SessionLocal() as session:
                # Get all indexes for feeds-related tables
                query = text("""
                    SELECT indexname, tablename FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename IN ('feeds', 'feed_health', 'feed_categories')
                """)
                existing_indexes = session.execute(query).fetchall()
                existing_names = [row[0] for row in existing_indexes]

                for index_name in required_indexes:
                    # Check if exact index exists or similar pattern
                    exact_match = index_name in existing_names
                    pattern_match = any(index_name.replace('_idx', '') in existing
                                      for existing in existing_names)

                    if exact_match or pattern_match:
                        results["existing"].append(index_name)
                    elif 'feed_categories' in index_name:
                        # Feed categories might not exist yet
                        results["optional_missing"].append(index_name)
                    else:
                        results["missing"].append(index_name)

        except Exception as e:
            print(f"❌ Feeds index check failed: {e}")
            results["error"] = str(e)

        return results

    def check_feeds_data_integrity(self) -> dict:
        """Check feeds data integrity."""
        try:
            with self.SessionLocal() as session:
                # Check for URL duplicates
                url_duplicates = session.execute(text("""
                    SELECT url, COUNT(*) as count
                    FROM feeds
                    GROUP BY url
                    HAVING COUNT(*) > 1
                    LIMIT 5
                """)).fetchall()

                # Get feed statistics
                total_feeds = session.execute(text("SELECT COUNT(*) FROM feeds")).scalar()
                active_feeds = session.execute(text("SELECT COUNT(*) FROM feeds WHERE active = true")).scalar()

                # Check feeds without health records
                feeds_without_health = session.execute(text("""
                    SELECT COUNT(*) FROM feeds f
                    LEFT JOIN feed_health fh ON f.id = fh.feed_id
                    WHERE fh.feed_id IS NULL
                """)).scalar()

                # Check recent health activity
                recent_health_updates = session.execute(text("""
                    SELECT COUNT(DISTINCT feed_id) FROM feed_health
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)).scalar()

                # Check referential integrity (items → feeds)
                orphaned_items = session.execute(text("""
                    SELECT COUNT(*) FROM items i
                    LEFT JOIN feeds f ON i.feed_id = f.id
                    WHERE f.id IS NULL
                """)).scalar()

                return {
                    "url_duplicates": len(url_duplicates),
                    "duplicates_sample": [dict(row._mapping) for row in url_duplicates[:3]],
                    "total_feeds": total_feeds,
                    "active_feeds": active_feeds,
                    "feeds_without_health": feeds_without_health,
                    "recent_health_updates": recent_health_updates,
                    "orphaned_items": orphaned_items,
                    "healthy": (len(url_duplicates) == 0 and
                              feeds_without_health == 0 and
                              orphaned_items == 0)
                }

        except Exception as e:
            print(f"❌ Feeds data integrity check failed: {e}")
            return {"error": str(e)}

    def check_feeds_api_health(self) -> dict:
        """Check feeds API endpoints."""
        try:
            endpoints_to_test = {
                "/api/feeds": "Feed list endpoint",
                "/api/feeds/1": "Feed details endpoint",
                "/api/feeds/1/health": "Feed health endpoint",
                "/api/health/feeds": "Feeds health summary",
                "/docs": "API documentation"
            }

            results = {}

            for endpoint, description in endpoints_to_test.items():
                try:
                    response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                    results[endpoint] = {
                        "description": description,
                        "status_code": response.status_code,
                        "healthy": response.status_code in [200, 404],  # 404 OK for feed/1 if doesn't exist
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                except Exception as e:
                    results[endpoint] = {
                        "description": description,
                        "status_code": 0,
                        "healthy": False,
                        "error": str(e)
                    }

            # Test feature flag endpoint
            try:
                flag_response = requests.get(f"{self.api_base}/api/admin/feature-flags/feeds_repo", timeout=5)
                results["feature_flag"] = {
                    "description": "Feeds repository feature flag",
                    "available": flag_response.status_code == 200,
                    "data": flag_response.json() if flag_response.status_code == 200 else None
                }
            except:
                results["feature_flag"] = {
                    "description": "Feeds repository feature flag",
                    "available": False
                }

            return results

        except Exception as e:
            print(f"❌ Feeds API health check failed: {e}")
            return {"error": str(e)}

    def check_crud_performance(self) -> dict:
        """Test CRUD operation performance."""
        try:
            performance_results = {}

            # Test feed list performance
            start_time = time.perf_counter()
            try:
                list_response = requests.get(f"{self.api_base}/api/feeds?limit=20", timeout=10)
                list_duration = (time.perf_counter() - start_time) * 1000

                performance_results["list_feeds"] = {
                    "duration_ms": round(list_duration, 2),
                    "success": list_response.status_code == 200,
                    "target_ms": 200,
                    "passed": list_duration <= 200
                }

                if list_response.status_code == 200:
                    feed_count = len(list_response.json().get('feeds', []))
                    performance_results["list_feeds"]["feed_count"] = feed_count

            except Exception as e:
                performance_results["list_feeds"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            # Test feed details performance (use first feed)
            try:
                # Get first feed ID
                list_response = requests.get(f"{self.api_base}/api/feeds?limit=1", timeout=5)
                if list_response.status_code == 200:
                    feeds = list_response.json().get('feeds', [])
                    if feeds:
                        feed_id = feeds[0]['id']

                        start_time = time.perf_counter()
                        detail_response = requests.get(f"{self.api_base}/api/feeds/{feed_id}", timeout=5)
                        detail_duration = (time.perf_counter() - start_time) * 1000

                        performance_results["feed_details"] = {
                            "duration_ms": round(detail_duration, 2),
                            "success": detail_response.status_code == 200,
                            "target_ms": 100,
                            "passed": detail_duration <= 100
                        }

            except Exception as e:
                performance_results["feed_details"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            # Test health query performance
            start_time = time.perf_counter()
            try:
                health_response = requests.get(f"{self.api_base}/api/health/feeds", timeout=10)
                health_duration = (time.perf_counter() - start_time) * 1000

                performance_results["health_summary"] = {
                    "duration_ms": round(health_duration, 2),
                    "success": health_response.status_code == 200,
                    "target_ms": 500,
                    "passed": health_duration <= 500
                }

            except Exception as e:
                performance_results["health_summary"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            return performance_results

        except Exception as e:
            return {"error": str(e)}

    def check_raw_sql_usage(self) -> dict:
        """Check for raw SQL usage in feeds code."""
        import subprocess
        import os

        try:
            # Change to project directory
            os.chdir('/home/cytrex/news-mcp')

            # Search for raw feeds SQL in web and API code
            result = subprocess.run([
                'grep', '-r', '-n',
                '--include=*.py',
                'session\\.exec.*feeds\\|session\\.exec.*feed_health\\|INSERT INTO feeds\\|UPDATE feeds',
                'app/web', 'app/api'
            ], capture_output=True, text=True, timeout=10)

            raw_sql_found = result.returncode == 0
            raw_sql_lines = result.stdout.strip().split('\n') if raw_sql_found and result.stdout.strip() else []

            return {
                "raw_sql_found": raw_sql_found,
                "violation_count": len(raw_sql_lines),
                "violations": raw_sql_lines[:10]  # First 10 violations
            }

        except Exception as e:
            return {"error": str(e)}

    def run_comprehensive_check(self) -> dict:
        """Run all feeds go-live checks and return comprehensive report."""
        print("🍽️  Running FeedsRepo Go-Live Readiness Check")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "repository": "Feeds",
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

        # 2. FeedsRepository implementation
        print("\n2️⃣ FeedsRepository Implementation")
        repo = self.check_feeds_repo_implementation()
        repo_ok = (repo.get("repository_available", False) and
                  repo.get("repository_instantiable", False) and
                  repo.get("methods_complete", False))
        results["checks"]["feeds_repository"] = {
            "status": "✅" if repo_ok else "❌",
            "ready": repo_ok,
            "details": repo
        }
        if not repo_ok:
            results["overall_ready"] = False
        print(f"   Available: {'✅' if repo.get('repository_available') else '❌'}")
        print(f"   Instantiable: {'✅' if repo.get('repository_instantiable') else '❌'}")
        print(f"   Methods Complete: {'✅' if repo.get('methods_complete') else '❌'}")
        if repo.get("missing_methods"):
            print(f"   ⚠️ Missing methods: {', '.join(repo['missing_methods'])}")
        if repo.get("error"):
            print(f"   ⚠️ Error: {repo['error']}")

        # 3. Feeds-specific indexes
        print("\n3️⃣ Feeds Indexes")
        indexes = self.check_feeds_indexes()
        indexes_ok = len(indexes.get("missing", [])) == 0
        results["checks"]["feeds_indexes"] = {
            "status": "✅" if indexes_ok else "❌",
            "ready": indexes_ok,
            "details": indexes
        }
        if not indexes_ok:
            results["overall_ready"] = False
        print(f"   Existing: {len(indexes.get('existing', []))}")
        print(f"   Missing: {len(indexes.get('missing', []))}")
        print(f"   Optional Missing: {len(indexes.get('optional_missing', []))}")
        if indexes.get("missing"):
            print(f"   ❌ Critical Missing: {', '.join(indexes['missing'])}")
        if indexes.get("optional_missing"):
            print(f"   ⚠️ Optional Missing: {', '.join(indexes['optional_missing'])}")

        # 4. Data integrity
        print("\n4️⃣ Feeds Data Integrity")
        integrity = self.check_feeds_data_integrity()
        integrity_ok = "error" not in integrity and integrity.get("healthy", False)
        results["checks"]["data_integrity"] = {
            "status": "✅" if integrity_ok else "❌",
            "ready": integrity_ok,
            "details": integrity
        }
        if not integrity_ok:
            results["overall_ready"] = False
        if integrity_ok:
            print(f"   Total feeds: {integrity['total_feeds']:,}")
            print(f"   Active feeds: {integrity['active_feeds']:,}")
            print(f"   URL duplicates: {integrity['url_duplicates']}")
            print(f"   Feeds without health: {integrity['feeds_without_health']}")
            print(f"   Recent health updates: {integrity['recent_health_updates']}")
            print(f"   Orphaned items: {integrity['orphaned_items']}")
        else:
            print(f"   ❌ {integrity.get('error', 'Data integrity issues found')}")

        # 5. API health
        print("\n5️⃣ Feeds API Health")
        api = self.check_feeds_api_health()
        api_ok = "error" not in api and all(
            endpoint_data.get("healthy", False)
            for endpoint, endpoint_data in api.items()
            if isinstance(endpoint_data, dict) and "healthy" in endpoint_data
        )
        results["checks"]["api_health"] = {
            "status": "✅" if api_ok else "❌",
            "ready": api_ok,
            "details": api
        }
        if not api_ok:
            results["overall_ready"] = False

        healthy_endpoints = sum(1 for data in api.values()
                              if isinstance(data, dict) and data.get("healthy", False))
        total_endpoints = len([data for data in api.values()
                             if isinstance(data, dict) and "healthy" in data])
        print(f"   API endpoints: {healthy_endpoints}/{total_endpoints} healthy")
        print(f"   Feature flags: {'✅' if api.get('feature_flag', {}).get('available') else '⚠️ Not configured'}")

        # 6. CRUD performance
        print("\n6️⃣ CRUD Performance")
        performance = self.check_crud_performance()
        perf_ok = "error" not in performance and all(
            test.get("passed", False) for test in performance.values() if isinstance(test, dict)
        )
        results["checks"]["crud_performance"] = {
            "status": "✅" if perf_ok else "❌",
            "ready": perf_ok,
            "details": performance
        }
        if not perf_ok:
            results["overall_ready"] = False

        for test_name, test_data in performance.items():
            if isinstance(test_data, dict):
                if "error" in test_data:
                    print(f"   {test_name}: ❌ {test_data['error']}")
                else:
                    status = "✅" if test_data.get("passed", False) else "❌"
                    duration = test_data.get("duration_ms", 0)
                    target = test_data.get("target_ms", 0)
                    print(f"   {test_name}: {status} {duration}ms (target: {target}ms)")

        # 7. Raw SQL usage check
        print("\n7️⃣ Raw SQL Usage")
        sql_check = self.check_raw_sql_usage()
        sql_ok = not sql_check.get("raw_sql_found", True)
        results["checks"]["raw_sql"] = {
            "status": "✅" if sql_ok else "❌",
            "ready": sql_ok,
            "details": sql_check
        }
        if not sql_ok:
            results["overall_ready"] = False
        print(f"   Raw SQL violations: {sql_check.get('violation_count', 'ERROR')}")
        if sql_check.get("violations"):
            print(f"   ⚠️ First violation: {sql_check['violations'][0][:80]}...")

        # Overall assessment
        print("\n" + "=" * 60)
        if results["overall_ready"]:
            print("🎯 FEEDS GO-LIVE STATUS: ✅ READY")
            print("✅ All prerequisite checks passed")
            print("🚀 FeedsRepository cutover can proceed")
        else:
            print("🎯 FEEDS GO-LIVE STATUS: ❌ NOT READY")
            print("❌ Some prerequisite checks failed")
            print("🔧 Address issues before proceeding with cutover")

        return results

def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="FeedsRepo Go-Live Readiness Check")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--check-indexes", action="store_true", help="Only check indexes")
    parser.add_argument("--check-api", action="store_true", help="Only check API health")
    parser.add_argument("--check-performance", action="store_true", help="Only check CRUD performance")

    args = parser.parse_args()

    checker = FeedsGoLiveChecker()

    if args.check_indexes:
        print("🔧 Checking feeds indexes...")
        indexes = checker.check_feeds_indexes()
        if indexes.get("missing"):
            print("❌ Missing critical indexes:")
            for idx in indexes["missing"]:
                print(f"  - {idx}")
        if indexes.get("optional_missing"):
            print("⚠️ Missing optional indexes:")
            for idx in indexes["optional_missing"]:
                print(f"  - {idx}")
        if not indexes.get("missing"):
            print("✅ All critical indexes exist")
        return

    if args.check_api:
        print("🌐 Checking feeds API health...")
        api = checker.check_feeds_api_health()
        if api.get("error"):
            print(f"❌ API check failed: {api['error']}")
        else:
            for endpoint, data in api.items():
                if isinstance(data, dict) and "healthy" in data:
                    status = "✅" if data["healthy"] else "❌"
                    duration = data.get("response_time_ms", 0)
                    print(f"   {endpoint}: {status} ({duration:.1f}ms)")
        return

    if args.check_performance:
        print("⚡ Checking CRUD performance...")
        performance = checker.check_crud_performance()
        if performance.get("error"):
            print(f"❌ Performance check failed: {performance['error']}")
        else:
            for test_name, test_data in performance.items():
                if isinstance(test_data, dict):
                    if "error" in test_data:
                        print(f"   {test_name}: ❌ {test_data['error']}")
                    else:
                        status = "✅" if test_data.get("passed", False) else "❌"
                        duration = test_data.get("duration_ms", 0)
                        target = test_data.get("target_ms", 0)
                        print(f"   {test_name}: {status} {duration}ms (target: {target}ms)")
        return

    results = checker.run_comprehensive_check()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary already printed in run_comprehensive_check
        pass

if __name__ == "__main__":
    main()