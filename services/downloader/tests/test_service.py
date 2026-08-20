import pytest
import pandas as pd

from src.schemas import PriceHistoryRequest, TickerMetadata
from src.service import DownloaderService
from dataclasses import asdict

class FakeCache:
    def __init__(self):
        self.saved_request = None
        self.saved_data = None

    def get_if_fresh(self, request):
        return None

    def save(self, request, data):
        self.saved_request = request
        self.saved_data = data

class FakeMetadata:
    def __init__(self):
        self.saved_data = None

    def get_if_fresh(self, request):
        return None

    def save(self, data):
        self.saved_data = data

class FakeYahooFinanceClient:
    def __init__(self):
        self.received_request = None
        self.response = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-01-02", ],
                "Open": [100.0, 101.0, ],
                "High": [112.0, 113.0, ],
                "Low": [98.0, 99.0, ],
                "Close": [110.0, 111.0, ],
                "Volume": [1_000, 1_200, ],
            },
        )
        self.response["Date"] = pd.to_datetime(self.response["Date"], errors="raise", utc=True, )
        self.response = self.response.set_index("Date")
        self.response.index.name = "Date"
        self.recieved_metadata_request = None
        self.metadata = TickerMetadata(ticker = 'AAPL')

    def download_price_history(self, request: PriceHistoryRequest) -> pd.DataFrame:
        self.received_request = request
        return self.response
    
    def download_metadata(self, request: str) -> dict:
        self.received_metadata_request = request
        return self.metadata


def test_get_price_history_builds_request_and_calls_client():
    fake_client = FakeYahooFinanceClient()
    fake_cache = FakeCache()
    fake_metadata = FakeMetadata()
    service = DownloaderService(client=fake_client, cache=fake_cache, metadata=fake_metadata)

    result = service.get_price_history(
        ticker="AAPL",
        period="10y",
        interval="1d",
        auto_adjust=True,
        aggregate=False,
    )

    expected_request = PriceHistoryRequest(
        ticker="AAPL",
        period="10y",
        interval="1d",
        auto_adjust=True,
        aggregate=False,
    )

    print(fake_client.received_request)
    print(expected_request)
    assert fake_client.received_request == expected_request
    assert fake_cache.saved_request == expected_request
    pd.testing.assert_frame_equal(fake_cache.saved_data, fake_client.response)
    pd.testing.assert_frame_equal(result, fake_client.response)


def test_get_price_history_uses_default_request_values():
    fake_client = FakeYahooFinanceClient()
    fake_cache = FakeCache()
    service = DownloaderService(client=fake_client, cache=fake_cache)

    service.get_price_history(ticker="MSFT")

    assert fake_client.received_request == PriceHistoryRequest(
        ticker="MSFT",
        period="10y",
        interval="1d",
        auto_adjust=True,
    )

def test_get_metadata_builds_request_and_calls_client():
    fake_client = FakeYahooFinanceClient()
    fake_cache = FakeCache()
    fake_metadata = FakeMetadata()
    service = DownloaderService(client=fake_client, cache=fake_cache, metadata=fake_metadata)

    result = service.get_metadata(ticker='AAPL')

    expected_result = asdict(TickerMetadata(ticker="AAPL"))

    assert fake_client.received_metadata_request.ticker == 'AAPL'
    assert result == expected_result

def test_filter_period_returns_requested_years():
    dates = pd.to_datetime(
        [
            "2020-01-01",
            "2021-01-01",
            "2022-01-01",
            "2023-01-01",
            "2024-01-01",
            "2025-01-01",
            "2026-01-01",
        ],
        utc=True,
    )

    data = pd.DataFrame(
        {
            "Close": [
                100.0,
                110.0,
                120.0,
                130.0,
                140.0,
                150.0,
                160.0,
            ]
        },
        index=dates,
    )

    result = DownloaderService._filter_period(
        data,
        "5y",
    )

    assert result.index.min() == pd.Timestamp(
        "2021-01-01",
        tz="UTC",
    )
    assert result.index.max() == pd.Timestamp(
        "2026-01-01",
        tz="UTC",
    )

