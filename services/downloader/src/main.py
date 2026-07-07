from .client import PriceHistoryRequest, YahooFinanceClient


def main() -> None:
    client = YahooFinanceClient()

    request = PriceHistoryRequest(
        ticker="AAPL",
        period="1mo",
    )

    data = client.download_price_history(request)

    print(data.tail())


if __name__ == "__main__":
    main()