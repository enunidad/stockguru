from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

import src.app as frontend_app
from src.exceptions import (
    ApiClientError,
    ApiResponseError,
    InvalidResponseError,
    ServiceUnavailableError,
)


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def downloader_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def analyzer_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def chartmgr_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def forecaster_client() -> AsyncMock:
    return AsyncMock()


def create_test_app(
    downloader_client: AsyncMock,
    analyzer_client: AsyncMock,
    chartmgr_client: AsyncMock,
    forecaster_client: AsyncMock,
):
    return frontend_app.create_app(
        downloader_client=downloader_client,
        analyzer_client=analyzer_client,
        chartmgr_client=chartmgr_client,
        forecaster_client=forecaster_client,
    )


@pytest_asyncio.fixture
async def client(
    aiohttp_client,
    downloader_client,
    analyzer_client,
    chartmgr_client,
    forecaster_client,
):
    app = create_test_app(
        downloader_client,
        analyzer_client,
        chartmgr_client,
        forecaster_client,
    )

    return await aiohttp_client(app)


# =========================================================
# Basic Pages
# =========================================================


@pytest.mark.asyncio
async def test_health_endpoint(
    client,
) -> None:
    response = await client.get(
        "/health"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "status": "ok",
        "service": "frontend",
    }


@pytest.mark.asyncio
async def test_index_returns_html(
    client,
) -> None:
    response = await client.get("/")

    body = await response.text()

    assert response.status == 200
    assert response.content_type == "text/html"

    assert "StockGuru" in body
    assert "Stock Analyzer" in body
    assert "Portfolio Forecaster" in body

    assert 'href="/analyzer"' in body
    assert 'href="/forecaster"' in body


@pytest.mark.asyncio
async def test_analyzer_page_returns_html(
    client,
) -> None:
    response = await client.get(
        "/analyzer"
    )

    body = await response.text()

    assert response.status == 200
    assert response.content_type == "text/html"

    assert "Stock Analyzer" in body
    assert 'id="stock-form"' in body


@pytest.mark.asyncio
async def test_forecaster_page_returns_html(
    client,
) -> None:
    response = await client.get(
        "/forecaster"
    )

    body = await response.text()

    assert response.status == 200
    assert response.content_type == "text/html"

    assert "Portfolio Forecaster" in body
    assert 'id="holdings-container"' in body
    assert 'id="run-forecast"' in body


@pytest.mark.asyncio
async def test_analyzer_javascript_is_served(
    client,
) -> None:
    response = await client.get(
        "/static/analyzer.js"
    )

    assert response.status == 200

    body = await response.text()

    assert "/api/analysis/" in body
    assert "/api/charting/price_history/" in body


@pytest.mark.asyncio
async def test_forecaster_javascript_is_served(
    client,
) -> None:
    response = await client.get(
        "/static/forecaster.js"
    )

    assert response.status == 200

    body = await response.text()

    assert "/api/forecast" in body


# =========================================================
# Downloader Price Proxy
# =========================================================


@pytest.mark.asyncio
async def test_price_proxy_returns_downloader_response(
    client,
    downloader_client,
) -> None:
    downloader_client.get_price_history.return_value = {
        "ticker": "AAPL",
        "period": "10y",
        "interval": "1mo",
        "rows": 1,
        "data": [
            {
                "Date": "2026-07-10",
                "Close": 315.32,
            }
        ],
    }

    response = await client.get(
        "/api/prices/aapl"
    )

    body = await response.json()

    assert response.status == 200

    assert body["ticker"] == "AAPL"
    assert body["rows"] == 1

    assert (
        body["data"][0]["Close"]
        == 315.32
    )

    downloader_client.get_price_history.assert_awaited_once()

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
    client,
    downloader_client,
) -> None:
    downloader_client.get_price_history.side_effect = (
        InvalidResponseError(
            "Downloader returned invalid JSON."
        )
    )

    response = await client.get(
        "/api/prices/AAPL"
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "invalid_downloader_response",
        "message": (
            "Downloader returned invalid JSON."
        ),
    }


