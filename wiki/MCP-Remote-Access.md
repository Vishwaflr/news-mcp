# MCP Remote Access - Connect from Remote Machines

Access your News MCP server from remote machines or LAN.

---

## 🌐 Remote Access Setup

### Server Configuration

Edit `.env` to allow remote connections:

```bash
# Bind to all interfaces
HOST=0.0.0.0
PORT=8000

# MCP Server
MCP_SERVER_PORT=8001
```

Start the MCP server:
```bash
./scripts/start_mcp_server.sh
```

### Firewall Configuration

```bash
# Ubuntu/Debian
sudo ufw allow 8001/tcp

# Check firewall status
sudo ufw status
```

---

## 🖥️ Client Configuration

On your local machine, configure Claude Desktop to connect to remote server:

```json
{
  "mcpServers": {
    "news-mcp-remote": {
      "command": "node",
      "args": ["/path/to/mcp-http-bridge.js"],
      "env": {
        "NEWS_MCP_SERVER_URL": "http://192.168.1.100:8001"
      }
    }
  }
}
```

Replace `192.168.1.100` with your server's IP address.

---

## 🔐 Security Considerations

**Current Setup:** No authentication (development only)

**Production Recommendations:**
- Use VPN or SSH tunnel for remote access
- Implement API key authentication
- Use HTTPS with SSL certificates
- Restrict access by IP address (firewall rules)

---

## 🔗 Related Documentation

- **[MCP Integration](MCP-Integration)** - MCP overview
- **[Claude Desktop Setup](Claude-Desktop-Setup)** - Local setup
- **[Deployment](Deployment-Production)** - Production security

---

**Last Updated:** 2025-10-01
