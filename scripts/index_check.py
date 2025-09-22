#!/usr/bin/env python3
"""
Index reality check script for repository queries.
Validates that required indexes exist and queries perform within SLO.
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, '/home/cytrex/news-mcp')

from app.config import settings
from app.repositories.items_repo import ItemsRepository
from app.schemas.items import ItemQuery
from app.db.session import DatabaseSession


class IndexChecker:
    """Check database indexes and query performance."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db_session = DatabaseSession(database_url)

    def check_existing_indexes(self) -> Dict[str, List[str]]:
        """Check what indexes currently exist."""
        with self.SessionLocal() as session:
            # Get all indexes
            query = """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
            """

            result = session.execute(text(query))
            indexes = {}

            for row in result:
                table = row.tablename
                if table not in indexes:
                    indexes[table] = []
                indexes[table].append({
                    'name': row.indexname,
                    'definition': row.indexdef
                })

            return indexes

    def check_required_indexes(self) -> List[Dict[str, Any]]:
        """Check if required indexes for ItemsRepository exist."""
        required_indexes = [
            {
                'table': 'items',
                'columns': ['feed_id', 'created_at'],
                'name': 'items_feed_timeline_idx',
                'description': 'Feed timeline queries',
                'query': 'CREATE INDEX CONCURRENTLY items_feed_timeline_idx ON items (feed_id, created_at DESC);'
            },
            {
                'table': 'items',
                'columns': ['published'],
                'name': 'items_published_idx',
                'description': 'Global timeline queries',
                'query': 'CREATE INDEX CONCURRENTLY items_published_idx ON items (published DESC NULLS LAST);'
            },
            {
                'table': 'items',
                'columns': ['content_hash'],
                'name': 'items_content_hash_idx',
                'description': 'Duplicate detection (should be unique)',
                'query': 'CREATE UNIQUE INDEX CONCURRENTLY items_content_hash_idx ON items (content_hash);'
            },
            {
                'table': 'item_analysis',
                'columns': ['item_id'],
                'name': 'item_analysis_item_id_idx',
                'description': 'Analysis joins',
                'query': 'CREATE INDEX CONCURRENTLY item_analysis_item_id_idx ON item_analysis (item_id);'
            },
            {
                'table': 'item_analysis',
                'columns': ['sentiment_label'],
                'name': 'item_analysis_sentiment_idx',
                'description': 'Sentiment filtering',
                'query': 'CREATE INDEX CONCURRENTLY item_analysis_sentiment_idx ON item_analysis (sentiment_label);'
            },
            {
                'table': 'feed_categories',
                'columns': ['feed_id'],
                'name': 'feed_categories_feed_id_idx',
                'description': 'Category filtering',
                'query': 'CREATE INDEX CONCURRENTLY feed_categories_feed_id_idx ON feed_categories (feed_id);'
            },
            {
                'table': 'feed_categories',
                'columns': ['category_id'],
                'name': 'feed_categories_category_id_idx',
                'description': 'Category filtering',
                'query': 'CREATE INDEX CONCURRENTLY feed_categories_category_id_idx ON feed_categories (category_id);'
            }
        ]

        existing_indexes = self.check_existing_indexes()
        results = []

        for req_idx in required_indexes:
            table = req_idx['table']
            idx_name = req_idx['name']

            exists = False
            if table in existing_indexes:
                for existing in existing_indexes[table]:
                    if idx_name in existing['name'] or self._covers_columns(existing['definition'], req_idx['columns']):
                        exists = True
                        break

            results.append({
                'name': idx_name,
                'table': table,
                'columns': req_idx['columns'],
                'description': req_idx['description'],
                'exists': exists,
                'create_query': req_idx['query']
            })

        return results

    def _covers_columns(self, index_def: str, required_columns: List[str]) -> bool:
        """Check if index definition covers required columns."""
        index_def_lower = index_def.lower()
        for col in required_columns:
            if col.lower() not in index_def_lower:
                return False
        return True

    async def run_performance_tests(self) -> List[Dict[str, Any]]:
        """Run performance tests on critical queries."""
        items_repo = ItemsRepository(self.db_session)

        test_cases = [
            {
                'name': 'Global timeline (no filters)',
                'query': ItemQuery(sort_by="created_at", sort_desc=True),
                'limit': 50,
                'target_ms': 100
            },
            {
                'name': 'Feed timeline',
                'query': ItemQuery(feed_ids=[1], sort_by="created_at", sort_desc=True),
                'limit': 50,
                'target_ms': 50
            },
            {
                'name': 'Sentiment filter',
                'query': ItemQuery(sentiment="positive", sort_by="created_at", sort_desc=True),
                'limit': 50,
                'target_ms': 200
            },
            {
                'name': 'Complex filter (feed + sentiment + impact)',
                'query': ItemQuery(
                    feed_ids=[1, 2, 3],
                    sentiment="positive",
                    impact_min=0.5,
                    sort_by="created_at",
                    sort_desc=True
                ),
                'limit': 50,
                'target_ms': 300
            },
            {
                'name': 'Search query',
                'query': ItemQuery(search="bitcoin", sort_by="created_at", sort_desc=True),
                'limit': 50,
                'target_ms': 500
            },
            {
                'name': 'Count query (no filters)',
                'query': ItemQuery(),
                'limit': 0,  # Count only
                'target_ms': 50
            }
        ]

        results = []

        for test_case in test_cases:
            try:
                # Warm up
                if test_case['limit'] > 0:
                    await items_repo.query(test_case['query'], limit=test_case['limit'])
                else:
                    await items_repo.count(test_case['query'])

                # Measure performance
                start_time = time.perf_counter()

                if test_case['limit'] > 0:
                    result = await items_repo.query(test_case['query'], limit=test_case['limit'])
                    row_count = len(result)
                else:
                    row_count = await items_repo.count(test_case['query'])

                duration_ms = (time.perf_counter() - start_time) * 1000

                results.append({
                    'name': test_case['name'],
                    'duration_ms': round(duration_ms, 2),
                    'target_ms': test_case['target_ms'],
                    'passed': duration_ms <= test_case['target_ms'],
                    'row_count': row_count,
                    'query': test_case['query'].dict()
                })

            except Exception as e:
                results.append({
                    'name': test_case['name'],
                    'duration_ms': 0,
                    'target_ms': test_case['target_ms'],
                    'passed': False,
                    'error': str(e),
                    'query': test_case['query'].dict()
                })

        return results

    def explain_query(self, sql: str, params: Dict[str, Any]) -> str:
        """Get EXPLAIN ANALYZE for a query."""
        with self.SessionLocal() as session:
            explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
            result = session.execute(text(explain_sql), params)
            return result.fetchone()[0]

    def get_table_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get table statistics."""
        with self.SessionLocal() as session:
            query = """
            SELECT
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
            """

            result = session.execute(text(query))
            stats = {}

            for row in result:
                stats[row.tablename] = {
                    'inserts': row.inserts,
                    'updates': row.updates,
                    'deletes': row.deletes,
                    'live_rows': row.live_rows,
                    'dead_rows': row.dead_rows,
                    'last_vacuum': row.last_vacuum,
                    'last_autovacuum': row.last_autovacuum,
                    'last_analyze': row.last_analyze,
                    'last_autoanalyze': row.last_autoanalyze
                }

            return stats

    def generate_report(self) -> str:
        """Generate comprehensive index and performance report."""
        print("🔍 Running index reality check...")

        # Check indexes
        print("📊 Checking required indexes...")
        index_results = self.check_required_indexes()

        # Run performance tests
        print("⏱️  Running performance tests...")
        perf_results = asyncio.run(self.run_performance_tests())

        # Get table stats
        print("📈 Getting table statistics...")
        table_stats = self.get_table_stats()

        # Generate report
        report = []
        report.append("# Index Reality Check Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Index status
        report.append("## Index Status")
        missing_indexes = [idx for idx in index_results if not idx['exists']]
        existing_indexes = [idx for idx in index_results if idx['exists']]

        report.append(f"✅ Existing indexes: {len(existing_indexes)}")
        report.append(f"❌ Missing indexes: {len(missing_indexes)}")
        report.append("")

        if missing_indexes:
            report.append("### Missing Indexes (CRITICAL)")
            for idx in missing_indexes:
                report.append(f"- **{idx['name']}** ({idx['table']}): {idx['description']}")
                report.append(f"  ```sql")
                report.append(f"  {idx['create_query']}")
                report.append(f"  ```")
            report.append("")

        # Performance results
        report.append("## Performance Test Results")
        passed_tests = [test for test in perf_results if test.get('passed', False)]
        failed_tests = [test for test in perf_results if not test.get('passed', False)]

        report.append(f"✅ Passed: {len(passed_tests)}")
        report.append(f"❌ Failed: {len(failed_tests)}")
        report.append("")

        if failed_tests:
            report.append("### Failed Tests (PERFORMANCE ISSUE)")
            for test in failed_tests:
                if 'error' in test:
                    report.append(f"- **{test['name']}**: ERROR - {test['error']}")
                else:
                    report.append(f"- **{test['name']}**: {test['duration_ms']:.1f}ms > {test['target_ms']}ms (rows: {test.get('row_count', 'N/A')})")
            report.append("")

        # Performance summary
        report.append("### Performance Summary")
        report.append("| Test | Duration (ms) | Target (ms) | Status | Rows |")
        report.append("|------|---------------|-------------|---------|------|")
        for test in perf_results:
            status = "✅" if test.get('passed', False) else "❌"
            duration = test['duration_ms'] if 'error' not in test else "ERROR"
            rows = test.get('row_count', 'N/A')
            report.append(f"| {test['name']} | {duration} | {test['target_ms']} | {status} | {rows} |")
        report.append("")

        # Table statistics
        report.append("## Table Statistics")
        for table_name, stats in table_stats.items():
            if table_name in ['items', 'item_analysis', 'feeds', 'feed_categories']:
                report.append(f"### {table_name}")
                report.append(f"- Live rows: {stats['live_rows']:,}")
                report.append(f"- Dead rows: {stats['dead_rows']:,}")
                report.append(f"- Last analyze: {stats['last_autoanalyze'] or 'Never'}")
                report.append("")

        # Recommendations
        report.append("## Recommendations")
        if missing_indexes:
            report.append("1. **URGENT**: Create missing indexes before production deployment")
            for idx in missing_indexes[:3]:  # Top 3
                report.append(f"   - {idx['name']}: {idx['description']}")

        if failed_tests:
            report.append("2. **Performance**: Investigate slow queries")
            for test in failed_tests[:3]:  # Top 3 slowest
                if 'error' not in test:
                    report.append(f"   - {test['name']}: {test['duration_ms']:.1f}ms")

        # Vacuum recommendations
        for table_name, stats in table_stats.items():
            if stats['dead_rows'] > stats['live_rows'] * 0.1:  # >10% dead rows
                report.append(f"3. **Maintenance**: VACUUM {table_name} (dead rows: {stats['dead_rows']:,})")

        return "\n".join(report)


async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--create-missing":
        create_missing = True
    else:
        create_missing = False

    checker = IndexChecker(settings.database_url)

    # Generate report
    report = checker.generate_report()
    print(report)

    # Save report
    with open('/home/cytrex/news-mcp/INDEX_REALITY_CHECK.md', 'w') as f:
        f.write(report)

    print(f"\n📄 Report saved to INDEX_REALITY_CHECK.md")

    # Optionally create missing indexes
    if create_missing:
        print("\n🔧 Creating missing indexes...")
        index_results = checker.check_required_indexes()
        missing = [idx for idx in index_results if not idx['exists']]

        if missing:
            print("⚠️  CREATING INDEXES CONCURRENTLY - This may take time!")
            for idx in missing:
                print(f"Creating {idx['name']}...")
                try:
                    with checker.SessionLocal() as session:
                        session.execute(text(idx['create_query']))
                        session.commit()
                    print(f"✅ Created {idx['name']}")
                except Exception as e:
                    print(f"❌ Failed to create {idx['name']}: {e}")
        else:
            print("✅ All indexes already exist!")


if __name__ == "__main__":
    asyncio.run(main())