@pytest.mark.asyncio
async def test_price_proxy_returns_503_when_downloader_unavailable(
    client,
    downloader_client,
) -> None:
    downloader_client.get_price_history.side_effect = (
        ApiClientError(
            "Downloader unavailable."
        )
    )

    response = await client.get(
        "/api/prices/AAPL"
    )

    body = await response.json()

    assert response.status == 503

    assert body == {
        "error": "downloader_unavailable",
        "message": "Downloader unavailable.",
    }


# =========================================================
# Metadata Proxy
# =========================================================


@pytest.mark.asyncio
async def test_metadata_proxy_returns_downloader_response(
    client,
    downloader_client,
) -> None:
    downloader_client.get_metadata.return_value = {
        "Company": "Apple Inc.",
        "Ticker": "AAPL",
        "Currency": "USD",
        "Industry": "Consumer Electronics",
        "Exchange": "NMS",
        "Country": "United States",
    }

    response = await client.get(
        "/api/metadata/aapl"
    )

    body = await response.json()

    assert response.status == 200

    assert body["Ticker"] == "AAPL"
    assert body["Company"] == "Apple Inc."

    downloader_client.get_metadata.assert_awaited_once_with(
        "AAPL"
    )


@pytest.mark.asyncio
async def test_metadata_proxy_returns_502_for_invalid_response(
    client,
    downloader_client,
) -> None:
    downloader_client.get_metadata.side_effect = (
        InvalidResponseError(
            "Invalid metadata."
        )
    )

    response = await client.get(
        "/api/metadata/AAPL"
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "invalid_downloader_response",
        "message": "Invalid metadata.",
    }


@pytest.mark.asyncio
async def test_metadata_proxy_returns_503_when_downloader_unavailable(
    client,
    downloader_client,
) -> None:
    downloader_client.get_metadata.side_effect = (
        ApiClientError(
            "Downloader unavailable."
        )
    )

    response = await client.get(
        "/api/metadata/AAPL"
    )

    body = await response.json()

    assert response.status == 503

    assert body == {
        "error": "downloader_unavailable",
        "message": "Downloader unavailable.",
    }


# =========================================================
# Analyzer Proxy
# =========================================================


@pytest.mark.asyncio
async def test_analysis_proxy_returns_analyzer_response(
    client,
    analyzer_client,
) -> None:
    analyzer_client.get_analysis.return_value = {
        "ticker": "AAPL",
        "cagr": 0.12,
        "volatility": 0.24,
        "max_drawdown": -0.31,
    }

    response = await client.get(
        "/api/analysis/aapl?period=5y"
    )

    body = await response.json()

    assert response.status == 200

    assert body["ticker"] == "AAPL"
    assert body["cagr"] == pytest.approx(
        0.12
    )

    analyzer_client.get_analysis.assert_awaited_once_with(
        "AAPL",
        period="5y",
    )


@pytest.mark.asyncio
async def test_analysis_proxy_uses_default_period(
    client,
    analyzer_client,
) -> None:
    analyzer_client.get_analysis.return_value = {
        "ticker": "AAPL",
    }

    response = await client.get(
        "/api/analysis/AAPL"
    )

    assert response.status == 200

    analyzer_client.get_analysis.assert_awaited_once_with(
        "AAPL",
        period="10y",
    )


@pytest.mark.asyncio
async def test_analysis_proxy_returns_502_for_invalid_response(
    client,
    analyzer_client,
) -> None:
    analyzer_client.get_analysis.side_effect = (
        InvalidResponseError(
            "Analyzer returned invalid JSON."
        )
    )

    response = await client.get(
        "/api/analysis/AAPL"
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "invalid_analyzer_response",
        "message": (
            "Analyzer returned invalid JSON."
        ),
    }


