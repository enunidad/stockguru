import pandas as pd
import pytest

from src.api import create_app, parse_bool
from src.exceptions import EmptyDownloadError


class FakeDownloaderService:
    def get_price_history(
        self,
        ticker: str,
        period: str,
        interval: str,
        auto_adjust: bool,
    ) -> pd.DataFrame:
        data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "Close": [110.0, 111.0],
            },
            index=pd.to_datetime(
                [
                    "2024-01-01 00:00:00-05:00",
                    "2024-01-02 00:00:00-05:00",
                ],
            ),
        )

        data.index.name = "Date"
        return data

    def get_metadata(self, ticker: str) -> dict:
        return {
            "ticker": ticker.upper(),
            "currency": "USD",
            "exchange": "NMS",
            "timezone": "America/New_York",
            "quote_type": "EQUITY",
            "raw": {},
        }


class FailingDownloaderService:
    def get_price_history(
        self,
        ticker: str,
        period: str = "10y",
        interval: str = "1mo",
        auto_adjust: bool = False,
    ) -> pd.DataFrame:
        raise EmptyDownloadError("No price history returned for ticker 'BAD'.")


@pytest.mark.asyncio
async def test_get_price_history_formats_dates_without_time(
    aiohttp_client,
):
    app = create_app(
        service_override=FakeDownloaderService()
    )
    client = await aiohttp_client(app)

    response = await client.get("/history/aapl")
    body = await response.json()

    assert response.status == 200

    assert body["data"][0]["Date"] == "2024-01-01"
    assert body["data"][1]["Date"] == "2024-01-02"

    assert " " not in body["data"][0]["Date"]
    assert "T" not in body["data"][0]["Date"]
    assert "-05:00" not in body["data"][0]["Date"]

@pytest.mark.asyncio
async def test_health_endpoint(aiohttp_client):
    app = create_app(service_override=FakeDownloaderService())
    client = await aiohttp_client(app)

    response = await client.get("/health")
    body = await response.json()

    assert response.status == 200
    assert body == {"status": "ok"}

@pytest.mark.asyncio
async def test_get_metadata_returns_json(
    aiohttp_client,
):
    app = create_app(
        service_override=FakeDownloaderService()
    )
    client = await aiohttp_client(app)

    response = await client.get("/metadata/aapl")
    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "currency": "USD",
        "exchange": "NMS",
        "timezone": "America/New_York",
        "quote_type": "EQUITY",
        "raw": {},
    }

@pytest.mark.asyncio
async def test_get_price_history_returns_json(aiohttp_client):
    app = create_app(
        service_override=FakeDownloaderService()
    )
    client = await aiohttp_client(app)

    response = await client.get(
        "/history/aapl"
        "?period=5y"
        "&interval=1mo"
        "&autoadjust=false"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1mo",
        "rows": 2,
        "data": [
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
        ],
    }

@pytest.mark.asyncio
async def test_get_price_history_rejects_invalid_auto_adjust(
    aiohttp_client,
):
    app = create_app(
        service_override=FakeDownloaderService()
    )
    client = await aiohttp_client(app)

    response = await client.get(
        "/history/AAPL?autoadjust=banana"
    )

    body = await response.json()

    assert response.status == 400
    assert body["error"] == "ValueError"
    assert "banana" in body["message"]


@pytest.mark.asyncio
async def test_get_price_history_returns_400_for_downloader_errors(aiohttp_client):
    app = create_app(service_override=FailingDownloaderService())
    client = await aiohttp_client(app)

    response = await client.get("/history/bad")
    body = await response.json()

    assert response.status == 400
    assert body["error"] == "EmptyDownloadError"
    assert body["message"] == "No price history returned for ticker 'BAD'."

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("YES", True),
        ("on", True),

        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("NO", False),
        ("off", False),

        (" true ", True),
        (" false ", False),
    ],
)
def test_parse_bool_valid_values(
    value: str,
    expected: bool,
) -> None:
    assert parse_bool(value) is expected

@pytest.mark.parametrize(
    "value",
    [
        "",
        "banana",
        "2",
        "y",
        "n",
        "t",
        "f",
        "maybe",
        "null",
    ],
)
def test_parse_bool_invalid_values(
    value: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Invalid boolean",
    ):
        parse_bool(value)