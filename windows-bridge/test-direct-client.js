#!/usr/bin/env node
/**
 * Test script for Direct HTTP MCP Client
 */

const { spawn } = require('child_process');

const SERVER_URL = process.env.NEWS_MCP_SERVER_URL || 'http://192.168.178.72:3001';

async function testDirectClient() {
    console.log('🧪 Testing Direct HTTP MCP Client...');
    console.log(`📡 Server URL: ${SERVER_URL}`);
    console.log('');

    return new Promise((resolve, reject) => {
        const client = spawn('node', ['direct-http-mcp-client.js'], {
            env: { ...process.env, NEWS_MCP_SERVER_URL: SERVER_URL, DEBUG: 'true' },
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let responses = [];
        let buffer = '';

        client.stdout.on('data', (data) => {
            buffer += data.toString();
            let lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const response = JSON.parse(line);
                        responses.push(response);
                    } catch (e) {
                        console.log(`📝 Raw output: ${line}`);
                    }
                }
            }
        });

        client.stderr.on('data', (data) => {
            console.log(`🔍 Debug: ${data.toString().trim()}`);
        });

        client.on('error', (error) => {
            reject(error);
        });

        // Test sequence
        setTimeout(() => {
            console.log('📤 Sending initialize request...');
            const initRequest = {
                jsonrpc: '2.0',
                id: 1,
                method: 'initialize',
                params: {}
            };
            client.stdin.write(JSON.stringify(initRequest) + '\n');
        }, 1000);

        setTimeout(() => {
            console.log('📤 Sending tools/list request...');
            const toolsRequest = {
                jsonrpc: '2.0',
                id: 2,
                method: 'tools/list',
                params: {}
            };
            client.stdin.write(JSON.stringify(toolsRequest) + '\n');
        }, 2000);

        setTimeout(() => {
            console.log('📤 Sending get_dashboard tool call...');
            const dashboardRequest = {
                jsonrpc: '2.0',
                id: 3,
                method: 'tools/call',
                params: {
                    name: 'get_dashboard',
                    arguments: {}
                }
            };
            client.stdin.write(JSON.stringify(dashboardRequest) + '\n');
        }, 3000);

        setTimeout(() => {
            client.stdin.end();

            setTimeout(() => {
                console.log('\n📊 Test Results:');
                console.log(`📥 Received ${responses.length} responses`);

                let passed = 0;
                let failed = 0;

                responses.forEach((response, i) => {
                    if (response.result) {
                        console.log(`✅ Response ${i + 1}: OK`);
                        if (response.result.tools && Array.isArray(response.result.tools)) {
                            console.log(`   📋 Found ${response.result.tools.length} tools`);
                        }
                        passed++;
                    } else if (response.error) {
                        console.log(`❌ Response ${i + 1}: Error - ${response.error.message}`);
                        failed++;
                    } else {
                        console.log(`⚠️  Response ${i + 1}: Unknown format`);
                        failed++;
                    }
                });

                console.log('');
                console.log(`✅ Passed: ${passed}`);
                console.log(`❌ Failed: ${failed}`);

                if (failed === 0 && passed >= 3) {
                    console.log('🎉 All tests passed! Direct client is working correctly.');
                    resolve(true);
                } else {
                    console.log('⚠️  Some tests failed or incomplete.');
                    resolve(false);
                }

                client.kill();
            }, 1000);
        }, 4000);
    });
}

if (require.main === module) {
    testDirectClient().catch(error => {
        console.error(`💥 Test failed: ${error.message}`);
        process.exit(1);
    });
}