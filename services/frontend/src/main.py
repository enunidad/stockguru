from __future__ import annotations

import asyncio
import json

from .client import DownloaderApiClient
from .schemas import PriceHistoryRequest


async def main() -> None:
    client = DownloaderApiClient(
        base_url="http://localhost:8080",
    )

    request = PriceHistoryRequest(
        ticker="AAPL",
    )

    response = await client.get_price_history(request)

    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    asyncio.run(main())