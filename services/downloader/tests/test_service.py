import pandas as pd

from src.schemas import PriceHistoryRequest
from src.service import DownloaderService

class FakeCache:
    def __init__(self):
        self.saved_request = None
        self.saved_data = None

    def get_if_fresh(self, request):
        return None

    def save(self, request, data):
        self.saved_request = request
        self.saved_data = data

class FakeYahooFinanceClient:
    def __init__(self):
        self.received_request = None
        self.response = pd.DataFrame(
            {
                "Close": [100.0, 101.0],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )

    def download_price_history(self, request: PriceHistoryRequest) -> pd.DataFrame:
        self.received_request = request
        return self.response


def test_get_price_history_builds_request_and_calls_client():
    fake_client = FakeYahooFinanceClient()
    fake_cache = FakeCache()
    service = DownloaderService(client=fake_client, cache=fake_cache)

    result = service.get_price_history(
        ticker="AAPL",
        period="5y",
        interval="1wk",
        auto_adjust=True,
    )

    expected_request = PriceHistoryRequest(
        ticker="AAPL",
        period="5y",
        interval="1wk",
        auto_adjust=True,
    )

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
        auto_adjust=False,
    )