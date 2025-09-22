#!/usr/bin/env python3
"""
Go-Live Readiness Check Template for Repository Cutover

Template script for validating repository migration prerequisites.
Copy and customize for each repository (Items, Analysis, Feeds, etc.).
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

class RepositoryGoLiveChecker:
    """Validates all go-live prerequisites for [REPO_NAME] cutover."""

    def __init__(self, repo_name: str, main_table: str, key_field: str = "id"):
        self.repo_name = repo_name
        self.main_table = main_table
        self.key_field = key_field
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

    def check_repository_implementation(self) -> dict:
        """Check if repository implementation is available."""
        try:
            # Dynamic import - customize for your repository
            module_path = f"app.repositories.{self.repo_name.lower()}_repo"
            class_name = f"{self.repo_name}Repository"

            module = __import__(module_path, fromlist=[class_name])
            repo_class = getattr(module, class_name)

            from app.db.session import db_session

            # Basic import test
            repo_available = True

            # Test repository instantiation
            try:
                repo = repo_class(db_session)
                repo_instantiable = True

                # Test if key methods exist - customize for your repository
                required_methods = ['get_by_id', 'create', 'update', 'delete']  # Customize
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

    def check_required_indexes(self) -> dict:
        """Check repository-specific indexes."""
        # Customize these indexes for your repository
        required_indexes = [
            f'{self.main_table}_{self.key_field}_idx',
            f'{self.main_table}_created_at_idx',
            # Add more repository-specific indexes
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

    def check_data_integrity(self) -> dict:
        """Check data integrity for the main table."""
        try:
            with self.SessionLocal() as session:
                # Check for duplicates
                duplicates = session.execute(text(f"""
                    SELECT {self.key_field}, COUNT(*) as count
                    FROM {self.main_table}
                    GROUP BY {self.key_field}
                    HAVING COUNT(*) > 1
                    LIMIT 5
                """)).fetchall()

                # Get table statistics
                total_rows = session.execute(text(f"SELECT COUNT(*) FROM {self.main_table}")).scalar()

                # Check for recent activity (last 24h) - customize the date field
                recent_activity = session.execute(text(f"""
                    SELECT COUNT(*) FROM {self.main_table}
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)).scalar()

                return {
                    "duplicate_keys": len(duplicates),
                    "duplicates_sample": [dict(row._mapping) for row in duplicates[:3]],
                    "total_rows": total_rows,
                    "recent_activity_24h": recent_activity,
                    "healthy": len(duplicates) == 0 and total_rows > 0
                }

        except Exception as e:
            print(f"❌ Data integrity check failed: {e}")
            return {"error": str(e)}

    def check_api_health(self) -> dict:
        """Check API endpoints related to this repository."""
        try:
            # Customize API endpoints for your repository
            test_endpoints = [
                f"/api/{self.repo_name.lower()}?limit=1",
                f"/docs",  # General API health
            ]

            results = {}
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                    results[endpoint] = {
                        "status_code": response.status_code,
                        "healthy": response.status_code == 200
                    }
                except Exception as e:
                    results[endpoint] = {
                        "status_code": 0,
                        "healthy": False,
                        "error": str(e)
                    }

            # Check feature flag endpoint
            try:
                flag_name = f"{self.repo_name.lower()}_repo"
                flag_response = requests.get(f"{self.api_base}/api/admin/feature-flags/{flag_name}", timeout=5)
                results["feature_flag"] = {
                    "available": flag_response.status_code == 200,
                    "data": flag_response.json() if flag_response.status_code == 200 else None
                }
            except:
                results["feature_flag"] = {"available": False}

            return results

        except Exception as e:
            print(f"❌ API health check failed: {e}")
            return {"error": str(e)}

    def check_raw_sql_usage(self) -> dict:
        """Check for raw SQL usage that should use repository."""
        import subprocess
        import os

        try:
            # Change to project directory
            os.chdir('/home/cytrex/news-mcp')

            # Search for raw SQL in relevant modules - customize paths
            search_paths = ['app/api', 'app/services']  # Add 'app/worker' if relevant

            result = subprocess.run([
                'grep', '-r', '-n',
                '--include=*.py',
                f'session\\.exec.*{self.main_table}\\|INSERT INTO {self.main_table}\\|UPDATE {self.main_table}',
                *search_paths
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
        """Run all go-live checks and return comprehensive report."""
        print(f"🚀 Running {self.repo_name}Repository Go-Live Readiness Check")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "repository": self.repo_name,
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

        # 2. Repository implementation
        print(f"\n2️⃣ {self.repo_name}Repository Implementation")
        repo = self.check_repository_implementation()
        repo_ok = repo.get("repository_available", False) and repo.get("repository_instantiable", False) and repo.get("methods_complete", False)
        results["checks"]["repository"] = {
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

        # 3. Required indexes
        print("\n3️⃣ Required Indexes")
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

        # 4. Data integrity
        print("\n4️⃣ Data Integrity")
        integrity = self.check_data_integrity()
        integrity_ok = "error" not in integrity and integrity.get("healthy", False)
        results["checks"]["data_integrity"] = {
            "status": "✅" if integrity_ok else "❌",
            "ready": integrity_ok,
            "details": integrity
        }
        if not integrity_ok:
            results["overall_ready"] = False
        if integrity_ok:
            print(f"   Total rows: {integrity['total_rows']:,}")
            print(f"   Duplicate keys: {integrity['duplicate_keys']}")
            print(f"   Recent activity (24h): {integrity['recent_activity_24h']:,}")
        else:
            print(f"   ❌ {integrity.get('error', 'Data integrity issues found')}")

        # 5. API health
        print("\n5️⃣ API Health")
        api = self.check_api_health()
        api_ok = "error" not in api and all(
            endpoint_data.get("healthy", False)
            for endpoint_data in api.values()
            if isinstance(endpoint_data, dict) and "healthy" in endpoint_data
        )
        results["checks"]["api"] = {
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
            print(f"🎯 {self.repo_name.upper()} GO-LIVE STATUS: ✅ READY")
            print("✅ All prerequisite checks passed")
            print(f"🚀 {self.repo_name}Repository cutover can proceed")
        else:
            print(f"🎯 {self.repo_name.upper()} GO-LIVE STATUS: ❌ NOT READY")
            print("❌ Some prerequisite checks failed")
            print("🔧 Address issues before proceeding with cutover")

        return results

def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Repository Go-Live Readiness Check")
    parser.add_argument("--repo", required=True, help="Repository name (e.g., Items, Analysis, Feeds)")
    parser.add_argument("--table", required=True, help="Main table name (e.g., items, feeds)")
    parser.add_argument("--key-field", default="id", help="Primary key field name")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--check-indexes", action="store_true", help="Only check indexes")
    parser.add_argument("--check-api", action="store_true", help="Only check API health")

    args = parser.parse_args()

    checker = RepositoryGoLiveChecker(args.repo, args.table, args.key_field)

    if args.check_indexes:
        print(f"🔧 Checking {args.repo} indexes...")
        indexes = checker.check_required_indexes()
        if indexes.get("missing"):
            print("❌ Missing indexes:")
            for idx in indexes["missing"]:
                print(f"  - {idx}")
        else:
            print("✅ All required indexes exist")
        return

    if args.check_api:
        print(f"🌐 Checking {args.repo} API health...")
        api = checker.check_api_health()
        if api.get("error"):
            print(f"❌ API check failed: {api['error']}")
        else:
            for endpoint, data in api.items():
                if isinstance(data, dict) and "healthy" in data:
                    status = "✅" if data["healthy"] else "❌"
                    print(f"   {endpoint}: {status}")
        return

    results = checker.run_comprehensive_check()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Summary already printed in run_comprehensive_check
        pass

if __name__ == "__main__":
    main()