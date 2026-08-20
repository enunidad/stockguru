from __future__ import annotations

import json
import math
from typing import Any

import pytest


pytestmark = pytest.mark.asyncio


TICKER = "AAPL"

PERIODS = (
    "1y",
    "2y",
    "5y",
    "10y",
)

INTERVALS = (
    "1d",
    "1wk",
    "2wk",
    "1mo",
    "2mo",
    "3mo",
)

BOOLEAN_VALUES = (
    "true",
    "1",
    "on",
    "yes",
    "false",
    "0",
    "off",
    "no",
)


# =========================================================
# HTTP helpers
# =========================================================


async def get_json(
    http_session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:

    async with http_session.get(
        url,
        params=params,
    ) as response:

        text = await response.text()

        assert response.status == 200, (
            f"\nGET {response.url}"
            f"\nstatus={response.status}"
            f"\nbody={text}"
        )

        assert "application/json" in (
            response.headers.get(
                "Content-Type",
                "",
            )
        )

        payload = json.loads(text)

        assert isinstance(
            payload,
            dict,
        )

        return payload


async def post_json(
    http_session,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:

    async with http_session.post(
        url,
        json=payload,
    ) as response:

        text = await response.text()

        assert response.status == 200, (
            f"\nPOST {response.url}"
            f"\nstatus={response.status}"
            f"\nbody={text}"
        )

        assert "application/json" in (
            response.headers.get(
                "Content-Type",
                "",
            )
        )

        result = json.loads(text)

        assert isinstance(
            result,
            dict,
        )

        return result


async def get_text(
    http_session,
    url: str,
) -> str:

    async with http_session.get(
        url
    ) as response:

        text = await response.text()

        assert response.status == 200, (
            f"\nGET {response.url}"
            f"\nstatus={response.status}"
            f"\nbody={text[:1000]}"
        )

        assert text.strip()

        return text


# =========================================================
# Generic assertions
# =========================================================


def assert_number(
    value: Any,
) -> None:

    assert isinstance(
        value,
        (int, float),
    )

    assert not isinstance(
        value,
        bool,
    )

    assert math.isfinite(
        float(value)
    )


def assert_price_history(
    payload: dict[str, Any],
    *,
    ticker: str,
    period: str,
    interval: str,
) -> None:

    assert {
        "ticker",
        "period",
        "interval",
        "rows",
        "data",
    } <= payload.keys()

    assert payload["ticker"] == ticker
    assert payload["period"] == period
    assert payload["interval"] == interval

    assert isinstance(
        payload["rows"],
        int,
    )

    assert isinstance(
        payload["data"],
        list,
    )

    assert payload["rows"] == len(
        payload["data"]
    )

    assert payload["rows"] > 0

    for row in payload["data"]:

        assert {
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        } <= row.keys()

        assert isinstance(
            row["Date"],
            str,
        )

        for field in (
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ):
            assert_number(
                row[field]
            )

        assert row["High"] >= row["Low"]
        assert row["High"] >= row["Open"]
        assert row["High"] >= row["Close"]

        assert row["Low"] <= row["Open"]
        assert row["Low"] <= row["Close"]

        assert row["Close"] > 0
        assert row["Volume"] >= 0


def assert_metadata(
    payload: dict[str, Any],
    *,
    ticker: str,
) -> None:

    assert {
        "ticker",
        "currency",
        "exchange",
        "timezone",
        "quote_type",
        "name",
        "sector",
        "industry",
        "country",
        "raw",
    } <= payload.keys()

    assert payload["ticker"] == ticker

    assert isinstance(
        payload["raw"],
        dict,
    )


def assert_analysis(
    payload: dict[str, Any],
    *,
    ticker: str,
    period: str,
) -> None:

    assert {
        "ticker",
        "period",
        "interval",
        "observations",
        "start_date",
        "end_date",
        "start_price",
        "current_price",
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
        "moving_average_50",
        "moving_average_200",
    } == payload.keys()

    assert payload["ticker"] == ticker
    assert payload["period"] == period

    # Analyzer currently always analyzes daily data.
    assert payload["interval"] == "1d"

    assert payload["observations"] >= 3

    assert isinstance(
        payload["start_date"],
        str,
    )

    assert isinstance(
        payload["end_date"],
        str,
    )

    assert payload["start_date"] <= (
        payload["end_date"]
    )

    assert_number(
        payload["start_price"]
    )

    assert_number(
        payload["current_price"]
    )

    assert payload["start_price"] > 0
    assert payload["current_price"] > 0

    for field in (
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
    ):
        assert_number(
            payload[field]
        )

    for field in (
        "moving_average_50",
        "moving_average_200",
    ):
        value = payload[field]

        if value is not None:
            assert_number(value)


def assert_chart(
    payload: dict[str, Any],
    *,
    chart_type: str,
    expected_series: set[str],
) -> None:

    assert {
        "chart_type",
        "title",
        "data",
        "labels",
        "legend",
    } == payload.keys()

    assert payload["chart_type"] == (
        chart_type
    )

    assert isinstance(
        payload["title"],
        str,
    )

    assert payload["title"]

    assert isinstance(
        payload["legend"],
        bool,
    )

    data = payload["data"]

    assert {
        "x_values",
        "y_values",
    } == data.keys()

    x_values = data["x_values"]
    y_values = data["y_values"]

    assert isinstance(
        x_values,
        list,
    )

    assert x_values

    assert set(
        y_values.keys()
    ) == expected_series

    for values in y_values.values():

        assert isinstance(
            values,
            list,
        )

        assert len(values) == len(
            x_values
        )

        for value in values:
            assert_number(value)


def assert_forecast(
    payload: dict[str, Any],
    *,
    years: int,
    expected_holdings: int,
) -> None:

    assert {
        "summary",
        "timeline",
        "holdings",
    } == payload.keys()

    summary = payload["summary"]

    assert {
        "initial_investment",
        "current_growth",
        "future_contributions",
        "stock_growth",
        "dividends",
        "future_value",
    } == summary.keys()

    for value in summary.values():
        assert_number(value)

    assert (
        summary["initial_investment"]
        >= 0
    )

    assert (
        summary["future_contributions"]
        >= 0
    )

    assert summary["dividends"] >= 0
    assert summary["future_value"] > 0

    timeline = payload["timeline"]

    assert len(timeline) == (
        years + 1
    )

    assert [
        point["year"]
        for point in timeline
    ] == list(
        range(years + 1)
    )

    for point in timeline:

        assert {
            "year",
            "value",
        } == point.keys()

        assert_number(
            point["value"]
        )

    holdings = payload["holdings"]

    assert len(holdings) == (
        expected_holdings
    )

    expected_fields = {
        "ticker",
        "initial_investment",
        "current_growth",
        "contributions",
        "growth",
        "dividends",
        "future_value",
        "dividend_yield",
        "purchased_shares",
        "drip_shares",
        "total_shares",
        "ending_price",
    }

    for holding in holdings:

        assert set(
            holding.keys()
        ) == expected_fields

        assert isinstance(
            holding["ticker"],
            str,
        )

        for field in (
            expected_fields
            - {"ticker"}
        ):
            assert_number(
                holding[field]
            )

        assert (
            holding["initial_investment"]
            >= 0
        )

        assert holding["dividends"] >= 0

        assert (
            holding["purchased_shares"]
            >= 0
        )

        assert (
            holding["drip_shares"]
            >= 0
        )

        assert holding["total_shares"] >= 0
        assert holding["ending_price"] > 0

    holding_total = sum(
        holding["future_value"]
        for holding in holdings
    )

    assert summary["future_value"] == (
        pytest.approx(
            holding_total,
            abs=0.05,
        )
    )


# =========================================================
# Health
# =========================================================


@pytest.mark.parametrize(
    (
        "service",
        "expected",
    ),
    [
        (
            "downloader",
            {
                "status": "ok",
            },
        ),
        (
            "analyzer",
            {
                "status": "ok",
                "service": "analyzer",
            },
        ),
        (
            "chartmgr",
            {
                "status": "ok",
                "service": "chartmgr",
            },
        ),
        (
            "forecaster",
            {
                "status": "ok",
                "service": "forecaster",
            },
        ),
        (
            "frontend",
            {
                "status": "ok",
                "service": "frontend",
            },
        ),
    ],
)
async def test_health_endpoints(
    http_session,
    service_urls,
    service,
    expected,
) -> None:

    payload = await get_json(
        http_session,
        f"{service_urls[service]}/health",
    )

    assert payload == expected


# =========================================================
# Downloader
# =========================================================


async def test_downloader_history_defaults(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['downloader']}"
            f"/history/{TICKER}"
        ),
    )

    assert_price_history(
        payload,
        ticker=TICKER,
        period="10y",
        interval="1d",
    )


