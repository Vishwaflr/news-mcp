@echo off
echo Setting up News MCP Direct Client for Windows...

REM Create direct client directory
mkdir %USERPROFILE%\news-mcp-direct 2>nul
cd %USERPROFILE%\news-mcp-direct

echo.
echo Copying direct client files...

REM Copy files (diese müssen manuell kopiert werden)
echo Please copy the following files to %USERPROFILE%\news-mcp-direct\:
echo - direct-http-mcp-client.js
echo - direct-client-package.json (rename to package.json)
echo - test-direct-client.js
echo.
echo Press any key when files are copied...
pause

REM Rename package.json
if exist direct-client-package.json (
    copy direct-client-package.json package.json
    del direct-client-package.json
)

echo.
echo Installing Node.js dependencies...
npm install

echo.
echo Testing connection to server...
set NEWS_MCP_SERVER_URL=http://192.168.178.72:3001
set DEBUG=true
node test-direct-client.js

echo.
echo Setup complete!
echo.
echo To use with Claude Desktop, add this to your claude_desktop_config.json:
echo.
echo {
echo   "mcpServers": {
echo     "news-mcp": {
echo       "command": "node",
echo       "args": ["%USERPROFILE%\\\\news-mcp-direct\\\\direct-http-mcp-client.js"],
echo       "env": {
echo         "NEWS_MCP_SERVER_URL": "http://192.168.178.72:3001"
echo       }
echo     }
echo   }
echo }
echo.
pause