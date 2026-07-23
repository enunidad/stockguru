from aiohttp import web

from src.api import create_app
from src.service import DownloaderService

def three() -> None:
    svc = DownloaderService()
    ans = svc.get_metadata(ticker = 'AAPL')
    print(ans)

def two() -> None:
    svc = DownloaderService()
    ans = svc.get_price_history(
        ticker='AAPL',
        period = "10y",
        interval= "1mo",
        auto_adjust= True)
    print(ans)



def main() -> None:
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    three()
    two()
    main()