@pytest.mark.parametrize(
    "period",
    PERIODS,
)
async def test_downloader_history_periods(
    http_session,
    service_urls,
    period,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['downloader']}"
            f"/history/{TICKER}"
        ),
        params={
            "period": period,
            "interval": "1mo",
        },
    )

    assert_price_history(
        payload,
        ticker=TICKER,
        period=period,
        interval="1mo",
    )


@pytest.mark.parametrize(
    "interval",
    INTERVALS,
)
async def test_downloader_history_intervals(
    http_session,
    service_urls,
    interval,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['downloader']}"
            f"/history/{TICKER}"
        ),
        params={
            "period": "1y",
            "interval": interval,
        },
    )

    assert_price_history(
        payload,
        ticker=TICKER,
        period="1y",
        interval=interval,
    )


@pytest.mark.parametrize(
    "parameter",
    (
        "autoadjust",
        "aggregate",
    ),
)
@pytest.mark.parametrize(
    "value",
    BOOLEAN_VALUES,
)
async def test_downloader_boolean_forms(
    http_session,
    service_urls,
    parameter,
    value,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['downloader']}"
            f"/history/{TICKER}"
        ),
        params={
            "period": "1y",
            "interval": "1d",
            parameter: value,
        },
    )

    assert_price_history(
        payload,
        ticker=TICKER,
        period="1y",
        interval="1d",
    )


