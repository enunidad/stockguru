from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import src.app as frontend_app
from src.exceptions import ApiClientError, InvalidResponseError


@pytest.fixture
def downloader_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def analyzer_client() -> AsyncMock:
    return AsyncMock()


def create_test_app(
    downloader_client: AsyncMock,
    analyzer_client: AsyncMock,
):
    return frontend_app.create_app(
        downloader_client=downloader_client,
        analyzer_client=analyzer_client,
    )


@pytest.mark.asyncio
async def test_health_endpoint(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/health")
    body = await response.json()

    assert response.status == 200
    assert body == {
        "status": "ok",
        "service": "frontend",
    }


@pytest.mark.asyncio
async def test_index_returns_html(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/")
    body = await response.text()

    assert response.status == 200
    assert response.content_type == "text/html"
    assert "StockGuru" in body
    assert 'id="stock-form"' in body


@pytest.mark.asyncio
async def test_static_javascript_is_served(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/static/app.js")
    body = await response.text()

    assert response.status == 200
    assert "stockForm.addEventListener" in body
    assert "stock-form" in body
    assert "/api/prices/" in body


@pytest.mark.asyncio
async def test_price_proxy_returns_downloader_response(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.get_price_history.return_value = {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
        "rows": 1,
        "data": [
            {
                "Date": "2026-07-10",
                "Close": 315.32,
            }
        ],
    }

    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get(
        "/api/prices/aapl?period=5y&interval=1wk"
    )
    body = await response.json()

    assert response.status == 200
    assert body["ticker"] == "AAPL"
    assert body["rows"] == 1
    assert body["data"][0]["Close"] == 315.32

    downloader_client.get_price_history.assert_awaited_once()

    request = (
        downloader_client
        .get_price_history
        .await_args
        .args[0]
    )

    assert request.ticker == "AAPL"
    assert request.period == "5y"
    assert request.interval == "1wk"


@pytest.mark.asyncio
async def test_price_proxy_uses_default_query_values(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.get_price_history.return_value = {
        "ticker": "AAPL",
        "period": "10y",
        "interval": "1mo",
        "rows": 0,
        "data": [],
    }

    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/AAPL")

    assert response.status == 200

    request = (
        downloader_client
        .get_price_history
        .await_args
        .args[0]
    )

    assert request.ticker == "AAPL"
    assert request.period == "10y"
    assert request.interval == "1mo"


@pytest.mark.asyncio
async def test_price_proxy_returns_502_for_invalid_response(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.get_price_history.side_effect = (
        InvalidResponseError(
            "The downloader returned invalid JSON."
        )
    )

    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/AAPL")
    body = await response.json()

    assert response.status == 502
    assert body == {
        "error": "invalid_downloader_response",
        "message": "The downloader returned invalid JSON.",
    }


@pytest.mark.asyncio
async def test_price_proxy_returns_503_when_downloader_unavailable(
    aiohttp_client,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.get_price_history.side_effect = (
        ApiClientError(
            "The downloader service is unavailable."
        )
    )

    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/AAPL")
    body = await response.json()

    assert response.status == 503
    assert body == {
        "error": "downloader_unavailable",
        "message": "The downloader service is unavailable.",
    }


@pytest.mark.asyncio
async def test_index_returns_500_when_template_missing(
    aiohttp_client,
    monkeypatch,
    tmp_path: Path,
    downloader_client,
    analyzer_client,
) -> None:
    monkeypatch.setattr(
        frontend_app,
        "TEMPLATES_DIR",
        tmp_path,
    )

    app = create_test_app(
        downloader_client,
        analyzer_client,
    )
    client = await aiohttp_client(app)

    response = await client.get("/")

    assert response.status == 500