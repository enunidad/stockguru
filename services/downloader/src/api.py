# services/downloader/src/api.py

from __future__ import annotations

from aiohttp import web

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


async def get_price_history(request: web.Request) -> web.Response:
    ticker = request.match_info["ticker"]

    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1mo")
    auto_adjust = request.query.get("autoadjust", True)
    if isinstance(auto_adjust, (int, float)):
        if auto_adjust in [0, 0.0]:
            auto_adjust = False
    elif isinstance(auto_adjust, str):
        if auto_adjust.lower() == 'false':
            auto_adjust = False
    else:
        auto_adjust = True

    try:
        data = request.app["service"].get_price_history(
            ticker=ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust
        )

        records = data.reset_index()
        records["Date"] = records["Date"].astype(str)

        return web.json_response(
            {
                "ticker": ticker.upper(),
                "period": period,
                "interval": interval,
                "rows": len(data),
                "data": records.to_dict(orient="records"),
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