# services/downloader/src/main.py

from .service import DownloaderService


def main() -> None:
    service = DownloaderService()

    data = service.get_price_history(
        ticker="AAPL",
        period="1mo",
    )

    print(data.tail())


if __name__ == "__main__":
    main()