#!/usr/bin/env node
/**
 * Direct HTTP-to-MCP Client for News-MCP
 * Connects Claude Desktop directly to HTTP API without double-bridging
 */

const http = require('http');
const { URL } = require('url');

const SERVER_URL = process.env.NEWS_MCP_SERVER_URL || 'http://192.168.178.72:3001';
const DEBUG = process.env.DEBUG === 'true';

function log(message, level = 'INFO') {
    if (DEBUG) {
        console.error(`[${new Date().toISOString()}] [${level}] ${message}`);
    }
}

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
                'User-Agent': 'Claude-Desktop-MCP-Client/1.0.0'
            },
            timeout: 10000
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
                    resolve({ error: 'Invalid JSON response', raw: responseData, status: res.statusCode });
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        if (data) {
            req.write(JSON.stringify(data));
        }
        req.end();
    });
}

class DirectHttpMcpClient {
    constructor() {
        this.serverUrl = SERVER_URL;
        this.tools = [];
        log(`Direct HTTP MCP Client connecting to ${this.serverUrl}`);
    }

    async initialize() {
        try {
            // Test connection and load tools
            const health = await makeHttpRequest('GET', '/health');
            if (health.status !== 'healthy') {
                throw new Error('Server not healthy');
            }

            const toolsResponse = await makeHttpRequest('GET', '/tools');
            if (toolsResponse.tools) {
                this.tools = toolsResponse.tools;
                log(`Loaded ${this.tools.length} tools from HTTP server`);
            } else {
                throw new Error('Failed to load tools from server');
            }
        } catch (error) {
            log(`Failed to initialize: ${error.message}`, 'ERROR');
            throw error;
        }
    }

    async handleRequest(request) {
        log(`Handling MCP request: ${request.method}`);

        switch (request.method) {
            case 'initialize':
                return {
                    protocolVersion: '2025-06-18',
                    capabilities: {
                        tools: {}
                    },
                    serverInfo: {
                        name: 'news-mcp-direct',
                        version: '1.0.0'
                    }
                };

            case 'tools/list':
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

            case 'resources/list':
                return {
                    resources: []
                };

            case 'prompts/list':
                return {
                    prompts: []
                };

            case 'notifications/initialized':
                // Notification - no response needed
                return null;

            case 'tools/call':
                const toolName = request.params.name;
                const args = request.params.arguments || {};

                try {
                    log(`Calling HTTP API: ${toolName} with args ${JSON.stringify(args)}`);

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

                    // Format response content
                    let content;
                    if (response.result && typeof response.result === 'object') {
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
                    log(`HTTP request failed: ${error.message}`, 'ERROR');
                    return {
                        isError: true,
                        content: [
                            {
                                type: 'text',
                                text: `HTTP request failed: ${error.message}`
                            }
                        ]
                    };
                }

            default:
                throw new Error(`Unknown MCP method: ${request.method}`);
        }
    }
}

async function main() {
    const client = new DirectHttpMcpClient();

    try {
        await client.initialize();
        log('Direct HTTP MCP Client initialized successfully');
    } catch (error) {
        log(`Client initialization failed: ${error.message}`, 'ERROR');
        process.exit(1);
    }

    let buffer = '';

    process.stdin.on('data', async (chunk) => {
        buffer += chunk.toString();

        let lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
            if (line.trim()) {
                let request = null;
                try {
                    request = JSON.parse(line);
                    log(`Received MCP request: ${request.method}`);

                    const response = await client.handleRequest(request);

                    // Only send response for requests with ID (not notifications)
                    if (request.id !== undefined && response !== null) {
                        const responseMessage = {
                            jsonrpc: '2.0',
                            id: request.id,
                            result: response
                        };

                        process.stdout.write(JSON.stringify(responseMessage) + '\n');
                        log(`Sent response for: ${request.method}`);
                    } else if (response === null) {
                        log(`Processed notification: ${request.method}`);
                    }
                } catch (error) {
                    log(`Error processing request: ${error.message}`, 'ERROR');

                    const errorResponse = {
                        jsonrpc: '2.0',
                        id: request?.id || 0,
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

    log('Direct HTTP MCP Client ready for Claude Desktop');
}

if (require.main === module) {
    main().catch(error => {
        log(`Fatal error: ${error.message}`, 'ERROR');
        process.exit(1);
    });
}