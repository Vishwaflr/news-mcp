#!/bin/bash
#
# Pre-commit hook to check for raw analysis SQL outside AnalysisRepository
# This script enforces the repository pattern for analysis operations
#

set -e

echo "🔍 Checking for raw analysis SQL violations..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Exit code
EXIT_CODE=0

# Check for direct item_analysis table operations
echo "Checking for direct item_analysis SQL operations..."
DIRECT_SQL_VIOLATIONS=$(grep -r -n --include="*.py" \
  -E "(INSERT INTO item_analysis|UPDATE item_analysis|DELETE FROM item_analysis)" \
  app/worker app/api app/services 2>/dev/null || true)

if [ ! -z "$DIRECT_SQL_VIOLATIONS" ]; then
  echo -e "${RED}❌ Direct item_analysis SQL operations detected:${NC}"
  echo "$DIRECT_SQL_VIOLATIONS"
  echo -e "${YELLOW}Use AnalysisRepository instead of raw SQL.${NC}"
  echo ""
  EXIT_CODE=1
fi

# Check for session.exec with analysis tables
echo "Checking for session.exec with item_analysis..."
SESSION_VIOLATIONS=$(grep -r -n --include="*.py" \
  -E "session\.exec.*item_analysis" \
  app/worker app/api app/services 2>/dev/null || true)

if [ ! -z "$SESSION_VIOLATIONS" ]; then
  echo -e "${RED}❌ Direct session.exec with item_analysis detected:${NC}"
  echo "$SESSION_VIOLATIONS"
  echo -e "${YELLOW}Use AnalysisRepository methods instead.${NC}"
  echo ""
  EXIT_CODE=1
fi

# Check for raw SQL strings containing analysis operations
echo "Checking for raw SQL strings with analysis operations..."
RAW_SQL_VIOLATIONS=$(grep -r -n --include="*.py" \
  -E "(\".*INSERT INTO item_analysis|'.*INSERT INTO item_analysis)" \
  app/worker app/api app/services 2>/dev/null || true)

if [ ! -z "$RAW_SQL_VIOLATIONS" ]; then
  echo -e "${RED}❌ Raw SQL strings with item_analysis INSERT detected:${NC}"
  echo "$RAW_SQL_VIOLATIONS"
  echo -e "${YELLOW}Use AnalysisRepository.upsert_analysis() instead.${NC}"
  echo ""
  EXIT_CODE=1
fi

# Check for analysis_runs operations outside repositories
echo "Checking for raw analysis_runs SQL..."
RUN_VIOLATIONS=$(grep -r -n --include="*.py" \
  -E "(INSERT INTO analysis_runs|UPDATE analysis_runs)" \
  app/worker app/api app/services 2>/dev/null | \
  grep -v "app/repositories/" || true)

if [ ! -z "$RUN_VIOLATIONS" ]; then
  echo -e "${RED}❌ Direct analysis_runs SQL operations detected outside repositories:${NC}"
  echo "$RUN_VIOLATIONS"
  echo -e "${YELLOW}Use appropriate repository methods instead.${NC}"
  echo ""
  EXIT_CODE=1
fi

# Check for analysis_run_items operations
echo "Checking for raw analysis_run_items SQL..."
RUN_ITEMS_VIOLATIONS=$(grep -r -n --include="*.py" \
  -E "(INSERT INTO analysis_run_items|UPDATE analysis_run_items)" \
  app/worker app/api app/services 2>/dev/null | \
  grep -v "app/repositories/" || true)

if [ ! -z "$RUN_ITEMS_VIOLATIONS" ]; then
  echo -e "${RED}❌ Direct analysis_run_items SQL operations detected outside repositories:${NC}"
  echo "$RUN_ITEMS_VIOLATIONS"
  echo -e "${YELLOW}Use appropriate repository methods instead.${NC}"
  echo ""
  EXIT_CODE=1
fi

# Check that analysis-related files use repository patterns
echo "Checking analysis files use repository patterns..."
ANALYSIS_FILES=$(find app/worker app/api -name "*.py" -exec grep -l "analysis" {} \; 2>/dev/null | \
  grep -E "(analysis|worker)" || true)

for file in $ANALYSIS_FILES; do
  if [ -f "$file" ]; then
    # Check if file contains database operations but no repository import
    if grep -q -E "(session\.exec|INSERT|UPDATE|SELECT.*item_analysis)" "$file"; then
      if ! grep -q "from app\.repositories" "$file" && ! grep -q "AnalysisRepository" "$file"; then
        echo -e "${YELLOW}⚠️  File $file contains DB operations but no repository import${NC}"
        echo "    Consider using AnalysisRepository if working with analysis data"
      fi
    fi
  fi
done

# Check for proper feature flag integration in worker
if [ -f "app/worker/analysis_worker.py" ]; then
  echo "Checking worker feature flag integration..."
  if ! grep -q "feature_flags" "app/worker/analysis_worker.py"; then
    echo -e "${YELLOW}⚠️  Worker missing feature flag integration${NC}"
    echo "    Worker should check 'analysis_repo' feature flag for repository usage"
  fi
fi

# Summary
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✅ No raw analysis SQL violations found${NC}"
else
  echo -e "${RED}❌ Raw analysis SQL violations detected${NC}"
  echo ""
  echo "Repository Pattern Guidelines:"
  echo "  • Use AnalysisRepository.upsert_analysis() instead of INSERT/UPDATE"
  echo "  • Use AnalysisRepository.get_by_item_id() instead of SELECT queries"
  echo "  • Use AnalysisRepository.get_aggregations() for analysis statistics"
  echo "  • Import repositories with: from app.repositories.analysis_repo import AnalysisRepository"
  echo ""
fi

exit $EXIT_CODE