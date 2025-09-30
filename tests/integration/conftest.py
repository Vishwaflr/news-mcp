"""
Pytest configuration for integration tests

Provides shared fixtures and configuration for integration test suite.
"""

import pytest
import httpx
import time
from typing import Generator


BASE_URL = "http://localhost:8001"
HEALTH_CHECK_RETRIES = 5
HEALTH_CHECK_DELAY = 2


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for HTTP Bridge API"""
    return BASE_URL


@pytest.fixture(scope="session", autouse=True)
def verify_server_running(base_url: str) -> None:
    """Verify HTTP Bridge server is running before tests"""
    client = httpx.Client(base_url=base_url, timeout=5.0)

    for attempt in range(HEALTH_CHECK_RETRIES):
        try:
            response = client.get("/health")
            if response.status_code == 200:
                health = response.json()
                if health.get("status") == "healthy":
                    print(f"\n✓ HTTP Bridge server is healthy at {base_url}")
                    return

        except Exception as e:
            if attempt < HEALTH_CHECK_RETRIES - 1:
                print(f"\n⚠ Server not ready (attempt {attempt + 1}/{HEALTH_CHECK_RETRIES}), waiting...")
                time.sleep(HEALTH_CHECK_DELAY)
            else:
                pytest.fail(
                    f"HTTP Bridge server not available at {base_url} after {HEALTH_CHECK_RETRIES} attempts.\n"
                    f"Error: {e}\n"
                    f"Please start the server with: python3 http_mcp_server.py"
                )


@pytest.fixture(scope="function")
def http_client(base_url: str) -> Generator[httpx.Client, None, None]:
    """HTTP client for making requests"""
    client = httpx.Client(base_url=base_url, timeout=60.0)
    yield client
    client.close()


@pytest.fixture(scope="session")
def tools_cache(base_url: str) -> dict:
    """Cached tools list to avoid repeated requests"""
    client = httpx.Client(base_url=base_url, timeout=30.0)
    response = client.get("/tools")

    if response.status_code != 200:
        pytest.fail(f"Failed to fetch tools: {response.status_code}")

    tools = response.json()
    return {tool["name"]: tool for tool in tools}


@pytest.fixture
def sample_tool_names(tools_cache: dict) -> list:
    """List of available tool names"""
    return list(tools_cache.keys())


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_data: marks tests that require database data"
    )
    config.addinivalue_line(
        "markers", "read_only: marks tests that only read data (safe to run)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on patterns"""
    for item in items:
        # Mark read-only tests
        if "list_" in item.nodeid or "get_" in item.nodeid or "search_" in item.nodeid:
            item.add_marker(pytest.mark.read_only)

        # Mark tests that require analyzed data
        if "sentiment" in item.nodeid.lower() or "analysis" in item.nodeid.lower():
            item.add_marker(pytest.mark.requires_data)


def pytest_report_header(config):
    """Add custom header to pytest report"""
    return [
        f"Integration Test Suite - HTTP Bridge API",
        f"Base URL: {BASE_URL}",
        f"Testing: Schema Propagation, Validation, Sentiment Filtering"
    ]