from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from schemas import PriceHistoryRequest


class PriceHistoryCache:
    def __init__(
        self,
        cache_dir: Path,
        ttl: timedelta = timedelta(days=1),
    ) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl

    def get_path(self, request: PriceHistoryRequest) -> Path:
        ticker = request.ticker.strip().upper()
        filename = f"{ticker}_{request.period}_{request.interval}.csv"
        return self.cache_dir / filename

    def exists(self, request: PriceHistoryRequest) -> bool:
        return self.get_path(request).exists()

    def is_fresh(self, request: PriceHistoryRequest) -> bool:
        path = self.get_path(request)

        if not path.exists():
            return False

        modified_time = datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        )

        return datetime.now(timezone.utc) - modified_time <= self.ttl

    def load(self, request: PriceHistoryRequest) -> pd.DataFrame:
        path = self.get_path(request)

        data = pd.read_csv(path, parse_dates=["Date"])
        data = data.set_index("Date")
        data.index.name = "Date"

        return data

    def save(
        self,
        request: PriceHistoryRequest,
        data: pd.DataFrame,
    ) -> Path:
        path = self.get_path(request)
        path.parent.mkdir(parents=True, exist_ok=True)

        output = data.copy()

        if output.index.name != "Date":
            output.index.name = "Date"

        output.to_csv(path)

        return path

    def get_if_fresh(self, request: PriceHistoryRequest) -> pd.DataFrame | None:
        if not self.is_fresh(request):
            return None

        return self.load(request)