#!/usr/bin/env node
/**
 * MCP-HTTP Bridge for News-MCP Server
 * Bridges Claude Desktop (MCP) to Linux HTTP Server
 */

const http = require('http');
const { URL } = require('url');

// Configuration
const SERVER_URL = process.env.NEWS_MCP_SERVER_URL || 'http://192.168.178.72:3001';
const DEBUG = process.env.DEBUG === 'true';

// Logging helper
function log(message, level = 'INFO') {
    if (DEBUG || level === 'ERROR') {
        console.error(`[${new Date().toISOString()}] [${level}] ${message}`);
    }
}

// HTTP request helper
function makeHttpRequest(method, path, data = null) {
    return new Promise((resolve, reject) => {
        const url = new URL(path, SERVER_URL);
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'News-MCP-Bridge/1.0.0'
            }
        };

        if (data) {
            const postData = JSON.stringify(data);
            options.headers['Content-Length'] = Buffer.byteLength(postData);
        }

        const req = http.request(options, (res) => {
            let responseData = '';
            res.on('data', (chunk) => {
                responseData += chunk;
            });
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(responseData);
                    resolve(parsed);
                } catch (e) {
                    resolve({ error: 'Invalid JSON response', raw: responseData });
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        if (data) {
            req.write(JSON.stringify(data));
        }
        req.end();
    });
}

// MCP Server Implementation
class NewsMCPBridge {
    constructor() {
        this.tools = [];
        this.serverUrl = SERVER_URL;
        log(`Initializing News MCP Bridge connecting to ${this.serverUrl}`);
    }

    async initialize() {
        try {
            // Test connection and get available tools
            const response = await makeHttpRequest('GET', '/tools');
            if (response.tools) {
                this.tools = response.tools;
                log(`Loaded ${this.tools.length} tools from server`);
            } else {
                throw new Error('Failed to load tools from server');
            }
        } catch (error) {
            log(`Failed to connect to server: ${error.message}`, 'ERROR');
            throw error;
        }
    }

    async handleRequest(request) {
        log(`Handling request: ${request.method}`);

        switch (request.method) {
            case 'initialize':
                return {
                    protocolVersion: '2025-06-18',
                    capabilities: {
                        tools: {}
                    },
                    serverInfo: {
                        name: 'news-mcp-bridge',
                        version: '1.0.0'
                    }
                };

            case 'tools/list':
                // Return the actual News-MCP tools
                return {
                    tools: this.tools.map(tool => ({
                        name: tool.name,
                        description: tool.description,
                        inputSchema: {
                            type: 'object',
                            properties: {},
                            additionalProperties: true
                        }
                    }))
                };

            case 'tools/call':
                const toolName = request.params.name;
                const args = request.params.arguments || {};

                try {
                    const response = await makeHttpRequest('POST', '/call', {
                        method: toolName,
                        params: args
                    });

                    if (response.error) {
                        return {
                            isError: true,
                            content: [
                                {
                                    type: 'text',
                                    text: `Error: ${response.error}`
                                }
                            ]
                        };
                    }

                    // Format response as MCP text content
                    let content;
                    if (typeof response.result === 'object' && response.result !== null) {
                        content = JSON.stringify(response.result, null, 2);
                    } else if (response.result && response.result.text) {
                        content = response.result.text;
                    } else {
                        content = String(response.result || 'No result');
                    }

                    return {
                        content: [
                            {
                                type: 'text',
                                text: content
                            }
                        ]
                    };
                } catch (error) {
                    log(`Tool call error: ${error.message}`, 'ERROR');
                    return {
                        isError: true,
                        content: [
                            {
                                type: 'text',
                                text: `Error calling tool: ${error.message}`
                            }
                        ]
                    };
                }

            default:
                throw new Error(`Unknown method: ${request.method}`);
        }
    }
}

// Main execution
async function main() {
    const bridge = new NewsMCPBridge();

    try {
        await bridge.initialize();
        log('Bridge initialized successfully');
    } catch (error) {
        log(`Bridge initialization failed: ${error.message}`, 'ERROR');
        process.exit(1);
    }

    // Handle MCP communication via stdio
    let buffer = '';

    process.stdin.on('data', async (chunk) => {
        buffer += chunk.toString();

        // Process complete JSON messages
        let lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
            if (line.trim()) {
                try {
                    const request = JSON.parse(line);
                    log(`Received request: ${request.method}`);

                    const response = await bridge.handleRequest(request);
                    const responseMessage = {
                        jsonrpc: '2.0',
                        id: request.id,
                        result: response
                    };

                    process.stdout.write(JSON.stringify(responseMessage) + '\n');
                    log(`Sent response for: ${request.method}`);
                } catch (error) {
                    log(`Error processing request: ${error.message}`, 'ERROR');
                    const errorResponse = {
                        jsonrpc: '2.0',
                        id: request.id || null,
                        error: {
                            code: -32603,
                            message: error.message
                        }
                    };
                    process.stdout.write(JSON.stringify(errorResponse) + '\n');
                }
            }
        }
    });

    process.stdin.on('end', () => {
        log('Input stream ended');
        process.exit(0);
    });

    log('Bridge ready for MCP communication');
}

// Start the bridge
if (require.main === module) {
    main().catch(error => {
        log(`Fatal error: ${error.message}`, 'ERROR');
        process.exit(1);
    });
}