async def test_downloader_metadata(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['downloader']}"
            f"/metadata/{TICKER}"
        ),
    )

    assert_metadata(
        payload,
        ticker=TICKER,
    )


@pytest.mark.parametrize(
    "period",
    PERIODS,
)
async def test_downloader_dividends(
    http_session,
    service_urls,
    period,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['downloader']}"
            f"/dividends/{TICKER}"
        ),
        params={
            "period": period,
        },
    )

    assert payload["ticker"] == TICKER
    assert payload["period"] == period

    assert payload["rows"] == len(
        payload["data"]
    )

    # AAPL is intentionally used here because it
    # has a stable dividend history.
    assert payload["rows"] > 0

    for row in payload["data"]:

        assert set(
            row.keys()
        ) == {
            "Date",
            "Dividend",
        }

        assert isinstance(
            row["Date"],
            str,
        )

        assert_number(
            row["Dividend"]
        )

        assert row["Dividend"] >= 0


# =========================================================
# Analyzer
# =========================================================


async def test_analyzer_defaults(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['analyzer']}"
            f"/analysis/{TICKER}"
        ),
    )

    assert_analysis(
        payload,
        ticker=TICKER,
        period="10y",
    )


@pytest.mark.parametrize(
    "period",
    PERIODS,
)
async def test_analyzer_periods(
    http_session,
    service_urls,
    period,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['analyzer']}"
            f"/analysis/{TICKER}"
        ),
        params={
            "period": period,
        },
    )

    assert_analysis(
        payload,
        ticker=TICKER,
        period=period,
    )


@pytest.mark.parametrize(
    "value",
    BOOLEAN_VALUES,
)
async def test_analyzer_accepts_boolean_forms(
    http_session,
    service_urls,
    value,
) -> None:
    """
    This is currently an input/parsing contract test.

    Analyzer accepts autoadjust, although the current
    AnalyzerService does not yet propagate the value to
    Downloader.
    """

    payload = await get_json(
        http_session,
        (
            f"{service_urls['analyzer']}"
            f"/analysis/{TICKER}"
        ),
        params={
            "period": "1y",
            "autoadjust": value,
        },
    )

    assert_analysis(
        payload,
        ticker=TICKER,
        period="1y",
    )


