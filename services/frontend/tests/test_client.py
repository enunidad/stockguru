from __future__ import annotations

import pytest
from aiohttp import web

from src.client import (
    AnalyzerApiClient,
    ChartMgrApiClient,
    DownloaderApiClient,
    ForecasterApiClient,
)
from src.exceptions import (
    ApiClientError,
    ApiResponseError,
    InvalidResponseError,
    ServiceUnavailableError,
)
from src.schemas import PriceHistoryRequest


# =========================================================
# DownloaderApiClient
# Price History
# =========================================================


@pytest.mark.asyncio
async def test_get_price_history_returns_downloader_response(
    aiohttp_server,
) -> None:
    received_request: dict[str, str] = {}

    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["ticker"] = (
            request.match_info["ticker"]
        )
        received_request["period"] = (
            request.query["period"]
        )
        received_request["interval"] = (
            request.query["interval"]
        )
        received_request["aggregate"] = (
            request.query["aggregate"]
        )

        return web.json_response(
            {
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
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.get_price_history(
        PriceHistoryRequest(
            ticker="AAPL",
            period="5y",
            interval="1wk",
        )
    )

    assert result["ticker"] == "AAPL"
    assert result["rows"] == 1

    assert (
        result["data"][0]["Close"]
        == 315.32
    )

    assert received_request == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
    }


@pytest.mark.asyncio
async def test_get_price_history_raises_for_http_error(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "InvalidTickerError",
                "message": "Ticker was invalid.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        ApiClientError,
        match="Downloader returned HTTP 400",
    ):
        await client.get_price_history(
            PriceHistoryRequest(
                ticker="BAD"
            )
        )


@pytest.mark.asyncio
async def test_get_price_history_raises_for_invalid_json(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Downloader returned invalid JSON",
    ):
        await client.get_price_history(
            PriceHistoryRequest(
                ticker="AAPL"
            )
        )


@pytest.mark.asyncio
async def test_get_price_history_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "ticker": "AAPL",
                    "rows": 1,
                }
            ]
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="must be a JSON object",
    ):
        await client.get_price_history(
            PriceHistoryRequest(
                ticker="AAPL"
            )
        )


@pytest.mark.asyncio
async def test_get_price_history_requires_ticker(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "rows": 1,
                "data": [],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Missing ticker",
    ):
        await client.get_price_history(
            PriceHistoryRequest(
                ticker="AAPL"
            )
        )


@pytest.mark.asyncio
async def test_get_price_history_requires_rows(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "ticker": "AAPL",
                "data": [],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Missing price history",
    ):
        await client.get_price_history(
            PriceHistoryRequest(
                ticker="AAPL"
            )
        )


@pytest.mark.asyncio
async def test_get_price_history_returns_service_unavailable_on_connection_failure(
    aiohttp_server,
) -> None:
    app = web.Application()

    server = await aiohttp_server(app)

    base_url = str(
        server.make_url("")
    ).rstrip("/")

    await server.close()

    client = DownloaderApiClient(
        base_url=base_url
    )

    with pytest.raises(
        ServiceUnavailableError,
        match="Unable to connect to Downloader service",
    ):
        await client.get_price_history(
            PriceHistoryRequest(
                ticker="AAPL"
            )
        )


# =========================================================
# DownloaderApiClient
# Metadata
# =========================================================


@pytest.mark.asyncio
async def test_get_metadata_returns_downloader_response(
    aiohttp_server,
) -> None:
    received_ticker = {}

    async def metadata_handler(
        request: web.Request,
    ) -> web.Response:
        received_ticker["ticker"] = (
            request.match_info["ticker"]
        )

        return web.json_response(
            {
                "Company": "Apple Inc.",
                "Ticker": "AAPL",
                "Currency": "USD",
                "Industry": "Consumer Electronics",
                "Exchange": "NMS",
                "Country": "United States",
            }
        )

    app = web.Application()

    app.router.add_get(
        "/metadata/{ticker}",
        metadata_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.get_metadata(
        " aapl "
    )

    assert received_ticker["ticker"] == "AAPL"

    assert result["Ticker"] == "AAPL"

    assert result["Company"] == "Apple Inc."


@pytest.mark.asyncio
async def test_get_metadata_raises_for_http_error(
    aiohttp_server,
) -> None:
    async def metadata_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "InvalidTickerError",
                "message": "Ticker was invalid.",
            },
            status=404,
        )

    app = web.Application()

    app.router.add_get(
        "/metadata/{ticker}",
        metadata_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        ApiClientError,
        match="Downloader returned HTTP 404: Ticker was invalid",
    ):
        await client.get_metadata(
            "BAD"
        )


