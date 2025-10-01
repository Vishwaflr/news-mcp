# MCP Examples - Real-World Usage

Real-world examples of using News MCP with Claude Desktop.

---

## 📰 Feed Management Examples

### Example 1: List All Feeds
> "Show me all my active RSS feeds"

Claude will use `feeds.list` tool to display:
- Feed titles
- Feed URLs
- Last fetch times
- Item counts

---

### Example 2: Add New Feed
> "Add the BBC News RSS feed to my system"

Claude will:
1. Search for BBC News RSS URL
2. Use `feeds.add` tool to create feed
3. Confirm addition with feed ID

---

### Example 3: Check Feed Health
> "Are any of my feeds having problems?"

Claude uses `health.check_feeds` to show:
- Feeds with errors
- Success rates
- Consecutive failures

---

## 🔍 Article Search Examples

### Example 4: Search Recent Articles
> "Find articles about climate change from the last 3 days"

Claude will use `articles.search` with parameters:
- Query: "climate change"
- Days: 3
- Sort: recent first

---

### Example 5: Get Trending Topics
> "What topics are trending in my news feeds?"

Claude uses `analytics.trending_topics` to show:
- Most common topics
- Topic frequencies
- Time ranges

---

## 🤖 Analysis Examples

### Example 6: Run Analysis
> "Analyze the sentiment of the latest 50 tech articles"

Claude will:
1. Use `articles.search` to find tech articles
2. Use `analysis.start_run` to create analysis job
3. Monitor progress with `analysis.get_run_status`
4. Show results when complete

---

### Example 7: Check Analysis Results
> "Show me the most positive articles from yesterday"

Claude uses `articles.analyzed` with filters:
- Sentiment: positive
- Date range: yesterday
- Sort: sentiment score (high to low)

---

## 📊 Statistics Examples

### Example 8: Dashboard Stats
> "Give me an overview of my news system"

Claude uses `analytics.dashboard_stats` to show:
- Total feeds
- Total articles
- Analyzed articles
- Active analysis runs

---

### Example 9: Feed Statistics
> "Which feed has the most articles?"

Claude uses `analytics.feed_stats` to display:
- Article counts per feed
- Average articles per day
- Fetch success rates

---

## 🔧 Database Examples

### Example 10: Custom Query
> "Show me articles published in the last hour"

Claude uses `database.execute_query` with SQL:
```sql
SELECT title, published, feed_id
FROM items
WHERE published > NOW() - INTERVAL '1 hour'
ORDER BY published DESC;
```

---

## 🔗 Related Documentation

- **[MCP Tools Reference](MCP-Tools-Reference)** - Complete tool list
- **[MCP Integration](MCP-Integration)** - Setup guide
- **[Claude Desktop Setup](Claude-Desktop-Setup)** - Configuration

---

**Last Updated:** 2025-10-01