@pytest.mark.asyncio
async def test_analysis_proxy_returns_503_when_analyzer_unavailable(
    client,
    analyzer_client,
) -> None:
    analyzer_client.get_analysis.side_effect = (
        ApiClientError(
            "Analyzer unavailable."
        )
    )

    response = await client.get(
        "/api/analysis/AAPL"
    )

    body = await response.json()

    assert response.status == 503

    assert body == {
        "error": "analyzer_unavailable",
        "message": "Analyzer unavailable.",
    }


# =========================================================
# ChartMgr Proxy
# =========================================================


@pytest.mark.asyncio
async def test_chart_proxy_returns_chartmgr_response(
    client,
    chartmgr_client,
) -> None:
    chartmgr_client.get_history_chart.return_value = {
        "chart_type": "candlestick",
        "title": "Monthly OHLC",
        "data": {
            "x_values": [
                "2026-06",
                "2026-07",
            ],
            "y_values": {
                "Open": [200.0, 210.0],
                "High": [220.0, 225.0],
                "Low": [195.0, 205.0],
                "Close": [215.0, 218.0],
            },
        },
        "labels": {
            "x": "Date",
            "y": "Value",
        },
        "legend": True,
    }

    response = await client.get(
        "/api/charting/price_history/aapl"
        "?period=5y&interval=1wk"
    )

    body = await response.json()

    assert response.status == 200

    assert body["chart_type"] == "candlestick"

    assert (
        body["data"]["y_values"]["Close"]
        == [
            215.0,
            218.0,
        ]
    )

    chartmgr_client.get_history_chart.assert_awaited_once_with(
        "AAPL",
        period="5y",
        interval="1wk",
    )


@pytest.mark.asyncio
async def test_chart_proxy_uses_defaults(
    client,
    chartmgr_client,
) -> None:
    chartmgr_client.get_history_chart.return_value = {
        "chart_type": "candlestick",
    }

    response = await client.get(
        "/api/charting/price_history/AAPL"
    )

    assert response.status == 200

    chartmgr_client.get_history_chart.assert_awaited_once_with(
        "AAPL",
        period="10y",
        interval="1mo",
    )


@pytest.mark.asyncio
async def test_chart_proxy_returns_502_for_invalid_response(
    client,
    chartmgr_client,
) -> None:
    chartmgr_client.get_history_chart.side_effect = (
        InvalidResponseError(
            "ChartMgr returned invalid JSON."
        )
    )

    response = await client.get(
        "/api/charting/price_history/AAPL"
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "invalid_chartmgr_response",
        "message": (
            "ChartMgr returned invalid JSON."
        ),
    }


@pytest.mark.asyncio
async def test_chart_proxy_preserves_chartmgr_4xx(
    client,
    chartmgr_client,
) -> None:
    chartmgr_client.get_history_chart.side_effect = (
        ApiResponseError(
            status=400,
            message="Invalid ticker.",
        )
    )

    response = await client.get(
        "/api/charting/price_history/BAD"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "chartmgr_request_error",
        "message": "Invalid ticker.",
    }


@pytest.mark.asyncio
async def test_chart_proxy_converts_chartmgr_5xx_to_502(
    client,
    chartmgr_client,
) -> None:
    chartmgr_client.get_history_chart.side_effect = (
        ApiResponseError(
            status=500,
            message="ChartMgr failed.",
        )
    )

    response = await client.get(
        "/api/charting/price_history/AAPL"
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "chartmgr_error",
        "message": "ChartMgr failed.",
    }


@pytest.mark.asyncio
async def test_chart_proxy_returns_503_when_chartmgr_unavailable(
    client,
    chartmgr_client,
) -> None:
    chartmgr_client.get_history_chart.side_effect = (
        ServiceUnavailableError(
            "Unable to communicate with ChartMgr."
        )
    )

    response = await client.get(
        "/api/charting/price_history/AAPL"
    )

    body = await response.json()

    assert response.status == 503

    assert body == {
        "error": "chartmgr_unavailable",
        "message": (
            "Unable to communicate with ChartMgr."
        ),
    }


# =========================================================
# Forecaster Proxy
# =========================================================