@pytest.mark.asyncio
async def test_get_metadata_rejects_invalid_json(
    aiohttp_server,
) -> None:
    async def metadata_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/metadata/{ticker}",
        metadata_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Downloader returned invalid metadata JSON",
    ):
        await client.get_metadata(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_metadata_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def metadata_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "Ticker": "AAPL",
                }
            ]
        )

    app = web.Application()

    app.router.add_get(
        "/metadata/{ticker}",
        metadata_handler,
    )

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match=(
            "Downloader metadata response "
            "must be a JSON object"
        ),
    ):
        await client.get_metadata(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_metadata_returns_service_unavailable_on_connection_failure(
    aiohttp_server,
) -> None:
    app = web.Application()

    server = await aiohttp_server(app)

    base_url = str(
        server.make_url("")
    ).rstrip("/")

    await server.close()

    client = DownloaderApiClient(
        base_url=base_url
    )

    with pytest.raises(
        ServiceUnavailableError,
        match="Unable to connect to Downloader service",
    ):
        await client.get_metadata(
            "AAPL"
        )


# =========================================================
# AnalyzerApiClient
# =========================================================


@pytest.mark.asyncio
async def test_get_analysis_returns_analyzer_response(
    aiohttp_server,
) -> None:
    received_request = {}

    async def analysis_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["ticker"] = (
            request.match_info["ticker"]
        )
        received_request["period"] = (
            request.query["period"]
        )
        received_request["interval"] = (
            request.query["interval"]
        )

        return web.json_response(
            {
                "ticker": "AAPL",
                "cagr": 0.12,
                "volatility": 0.25,
            }
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        analysis_handler,
    )

    server = await aiohttp_server(app)

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.get_analysis(
        " aapl ",
        period="5y",
        interval="1wk",
    )

    assert result["ticker"] == "AAPL"

    assert result["cagr"] == pytest.approx(
        0.12
    )

    assert received_request == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
    }


@pytest.mark.asyncio
async def test_get_analysis_uses_defaults(
    aiohttp_server,
) -> None:
    received_request = {}

    async def analysis_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["period"] = (
            request.query["period"]
        )
        received_request["interval"] = (
            request.query["interval"]
        )

        return web.json_response(
            {
                "ticker": "AAPL",
            }
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        analysis_handler,
    )

    server = await aiohttp_server(app)

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.get_analysis(
        "AAPL"
    )

    assert received_request == {
        "period": "10y",
        "interval": "1mo",
    }


@pytest.mark.asyncio
async def test_get_analysis_raises_for_http_error(
    aiohttp_server,
) -> None:
    async def analysis_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "analysis_error",
                "message": "Unable to analyze ticker.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        analysis_handler,
    )

    server = await aiohttp_server(app)

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        ApiClientError,
        match="Analyzer returned HTTP 400",
    ):
        await client.get_analysis(
            "BAD"
        )


@pytest.mark.asyncio
async def test_get_analysis_rejects_invalid_json(
    aiohttp_server,
) -> None:
    async def analysis_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        analysis_handler,
    )

    server = await aiohttp_server(app)

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Analyzer returned invalid JSON",
    ):
        await client.get_analysis(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_analysis_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def analysis_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "ticker": "AAPL",
                }
            ]
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        analysis_handler,
    )

    server = await aiohttp_server(app)

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Analyzer response must be a JSON object",
    ):
        await client.get_analysis(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_analysis_returns_client_error_on_connection_failure(
    aiohttp_server,
) -> None:
    app = web.Application()

    server = await aiohttp_server(app)

    base_url = str(
        server.make_url("")
    ).rstrip("/")

    await server.close()

    client = AnalyzerApiClient(
        base_url=base_url
    )

    with pytest.raises(
        ApiClientError,
        match="Unable to communicate with analyzer",
    ):
        await client.get_analysis(
            "AAPL"
        )


# =========================================================
# ChartMgrApiClient
# History Chart
# =========================================================


@pytest.mark.asyncio
async def test_get_history_chart_returns_chartmgr_response(
    aiohttp_server,
) -> None:
    received_request: dict[str, str] = {}

    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["ticker"] = (
            request.match_info["ticker"]
        )
        received_request["period"] = (
            request.query["period"]
        )
        received_request["interval"] = (
            request.query["interval"]
        )

        return web.json_response(
            {
                "chart_type": "candlestick",
                "title": "Monthly OHLC",
                "data": {
                    "x_values": [
                        "2026-06",
                        "2026-07",
                    ],
                    "y_values": {
                        "Open": [
                            200.0,
                            210.0,
                        ],
                        "High": [
                            220.0,
                            225.0,
                        ],
                        "Low": [
                            195.0,
                            205.0,
                        ],
                        "Close": [
                            215.0,
                            218.0,
                        ],
                    },
                },
                "labels": {
                    "x": "Date",
                    "y": "Value",
                },
                "legend": True,
            }
        )

    app = web.Application()

    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.get_history_chart(
        "aapl",
        period="5y",
        interval="1wk",
    )

    assert result["chart_type"] == "candlestick"
    assert result["title"] == "Monthly OHLC"

    assert (
        result["data"]["x_values"]
        == [
            "2026-06",
            "2026-07",
        ]
    )

    assert (
        result["data"]["y_values"]["Close"]
        == [
            215.0,
            218.0,
        ]
    )

    assert received_request == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
    }


