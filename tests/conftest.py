"""Test configuration and fixtures."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.common.logging import CONSOLE_LOGGING_CONFIG
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    return create_app(CONSOLE_LOGGING_CONFIG)


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
