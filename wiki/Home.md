# Welcome to News MCP Wiki

**Enterprise RSS MCP Server** - AI-powered news aggregation with 48 native tools for Claude Desktop.

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)](https://github.com/CytrexSGR/news-mcp/releases)
[![MCP](https://img.shields.io/badge/MCP-48_Tools-orange.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

---

## 🚀 Quick Links

| Topic | Description | Link |
|-------|-------------|------|
| ⚡ **Quick Start** | Get running in 5 minutes | [Quick Start Guide](Quick-Start) |
| 📊 **Dashboards** | 11 web dashboards overview | [Dashboard Overview](Dashboard-Overview) |
| 🔌 **MCP Setup** | Connect to Claude Desktop | [MCP Integration](MCP-Integration) |
| 📡 **API Reference** | Complete REST API docs | [API Overview](API-Overview) |
| 🏗️ **Architecture** | System design & patterns | [Architecture](Architecture) |
| 🔧 **Troubleshooting** | Common issues & solutions | [Troubleshooting](Troubleshooting) |

---

## 📖 What is News MCP?

News MCP is a **Model Context Protocol (MCP) server** for intelligent RSS feed aggregation with AI-powered analysis. It provides:

- **48 MCP Tools** - Control feeds, search articles, run analysis directly from Claude Desktop
- **Auto-Analysis System** - Automatic AI sentiment analysis of new feed items
- **11 Web Dashboards** - Comprehensive monitoring and management interfaces
- **172+ REST API Endpoints** - Complete programmatic access
- **Enterprise-Ready** - Production-proven with 37+ active feeds, 11,000+ articles

---

## 🎯 Key Features

### 🔌 MCP Integration (Model Context Protocol)
- **48 Native Tools** for Claude Desktop integration
- Feed management (list, add, update, delete, test, refresh)
- Analytics (dashboard stats, trending topics, article search)
- Database access (safe read-only SQL queries)
- Health monitoring (diagnostics, error analysis, scheduler status)
- **[Learn more →](MCP-Integration)**

### 📊 Web Dashboards
- **Main Dashboard** - System overview
- **Analysis Cockpit v4** - Manual analysis interface with Alpine.js
- **Auto-Analysis Dashboard** - Monitor automatic analysis
- **Manager Control Center** - Emergency controls & system management
- **Feed Management** - RSS feed CRUD operations
- **[View all dashboards →](Dashboard-Overview)**

### 🤖 Auto-Analysis System
- Automatic AI analysis of new feed items (Phase 2 ✅)
- Configurable per-feed activation
- Queue management with rate limiting
- OpenAI GPT integration for sentiment analysis
- **[Setup guide →](Auto-Analysis-Dashboard)**

### 📡 REST API
- 172+ endpoints across 15 categories
- Feed Management, Items, Analysis, Templates
- Statistics, Metrics, Health Monitoring
- HTMX components for progressive enhancement
- WebSocket support for real-time updates
- **[API documentation →](API-Overview)**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Web Server (Port 8000) + MCP Server (8001)    │
├─────────────────────────────────────────────────────────┤
│  📡 172 API Endpoints | 🌐 11 Web Dashboards           │
│  🔌 48 MCP Tools      | 📊 Real-time WebSocket         │
├─────────────────────────────────────────────────────────┤
│  ⚙️  Background Workers                                  │
│  • Analysis Worker    • Feed Scheduler                 │
│  • Auto-Analysis      • Queue Processor                │
├─────────────────────────────────────────────────────────┤
│  🗄️  PostgreSQL Database (30 Tables, 11,000+ Items)    │
└─────────────────────────────────────────────────────────┘
```

**[Detailed architecture →](Architecture)**

---

## 📚 Documentation Sections

### 🚀 Getting Started
- **[Quick Start](Quick-Start)** - 5-minute setup guide
- **[Installation](Installation)** - Detailed installation steps
- **[Configuration](Configuration)** - Environment variables & settings
- **[First Steps](First-Steps)** - Initial configuration walkthrough

### 📊 Dashboards & Web UI
- **[Dashboard Overview](Dashboard-Overview)** - All 11 dashboards explained
- **[Analysis Cockpit v4](Analysis-Cockpit)** - Manual analysis interface
- **[Auto-Analysis Dashboard](Auto-Analysis-Dashboard)** - Automatic analysis monitoring
- **[Manager Control Center](Manager-Control-Center)** - System controls

### 🔌 MCP Integration
- **[Claude Desktop Setup](Claude-Desktop-Setup)** - Step-by-step MCP configuration
- **[MCP Tools Reference](MCP-Tools-Reference)** - All 48 tools documented
- **[Remote/LAN Access](MCP-Remote-Access)** - Connect from remote machines
- **[MCP Examples](MCP-Examples)** - Real-world usage examples

### 📡 API Guide
- **[REST API Overview](API-Overview)** - API architecture & conventions
- **[Feed Management API](API-Feed-Management)** - Feed CRUD operations
- **[Analysis API](API-Analysis)** - Analysis runs & results
- **[Auto-Analysis API](API-Auto-Analysis)** - Automatic analysis endpoints
- **[WebSocket API](API-WebSocket)** - Real-time updates

### 🎯 Features & Tutorials
- **[Auto-Analysis System](Feature-Auto-Analysis)** - Complete guide
- **[Dynamic Templates](Feature-Templates)** - Feed template system
- **[Sentiment Analysis](Feature-Sentiment-Analysis)** - AI analysis details
- **[Feed Health Monitoring](Feature-Feed-Health)** - Health checks & diagnostics
- **[Real-time Updates](Feature-WebSocket)** - WebSocket integration

### 🏗️ Architecture & Development
- **[System Architecture](Architecture)** - High-level design
- **[Database Schema](Database-Schema)** - 30 tables documented
- **[Repository Pattern](Repository-Pattern)** - Data access layer
- **[Worker System](Worker-System)** - Background processing
- **[Feature Flags](Feature-Flags)** - Gradual rollout system

### 🚀 Deployment
- **[Production Setup](Deployment-Production)** - Production checklist
- **[Docker Deployment](Deployment-Docker)** - Container setup
- **[Systemd Services](Deployment-Systemd)** - Service management
- **[Monitoring & Logs](Deployment-Monitoring)** - Observability

### 🔧 Troubleshooting
- **[Common Issues](Troubleshooting-Common)** - FAQ & solutions
- **[Dashboard Problems](Troubleshooting-Dashboard)** - UI issues
- **[Database Problems](Troubleshooting-Database)** - DB errors
- **[MCP Connection Issues](Troubleshooting-MCP)** - MCP debugging
- **[Performance Tuning](Troubleshooting-Performance)** - Optimization

### 📚 Reference
- **[Environment Variables](Reference-Environment)** - All .env settings
- **[Configuration Files](Reference-Config)** - Config file reference
- **[Database Tables](Reference-Database)** - Schema reference
- **[Dashboard URLs](Reference-URLs)** - Quick URL reference
- **[CLI Commands](Reference-CLI)** - Command-line tools

---

## 📊 Current System Status

**Version:** 4.0.0
**Status:** ✅ Production Ready

### Metrics
- **Feeds:** 37 active
- **Articles:** 11,000+ items
- **Analysis Runs:** 75+ completed
- **Auto-Analysis:** 9 feeds (100% rollout)
- **MCP Tools:** 48 available
- **API Endpoints:** 172+
- **Dashboards:** 11 web interfaces

---

## 🤝 Contributing

This wiki is maintained by the News MCP community. To contribute:

1. Report issues: [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
2. Suggest improvements: [GitHub Discussions](https://github.com/CytrexSGR/news-mcp/discussions)
3. Read contributing guide: [CONTRIBUTING.md](https://github.com/CytrexSGR/news-mcp/blob/main/CONTRIBUTING.md)

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/CytrexSGR/news-mcp/issues)
- **Discussions:** [GitHub Discussions](https://github.com/CytrexSGR/news-mcp/discussions)
- **Wiki:** You are here! 📖

---

**Last Updated:** 2025-10-01
**Wiki Version:** 1.0.0
**Project Version:** 4.0.0
