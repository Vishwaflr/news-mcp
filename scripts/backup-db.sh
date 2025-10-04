#!/bin/bash
# Database Backup Script for News MCP
# Usage: ./backup-db.sh [backup_dir]

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default backup directory
BACKUP_DIR="${1:-/home/cytrex/news-mcp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="news_db_backup_${TIMESTAMP}.dump"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Database credentials
export PGPASSWORD='Aug2012#'
DB_HOST="localhost"
DB_USER="cytrex"
DB_NAME="news_db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}     News MCP Database Backup${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Get database size before backup
DB_SIZE=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" | xargs)
echo -e "${YELLOW}Database size: $DB_SIZE${NC}"

# Get table counts
FEED_COUNT=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM feeds;" | xargs)
ITEM_COUNT=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM items;" | xargs)
ANALYSIS_COUNT=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM item_analysis;" | xargs)

echo -e "${YELLOW}Contents:${NC}"
echo "  - Feeds: $FEED_COUNT"
echo "  - Items: $ITEM_COUNT"
echo "  - Analyses: $ANALYSIS_COUNT"
echo ""

echo -e "${BLUE}Creating backup...${NC}"
echo "Backup file: $BACKUP_PATH"

# Create compressed backup
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_PATH"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully!${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo "  Location: $BACKUP_DIR"

    # Create latest symlink
    ln -sf "$BACKUP_FILE" "${BACKUP_DIR}/latest.dump"
    echo -e "${GREEN}✓ Symlink created: latest.dump → $BACKUP_FILE${NC}"

    # Cleanup old backups (keep last 7 days)
    echo ""
    echo -e "${BLUE}Cleaning up old backups (keeping last 7)...${NC}"
    cd "$BACKUP_DIR"
    ls -t news_db_backup_*.dump | tail -n +8 | xargs -r rm -v

    # Show remaining backups
    echo ""
    echo -e "${YELLOW}Available backups:${NC}"
    ls -lh "$BACKUP_DIR"/news_db_backup_*.dump 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Backup complete!${NC}"
echo ""
echo -e "${YELLOW}To restore this backup:${NC}"
echo "export PGPASSWORD='Aug2012#'"
echo "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -c $BACKUP_PATH"
