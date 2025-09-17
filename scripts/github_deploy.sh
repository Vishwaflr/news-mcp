#!/bin/bash
# GitHub Deployment Script for News MCP
# This script will create the repository and upload all files

set -e

# Configuration
REPO_NAME="news-mcp"
REPO_DESCRIPTION="🔥 Dynamic RSS Management & Content Processing System with Hot-Reload Templates"
GITHUB_USERNAME="${GITHUB_USERNAME:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

echo "🚀 News MCP GitHub Deployment Script"
echo "====================================="

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "📦 Installing GitHub CLI..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update
        sudo apt install -y gh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install gh
    else
        echo "❌ Please install GitHub CLI manually: https://cli.github.com/"
        exit 1
    fi
fi

# Authenticate with GitHub
echo "🔐 Authenticating with GitHub..."
if [ -n "$GITHUB_TOKEN" ]; then
    echo "$GITHUB_TOKEN" | gh auth login --with-token
else
    echo "Please authenticate with GitHub:"
    gh auth login
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub authentication failed"
    exit 1
fi

echo "✅ Successfully authenticated with GitHub"

# Get GitHub username
if [ -z "$GITHUB_USERNAME" ]; then
    GITHUB_USERNAME=$(gh api user --jq .login)
fi

echo "👤 GitHub Username: $GITHUB_USERNAME"

# Check if repository already exists
if gh repo view "$GITHUB_USERNAME/$REPO_NAME" &> /dev/null; then
    echo "⚠️  Repository $GITHUB_USERNAME/$REPO_NAME already exists"
    read -p "Do you want to continue and push to existing repo? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
else
    # Create repository
    echo "📦 Creating GitHub repository..."
    gh repo create "$REPO_NAME" \
        --public \
        --description "$REPO_DESCRIPTION" \
        --homepage "https://$GITHUB_USERNAME.github.io/$REPO_NAME"

    echo "✅ Repository created: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
fi

# Add remote if not exists
if ! git remote get-url origin &> /dev/null; then
    echo "🔗 Adding GitHub remote..."
    git remote add origin "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
else
    echo "🔗 Updating GitHub remote..."
    git remote set-url origin "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
fi

# Push main branch
echo "⬆️  Pushing main branch..."
git push -u origin main

# Push tags
echo "🏷️  Pushing tags..."
git push origin --tags

# Configure repository settings
echo "⚙️  Configuring repository settings..."
gh repo edit "$GITHUB_USERNAME/$REPO_NAME" \
    --enable-issues=true \
    --enable-wiki=true \
    --enable-discussions=true \
    --default-branch=main

# Create initial release
echo "🎉 Creating release v2.0.0..."
gh release create "v2.0.0" \
    --title "🔥 News MCP v2.0.0 - Dynamic Template Management System" \
    --notes "$(cat <<'EOF'
## 🚀 Major Release: Dynamic Template Management System

### New Features
✅ Database-driven Dynamic Template System
✅ Hot-Reload Configuration Management
✅ Web UI Template Management Interface
✅ Automated Template Assignment
✅ Built-in Templates (Heise, Cointelegraph, WSJ)
✅ Configuration Change Tracking & Audit
✅ Microservices Architecture (Web UI + Scheduler)

### Architecture
- FastAPI web application with SQLModel ORM
- Separate dynamic scheduler service
- Real-time configuration updates without downtime
- HTMX-powered template management UI
- Production-ready deployment documentation

### Documentation
- Complete README with quick start guide
- Comprehensive deployment documentation
- Detailed changelog and contribution guidelines
- Docker & cloud deployment configurations

**Full changelog**: [CHANGELOG.md](https://github.com/$GITHUB_USERNAME/$REPO_NAME/blob/main/CHANGELOG.md)
**Documentation**: [README.md](https://github.com/$GITHUB_USERNAME/$REPO_NAME/blob/main/README.md)
**Deployment**: [DEPLOYMENT.md](https://github.com/$GITHUB_USERNAME/$REPO_NAME/blob/main/DEPLOYMENT.md)
EOF
    )"

# Add topics/tags
echo "🏷️  Adding repository topics..."
gh repo edit "$GITHUB_USERNAME/$REPO_NAME" \
    --add-topic "rss" \
    --add-topic "news" \
    --add-topic "mcp" \
    --add-topic "fastapi" \
    --add-topic "template-management" \
    --add-topic "hot-reload" \
    --add-topic "microservices" \
    --add-topic "python" \
    --add-topic "htmx" \
    --add-topic "dynamic-configuration"

# Final success message
echo ""
echo "🎉 SUCCESS! News MCP has been deployed to GitHub!"
echo "🔗 Repository: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo "🎯 Release: https://github.com/$GITHUB_USERNAME/$REPO_NAME/releases/tag/v2.0.0"
echo "📖 Documentation: https://github.com/$GITHUB_USERNAME/$REPO_NAME/blob/main/README.md"
echo ""
echo "Next steps:"
echo "1. 🌟 Star the repository"
echo "2. 📢 Share with the community"
echo "3. 🐛 Report issues or contribute"
echo "4. 🚀 Deploy to production using DEPLOYMENT.md"

# Open in browser (optional)
read -p "🌐 Open repository in browser? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    gh repo view --web
fi