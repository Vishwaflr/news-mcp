# Database Backup Strategy

## Overview
Automated PostgreSQL database backups for News MCP system.

## Backup Script

**Location:** `/home/cytrex/news-mcp/scripts/backup-db.sh`

**Features:**
- ✅ Compressed PostgreSQL dump format (.dump)
- ✅ Automatic old backup cleanup (keeps last 7 backups)
- ✅ Database statistics before backup (size, counts)
- ✅ Latest symlink for easy access
- ✅ Color-coded output

**Manual Usage:**
```bash
cd /home/cytrex/news-mcp
./scripts/backup-db.sh [backup_dir]
```

**Default backup location:** `/home/cytrex/news-mcp/backups/`

## Automated Backups (Cron)

### Daily Backups (3 AM)
Add to crontab:
```bash
# Open crontab editor
crontab -e

# Add this line for daily backups at 3 AM
0 3 * * * cd /home/cytrex/news-mcp && ./scripts/backup-db.sh >> logs/backup.log 2>&1
```

### Hourly Backups (during business hours)
```bash
# Every hour from 8 AM to 8 PM
0 8-20 * * * cd /home/cytrex/news-mcp && ./scripts/backup-db.sh >> logs/backup.log 2>&1
```

### Weekly Full Backups
```bash
# Every Sunday at 2 AM
0 2 * * 0 cd /home/cytrex/news-mcp && ./scripts/backup-db.sh /home/cytrex/backups/weekly >> logs/backup-weekly.log 2>&1
```

## Restore Procedures

### Quick Restore (from latest backup)
```bash
export PGPASSWORD='Aug2012#'
pg_restore -h localhost -U cytrex -d news_db -c /home/cytrex/news-mcp/backups/latest.dump
```

### Restore Specific Backup
```bash
# List available backups
ls -lh /home/cytrex/news-mcp/backups/

# Restore specific backup
export PGPASSWORD='Aug2012#'
pg_restore -h localhost -U cytrex -d news_db -c /home/cytrex/news-mcp/backups/news_db_backup_YYYYMMDD_HHMMSS.dump
```

### Restore to New Database
```bash
export PGPASSWORD='Aug2012#'

# Create new database
psql -h localhost -U cytrex -d postgres -c "CREATE DATABASE news_db_restored;"

# Restore backup
pg_restore -h localhost -U cytrex -d news_db_restored /home/cytrex/news-mcp/backups/latest.dump
```

## Backup Verification

### Check Backup Integrity
```bash
# List contents of backup file
pg_restore -l /home/cytrex/news-mcp/backups/latest.dump | head -20
```

### Test Restore (without applying)
```bash
# Dry run (only check for errors)
pg_restore -l /home/cytrex/news-mcp/backups/latest.dump > /dev/null
```

## Backup Retention Policy

**Current Policy:** Keep last 7 backups
- Automatically deletes backups older than 7th most recent
- Configurable in `/home/cytrex/news-mcp/scripts/backup-db.sh` (line with `tail -n +8`)

**To change retention (e.g., keep 14 backups):**
```bash
# Edit backup script
nano /home/cytrex/news-mcp/scripts/backup-db.sh

# Change this line:
ls -t news_db_backup_*.dump | tail -n +8 | xargs -r rm -v

# To this:
ls -t news_db_backup_*.dump | tail -n +15 | xargs -r rm -v
```

## Monitoring Backups

### Check Last Backup
```bash
ls -lh /home/cytrex/news-mcp/backups/latest.dump
```

### View Backup Log
```bash
tail -f logs/backup.log
```

### Check Backup Success (from cron logs)
```bash
grep -i "backup complete" logs/backup.log | tail -5
```

## Off-site Backups

### Manual Off-site Copy
```bash
# Copy to remote server via rsync
rsync -avz /home/cytrex/news-mcp/backups/ user@remote:/path/to/backups/

# Copy to cloud storage (example with rclone)
rclone copy /home/cytrex/news-mcp/backups/ remote:news-mcp-backups/
```

### Automated Off-site (via cron)
```bash
# Daily off-site backup at 4 AM
0 4 * * * rsync -avz /home/cytrex/news-mcp/backups/ user@remote:/backups/news-mcp/ >> logs/backup-offsite.log 2>&1
```

## Disaster Recovery

### Complete System Recovery Steps

1. **Install Docker & Dependencies**
   ```bash
   sudo apt-get update
   sudo apt-get install docker.io docker-compose postgresql-client
   ```

2. **Clone Repository**
   ```bash
   git clone <repo-url> /home/cytrex/news-mcp
   cd /home/cytrex/news-mcp
   ```

3. **Start Docker Services**
   ```bash
   ./scripts/docker-start.sh dev
   ```

4. **Wait for PostgreSQL to be Ready**
   ```bash
   docker exec news-mcp-postgres pg_isready
   ```

5. **Restore Latest Backup**
   ```bash
   export PGPASSWORD='Aug2012#'
   pg_restore -h localhost -U cytrex -d news_db -c /path/to/latest.dump
   ```

6. **Start Application Services**
   ```bash
   ./scripts/service-manager.sh start
   ```

7. **Verify Services**
   ```bash
   curl http://localhost:8000/health
   ./scripts/service-manager.sh status
   ```

## Backup Size Estimates

**Typical Sizes:**
- Empty database: ~140 KB
- 1 feed, 50 items: ~144 KB
- 45 feeds, 22k items: ~10-20 MB (estimated)
- 100 feeds, 100k items: ~50-100 MB (estimated)

**Retention Storage Needs:**
- 7 days @ 20 MB/backup = ~140 MB
- 30 days @ 20 MB/backup = ~600 MB
- 90 days @ 20 MB/backup = ~1.8 GB

## Security Notes

⚠️ **Backup files contain:**
- All database data (feeds, items, analysis)
- User settings and configurations
- No passwords (PostgreSQL stores hashed passwords)

✅ **Backup security:**
- Stored locally with filesystem permissions (600)
- Accessible only to cytrex user
- For production: encrypt backups before off-site storage

**Encryption for off-site:**
```bash
# Encrypt backup before upload
gpg --encrypt --recipient your@email.com /home/cytrex/news-mcp/backups/latest.dump

# Decrypt when needed
gpg --decrypt latest.dump.gpg > latest.dump
```

## Troubleshooting

### "database is being accessed by other users"
```bash
# Stop all services first
./scripts/service-manager.sh stop

# Then restore
pg_restore -h localhost -U cytrex -d news_db -c backup.dump
```

### "permission denied for schema public"
```bash
# Use cytrex (admin) user, not news_user
export PGPASSWORD='Aug2012#'
pg_restore -h localhost -U cytrex -d news_db -c backup.dump
```

### "relation already exists"
```bash
# Use -c flag to drop existing objects first
pg_restore -h localhost -U cytrex -d news_db -c backup.dump

# Or use --clean --if-exists for safer cleanup
pg_restore -h localhost -U cytrex -d news_db --clean --if-exists backup.dump
```

## Current Status

**First Backup:** October 4, 2025 08:52:25
- Database size: 9837 kB (~9.6 MB)
- Feeds: 1
- Items: 50
- Analyses: 2
- Backup size: 144 KB (compressed)

**Backup location:** `/home/cytrex/news-mcp/backups/`
**Latest symlink:** `/home/cytrex/news-mcp/backups/latest.dump`