@pytest.mark.asyncio
async def test_get_history_chart_uses_defaults(
    aiohttp_server,
) -> None:
    received_request: dict[str, str] = {}

    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["period"] = (
            request.query["period"]
        )
        received_request["interval"] = (
            request.query["interval"]
        )

        return web.json_response(
            {
                "chart_type": "candlestick",
                "title": "Monthly OHLC",
                "data": {
                    "x_values": [],
                    "y_values": {},
                },
                "labels": {
                    "x": "Date",
                    "y": "Value",
                },
                "legend": True,
            }
        )

    app = web.Application()

    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.get_history_chart(
        "AAPL"
    )

    assert received_request == {
        "period": "10y",
        "interval": "1mo",
    }


@pytest.mark.asyncio
async def test_get_history_chart_raises_for_http_error(
    aiohttp_server,
) -> None:
    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "downloader_request_error",
                "message": "Ticker was invalid.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        ApiResponseError
    ) as exc_info:
        await client.get_history_chart(
            "BAD"
        )

    assert exc_info.value.status == 400

    assert "Ticker was invalid." in (
        exc_info.value.message
    )


@pytest.mark.asyncio
async def test_get_history_chart_raises_for_invalid_json(
    aiohttp_server,
) -> None:
    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="ChartMgr returned invalid JSON",
    ):
        await client.get_history_chart(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_history_chart_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "chart_type": "candlestick",
                }
            ]
        )

    app = web.Application()

    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="ChartMgr response must be a JSON object",
    ):
        await client.get_history_chart(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_history_chart_returns_service_unavailable_on_connection_failure(
    aiohttp_server,
) -> None:
    app = web.Application()

    server = await aiohttp_server(app)

    base_url = str(
        server.make_url("")
    ).rstrip("/")

    await server.close()

    client = ChartMgrApiClient(
        base_url=base_url
    )

    with pytest.raises(
        ServiceUnavailableError,
        match="Unable to communicate with ChartMgr",
    ):
        await client.get_history_chart(
            "AAPL"
        )


# =========================================================
# ChartMgrApiClient
# Portfolio Overview
# =========================================================


@pytest.mark.asyncio
async def test_get_portfolio_overview_returns_chartmgr_response(
    aiohttp_server,
) -> None:
    received_payload = {}

    async def portfolio_handler(
        request: web.Request,
    ) -> web.Response:
        received_payload.update(
            await request.json()
        )

        return web.json_response(
            {
                "chart_type": "donut",
                "title": "Portfolio Overview",
                "labels": [
                    "Total Invested",
                    "Current Growth",
                    "Future Contributions",
                    "Stock Growth",
                    "Dividends / DRIP",
                ],
                "values": [
                    9000.0,
                    1000.0,
                    120000.0,
                    80000.0,
                    20000.0,
                ],
            }
        )

    app = web.Application()

    app.router.add_post(
        "/charting/portfolio_overview",
        portfolio_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    payload = {
        "initial_investment": 9000.0,
        "current_growth": 1000.0,
        "future_contributions": 120000.0,
        "stock_growth": 80000.0,
        "dividends": 20000.0,
    }

    result = await client.get_portfolio_overview(
        payload
    )

    assert received_payload == payload

    assert result["chart_type"] == "donut"

    assert result["title"] == (
        "Portfolio Overview"
    )


@pytest.mark.asyncio
async def test_get_portfolio_overview_preserves_http_error(
    aiohttp_server,
) -> None:
    async def portfolio_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "invalid_request",
                "message": "Invalid portfolio values.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_post(
        "/charting/portfolio_overview",
        portfolio_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        ApiResponseError
    ) as exc_info:
        await client.get_portfolio_overview(
            {
                "initial_investment": -1,
            }
        )

    assert exc_info.value.status == 400

    assert "Invalid portfolio values." in (
        exc_info.value.message
    )


@pytest.mark.asyncio
async def test_get_portfolio_overview_rejects_invalid_json(
    aiohttp_server,
) -> None:
    async def portfolio_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_post(
        "/charting/portfolio_overview",
        portfolio_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="ChartMgr returned invalid JSON",
    ):
        await client.get_portfolio_overview(
            {}
        )


@pytest.mark.asyncio
async def test_get_portfolio_overview_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def portfolio_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "chart_type": "donut",
                }
            ]
        )

    app = web.Application()

    app.router.add_post(
        "/charting/portfolio_overview",
        portfolio_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="ChartMgr response must be a JSON object",
    ):
        await client.get_portfolio_overview(
            {}
        )


