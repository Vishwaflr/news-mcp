#\!/bin/bash
export DEBUG=true
export NEWS_MCP_SERVER_URL=http://localhost:8001

{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' 
    sleep 1
    echo '{"method":"notifications/initialized","jsonrpc":"2.0"}' 
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' 
    sleep 1
} | node mcp-http-bridge.js 2>&1