def test_filter_period_10y_returns_full_data():
    data = pd.DataFrame(
        {"Close": [100.0, 200.0]},
        index=pd.to_datetime(
            [
                "2016-01-01",
                "2026-01-01",
            ],
            utc=True,
        ),
    )

    result = DownloaderService._filter_period(
        data,
        "10y",
    )

    pd.testing.assert_frame_equal(
        result,
        data,
    )

def test_filter_period_rejects_unsupported_period():
    data = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.to_datetime(
            ["2026-01-01"],
            utc=True,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported period",
    ):
        DownloaderService._filter_period(
            data,
            "banana",
        )

# =========================================================
# Dividend Test Helpers
# =========================================================


def make_dividend_history() -> pd.Series:
    dividends = pd.Series(
        [
            0.20,
            0.22,
            0.24,
            0.25,
            0.26,
            0.27,
        ],
        index=pd.to_datetime(
            [
                "2020-08-01",
                "2022-08-01",
                "2023-08-01",
                "2024-08-01",
                "2025-08-01",
                "2026-08-01",
            ],
            utc=True,
        ),
        name="Dividends",
        dtype=float,
    )

    dividends.index.name = "Date"

    return dividends


class FakeDividendCache:
    def __init__(
        self,
        cached_data=None,
    ):
        self.cached_data = cached_data
        self.requested_ticker = None
        self.saved_ticker = None
        self.saved_data = None


    def get_if_fresh(
        self,
        ticker,
    ):
        self.requested_ticker = ticker

        return self.cached_data


    def save(
        self,
        ticker,
        dividends,
    ):
        self.saved_ticker = ticker
        self.saved_data = dividends


class FakeDividendClient:
    def __init__(
        self,
        dividends=None,
    ):
        self.dividends = (
            dividends
            if dividends is not None
            else make_dividend_history()
        )

        self.received_ticker = None


    def download_dividends(
        self,
        ticker,
    ):
        self.received_ticker = ticker

        return self.dividends


# =========================================================
# Dividend Period Filtering
# =========================================================


def test_filter_dividend_period_returns_requested_years():
    dividends = make_dividend_history()

    result = DownloaderService._filter_dividend_period(
        dividends,
        "2y",
    )

    assert list(result.index) == [
        pd.Timestamp(
            "2024-08-01",
            tz="UTC",
        ),
        pd.Timestamp(
            "2025-08-01",
            tz="UTC",
        ),
        pd.Timestamp(
            "2026-08-01",
            tz="UTC",
        ),
    ]


def test_filter_dividend_period_includes_cutoff_date():
    dividends = pd.Series(
        [
            0.25,
            0.26,
        ],
        index=pd.to_datetime(
            [
                "2025-08-01",
                "2026-08-01",
            ],
            utc=True,
        ),
        name="Dividends",
    )

    result = DownloaderService._filter_dividend_period(
        dividends,
        "1y",
    )

    assert len(result) == 2

    assert result.index.min() == pd.Timestamp(
        "2025-08-01",
        tz="UTC",
    )


@pytest.mark.parametrize(
    (
        "period",
        "expected_start",
    ),
    [
        (
            "1y",
            "2025-08-01",
        ),
        (
            "2y",
            "2024-08-01",
        ),
        (
            "5y",
            "2022-08-01",
        ),
        (
            "10y",
            "2020-08-01",
        ),
    ],
)
def test_filter_dividend_period_supports_expected_periods(
    period,
    expected_start,
):
    dividends = make_dividend_history()

    result = DownloaderService._filter_dividend_period(
        dividends,
        period,
    )

    assert result.index.min() == pd.Timestamp(
        expected_start,
        tz="UTC",
    )


def test_filter_dividend_period_returns_empty_series_unchanged():
    dividends = pd.Series(
        dtype=float,
        name="Dividends",
    )

    result = DownloaderService._filter_dividend_period(
        dividends,
        "1y",
    )

    assert result is dividends
    assert result.empty


def test_filter_dividend_period_rejects_unsupported_period():
    dividends = make_dividend_history()

    with pytest.raises(
        ValueError,
        match="Unsupported period",
    ):
        DownloaderService._filter_dividend_period(
            dividends,
            "banana",
        )