@pytest.mark.asyncio
async def test_get_portfolio_overview_returns_service_unavailable_on_connection_failure(
    aiohttp_server,
) -> None:
    app = web.Application()

    server = await aiohttp_server(app)

    base_url = str(
        server.make_url("")
    ).rstrip("/")

    await server.close()

    client = ChartMgrApiClient(
        base_url=base_url
    )

    with pytest.raises(
        ServiceUnavailableError,
        match="Unable to communicate with ChartMgr",
    ):
        await client.get_portfolio_overview(
            {}
        )


# =========================================================
# ForecasterApiClient
# =========================================================


@pytest.mark.asyncio
async def test_forecast_returns_forecaster_response(
    aiohttp_server,
) -> None:
    received_payload = {}

    async def forecast_handler(
        request: web.Request,
    ) -> web.Response:
        received_payload.update(
            await request.json()
        )

        return web.json_response(
            {
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
        )

    app = web.Application()

    app.router.add_post(
        "/forecast",
        forecast_handler,
    )

    server = await aiohttp_server(app)

    client = ForecasterApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    payload = {
        "holdings": [
            {
                "ticker": "AAPL",
                "shares": 50.0,
                "average_cost": 180.0,
                "contribution_weight": 1.0,
            }
        ],
        "years": 20,
        "contribution_amount": 500.0,
        "contribution_frequency": "monthly",
        "drip": True,
    }

    result = await client.forecast(
        payload
    )

    assert received_payload == payload

    assert (
        result["summary"]["future_value"]
        == pytest.approx(230000.0)
    )


@pytest.mark.asyncio
async def test_forecast_preserves_http_error(
    aiohttp_server,
) -> None:
    async def forecast_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "forecast_error",
                "message": "Invalid forecast.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_post(
        "/forecast",
        forecast_handler,
    )

    server = await aiohttp_server(app)

    client = ForecasterApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        ApiResponseError
    ) as exc_info:
        await client.forecast(
            {
                "holdings": [],
            }
        )

    assert exc_info.value.status == 400

    assert "Invalid forecast." in (
        exc_info.value.message
    )


@pytest.mark.asyncio
async def test_forecast_rejects_invalid_json(
    aiohttp_server,
) -> None:
    async def forecast_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_post(
        "/forecast",
        forecast_handler,
    )

    server = await aiohttp_server(app)

    client = ForecasterApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Forecaster returned invalid JSON",
    ):
        await client.forecast(
            {}
        )


@pytest.mark.asyncio
async def test_forecast_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def forecast_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "summary": {},
                }
            ]
        )

    app = web.Application()

    app.router.add_post(
        "/forecast",
        forecast_handler,
    )

    server = await aiohttp_server(app)

    client = ForecasterApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Forecaster response must be a JSON object",
    ):
        await client.forecast(
            {}
        )


@pytest.mark.asyncio
async def test_forecast_returns_service_unavailable_on_connection_failure(
    aiohttp_server,
) -> None:
    app = web.Application()

    server = await aiohttp_server(app)

    base_url = str(
        server.make_url("")
    ).rstrip("/")

    await server.close()

    client = ForecasterApiClient(
        base_url=base_url
    )

    with pytest.raises(
        ServiceUnavailableError,
        match="Unable to communicate with Forecaster",
    ):
        await client.forecast(
            {}
        )