@pytest.mark.asyncio
async def test_forecast_proxy_returns_forecaster_response(
    client,
    forecaster_client,
) -> None:
    payload = {
        "holdings": [
            {
                "ticker": "AAPL",
                "shares": 50,
                "average_cost": 180.0,
                "contribution_weight": 1.0,
            }
        ],
        "years": 20,
        "contribution_amount": 500.0,
        "contribution_frequency": "monthly",
        "drip": True,
    }

    forecast_result = {
        "summary": {
            "initial_investment": 9000.0,
            "current_growth": 1000.0,
            "future_contributions": 120000.0,
            "stock_growth": 80000.0,
            "dividends": 20000.0,
            "future_value": 230000.0,
        },
        "timeline": [],
        "holdings": [],
    }

    forecaster_client.forecast.return_value = (
        forecast_result
    )

    response = await client.post(
        "/api/forecast",
        json=payload,
    )

    body = await response.json()

    assert response.status == 200
    assert body == forecast_result

    forecaster_client.forecast.assert_awaited_once_with(
        payload
    )


@pytest.mark.asyncio
async def test_forecast_proxy_rejects_invalid_json(
    client,
    forecaster_client,
) -> None:
    response = await client.post(
        "/api/forecast",
        data="{not-valid-json",
        headers={
            "Content-Type": "application/json",
        },
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "invalid_json",
        "message": (
            "Request body must contain valid JSON."
        ),
    }

    forecaster_client.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_proxy_returns_502_for_invalid_response(
    client,
    forecaster_client,
) -> None:
    forecaster_client.forecast.side_effect = (
        InvalidResponseError(
            "Forecaster returned invalid JSON."
        )
    )

    response = await client.post(
        "/api/forecast",
        json={
            "holdings": [],
        },
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "invalid_forecaster_response",
        "message": (
            "Forecaster returned invalid JSON."
        ),
    }


@pytest.mark.asyncio
async def test_forecast_proxy_preserves_forecaster_4xx(
    client,
    forecaster_client,
) -> None:
    forecaster_client.forecast.side_effect = (
        ApiResponseError(
            status=400,
            message="Invalid forecast request.",
        )
    )

    response = await client.post(
        "/api/forecast",
        json={
            "holdings": [],
        },
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "forecaster_request_error",
        "message": (
            "Invalid forecast request."
        ),
    }


@pytest.mark.asyncio
async def test_forecast_proxy_converts_forecaster_5xx_to_502(
    client,
    forecaster_client,
) -> None:
    forecaster_client.forecast.side_effect = (
        ApiResponseError(
            status=500,
            message="Forecaster failed.",
        )
    )

    response = await client.post(
        "/api/forecast",
        json={
            "holdings": [],
        },
    )

    body = await response.json()

    assert response.status == 502

    assert body == {
        "error": "forecaster_error",
        "message": "Forecaster failed.",
    }


@pytest.mark.asyncio
async def test_forecast_proxy_returns_503_when_forecaster_unavailable(
    client,
    forecaster_client,
) -> None:
    forecaster_client.forecast.side_effect = (
        ServiceUnavailableError(
            "Unable to communicate with Forecaster."
        )
    )

    response = await client.post(
        "/api/forecast",
        json={
            "holdings": [],
        },
    )

    body = await response.json()

    assert response.status == 503

    assert body == {
        "error": "forecaster_unavailable",
        "message": (
            "Unable to communicate with Forecaster."
        ),
    }


# =========================================================
# Template Failure
# =========================================================


@pytest.mark.asyncio
async def test_index_returns_500_when_template_missing(
    aiohttp_client,
    monkeypatch,
    tmp_path: Path,
    downloader_client,
    analyzer_client,
    chartmgr_client,
    forecaster_client,
) -> None:
    monkeypatch.setattr(
        frontend_app,
        "TEMPLATES_DIR",
        tmp_path,
    )

    app = create_test_app(
        downloader_client,
        analyzer_client,
        chartmgr_client,
        forecaster_client,
    )

    client = await aiohttp_client(app)

    response = await client.get("/")

    assert response.status == 500