# =========================================================
# DownloaderService.get_dividends
# =========================================================


def test_get_dividends_uses_fresh_cache():
    dividends = make_dividend_history()

    fake_client = FakeDividendClient()

    fake_dividend_cache = FakeDividendCache(
        cached_data=dividends,
    )

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    result = service.get_dividends(
        ticker="AAPL",
        period="10y",
    )

    assert (
        fake_dividend_cache.requested_ticker
        == "AAPL"
    )

    assert fake_client.received_ticker is None

    assert fake_dividend_cache.saved_data is None

    pd.testing.assert_series_equal(
        result,
        dividends,
    )


def test_get_dividends_normalizes_ticker_before_cache_lookup():
    dividends = make_dividend_history()

    fake_client = FakeDividendClient()

    fake_dividend_cache = FakeDividendCache(
        cached_data=dividends,
    )

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    service.get_dividends(
        ticker="  aapl  ",
    )

    assert (
        fake_dividend_cache.requested_ticker
        == "AAPL"
    )


def test_get_dividends_downloads_when_cache_missing():
    dividends = make_dividend_history()

    fake_client = FakeDividendClient(
        dividends=dividends,
    )

    fake_dividend_cache = FakeDividendCache(
        cached_data=None,
    )

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    result = service.get_dividends(
        ticker=" aapl ",
        period="10y",
    )

    assert fake_client.received_ticker == "AAPL"

    pd.testing.assert_series_equal(
        result,
        dividends,
    )


def test_get_dividends_saves_downloaded_data_to_cache():
    dividends = make_dividend_history()

    fake_client = FakeDividendClient(
        dividends=dividends,
    )

    fake_dividend_cache = FakeDividendCache()

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    service.get_dividends(
        ticker="msft",
    )

    assert (
        fake_dividend_cache.saved_ticker
        == "MSFT"
    )

    pd.testing.assert_series_equal(
        fake_dividend_cache.saved_data,
        dividends,
    )


def test_get_dividends_filters_cached_history_to_requested_period():
    dividends = make_dividend_history()

    fake_client = FakeDividendClient()

    fake_dividend_cache = FakeDividendCache(
        cached_data=dividends,
    )

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    result = service.get_dividends(
        ticker="AAPL",
        period="1y",
    )

    assert list(result.index) == [
        pd.Timestamp(
            "2025-08-01",
            tz="UTC",
        ),
        pd.Timestamp(
            "2026-08-01",
            tz="UTC",
        ),
    ]


def test_get_dividends_filters_downloaded_history_to_requested_period():
    dividends = make_dividend_history()

    fake_client = FakeDividendClient(
        dividends=dividends,
    )

    fake_dividend_cache = FakeDividendCache()

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    result = service.get_dividends(
        ticker="AAPL",
        period="2y",
    )

    assert list(result.index) == [
        pd.Timestamp(
            "2024-08-01",
            tz="UTC",
        ),
        pd.Timestamp(
            "2025-08-01",
            tz="UTC",
        ),
        pd.Timestamp(
            "2026-08-01",
            tz="UTC",
        ),
    ]


def test_get_dividends_handles_empty_download():
    dividends = pd.Series(
        dtype=float,
        name="Dividends",
    )

    fake_client = FakeDividendClient(
        dividends=dividends,
    )

    fake_dividend_cache = FakeDividendCache()

    service = DownloaderService(
        client=fake_client,
        dividend=fake_dividend_cache,
    )

    result = service.get_dividends(
        ticker="AAPL",
        period="10y",
    )

    assert result.empty

    pd.testing.assert_series_equal(
        fake_dividend_cache.saved_data,
        dividends,
    )


def test_get_dividends_rejects_unsupported_period():
    fake_dividend_cache = FakeDividendCache(
        cached_data=make_dividend_history(),
    )

    service = DownloaderService(
        client=FakeDividendClient(),
        dividend=fake_dividend_cache,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported period",
    ):
        service.get_dividends(
            ticker="AAPL",
            period="3y",
        )