# =========================================================
# ChartMgr
# =========================================================


@pytest.mark.parametrize(
    (
        "path",
        "chart_type",
        "series",
    ),
    [
        (
            "price_history",
            "candlestick",
            {
                "Open",
                "High",
                "Low",
                "Close",
            },
        ),
        (
            "volume",
            "bar",
            {
                "Volume",
            },
        ),
    ],
)
async def test_chartmgr_history_defaults(
    http_session,
    service_urls,
    path,
    chart_type,
    series,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['chartmgr']}"
            f"/charting/{path}/{TICKER}"
        ),
    )

    assert_chart(
        payload,
        chart_type=chart_type,
        expected_series=series,
    )


@pytest.mark.parametrize(
    "period,interval",
    [
        (
            "1y",
            "1wk",
        ),
        (
            "2y",
            "2wk",
        ),
        (
            "5y",
            "1mo",
        ),
        (
            "10y",
            "3mo",
        ),
    ],
)
async def test_chartmgr_price_history_variants(
    http_session,
    service_urls,
    period,
    interval,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['chartmgr']}"
            f"/charting/price_history/{TICKER}"
        ),
        params={
            "period": period,
            "interval": interval,
        },
    )

    assert_chart(
        payload,
        chart_type="candlestick",
        expected_series={
            "Open",
            "High",
            "Low",
            "Close",
        },
    )


@pytest.mark.parametrize(
    "portfolio,expected_chart_type",
    [
        (
            {
                "initial_investment": 1000,
                "current_growth": 100,
                "future_contributions": 500,
                "stock_growth": 250,
                "dividends": 50,
            },
            "donut",
        ),
        (
            {
                "initial_investment": 1000,
                "current_growth": -100,
                "future_contributions": 500,
                "stock_growth": 250,
                "dividends": 50,
            },
            "bar",
        ),
    ],
)
async def test_chartmgr_portfolio_overview(
    http_session,
    service_urls,
    portfolio,
    expected_chart_type,
) -> None:

    payload = await post_json(
        http_session,
        (
            f"{service_urls['chartmgr']}"
            "/charting/portfolio_overview"
        ),
        portfolio,
    )

    assert payload["chart_type"] == (
        expected_chart_type
    )

    assert payload["title"] == (
        "Portfolio Overview"
    )

    assert payload["labels"] == [
        "Total Invested",
        "Current Growth",
        "Future Contributions",
        "Stock Growth",
        "Dividends / DRIP",
    ]

    assert len(
        payload["values"]
    ) == 5

    for value in payload["values"]:
        assert_number(value)

    assert payload["total"] == (
        pytest.approx(
            sum(payload["values"]),
            abs=0.01,
        )
    )


# =========================================================
# Forecaster
# =========================================================


@pytest.mark.parametrize(
    (
        "request_payload",
        "years",
        "holding_count",
    ),
    [
        (
            {
                "holdings": [
                    {
                        "ticker": TICKER,
                        "shares": 2,
                    },
                ],
            },
            10,
            1,
        ),
        (
            {
                "holdings": [
                    {
                        "ticker": TICKER,
                        "shares": 2,
                        "average_cost": 100,
                    },
                ],
                "years": 2,
                "drip": False,
            },
            2,
            1,
        ),
        (
            {
                "holdings": [
                    {
                        "ticker": TICKER,
                        "shares": 2,
                        "contribution_weight": 1,
                    },
                ],
                "years": 1,
                "contribution_amount": 100,
                "contribution_frequency": "monthly",
                "drip": True,
            },
            1,
            1,
        ),
        (
            {
                "holdings": [
                    {
                        "ticker": TICKER,
                        "shares": 2,
                        "contribution_weight": 1,
                    },
                ],
                "years": 1,
                "contribution_amount": 100,
                "contribution_frequency": "quarterly",
                "drip": False,
            },
            1,
            1,
        ),
        (
            {
                "holdings": [
                    {
                        "ticker": TICKER,
                        "shares": 2,
                        "contribution_weight": 1,
                    },
                ],
                "years": 1,
                "contribution_amount": 100,
                "contribution_frequency": "annually",
                "drip": True,
            },
            1,
            1,
        ),
        (
            {
                "holdings": [
                    {
                        "ticker": "AAPL",
                        "shares": 1,
                        "average_cost": 100,
                        "contribution_weight": 0.5,
                    },
                    {
                        "ticker": "MSFT",
                        "shares": 1,
                        "average_cost": 100,
                        "contribution_weight": 0.5,
                    },
                ],
                "years": 1,
                "contribution_amount": 100,
                "contribution_frequency": "monthly",
                "drip": True,
            },
            1,
            2,
        ),
    ],
)
async def test_forecaster_variants(
    http_session,
    service_urls,
    request_payload,
    years,
    holding_count,
) -> None:

    payload = await post_json(
        http_session,
        (
            f"{service_urls['forecaster']}"
            "/forecast"
        ),
        request_payload,
    )

    assert_forecast(
        payload,
        years=years,
        expected_holdings=holding_count,
    )


