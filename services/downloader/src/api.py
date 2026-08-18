# services/downloader/src/api.py

from __future__ import annotations

from aiohttp import web
import pandas as pd

from .exceptions import DownloaderClientError
from .service import DownloaderService


async def health(request: web.Request) -> web.Response:
    """
    health handler
    """
    return web.json_response({"status": "ok"})

async def get_metadata(request: web.Request) -> web.Response:
    """
    metadata handler

    Raises:
        DownloaderClientError: If service is unable to get metadata for the requested ticker
    """
    ticker = request.match_info["ticker"]

    try:
        metadata = request.app["service"].get_metadata(ticker)
        return web.json_response(metadata)
    
    except DownloaderClientError as exc:
        return web.json_response({"error": type(exc).__name__, "message": str(exc), }, status=400, )

def parse_bool(value: str) -> bool:
    """
    helper function to parse string booleans properly

    Args:
        value (str): the string to be evaluated into a boolean
    
    Returns:
        bool: The parsed value as a boolean
    
    Raises:
        ValueError: is the value to be parsed is not expected
    """
    normalized = value.strip().lower()

    if normalized in ['true', '1', 'on', 'yes']:
        return True
    if normalized in ['false', '0', 'off', 'no']:
        return False
    raise ValueError(f'Invalid boolean value {value}')

async def get_price_history(request: web.Request) -> web.Response:
    """
    price history handler

    Raises:
        ValueError: If auto_adjust is not an expected value to be parsed as boolean
        DownloaderClientError: If service is unable to get the ticker price history
    """
    ticker = request.match_info["ticker"]

    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1d")
    auto_adjust_value = request.query.get("autoadjust", "true")
    aggregate_value = request.query.get("aggregate", "true")

    try:
        auto_adjust = parse_bool(auto_adjust_value)
        aggregate = parse_bool(aggregate_value)
    except ValueError as exc:
        return web.json_response({"error": type(exc).__name__, "message": str(exc), }, status=400, )

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

async def get_dividends(
    request: web.Request,
) -> web.Response:
    """
    dividend history handler

    Raises:
        DownloaderClientError:
            If service is unable to get dividend history.

        ValueError:
            If the requested period is unsupported.
    """
    ticker = request.match_info["ticker"]

    period = request.query.get(
        "period",
        "10y",
    )

    try:
        dividends = (
            request.app["service"].get_dividends(
                ticker=ticker,
                period=period,
            )
        )

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

        return web.json_response(
            {
                "ticker": ticker.upper(),
                "period": period,
                "rows": len(dividends),
                "data": records,
            }
        )

    except (
        DownloaderClientError,
        ValueError,
    ) as exc:
        return web.json_response(
            {
                "error": type(exc).__name__,
                "message": str(exc),
            },
            status=400,
        )

def create_app(service_override: DownloaderService | None = None) -> web.Application:
    """
    starting an application for history and metadata
    """
    app = web.Application()
    app["service"] = service_override or DownloaderService()

    app.router.add_get("/health", health)
    app.router.add_get("/history/{ticker}", get_price_history)
    app.router.add_get("/metadata/{ticker}", get_metadata)
    app.router.add_get("/dividends/{ticker}", get_dividends)

    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)