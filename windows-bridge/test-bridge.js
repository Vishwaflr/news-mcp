#!/usr/bin/env node
/**
 * Test script for News MCP Bridge
 */

const http = require('http');
const { URL } = require('url');

const SERVER_URL = process.env.NEWS_MCP_SERVER_URL || 'http://192.168.178.72:3001';

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
                'User-Agent': 'News-MCP-Bridge-Test/1.0.0'
            },
            timeout: 5000
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
                    resolve({ status: res.statusCode, data: parsed });
                } catch (e) {
                    resolve({ status: res.statusCode, data: responseData });
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

async function runTests() {
    console.log('🧪 Testing News MCP Bridge Connection...');
    console.log(`📡 Server URL: ${SERVER_URL}`);
    console.log('');

    const tests = [
        {
            name: 'Health Check',
            method: 'GET',
            path: '/health'
        },
        {
            name: 'List Tools',
            method: 'GET',
            path: '/tools'
        },
        {
            name: 'Get Dashboard',
            method: 'POST',
            path: '/call',
            data: { method: 'get_dashboard', params: {} }
        },
        {
            name: 'List Feeds',
            method: 'POST',
            path: '/call',
            data: { method: 'list_feeds', params: { limit: 5 } }
        }
    ];

    let passed = 0;
    let failed = 0;

    for (const test of tests) {
        try {
            console.log(`🔄 ${test.name}...`);
            const result = await makeHttpRequest(test.method, test.path, test.data);

            if (result.status === 200) {
                console.log(`✅ ${test.name} - OK`);
                if (test.name === 'List Tools' && result.data.tools) {
                    console.log(`   📋 Found ${result.data.tools.length} tools`);
                }
                passed++;
            } else {
                console.log(`❌ ${test.name} - HTTP ${result.status}`);
                failed++;
            }
        } catch (error) {
            console.log(`❌ ${test.name} - ${error.message}`);
            failed++;
        }
    }

    console.log('');
    console.log('📊 Test Results:');
    console.log(`✅ Passed: ${passed}`);
    console.log(`❌ Failed: ${failed}`);

    if (failed === 0) {
        console.log('🎉 All tests passed! Bridge is ready for Claude Desktop.');
        process.exit(0);
    } else {
        console.log('⚠️  Some tests failed. Check server connection.');
        process.exit(1);
    }
}

if (require.main === module) {
    runTests().catch(error => {
        console.error(`💥 Test runner error: ${error.message}`);
        process.exit(1);
    });
}