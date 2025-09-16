#!/bin/bash

set -e

echo "Installing News MCP system..."

# Create user and group
if ! id "news-mcp" &>/dev/null; then
    sudo useradd --system --shell /bin/bash --home /opt/news-mcp news-mcp
    echo "Created news-mcp user"
fi

# Create directory and copy files
sudo mkdir -p /opt/news-mcp
sudo cp -r . /opt/news-mcp/
sudo chown -R news-mcp:news-mcp /opt/news-mcp

# Setup Python virtual environment
sudo -u news-mcp python3 -m venv /opt/news-mcp/venv
sudo -u news-mcp /opt/news-mcp/venv/bin/pip install -r /opt/news-mcp/requirements.txt

# Copy systemd service files
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable news-api.service
sudo systemctl enable news-fetcher.service
sudo systemctl enable news-mcp.service

# Create .env file if it doesn't exist
if [ ! -f /opt/news-mcp/.env ]; then
    sudo -u news-mcp cp /opt/news-mcp/.env.example /opt/news-mcp/.env
    echo "Created .env file from template"
fi

echo "Installation complete!"
echo ""
echo "To start the services:"
echo "  sudo systemctl start news-api"
echo "  sudo systemctl start news-fetcher"
echo "  sudo systemctl start news-mcp"
echo ""
echo "To check status:"
echo "  sudo systemctl status news-api"
echo "  sudo journalctl -u news-api -f"
echo ""
echo "Web interface: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"