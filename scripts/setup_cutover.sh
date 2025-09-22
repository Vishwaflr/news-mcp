#!/bin/bash
# Setup script for safe repository cutover

set -e

echo "🚀 Setting up Repository Cutover Infrastructure"

# 1. Run index reality check
echo "📊 Running index reality check..."
cd /home/cytrex/news-mcp
source venv/bin/activate
export PYTHONPATH=/home/cytrex/news-mcp

python scripts/index_check.py

# 2. Setup feature flags in canary mode
echo "🎛️  Setting up feature flags..."

# Create feature flags configuration
cat > feature_flags.json << EOF
{
  "items_repo": {
    "status": "canary",
    "rollout_percentage": 5,
    "emergency_threshold": 0.05,
    "emergency_latency_multiplier": 1.3
  },
  "shadow_compare": {
    "status": "on",
    "rollout_percentage": 10
  }
}
EOF

export FEATURE_FLAGS_JSON=$(cat feature_flags.json)
rm feature_flags.json

echo "Feature flags configured:"
echo "- items_repo: 5% canary rollout"
echo "- shadow_compare: 10% sampling"

# 3. Test repository functionality
echo "🧪 Testing repository functionality..."

python -c "
import asyncio
import sys
sys.path.insert(0, '/home/cytrex/news-mcp')

from app.db.session import DatabaseSession
from app.repositories.items_repo import ItemsRepository
from app.schemas.items import ItemQuery
from app.config import DATABASE_URL

async def test_repo():
    db_session = DatabaseSession(DATABASE_URL)
    items_repo = ItemsRepository(db_session)

    # Test basic query
    items = await items_repo.query(ItemQuery(), limit=5)
    print(f'✅ Repository test: {len(items)} items retrieved')

    # Test count
    count = await items_repo.count()
    print(f'✅ Count test: {count} total items')

    # Test statistics
    stats = await items_repo.get_statistics()
    print(f'✅ Statistics test: {stats.total_count} total, {stats.today_count} today')

    return True

try:
    result = asyncio.run(test_repo())
    print('✅ All repository tests passed!')
except Exception as e:
    print(f'❌ Repository test failed: {e}')
    exit(1)
"

# 4. Setup monitoring endpoints
echo "📈 Setting up monitoring..."

# Create simple monitoring dashboard script
cat > monitoring_dashboard.py << 'EOF'
#!/usr/bin/env python3
import asyncio
import sys
import json
from datetime import datetime

sys.path.insert(0, '/home/cytrex/news-mcp')

from app.utils.feature_flags import feature_flags
from app.utils.shadow_compare import shadow_comparer
from app.utils.monitoring import metrics_collector

def print_dashboard():
    print("\n🎛️  REPOSITORY CUTOVER DASHBOARD")
    print("=" * 50)

    # Feature flags
    print("\n📊 Feature Flags:")
    for name, flag_data in feature_flags.get_all_flags().items():
        status = flag_data.get('status', 'unknown')
        percentage = flag_data.get('rollout_percentage', 0)
        error_count = flag_data.get('error_count', 0)
        success_count = flag_data.get('success_count', 0)

        print(f"  {name}: {status} ({percentage}% rollout)")
        if success_count > 0 or error_count > 0:
            total = success_count + error_count
            error_rate = error_count / total * 100 if total > 0 else 0
            print(f"    Success: {success_count}, Errors: {error_count} ({error_rate:.1f}% error rate)")

    # Shadow comparison
    print("\n🔍 Shadow Comparison:")
    stats = shadow_comparer.get_comparison_stats()
    if stats.get('total_comparisons', 0) > 0:
        print(f"  Total comparisons: {stats['total_comparisons']}")
        print(f"  Match rate: {stats['match_rate']:.1%}")
        print(f"  Mismatches: {stats['mismatch_count']}")
        print(f"  Errors: {stats['error_count']}")

        perf = stats.get('performance', {})
        old_avg = perf.get('old_avg_ms', 0)
        new_avg = perf.get('new_avg_ms', 0)
        if old_avg > 0 and new_avg > 0:
            improvement = (old_avg - new_avg) / old_avg * 100
            print(f"  Performance: {old_avg:.1f}ms → {new_avg:.1f}ms ({improvement:+.1f}%)")
    else:
        print("  No comparisons yet")

    # Performance metrics
    print("\n⏱️  Performance Summary:")
    perf_summary = metrics_collector.get_performance_summary()
    for operation, data in perf_summary.items():
        if data.get('total_requests', 0) > 0:
            avg_ms = data['duration_stats']['avg_ms']
            p95_ms = data['duration_stats']['p95_ms']
            success_rate = data['success_rate'] * 100
            print(f"  {operation}: {avg_ms:.1f}ms avg, {p95_ms:.1f}ms p95 ({success_rate:.1f}% success)")

if __name__ == "__main__":
    print_dashboard()
EOF

chmod +x monitoring_dashboard.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Run index check: python scripts/index_check.py"
echo "2. Monitor dashboard: python monitoring_dashboard.py"
echo "3. Check metrics: curl http://localhost:8000/api/admin/feature-flags/metrics/dashboard"
echo "4. Toggle flag: curl -X POST http://localhost:8000/api/admin/feature-flags/items_repo -d '{\"status\":\"canary\",\"rollout_percentage\":10}'"
echo ""
echo "🎯 Current status:"
echo "- Feature flags: Canary mode (5% rollout)"
echo "- Shadow comparison: Active (10% sampling)"
echo "- Repository: Ready for testing"
echo ""
echo "💡 To increase rollout: Change rollout_percentage via API"
echo "💡 Emergency disable: POST status=emergency_off"
echo "💡 Monitor logs for performance/error alerts"