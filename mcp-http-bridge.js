#!/usr/bin/env node
/**
 * MCP HTTP Bridge for News MCP Server
 * Bridges Claude Desktop (stdio MCP) to HTTP MCP Server (JSON-RPC)
 *
 * Usage: node mcp-http-bridge.js
 * Environment: NEWS_MCP_SERVER_URL (default: http://localhost:8001)
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

const SERVER_URL = process.env.NEWS_MCP_SERVER_URL || 'http://localhost:8001';
const DEBUG = process.env.DEBUG === 'true';

function log(message, level = 'INFO') {
    if (DEBUG) {
        console.error(`[${new Date().toISOString()}] [${level}] ${message}`);
    }
}

function makeHttpRequest(endpoint, body) {
    return new Promise((resolve, reject) => {
        const url = new URL(endpoint, SERVER_URL);
        const isHttps = url.protocol === 'https:';
        const httpModule = isHttps ? https : http;

        const options = {
            hostname: url.hostname,
            port: url.port || (isHttps ? 443 : 80),
            path: url.pathname + url.search,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body)
            },
            timeout: 30000
        };

        const req = httpModule.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        status: res.statusCode,
                        data: JSON.parse(data)
                    });
                } catch (e) {
                    reject(new Error(`JSON parse error: ${e.message}`));
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.write(body);
        req.end();
    });
}

class MCPHttpBridge {
    constructor() {
        this.serverInfo = null;
        this.tools = [];
    }

    async initialize(params) {
        log('Initializing MCP bridge...');

        try {
            const response = await makeHttpRequest('/mcp', JSON.stringify({
                jsonrpc: '2.0',
                id: 1,
                method: 'initialize',
                params: params || {}
            }));

            if (response.status !== 200) {
                throw new Error(`HTTP ${response.status}: ${JSON.stringify(response.data)}`);
            }

            if (response.data.error) {
                throw new Error(`MCP Error: ${response.data.error.message}`);
            }

            this.serverInfo = response.data.result.serverInfo;
            log(`Connected to ${this.serverInfo.name} v${this.serverInfo.version}`);

            await this.loadTools();

            return {
                protocolVersion: '2024-11-05',
                serverInfo: this.serverInfo,
                capabilities: {
                    tools: { listChanged: true }
                }
            };
        } catch (error) {
            log(`Initialization failed: ${error.message}`, 'ERROR');
            throw error;
        }
    }

    async loadTools() {
        try {
            const response = await makeHttpRequest('/mcp', JSON.stringify({
                jsonrpc: '2.0',
                id: 2,
                method: 'tools/list',
                params: {}
            }));

            if (response.status === 200 && response.data.result) {
                this.tools = response.data.result.tools || [];
                log(`Loaded ${this.tools.length} tools`);
            }
        } catch (error) {
            log(`Failed to load tools: ${error.message}`, 'ERROR');
            this.tools = [];
        }
    }

    async handleToolsList() {
        return { tools: this.tools };
    }

    async handleToolCall(name, args) {
        log(`Calling tool: ${name}`);

        try {
            const response = await makeHttpRequest('/mcp', JSON.stringify({
                jsonrpc: '2.0',
                id: Date.now(),
                method: 'tools/call',
                params: {
                    name: name,
                    arguments: args || {}
                }
            }));

            if (response.status !== 200) {
                throw new Error(`HTTP ${response.status}`);
            }

            if (response.data.error) {
                throw new Error(response.data.error.message);
            }

            return response.data.result;
        } catch (error) {
            log(`Tool call failed: ${error.message}`, 'ERROR');
            throw error;
        }
    }

    async handleRequest(request) {
        const { method, params, id } = request;

        try {
            let result;

            switch (method) {
                case 'initialize':
                    result = await this.initialize(params);
                    break;

                case 'tools/list':
                    result = await this.handleToolsList();
                    break;

                case 'tools/call':
                    result = await this.handleToolCall(params.name, params.arguments);
                    break;

                case 'prompts/list':
                    result = { prompts: [] };
                    break;

                case 'resources/list':
                    result = { resources: [] };
                    break;

                case 'ping':
                    result = {};
                    break;

                default:
                    throw new Error(`Unknown method: ${method}`);
            }

            return {
                jsonrpc: '2.0',
                id: id,
                result: result
            };
        } catch (error) {
            return {
                jsonrpc: '2.0',
                id: id,
                error: {
                    code: -32603,
                    message: error.message
                }
            };
        }
    }

    start() {
        log(`MCP HTTP Bridge starting (Server: ${SERVER_URL})`);

        let buffer = '';

        process.stdin.on('data', async (chunk) => {
            buffer += chunk.toString();

            let newlineIndex;
            while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
                const line = buffer.slice(0, newlineIndex).trim();
                buffer = buffer.slice(newlineIndex + 1);

                if (line) {
                    try {
                        const request = JSON.parse(line);
                        log(`Request: ${request.method}`);

                        // Notifications don't have an id and don't expect a response
                        if (request.method && request.method.includes('notifications/')) {
                            log(`Notification received, no response needed`);
                            continue;
                        }

                        const response = await this.handleRequest(request);

                        process.stdout.write(JSON.stringify(response) + '\n');
                    } catch (error) {
                        log(`Error processing request: ${error.message}`, 'ERROR');

                        process.stdout.write(JSON.stringify({
                            jsonrpc: '2.0',
                            id: null,
                            error: {
                                code: -32700,
                                message: 'Parse error'
                            }
                        }) + '\n');
                    }
                }
            }
        });

        process.stdin.on('end', () => {
            log('stdin closed, exiting');
            process.exit(0);
        });

        process.on('SIGINT', () => {
            log('Received SIGINT, exiting');
            process.exit(0);
        });

        process.on('SIGTERM', () => {
            log('Received SIGTERM, exiting');
            process.exit(0);
        });
    }
}

const bridge = new MCPHttpBridge();
bridge.start();