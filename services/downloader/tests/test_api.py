import pandas as pd
import pytest

from src.api import create_app
from src.exceptions import EmptyDownloadError


class FakeDownloaderService:
    def get_price_history(
        self,
        ticker: str,
        period: str = "10y",
        interval: str = "1d",
        auto_adjust: bool = False,
    ) -> pd.DataFrame:
        data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "Close": [110.0, 111.0],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )

        data.index.name = 'Date'
        return data


class FailingDownloaderService:
    def get_price_history(
        self,
        ticker: str,
        period: str = "10y",
        interval: str = "1d",
        auto_adjust: bool = False,
    ) -> pd.DataFrame:
        raise EmptyDownloadError("No price history returned for ticker 'BAD'.")


@pytest.mark.asyncio
async def test_health_endpoint(aiohttp_client):
    app = create_app(service_override=FakeDownloaderService())
    client = await aiohttp_client(app)

    response = await client.get("/health")
    body = await response.json()

    assert response.status == 200
    assert body == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_price_history_returns_json(aiohttp_client):
    app = create_app(service_override=FakeDownloaderService())
    client = await aiohttp_client(app)

    response = await client.get("/history/aapl?period=5y&interval=1wk")
    body = await response.json()

    assert response.status == 200
    assert body["ticker"] == "AAPL"
    assert body["period"] == "5y"
    assert body["interval"] == "1wk"
    assert body["rows"] == 2
    assert body["data"] == [
        {
            "Date": "2024-01-01",
            "Open": 100.0,
            "Close": 110.0,
        },
        {
            "Date": "2024-01-02",
            "Open": 101.0,
            "Close": 111.0,
        },
    ]


@pytest.mark.asyncio
async def test_get_price_history_returns_400_for_downloader_errors(aiohttp_client):
    app = create_app(service_override=FailingDownloaderService())
    client = await aiohttp_client(app)

    response = await client.get("/history/bad")
    body = await response.json()

    assert response.status == 400
    assert body["error"] == "EmptyDownloadError"
    assert body["message"] == "No price history returned for ticker 'BAD'."