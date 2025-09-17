@echo off
echo Setting up News MCP Bridge for Windows...

REM Create bridge directory
mkdir %USERPROFILE%\news-mcp-bridge 2>nul
cd %USERPROFILE%\news-mcp-bridge

echo.
echo Copying bridge files...

REM Copy files (diese müssen manuell kopiert werden)
echo Please copy the following files to %USERPROFILE%\news-mcp-bridge\:
echo - mcp-news-bridge.js
echo - bridge-package.json (rename to package.json)
echo - test-bridge.js
echo.
echo Press any key when files are copied...
pause

REM Rename package.json
if exist bridge-package.json (
    copy bridge-package.json package.json
    del bridge-package.json
)

echo.
echo Installing Node.js dependencies...
npm install

echo.
echo Testing connection to server...
set NEWS_MCP_SERVER_URL=http://192.168.178.72:3001
set DEBUG=true
node mcp-news-bridge.js --test

echo.
echo Setup complete!
echo.
echo To use with Claude Desktop, add this to your claude_desktop_config.json:
echo.
echo {
echo   "mcpServers": {
echo     "news-mcp": {
echo       "command": "node",
echo       "args": ["%USERPROFILE%\\news-mcp-bridge\\mcp-news-bridge.js"],
echo       "env": {
echo         "NEWS_MCP_SERVER_URL": "http://192.168.178.72:3001"
echo       }
echo     }
echo   }
echo }
echo.
pause