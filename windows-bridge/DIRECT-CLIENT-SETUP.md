# News MCP Direct Client Setup für Claude Desktop (Windows)

## 📋 Einfache Architektur (EMPFOHLEN)

```
Windows Claude Desktop
    ↓ (MCP Protokoll via stdio)
Direct HTTP MCP Client (Node.js)
    ↓ (HTTP Requests)
Linux Server HTTP API (192.168.178.72:3001) ✅ Läuft
    ↓
News-MCP Tools
```

## 🎯 Schritt-für-Schritt Setup

### 1. Linux Server starten

```bash
# Auf Linux Server (192.168.178.72)
cd /home/cytrex/news-mcp
source venv/bin/activate
python3 mcp_http_server.py
```

### 2. Windows Direct Client Setup

**Verzeichnis erstellen:**
```cmd
mkdir %USERPROFILE%\news-mcp-direct
cd %USERPROFILE%\news-mcp-direct
```

**Dateien kopieren:**
Von Linux Server kopieren:
- `direct-http-mcp-client.js`
- `bridge-package.json` → umbenennen zu `package.json`
- `test-direct-client.js`

**Dependencies installieren:**
```cmd
npm install
```

### 3. Verbindung testen

```cmd
set NEWS_MCP_SERVER_URL=http://192.168.178.72:3001
node test-direct-client.js
```

**Erwartete Ausgabe:**
```
🧪 Testing Direct HTTP MCP Client...
📡 Server URL: http://192.168.178.72:3001
📤 Sending initialize request...
📤 Sending tools/list request...
📤 Sending get_dashboard tool call...

📊 Test Results:
📥 Received 3 responses
✅ Response 1: OK
✅ Response 2: OK
   📋 Found 25 tools
✅ Response 3: OK
🎉 All tests passed! Direct client is working correctly.
```

### 4. Claude Desktop konfigurieren

**Datei:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "news-mcp": {
      "command": "node",
      "args": ["%USERPROFILE%\\news-mcp-direct\\direct-http-mcp-client.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://192.168.178.72:3001",
        "DEBUG": "false"
      }
    }
  }
}
```

### 5. Claude Desktop neustarten

## 🔧 Verfügbare Tools

Nach erfolgreichem Setup stehen alle 25 News-MCP Tools zur Verfügung:

### Feed Management
- `list_feeds` - Alle Feeds auflisten
- `add_feed` - Neuen Feed hinzufügen
- `update_feed` - Feed-Konfiguration ändern
- `delete_feed` - Feed löschen
- `test_feed` - Feed-URL testen
- `refresh_feed` - Feed manuell aktualisieren

### Analytics & Statistics
- `get_dashboard` - Dashboard-Statistiken
- `feed_performance` - Feed-Performance analysieren
- `latest_articles` - Neueste Artikel
- `search_articles` - Artikel durchsuchen
- `trending_topics` - Trending-Themen
- `export_data` - Daten exportieren

### Template Management
- `list_templates` - Templates auflisten
- `template_performance` - Template-Performance
- `assign_template` - Template zuweisen

### Database Operations
- `execute_query` - Sichere SQL-Abfragen
- `table_info` - Tabellen-Informationen
- `quick_queries` - Vordefinierte Abfragen

### Health Monitoring
- `system_health` - System-Gesundheit
- `feed_diagnostics` - Feed-Diagnose
- `error_analysis` - Fehler-Analyse
- `scheduler_status` - Scheduler-Status

### Administration
- `maintenance_tasks` - Wartungsaufgaben
- `log_analysis` - Log-Analyse
- `usage_stats` - Nutzungsstatistiken

## 🧪 Beispiel-Nutzung in Claude Desktop

```
@news-mcp get_dashboard

@news-mcp list_feeds {"include_health": true}

@news-mcp latest_articles {"limit": 10, "since_hours": 24}

@news-mcp search_articles {"query": "technology", "limit": 5}

@news-mcp system_health
```

## 🐛 Troubleshooting

### Verbindungsprobleme
```cmd
# Test HTTP Server
curl http://192.168.178.72:3001/health

# Test Direct Client
node test-direct-client.js

# Debug Mode
set DEBUG=true
node direct-http-mcp-client.js
```

### Claude Desktop Logs
- Logs: `%APPDATA%\Claude\logs\`
- Config: `%APPDATA%\Claude\claude_desktop_config.json`

### Häufige Probleme

1. **Server nicht erreichbar:** Linux HTTP Server prüfen
2. **Node.js fehlt:** Node.js installieren (>= 14.0.0)
3. **Firewall blockiert:** Port 3001 freigeben
4. **Path-Probleme:** Absolute Pfade verwenden

## ✅ Status Check

- [ ] Linux HTTP Server läuft (Port 3001)
- [ ] Direct Client installiert
- [ ] Verbindungstest erfolgreich
- [ ] Claude Desktop konfiguriert
- [ ] Tools funktionieren

## 🆚 Unterschiede zur Bridge-Lösung

### Direct Client (EMPFOHLEN)
- ✅ Einfacher
- ✅ Weniger Fehlerquellen
- ✅ Direkte HTTP API Nutzung
- ✅ Bessere Performance

### Bridge-Lösung
- ⚠️ Double-Bridging
- ⚠️ Komplexer
- ⚠️ Mehr Fehlerquellen
- ⚠️ Overhead

## 📡 Netzwerk-Anforderungen

- **Port:** 3001 (HTTP)
- **Protocol:** HTTP/1.1
- **Server IP:** 192.168.178.72
- **LAN:** Beide Systeme im gleichen Netzwerk