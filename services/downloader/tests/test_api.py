import pandas as pd
import pytest

from src.api import create_app, parse_bool
from src.exceptions import EmptyDownloadError

class InvalidPeriodDownloaderService:
    def get_price_history(
        self,
        ticker: str,
        period: str,
        interval: str,
        auto_adjust: bool,
        aggregate: bool,
    ):
        raise ValueError(
            f"Unsupported period '{period}'."
        )

class FakeDownloaderService:
    def get_price_history(
        self,
        ticker: str,
        period: str,
        interval: str,
        auto_adjust: bool,
        aggregate: bool,
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
        aggregate: bool = False,
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

@pytest.mark.asyncio
async def test_get_price_history_returns_400_for_invalid_period(
    aiohttp_client,
):
    app = create_app(
        service_override=InvalidPeriodDownloaderService()
    )
    client = await aiohttp_client(app)

    response = await client.get(
        "/history/AAPL?period=banana"
    )
    body = await response.json()

    assert response.status == 400
    assert body == {
        "error": "ValueError",
        "message": "Unsupported period 'banana'.",
    }

# =========================================================
# Dividend API Test Services
# =========================================================


class FakeDividendDownloaderService:
    def __init__(self):
        self.received_ticker = None
        self.received_period = None


    def get_dividends(
        self,
        ticker: str,
        period: str,
    ) -> pd.Series:
        self.received_ticker = ticker
        self.received_period = period

        dividends = pd.Series(
            [
                0.24,
                0.25,
                0.26,
            ],
            index=pd.to_datetime(
                [
                    "2026-02-08 00:00:00-05:00",
                    "2026-05-08 00:00:00-04:00",
                    "2026-08-08 00:00:00-04:00",
                ],
                utc=True,
            ),
            name="Dividends",
            dtype=float,
        )

        dividends.index.name = "Date"

        return dividends


class EmptyDividendDownloaderService:
    def get_dividends(
        self,
        ticker: str,
        period: str,
    ) -> pd.Series:
        dividends = pd.Series(
            dtype=float,
            name="Dividends",
        )

        dividends.index.name = "Date"

        return dividends


class InvalidDividendPeriodService:
    def get_dividends(
        self,
        ticker: str,
        period: str,
    ) -> pd.Series:
        raise ValueError(
            f"Unsupported period '{period}'."
        )


class FailingDividendDownloaderService:
    def get_dividends(
        self,
        ticker: str,
        period: str,
    ) -> pd.Series:
        raise EmptyDownloadError(
            f"No dividend history returned for ticker '{ticker.upper()}'."
        )


# =========================================================
# Dividend Endpoint
# =========================================================


@pytest.mark.asyncio
async def test_get_dividends_returns_json(
    aiohttp_client,
):
    service = FakeDividendDownloaderService()

    app = create_app(
        service_override=service
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/aapl?period=5y"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "period": "5y",
        "rows": 3,
        "data": [
            {
                "Date": "2026-02-08",
                "Dividend": 0.24,
            },
            {
                "Date": "2026-05-08",
                "Dividend": 0.25,
            },
            {
                "Date": "2026-08-08",
                "Dividend": 0.26,
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_dividends_passes_ticker_and_period_to_service(
    aiohttp_client,
):
    service = FakeDividendDownloaderService()

    app = create_app(
        service_override=service
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/msft?period=2y"
    )

    assert response.status == 200

    assert service.received_ticker == "msft"
    assert service.received_period == "2y"


@pytest.mark.asyncio
async def test_get_dividends_uses_default_period(
    aiohttp_client,
):
    service = FakeDividendDownloaderService()

    app = create_app(
        service_override=service
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert service.received_period == "10y"

    assert body["period"] == "10y"


@pytest.mark.asyncio
async def test_get_dividends_formats_dates_without_time(
    aiohttp_client,
):
    app = create_app(
        service_override=FakeDividendDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert body["data"][0]["Date"] == "2026-02-08"

    assert " " not in body["data"][0]["Date"]
    assert "T" not in body["data"][0]["Date"]
    assert "-05:00" not in body["data"][0]["Date"]


@pytest.mark.asyncio
async def test_get_dividends_converts_values_to_float(
    aiohttp_client,
):
    app = create_app(
        service_override=FakeDividendDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert all(
        isinstance(
            record["Dividend"],
            float,
        )
        for record in body["data"]
    )


@pytest.mark.asyncio
async def test_get_dividends_returns_empty_history(
    aiohttp_client,
):
    app = create_app(
        service_override=EmptyDividendDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL"
    )

    body = await response.json()

    assert response.status == 200

    assert body == {
        "ticker": "AAPL",
        "period": "10y",
        "rows": 0,
        "data": [],
    }


@pytest.mark.asyncio
async def test_get_dividends_returns_400_for_invalid_period(
    aiohttp_client,
):
    app = create_app(
        service_override=InvalidDividendPeriodService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/AAPL?period=banana"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "ValueError",
        "message": "Unsupported period 'banana'.",
    }


@pytest.mark.asyncio
async def test_get_dividends_returns_400_for_downloader_error(
    aiohttp_client,
):
    app = create_app(
        service_override=FailingDividendDownloaderService()
    )

    client = await aiohttp_client(app)

    response = await client.get(
        "/dividends/BAD"
    )

    body = await response.json()

    assert response.status == 400

    assert body == {
        "error": "EmptyDownloadError",
        "message": (
            "No dividend history returned "
            "for ticker 'BAD'."
        ),
    }