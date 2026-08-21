# integration_tests/conftest.py

from __future__ import annotations

import os

import aiohttp
import pytest
import pytest_asyncio


DEFAULT_SERVICE_URLS = {
    "downloader": "http://localhost:8080",
    "analyzer": "http://localhost:8090",
    "chartmgr": "http://localhost:8050",
    "forecaster": "http://localhost:8060",
    "frontend": "http://localhost:8000",
}


@pytest.fixture(scope="session")
def service_urls() -> dict[str, str]:
    """
    URLs for the running StocksGuru services.

    Environment variables can override the local defaults,
    which also makes these tests usable against deployed
    environments later if desired.
    """

    return {
        "downloader": os.getenv(
            "DOWNLOADER_BASE_URL",
            DEFAULT_SERVICE_URLS["downloader"],
        ),
        "analyzer": os.getenv(
            "ANALYZER_BASE_URL",
            DEFAULT_SERVICE_URLS["analyzer"],
        ),
        "chartmgr": os.getenv(
            "CHARTMGR_BASE_URL",
            DEFAULT_SERVICE_URLS["chartmgr"],
        ),
        "forecaster": os.getenv(
            "FORECASTER_BASE_URL",
            DEFAULT_SERVICE_URLS["forecaster"],
        ),
        "frontend": os.getenv(
            "FRONTEND_BASE_URL",
            DEFAULT_SERVICE_URLS["frontend"],
        ),
    }


@pytest_asyncio.fixture
async def http_session():
    """
    Real HTTP client used by integration tests.

    No mocks.
    No fake service clients.
    """

    timeout = aiohttp.ClientTimeout(
        total=30,
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
    ) as session:
        yield session