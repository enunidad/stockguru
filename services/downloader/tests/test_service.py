import pandas as pd

from src.schemas import PriceHistoryRequest
from src.service import DownloaderService


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
    service = DownloaderService(client=fake_client)

    result = service.get_price_history(
        ticker="AAPL",
        period="5y",
        interval="1wk",
        auto_adjust=True,
    )

    assert fake_client.received_request == PriceHistoryRequest(
        ticker="AAPL",
        period="5y",
        interval="1wk",
        auto_adjust=True,
    )
    pd.testing.assert_frame_equal(result, fake_client.response)


def test_get_price_history_uses_default_request_values():
    fake_client = FakeYahooFinanceClient()
    service = DownloaderService(client=fake_client)

    service.get_price_history(ticker="MSFT")

    assert fake_client.received_request == PriceHistoryRequest(
        ticker="MSFT",
        period="10y",
        interval="1d",
        auto_adjust=False,
    )