#!/usr/bin/env python3
"""
Go-Live Readiness Check for AnalysisRepo Cutover

Analysis-specific validation script that checks worker health,
repository implementation, and run consistency.
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

class AnalysisGoLiveChecker:
    """Validates all go-live prerequisites for AnalysisRepo cutover."""

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

    def check_analysis_repo_implementation(self) -> dict:
        """Check if AnalysisRepository implementation is available."""
        try:
            from app.repositories.analysis_repo import AnalysisRepository
            from app.db.session import db_session

            # Basic import test
            repo_available = True

            # Test repository instantiation
            try:
                repo = AnalysisRepository(db_session)
                repo_instantiable = True

                # Test if key methods exist
                required_methods = ['upsert_analysis', 'get_by_item_id', 'get_analysis_status', 'get_aggregations']
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

    def check_analysis_indexes(self) -> dict:
        """Check analysis-specific indexes."""
        required_indexes = [
            'item_analysis_item_id_idx',
            'analysis_runs_status_idx',
            'analysis_run_items_run_id_idx',
            'analysis_run_items_status_idx'
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
            print(f"❌ Analysis index check failed: {e}")
            results["error"] = str(e)

        return results

    def check_analysis_data_integrity(self) -> dict:
        """Check analysis data integrity."""
        try:
            with self.SessionLocal() as session:
                # Check for duplicate item_ids in item_analysis
                duplicates = session.execute(text("""
                    SELECT item_id, COUNT(*) as count
                    FROM item_analysis
                    GROUP BY item_id
                    HAVING COUNT(*) > 1
                    LIMIT 5
                """)).fetchall()

                # Check analysis coverage
                total_items = session.execute(text("SELECT COUNT(*) FROM items")).scalar()
                analyzed_items = session.execute(text("SELECT COUNT(DISTINCT item_id) FROM item_analysis")).scalar()
                coverage = round(analyzed_items / total_items * 100, 1) if total_items > 0 else 0

                # Check run consistency
                run_consistency = session.execute(text("""
                    SELECT
                        ar.status as run_status,
                        COUNT(ari.item_id) as total_items,
                        COUNT(CASE WHEN ari.status = 'completed' THEN 1 END) as completed_items,
                        COUNT(CASE WHEN ari.status = 'failed' THEN 1 END) as failed_items
                    FROM analysis_runs ar
                    LEFT JOIN analysis_run_items ari ON ar.id = ari.run_id
                    WHERE ar.created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY ar.id, ar.status
                    LIMIT 10
                """)).fetchall()

                return {
                    "duplicate_items": len(duplicates),
                    "duplicates_sample": [dict(row._mapping) for row in duplicates[:3]],
                    "analysis_coverage": coverage,
                    "total_items": total_items,
                    "analyzed_items": analyzed_items,
                    "run_consistency": [dict(row._mapping) for row in run_consistency]
                }

        except Exception as e:
            print(f"❌ Data integrity check failed: {e}")
            return {"error": str(e)}

    def check_worker_health(self) -> dict:
        """Check analysis worker health via API."""
        try:
            # Test worker status endpoint
            response = requests.get(f"{self.api_base}/api/analysis/worker/status", timeout=5)
            worker_responsive = response.status_code == 200

            if worker_responsive:
                worker_data = response.json()
            else:
                worker_data = None

            # Test analysis stats endpoint
            try:
                stats_response = requests.get(f"{self.api_base}/api/analysis/stats", timeout=5)
                stats_available = stats_response.status_code == 200
                if stats_available:
                    stats_data = stats_response.json()
                else:
                    stats_data = None
            except:
                stats_available = False
                stats_data = None

            return {
                "worker_responsive": worker_responsive,
                "worker_data": worker_data,
                "stats_available": stats_available,
                "stats_data": stats_data
            }

        except Exception as e:
            print(f"❌ Worker health check failed: {e}")
            return {"error": str(e)}

    def check_raw_sql_usage(self) -> dict:
        """Check for raw SQL usage in analysis code that should use repository."""
        import subprocess
        import os

        try:
            # Change to project directory
            os.chdir('/home/cytrex/news-mcp')

            # Search for raw analysis SQL in worker and API code
            result = subprocess.run([
                'grep', '-r', '-n',
                '--include=*.py',
                'session\\.exec.*analysis\\|INSERT INTO item_analysis\\|UPDATE item_analysis',
                'app/worker', 'app/api'
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
        """Run all analysis go-live checks and return comprehensive report."""
        print("🧬 Running AnalysisRepo Go-Live Readiness Check")
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

        # 2. AnalysisRepository implementation
        print("\n2️⃣ AnalysisRepository Implementation")
        repo = self.check_analysis_repo_implementation()
        repo_ok = repo.get("repository_available", False) and repo.get("repository_instantiable", False) and repo.get("methods_complete", False)
        results["checks"]["analysis_repository"] = {
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

        # 3. Analysis-specific indexes
        print("\n3️⃣ Analysis Indexes")
        indexes = self.check_analysis_indexes()
        indexes_ok = len(indexes.get("missing", [])) == 0
        results["checks"]["analysis_indexes"] = {
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

        # 4. Data integrity
        print("\n4️⃣ Analysis Data Integrity")
        integrity = self.check_analysis_data_integrity()
        integrity_ok = "error" not in integrity and integrity.get("duplicate_items", 0) == 0
        results["checks"]["data_integrity"] = {
            "status": "✅" if integrity_ok else "❌",
            "ready": integrity_ok,
            "details": integrity
        }
        if not integrity_ok:
            results["overall_ready"] = False
        if integrity_ok:
            print(f"   Analysis coverage: {integrity['analysis_coverage']}%")
            print(f"   Duplicate items: {integrity['duplicate_items']}")
            print(f"   Run consistency: {len(integrity.get('run_consistency', []))} recent runs")
        else:
            print(f"   ❌ {integrity.get('error', 'Data integrity issues found')}")

        # 5. Worker health
        print("\n5️⃣ Worker Health")
        worker = self.check_worker_health()
        worker_ok = worker.get("worker_responsive", False)
        results["checks"]["worker_health"] = {
            "status": "✅" if worker_ok else "❌",
            "ready": worker_ok,
            "details": worker
        }
        if not worker_ok:
            results["overall_ready"] = False
        print(f"   Worker responsive: {'✅' if worker.get('worker_responsive') else '❌'}")
        print(f"   Stats available: {'✅' if worker.get('stats_available') else '⚠️ Not configured'}")
        if worker.get("worker_data"):
            heartbeat = worker["worker_data"].get("heartbeat_age_seconds", 999)
            print(f"   Heartbeat age: {heartbeat}s {'✅' if heartbeat < 30 else '❌'}")

        # 6. Raw SQL usage check
        print("\n6️⃣ Raw SQL Usage")
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
            print("🎯 ANALYSIS GO-LIVE STATUS: ✅ READY")
            print("✅ All prerequisite checks passed")
            print("🚀 AnalysisRepo cutover can proceed")
        else:
            print("🎯 ANALYSIS GO-LIVE STATUS: ❌ NOT READY")
            print("❌ Some prerequisite checks failed")
            print("🔧 Address issues before proceeding with cutover")

        return results

def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="AnalysisRepo Go-Live Readiness Check")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--check-indexes", action="store_true", help="Only check indexes")
    parser.add_argument("--check-worker", action="store_true", help="Only check worker health")

    args = parser.parse_args()

    checker = AnalysisGoLiveChecker()

    if args.check_indexes:
        print("🔧 Checking analysis indexes...")
        indexes = checker.check_analysis_indexes()
        if indexes.get("missing"):
            print("❌ Missing indexes:")
            for idx in indexes["missing"]:
                print(f"  - {idx}")
        else:
            print("✅ All required indexes exist")
        return

    if args.check_worker:
        print("🤖 Checking worker health...")
        worker = checker.check_worker_health()
        if worker.get("error"):
            print(f"❌ Worker check failed: {worker['error']}")
        elif worker.get("worker_responsive"):
            print("✅ Worker is responsive")
            if worker.get("worker_data"):
                data = worker["worker_data"]
                print(f"   Heartbeat: {data.get('heartbeat_age_seconds', 'N/A')}s")
                print(f"   Queue length: {data.get('queue_length', 'N/A')}")
        else:
            print("❌ Worker not responsive")
        return

    results = checker.run_comprehensive_check()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary already printed in run_comprehensive_check
        pass

if __name__ == "__main__":
    main()