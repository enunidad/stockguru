# services/downloader/src/api.py

from __future__ import annotations

from aiohttp import web
import pandas as pd

from .exceptions import DownloaderClientError
from .service import DownloaderService


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "code": "200"})

async def get_metadata(request: web.Request) -> web.Response:
    ticker = request.match_info["ticker"]
    try:
        metadata = request.app["service"].get_metadata(ticker)
        return web.json_response(metadata)
    
    except DownloaderClientError as exc:
        return web.json_response({"error": type(exc).__name__, "message": str(exc), }, status=400, )


async def get_price_history(request: web.Request) -> web.Response:
    ticker = request.match_info["ticker"]
    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1d")
    auto_adjust = request.query.get("autoadjust", "true")
    aggregate = request.query.get("aggregate", "true")

    try:
        data = request.app["service"].get_price_history(
            ticker=ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            aggregate=aggregate,
        )

        records = data.reset_index()

        records["Date"] = pd.to_datetime(records["Date"], utc=True).dt.strftime("%Y-%m-%d")

        return web.json_response(
            {
                "ticker": ticker.upper(),
                "period": period,
                "interval": interval,
                "rows": len(data),
                "data": records.to_dict(orient="records"),
            }
        )

    except (DownloaderClientError, ValueError) as exc:
        return web.json_response({"error": type(exc).__name__, "message": str(exc), }, status=400, )

async def get_dividends(request: web.Request, ) -> web.Response:
    ticker = request.match_info["ticker"]

    period = request.query.get("period", "10y", )

    try:
        dividends = (request.app["service"].get_dividends(ticker=ticker, period=period, ))

        records = [
            {
                "Date": pd.to_datetime(
                    date,
                    utc=True,
                ).strftime("%Y-%m-%d"),
                "Dividend": float(amount),
            }
            for date, amount in dividends.items()
        ]

        return web.json_response({"ticker": ticker.upper(), "period": period, 
                                    "rows": len(dividends), "data": records, })

    except (DownloaderClientError, ValueError, ) as exc:
        return web.json_response({"error": type(exc).__name__, "message": str(exc), }, status=400, )

def create_app(service: DownloaderService | None = None) -> web.Application:
    app = web.Application()
    app["service"] = service or DownloaderService()

    app.router.add_get("/health", health)
    app.router.add_get("/history/{ticker}", get_price_history)
    app.router.add_get("/metadata/{ticker}", get_metadata)
    app.router.add_get("/dividends/{ticker}", get_dividends)

    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)