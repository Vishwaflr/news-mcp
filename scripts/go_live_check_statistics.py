#!/usr/bin/env python3
"""
Go-Live Readiness Check for StatisticsRepo Cutover

Validates all go-live prerequisites for statistics repository migration.
Focuses on aggregation performance, index optimization, and data consistency.
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

class StatisticsGoLiveChecker:
    """Validates all go-live prerequisites for StatisticsRepo cutover."""

    def __init__(self):
        self.engine = create_engine(settings.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.api_base = f"http://{settings.api_host}:{settings.api_port}"

        # SLO Targets (in milliseconds)
        self.slo_targets = {
            "global_summary_24h": 400,
            "feed_summary_24h": 600,
            "trend_series_24h": 800,
            "trend_series_7d": 1500,
            "topk_feeds": 400,
            "coverage_slo": 300
        }

    def check_database_connection(self) -> bool:
        """Check database connectivity."""
        try:
            with self.SessionLocal() as session:
                result = session.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def check_statistics_repo_implementation(self) -> dict:
        """Check if StatisticsRepository implementation is available."""
        try:
            from app.repositories.statistics_repo import StatisticsRepository
            from app.db.session import db_session

            # Basic import test
            repo_available = True

            # Test repository instantiation
            try:
                repo = StatisticsRepository(db_session)
                repo_instantiable = True

                # Test if key methods exist
                required_methods = [
                    'global_summary', 'feed_summary', 'coverage_slo',
                    'trend_series', 'topk_feeds'
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

    def check_aggregation_indexes(self) -> dict:
        """Check aggregation-optimized indexes."""
        required_indexes = {
            # Items table indexes
            "items_published_at": {
                "table": "items",
                "description": "Time window filtering for aggregations",
                "pattern": "published_at"
            },
            "items_published_at_partial": {
                "table": "items",
                "description": "Partial index for recent items (30 days)",
                "pattern": "published_at.*WHERE.*interval",
                "optional": True
            },
            "items_feed_id_published": {
                "table": "items",
                "description": "Feed-specific time series",
                "pattern": "feed_id.*published_at"
            },

            # Item analysis indexes for JSONB aggregations
            "ia_impact_overall": {
                "table": "item_analysis",
                "description": "Impact aggregations via JSONB",
                "pattern": "impact_json.*overall",
                "optional": True  # Might use first-class columns instead
            },
            "ia_sentiment_label": {
                "table": "item_analysis",
                "description": "Sentiment filtering via JSONB",
                "pattern": "sentiment_json.*label",
                "optional": True
            },
            "ia_urgency_score": {
                "table": "item_analysis",
                "description": "Urgency filtering via JSONB",
                "pattern": "sentiment_json.*urgency",
                "optional": True
            }
        }

        results = {"missing": [], "existing": [], "optional_missing": []}

        try:
            with self.SessionLocal() as session:
                # Get all indexes for relevant tables
                query = text("""
                    SELECT indexname, tablename, indexdef FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename IN ('items', 'item_analysis')
                """)
                existing_indexes = session.execute(query).fetchall()

                for index_key, index_info in required_indexes.items():
                    table = index_info["table"]
                    pattern = index_info["pattern"]
                    optional = index_info.get("optional", False)

                    # Check if any existing index matches the pattern
                    found = False
                    for idx_name, idx_table, idx_def in existing_indexes:
                        if idx_table == table:
                            # Pattern matching in index definition
                            if all(part.lower() in idx_def.lower() for part in pattern.split(".*")):
                                found = True
                                break

                    if found:
                        results["existing"].append(index_key)
                    elif optional:
                        results["optional_missing"].append(index_key)
                    else:
                        results["missing"].append(index_key)

        except Exception as e:
            print(f"❌ Aggregation index check failed: {e}")
            results["error"] = str(e)

        return results

    def check_data_volume_and_quality(self) -> dict:
        """Check data volume and quality for statistics."""
        try:
            with self.SessionLocal() as session:
                # Basic data volume
                total_items = session.execute(text("SELECT COUNT(*) FROM items")).scalar()

                # Recent data (last 30 days)
                recent_items = session.execute(text("""
                    SELECT COUNT(*) FROM items
                    WHERE published_at > NOW() - INTERVAL '30 days'
                """)).scalar()

                # Analysis coverage
                analyzed_items = session.execute(text("""
                    SELECT COUNT(DISTINCT ia.item_id) FROM item_analysis ia
                    JOIN items i ON ia.item_id = i.id
                    WHERE i.published_at > NOW() - INTERVAL '30 days'
                """)).scalar()

                analysis_coverage = round(analyzed_items / recent_items * 100, 1) if recent_items > 0 else 0

                # Feed distribution
                feed_count = session.execute(text("SELECT COUNT(*) FROM feeds WHERE active = true")).scalar()

                # Data quality checks
                items_without_published = session.execute(text("""
                    SELECT COUNT(*) FROM items WHERE published_at IS NULL
                """)).scalar()

                items_future_published = session.execute(text("""
                    SELECT COUNT(*) FROM items
                    WHERE published_at > NOW() + INTERVAL '1 hour'
                """)).scalar()

                return {
                    "total_items": total_items,
                    "recent_items_30d": recent_items,
                    "analyzed_items_30d": analyzed_items,
                    "analysis_coverage_pct": analysis_coverage,
                    "active_feeds": feed_count,
                    "data_quality": {
                        "items_without_published": items_without_published,
                        "items_future_published": items_future_published
                    },
                    "sufficient_data": (recent_items >= 1000 and
                                      analysis_coverage >= 80 and
                                      items_without_published == 0 and
                                      items_future_published == 0)
                }

        except Exception as e:
            print(f"❌ Data volume check failed: {e}")
            return {"error": str(e)}

    def check_aggregation_performance(self) -> dict:
        """Test aggregation query performance against SLO targets."""
        try:
            performance_results = {}

            # Test global summary (24h)
            start_time = time.perf_counter()
            try:
                response = requests.get(f"{self.api_base}/api/statistics/global-summary?period=24h", timeout=30)
                duration = (time.perf_counter() - start_time) * 1000

                performance_results["global_summary_24h"] = {
                    "duration_ms": round(duration, 2),
                    "success": response.status_code == 200,
                    "target_ms": self.slo_targets["global_summary_24h"],
                    "passed": duration <= self.slo_targets["global_summary_24h"],
                    "response_size": len(response.content) if response.status_code == 200 else 0
                }

            except Exception as e:
                performance_results["global_summary_24h"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            # Test feed summary (24h, multiple feeds)
            start_time = time.perf_counter()
            try:
                response = requests.get(f"{self.api_base}/api/statistics/feed-summary?feed_ids=1,2,3&period=24h", timeout=30)
                duration = (time.perf_counter() - start_time) * 1000

                performance_results["feed_summary_24h"] = {
                    "duration_ms": round(duration, 2),
                    "success": response.status_code == 200,
                    "target_ms": self.slo_targets["feed_summary_24h"],
                    "passed": duration <= self.slo_targets["feed_summary_24h"]
                }

            except Exception as e:
                performance_results["feed_summary_24h"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            # Test trend series (24h with 1h buckets)
            start_time = time.perf_counter()
            try:
                response = requests.get(f"{self.api_base}/api/statistics/trends?metric=items&period=24h&bucket=1h", timeout=30)
                duration = (time.perf_counter() - start_time) * 1000

                performance_results["trend_series_24h"] = {
                    "duration_ms": round(duration, 2),
                    "success": response.status_code == 200,
                    "target_ms": self.slo_targets["trend_series_24h"],
                    "passed": duration <= self.slo_targets["trend_series_24h"]
                }

            except Exception as e:
                performance_results["trend_series_24h"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            # Test trend series (7d with 1h buckets - most demanding)
            start_time = time.perf_counter()
            try:
                response = requests.get(f"{self.api_base}/api/statistics/trends?metric=items&period=7d&bucket=1h", timeout=30)
                duration = (time.perf_counter() - start_time) * 1000

                performance_results["trend_series_7d"] = {
                    "duration_ms": round(duration, 2),
                    "success": response.status_code == 200,
                    "target_ms": self.slo_targets["trend_series_7d"],
                    "passed": duration <= self.slo_targets["trend_series_7d"]
                }

            except Exception as e:
                performance_results["trend_series_7d"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            # Test coverage SLO
            start_time = time.perf_counter()
            try:
                response = requests.get(f"{self.api_base}/api/statistics/coverage-slo", timeout=10)
                duration = (time.perf_counter() - start_time) * 1000

                performance_results["coverage_slo"] = {
                    "duration_ms": round(duration, 2),
                    "success": response.status_code == 200,
                    "target_ms": self.slo_targets["coverage_slo"],
                    "passed": duration <= self.slo_targets["coverage_slo"]
                }

            except Exception as e:
                performance_results["coverage_slo"] = {
                    "duration_ms": 0,
                    "success": False,
                    "error": str(e)
                }

            return performance_results

        except Exception as e:
            return {"error": str(e)}

    def check_query_execution_plans(self) -> dict:
        """Analyze query execution plans for critical aggregations."""
        try:
            plan_results = {}

            with self.SessionLocal() as session:
                # Test plan for global summary query
                try:
                    explain_query = text("""
                        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                        SELECT
                            COUNT(*) as total_items,
                            COUNT(ia.item_id) as analyzed_items,
                            AVG((ia.impact_json->>'overall')::numeric) as avg_impact
                        FROM items i
                        LEFT JOIN item_analysis ia ON i.id = ia.item_id
                        WHERE i.published_at > NOW() - INTERVAL '24 hours'
                    """)

                    result = session.execute(explain_query).fetchone()
                    plan_data = result[0][0]  # First element of JSON array

                    execution_time = plan_data.get('Execution Time', 0)
                    total_cost = plan_data.get('Plan', {}).get('Total Cost', 0)

                    plan_results["global_summary_plan"] = {
                        "execution_time_ms": execution_time,
                        "total_cost": total_cost,
                        "uses_index": "Index" in str(plan_data),
                        "sequential_scans": "Seq Scan" in str(plan_data),
                        "healthy": execution_time < 400 and not ("Seq Scan" in str(plan_data))
                    }

                except Exception as e:
                    plan_results["global_summary_plan"] = {"error": str(e)}

                # Test plan for trend series query
                try:
                    explain_query = text("""
                        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                        SELECT
                            date_trunc('hour', i.published_at) as bucket,
                            COUNT(*) as items_count
                        FROM items i
                        WHERE i.published_at > NOW() - INTERVAL '24 hours'
                        GROUP BY date_trunc('hour', i.published_at)
                        ORDER BY bucket
                    """)

                    result = session.execute(explain_query).fetchone()
                    plan_data = result[0][0]

                    execution_time = plan_data.get('Execution Time', 0)

                    plan_results["trend_series_plan"] = {
                        "execution_time_ms": execution_time,
                        "uses_index": "Index" in str(plan_data),
                        "healthy": execution_time < 800
                    }

                except Exception as e:
                    plan_results["trend_series_plan"] = {"error": str(e)}

            return plan_results

        except Exception as e:
            return {"error": str(e)}

    def check_raw_sql_usage(self) -> dict:
        """Check for raw aggregation SQL usage outside repository."""
        import subprocess
        import os

        try:
            # Change to project directory
            os.chdir('/home/cytrex/news-mcp')

            # Search for raw aggregation SQL in web and API code
            result = subprocess.run([
                'grep', '-r', '-n',
                '--include=*.py',
                'session\\.exec.*(COUNT\\|SUM\\|AVG\\|GROUP BY)',
                'app/web', 'app/api'
            ], capture_output=True, text=True, timeout=10)

            raw_sql_found = result.returncode == 0
            raw_sql_lines = result.stdout.strip().split('\n') if raw_sql_found and result.stdout.strip() else []

            # Filter out repository files
            filtered_violations = [line for line in raw_sql_lines
                                 if 'repositories/' not in line and 'legacy' not in line]

            return {
                "raw_aggregation_sql_found": len(filtered_violations) > 0,
                "violation_count": len(filtered_violations),
                "violations": filtered_violations[:10]  # First 10 violations
            }

        except Exception as e:
            return {"error": str(e)}

    def run_comprehensive_check(self) -> dict:
        """Run all statistics go-live checks and return comprehensive report."""
        print("📊 Running StatisticsRepo Go-Live Readiness Check")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "repository": "Statistics",
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

        # 2. StatisticsRepository implementation
        print("\n2️⃣ StatisticsRepository Implementation")
        repo = self.check_statistics_repo_implementation()
        repo_ok = (repo.get("repository_available", False) and
                  repo.get("repository_instantiable", False) and
                  repo.get("methods_complete", False))
        results["checks"]["statistics_repository"] = {
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

        # 3. Aggregation-optimized indexes
        print("\n3️⃣ Aggregation Indexes")
        indexes = self.check_aggregation_indexes()
        indexes_ok = len(indexes.get("missing", [])) == 0
        results["checks"]["aggregation_indexes"] = {
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

        # 4. Data volume and quality
        print("\n4️⃣ Data Volume & Quality")
        data_check = self.check_data_volume_and_quality()
        data_ok = "error" not in data_check and data_check.get("sufficient_data", False)
        results["checks"]["data_quality"] = {
            "status": "✅" if data_ok else "❌",
            "ready": data_ok,
            "details": data_check
        }
        if not data_ok:
            results["overall_ready"] = False
        if data_ok:
            print(f"   Total items: {data_check['total_items']:,}")
            print(f"   Recent items (30d): {data_check['recent_items_30d']:,}")
            print(f"   Analysis coverage: {data_check['analysis_coverage_pct']}%")
            print(f"   Active feeds: {data_check['active_feeds']}")
            quality = data_check['data_quality']
            print(f"   Items without published_at: {quality['items_without_published']}")
            print(f"   Items with future published_at: {quality['items_future_published']}")
        else:
            print(f"   ❌ {data_check.get('error', 'Insufficient data for statistics')}")

        # 5. Aggregation performance
        print("\n5️⃣ Aggregation Performance")
        performance = self.check_aggregation_performance()
        perf_ok = "error" not in performance and all(
            test.get("passed", False) for test in performance.values() if isinstance(test, dict)
        )
        results["checks"]["aggregation_performance"] = {
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

        # 6. Query execution plans
        print("\n6️⃣ Query Execution Plans")
        plans = self.check_query_execution_plans()
        plans_ok = "error" not in plans and all(
            plan.get("healthy", False) for plan in plans.values() if isinstance(plan, dict) and "healthy" in plan
        )
        results["checks"]["execution_plans"] = {
            "status": "✅" if plans_ok else "❌",
            "ready": plans_ok,
            "details": plans
        }
        if not plans_ok:
            results["overall_ready"] = False

        for plan_name, plan_data in plans.items():
            if isinstance(plan_data, dict):
                if "error" in plan_data:
                    print(f"   {plan_name}: ❌ {plan_data['error']}")
                else:
                    status = "✅" if plan_data.get("healthy", False) else "❌"
                    exec_time = plan_data.get("execution_time_ms", 0)
                    uses_index = plan_data.get("uses_index", False)
                    print(f"   {plan_name}: {status} {exec_time:.1f}ms (index: {'✅' if uses_index else '❌'})")

        # 7. Raw SQL usage check
        print("\n7️⃣ Raw Aggregation SQL Usage")
        sql_check = self.check_raw_sql_usage()
        sql_ok = not sql_check.get("raw_aggregation_sql_found", True)
        results["checks"]["raw_sql"] = {
            "status": "✅" if sql_ok else "❌",
            "ready": sql_ok,
            "details": sql_check
        }
        if not sql_ok:
            results["overall_ready"] = False
        print(f"   Raw aggregation SQL violations: {sql_check.get('violation_count', 'ERROR')}")
        if sql_check.get("violations"):
            print(f"   ⚠️ First violation: {sql_check['violations'][0][:80]}...")

        # Overall assessment
        print("\n" + "=" * 60)
        if results["overall_ready"]:
            print("🎯 STATISTICS GO-LIVE STATUS: ✅ READY")
            print("✅ All prerequisite checks passed")
            print("🚀 StatisticsRepository cutover can proceed")
        else:
            print("🎯 STATISTICS GO-LIVE STATUS: ❌ NOT READY")
            print("❌ Some prerequisite checks failed")
            print("🔧 Address issues before proceeding with cutover")

        return results

def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="StatisticsRepo Go-Live Readiness Check")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--check-indexes", action="store_true", help="Only check aggregation indexes")
    parser.add_argument("--check-performance", action="store_true", help="Only check aggregation performance")
    parser.add_argument("--check-plans", action="store_true", help="Only check query execution plans")

    args = parser.parse_args()

    checker = StatisticsGoLiveChecker()

    if args.check_indexes:
        print("🔧 Checking aggregation indexes...")
        indexes = checker.check_aggregation_indexes()
        if indexes.get("missing"):
            print("❌ Missing critical indexes:")
            for idx in indexes["missing"]:
                print(f"  - {idx}")
        if indexes.get("optional_missing"):
            print("⚠️ Missing optional indexes:")
            for idx in indexes["optional_missing"]:
                print(f"  - {idx}")
        if not indexes.get("missing"):
            print("✅ All critical aggregation indexes exist")
        return

    if args.check_performance:
        print("⚡ Checking aggregation performance...")
        performance = checker.check_aggregation_performance()
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

    if args.check_plans:
        print("📋 Checking query execution plans...")
        plans = checker.check_query_execution_plans()
        if plans.get("error"):
            print(f"❌ Plan check failed: {plans['error']}")
        else:
            for plan_name, plan_data in plans.items():
                if isinstance(plan_data, dict):
                    if "error" in plan_data:
                        print(f"   {plan_name}: ❌ {plan_data['error']}")
                    else:
                        status = "✅" if plan_data.get("healthy", False) else "❌"
                        exec_time = plan_data.get("execution_time_ms", 0)
                        uses_index = plan_data.get("uses_index", False)
                        seq_scan = plan_data.get("sequential_scans", False)
                        print(f"   {plan_name}: {status} {exec_time:.1f}ms")
                        print(f"     Uses index: {'✅' if uses_index else '❌'}")
                        print(f"     Sequential scan: {'❌' if seq_scan else '✅'}")
        return

    results = checker.run_comprehensive_check()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary already printed in run_comprehensive_check
        pass

if __name__ == "__main__":
    main()