# =========================================================
# Frontend pages
# =========================================================


@pytest.mark.parametrize(
    "path",
    (
        "/",
        "/analyzer",
        "/forecaster",
    ),
)
async def test_frontend_pages(
    http_session,
    service_urls,
    path,
) -> None:

    html = await get_text(
        http_session,
        (
            f"{service_urls['frontend']}"
            f"{path}"
        ),
    )

    assert "<html" in html.lower()


async def test_frontend_static_files(
    http_session,
    service_urls,
) -> None:

    css = await get_text(
        http_session,
        (
            f"{service_urls['frontend']}"
            "/static/theme.css"
        ),
    )

    assert "--sg-" in css


# =========================================================
# Frontend -> service flows
# =========================================================


async def test_frontend_price_flow(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['frontend']}"
            f"/api/prices/{TICKER}"
        ),
    )

    assert_price_history(
        payload,
        ticker=TICKER,
        period="10y",
        interval="1mo",
    )


async def test_frontend_metadata_flow(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['frontend']}"
            f"/api/metadata/{TICKER}"
        ),
    )

    assert_metadata(
        payload,
        ticker=TICKER,
    )


async def test_frontend_analysis_flow(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['frontend']}"
            f"/api/analysis/{TICKER}"
        ),
        params={
            "period": "1y",
        },
    )

    assert_analysis(
        payload,
        ticker=TICKER,
        period="1y",
    )


async def test_frontend_chart_flow(
    http_session,
    service_urls,
) -> None:

    payload = await get_json(
        http_session,
        (
            f"{service_urls['frontend']}"
            "/api/charting/"
            f"price_history/{TICKER}"
        ),
        params={
            "period": "1y",
            "interval": "1mo",
        },
    )

    assert_chart(
        payload,
        chart_type="candlestick",
        expected_series={
            "Open",
            "High",
            "Low",
            "Close",
        },
    )


async def test_frontend_forecast_flow(
    http_session,
    service_urls,
) -> None:

    request_payload = {
        "holdings": [
            {
                "ticker": TICKER,
                "shares": 2,
                "average_cost": 100,
            },
        ],
        "years": 1,
        "drip": True,
    }

    payload = await post_json(
        http_session,
        (
            f"{service_urls['frontend']}"
            "/api/forecast"
        ),
        request_payload,
    )

    assert_forecast(
        payload,
        years=1,
        expected_holdings=1,
    )


async def test_frontend_portfolio_chart_flow(
    http_session,
    service_urls,
) -> None:

    request_payload = {
        "initial_investment": 1000,
        "current_growth": 100,
        "future_contributions": 500,
        "stock_growth": 250,
        "dividends": 50,
    }

    payload = await post_json(
        http_session,
        (
            f"{service_urls['frontend']}"
            "/api/charting/"
            "portfolio_overview"
        ),
        request_payload,
    )

    assert payload["chart_type"] == "donut"
    assert payload["title"] == (
        "Portfolio Overview"
    )

    assert len(
        payload["labels"]
    ) == 5

    assert len(
        payload["values"]
    ) == 5

    assert payload["total"] == (
        pytest.approx(
            sum(payload["values"]),
            abs=0.01,
        )
    )