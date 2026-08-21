from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

import src.app as frontend_app


@pytest.fixture
def app():
    return frontend_app.create_app(
        downloader_client=AsyncMock(),
        analyzer_client=AsyncMock(),
        chartmgr_client=AsyncMock(),
        forecaster_client=AsyncMock(),
    )


async def get_page(
    aiohttp_client,
    app,
    path: str,
) -> BeautifulSoup:
    client = await aiohttp_client(app)

    response = await client.get(path)
    body = await response.text()

    assert response.status == 200
    assert response.content_type == "text/html"

    soup = BeautifulSoup(
        body,
        "html.parser",
    )

    assert soup.html is not None
    assert soup.head is not None
    assert soup.body is not None
    assert soup.title is not None

    return soup


@pytest.mark.asyncio
async def test_home_page_html(
    aiohttp_client,
    app,
) -> None:
    soup = await get_page(
        aiohttp_client,
        app,
        "/",
    )

    assert (
        soup.title.get_text(strip=True)
        == "StockGuru"
    )

    assert soup.select_one(
        "main.landing-main"
    ) is not None

    assert soup.select_one(
        'a[href="/analyzer"]'
    ) is not None

    assert soup.select_one(
        'a[href="/forecaster"]'
    ) is not None

    assert soup.select_one(
        'link[href="/static/landing.css"]'
    ) is not None


@pytest.mark.asyncio
async def test_analyzer_page_html(
    aiohttp_client,
    app,
) -> None:
    soup = await get_page(
        aiohttp_client,
        app,
        "/analyzer",
    )

    assert (
        soup.title.get_text(strip=True)
        == "StockGuru - Stock Analyzer"
    )

    # Search form
    form = soup.find(
        "form",
        id="stock-form",
    )
    assert form is not None

    ticker = soup.find(
        "input",
        id="ticker",
    )
    assert ticker is not None
    assert ticker.get("name") == "ticker"
    assert ticker.get("type") == "text"
    assert ticker.has_attr("required")

    submit_button = form.find(
        "button",
        attrs={"type": "submit"},
    )
    assert submit_button is not None
    assert (
        submit_button.get_text(strip=True)
        == "Analyze"
    )

    # Data sections
    assert soup.find(
        id="metadata-section"
    ) is not None

    assert soup.find(
        id="results-section"
    ) is not None

    # Metadata output
    for element_id in (
        "company-name",
        "metadata-ticker",
        "currency",
        "exchange",
        "country",
        "industry",
    ):
        assert soup.find(
            id=element_id
        ) is not None

    # Chart
    assert soup.find(
        id="price-history-chart"
    ) is not None

    # Analysis metrics
    for element_id in (
        "cagr",
        "volatility",
        "max-drawdown",
        "sma",
        "ema",
    ):
        assert soup.find(
            id=element_id
        ) is not None

    # Required Javascript
    assert soup.select_one(
        'script[src="/static/sidebar.js"]'
    ) is not None

    assert soup.select_one(
        'script[src="/static/analyzer.js"]'
    ) is not None


@pytest.mark.asyncio
async def test_forecaster_page_html(
    aiohttp_client,
    app,
) -> None:
    soup = await get_page(
        aiohttp_client,
        app,
        "/forecaster",
    )

    assert (
        soup.title.get_text(strip=True)
        == "StockGuru - Portfolio Forecaster"
    )

    # Portfolio inputs
    assert soup.find(
        id="holdings-container"
    ) is not None

    holding = soup.select_one(
        "#holdings-container .holding-row"
    )
    assert holding is not None

    assert holding.select_one(
        ".holding-ticker"
    ) is not None

    assert holding.select_one(
        ".holding-shares"
    ) is not None

    assert holding.select_one(
        ".holding-average-cost"
    ) is not None

    assert soup.find(
        id="add-stock"
    ) is not None

    # Contribution settings
    contribution = soup.find(
        "input",
        id="contribution-amount",
    )
    assert contribution is not None
    assert contribution.get("type") == "number"

    frequency = soup.find(
        "select",
        id="contribution-frequency",
    )
    assert frequency is not None

    frequencies = {
        option.get("value")
        for option in frequency.find_all("option")
    }

    assert frequencies == {
        "monthly",
        "quarterly",
        "annually",
    }

    # Projection horizon
    years = soup.find(
        "input",
        id="projection-years",
    )
    assert years is not None
    assert years.get("type") == "range"
    assert years.get("min") == "0"
    assert years.get("max") == "25"

    # DRIP
    drip = soup.find(
        "input",
        id="drip",
    )
    assert drip is not None
    assert drip.get("type") == "checkbox"
    assert drip.has_attr("checked")

    # Run projection
    run_button = soup.find(
        "button",
        id="run-forecast",
    )
    assert run_button is not None
    assert (
        run_button.get_text(strip=True)
        == "Run Projection"
    )

    assert soup.find(
        id="forecast-status"
    ) is not None

    # Projection result areas
    assert soup.find(
        id="portfolio-overview-chart"
    ) is not None

    for element_id in (
        "source-investment",
        "source-current-growth",
        "source-contributions",
        "source-growth",
        "source-dividends",
        "source-total",
    ):
        assert soup.find(
            id=element_id
        ) is not None

    # Forecast table
    table = soup.select_one(
        "table.forecast-table"
    )
    assert table is not None

    assert soup.find(
        "tbody",
        id="holdings-body",
    ) is not None

    assert soup.find(
        "tfoot",
        id="holdings-footer",
    ) is not None

    # Required Javascript
    assert soup.select_one(
        'script[src="/static/forecaster.js"]'
    ) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/analyzer",
        "/forecaster",
    ],
)
async def test_main_pages_have_navigation(
    aiohttp_client,
    app,
    path,
) -> None:
    soup = await get_page(
        aiohttp_client,
        app,
        path,
    )

    links = {
        link.get("href")
        for link in soup.find_all(
            "a",
            href=True,
        )
    }

    assert "/" in links
    assert "/analyzer" in links
    assert "/forecaster" in links