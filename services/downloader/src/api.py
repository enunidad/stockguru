# services/downloader/src/api.py

from __future__ import annotations

from aiohttp import web
import pandas as pd

from .exceptions import DownloaderClientError
from .service import DownloaderService


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

async def get_metadata(request: web.Request) -> web.Response:
    ticker = request.match_info["ticker"]

    try:
        metadata = request.app["service"].get_metadata(ticker)
        return web.json_response(metadata)
    
    except DownloaderClientError as exc:
        return web.json_response(
            {
                "error": type(exc).__name__,
                "message": str(exc),
            },
            status=400,
        )

def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized in ['true', '1', 'on', 'yes']:
        return True
    if normalized in ['false', '0', 'off', 'no']:
        return False
    raise ValueError(f'Invalid boolean value {value}')

async def get_price_history(request: web.Request) -> web.Response:
    ticker = request.match_info["ticker"]

    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1mo")
    auto_adjust = request.query.get("autoadjust", "True")

    try:
        auto_adjust = parse_bool(auto_adjust)
    except ValueError as exc:
        return web.json_response(
            {
                "error": type(exc).__name__,
                "message": str(exc),
            },
            status=400,
        )

    try:
        data = request.app["service"].get_price_history(
            ticker=ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust
        )

        records = data.reset_index()

        records["Date"] = pd.to_datetime(records["Date"], utc=True).dt.strftime("%Y-%m-%d")

        return web.json_response(
            {
                "ticker": ticker.upper(),
                "period": period,
                "interval": interval,
                "rows": len(data),
                "data": data.to_dict(orient="records"),
            }
        )

    except DownloaderClientError as exc:
        return web.json_response(
            {
                "error": type(exc).__name__,
                "message": str(exc),
            },
            status=400,
        )


def create_app(service_override: DownloaderService | None = None) -> web.Application:
    app = web.Application()
    app["service"] = service_override or DownloaderService()

    app.router.add_get("/health", health)
    app.router.add_get("/history/{ticker}", get_price_history)
    app.router.add_get("/metadata/{ticker}", get_metadata)

    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)