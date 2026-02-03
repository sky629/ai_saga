"""Test configuration and fixtures.

Note: App-related fixtures (app, client, async_client) require environment
variables to be set. Unit tests for isolated modules like LLM can run without them.
"""

import asyncio
import os

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create FastAPI application for testing.
    
    Requires environment variables to be set.
    Skip this fixture for unit tests that don't need the full app.
    """
    # Lazy import to avoid loading settings at module level
    from app.common.logging import CONSOLE_LOGGING_CONFIG
    from app.main import create_app
    return create_app(CONSOLE_LOGGING_CONFIG)


@pytest.fixture
def client(app):
    """Create test client."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
