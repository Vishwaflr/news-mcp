#!/usr/bin/env python3
"""
Pre-commit hook to check for unsafe migration operations.
Run this before committing Alembic migrations.
"""

import sys
import re
from pathlib import Path

# Tables that should never be dropped
PROTECTED_TABLES = {
    'item_analysis',
    'analysis_runs',
    'analysis_run_items',
    'analysis_presets',
    'content_processing_logs',
}

# Columns that are critical and shouldn't be dropped
PROTECTED_COLUMNS = {
    'items.created_at',
    'feeds.created_at',
    'feeds.updated_at',
}

def check_migration_file(filepath: Path) -> list[str]:
    """Check a migration file for dangerous operations."""
    issues = []

    with open(filepath, 'r') as f:
        content = f.read()

    # Check for DROP TABLE
    drop_tables = re.findall(r"DROP TABLE\s+(?:IF EXISTS\s+)?['\"]?(\w+)['\"]?", content, re.IGNORECASE)
    for table in drop_tables:
        if table.lower() in PROTECTED_TABLES:
            issues.append(f"❌ CRITICAL: Dropping protected table '{table}'")
        elif table.lower() != 'basetablemodel':  # basetablemodel is OK to drop
            issues.append(f"⚠️  WARNING: Dropping table '{table}' - ensure this is intentional")

    # Check for DROP COLUMN
    drop_columns = re.findall(r"DROP COLUMN\s+['\"]?(\w+)['\"]?", content, re.IGNORECASE)
    for column in drop_columns:
        issues.append(f"⚠️  WARNING: Dropping column '{column}' - ensure data migration is handled")

    # Check for op.drop_table
    op_drops = re.findall(r"op\.drop_table\(['\"](\w+)['\"]", content)
    for table in op_drops:
        if table.lower() in PROTECTED_TABLES:
            issues.append(f"❌ CRITICAL: op.drop_table on protected table '{table}'")

    return issues


def main():
    """Check all migration files in alembic/versions."""
    versions_dir = Path('alembic/versions')

    if not versions_dir.exists():
        print("No alembic/versions directory found")
        return 0

    all_issues = []

    for migration_file in versions_dir.glob('*.py'):
        if migration_file.name == '__pycache__':
            continue

        issues = check_migration_file(migration_file)
        if issues:
            print(f"\n📄 {migration_file.name}:")
            for issue in issues:
                print(f"  {issue}")
            all_issues.extend(issues)

    if any('CRITICAL' in issue for issue in all_issues):
        print("\n🛑 Critical issues found! Migration blocked.")
        return 1
    elif all_issues:
        print("\n⚠️  Warnings found. Review carefully before proceeding.")
        return 0
    else:
        print("✅ All migrations look safe!")
        return 0


if __name__ == '__main__':
    sys.exit(main())