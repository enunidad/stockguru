from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from typing import Optional, Any
from dataclasses import asdict

import pandas as pd

from .schemas import PriceHistoryRequest, TickerMetadata
from .exceptions import CacheSaveError, CacheLoadError

class DownloaderCache:
    def __init__(self, cache_dir: Path, ttl: timedelta=timedelta(days=1), ) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl

    def get_path(self, request: PriceHistoryRequest, kind: str|None = None) -> Path:
        ticker = request.ticker.ticker
        if kind is None:
            filename = f"{request.period}_{request.interval}_{str(request.auto_adjust)}.csv"
        else:
            filename = f"{ticker}_{kind}.csv"
        return self.cache_dir / ticker / filename
    
    def _save(self, request, data, kind=None):
        path = self.get_path(request, kind)
        path.parent.mkdir(parents=True, exist_ok=True)

        if kind is None:
            if isinstance(data, pd.DataFrame):
                data.to_csv(path)
            else:
                raise CacheSaveError("price_history object must be pandas.DataFrame.")
        elif kind == "metadata":
            if isinstance(data, TickerMetadata):
                with path.open("w", encoding="utf-8", ) as file:
                    json.dump(asdict(data), file, indent=2, sort_keys=True, )
            else:
                raise CacheSaveError("metadata object must be of class TickerMetadata")
        elif kind == "dividends":
            if isinstance(data, pd.Series):
                output = data.copy()
                output.index.name = "Date"
                output.name = "Dividends"
                output.to_csv(path, header=True, )
            else:
                raise CacheSaveError("dividends object must be pandas.Series.")
        else:
            raise CacheSaveError(f"{kind} saving logic undefined")

    def save(self, request: PriceHistoryRequest, data: dict[str, Any]) -> None:
        expected = {"price_history", "metadata", "dividends"}
        unexpected = set(data) - expected
        if unexpected:
            raise CacheSaveError(f"Unexpected object to save: {unexpected}")
        
        missing = expected - set(data)
        if missing:
            raise CacheSaveError(f"Missing objects to save: {missing}")
        for kind, entry in data.items():
            self._save(request, entry, None if kind == "price_history" else kind)
    
    def load(self, request: PriceHistoryRequest, kind: str|None = None) -> Any:
        path = self.get_path(request, kind)
        if not path.exists():
            raise CacheLoadError(f"Path {str(path)} does not exist")
        if kind is None:
            data = pd.read_csv(path)
            data["Date"] = pd.to_datetime(data["Date"], errors="raise", utc=True,)

            data = data.set_index("Date")
            data.index.name = "Date"

            return data
        elif kind == "metadata":
            with path.open("r", encoding="utf-8", ) as file:
                payload = json.load(file)

            return TickerMetadata(**payload)
        elif kind == "dividends":
            data = pd.read_csv(path, parse_dates=["Date"], )

            if data.empty:
                dividends = pd.Series(dtype=float, name="Dividends", )
                dividends.index.name = "Date"
                return dividends

            data["Date"] = pd.to_datetime(data["Date"], errors="raise", utc=True, )
            data = data.set_index("Date")
            dividends = data["Dividends"]
            dividends.index.name = "Date"
            dividends.name = "Dividends"

            return dividends
        else:
            raise CacheLoadError(f"No data to load for {kind}.")

    def get_if_fresh(self, request: PriceHistoryRequest, kind:str|None = None) -> Optional[Any]:
        if self.is_fresh(request, kind):
            return self.load(request, kind)
        return None
    
    def is_fresh(self, request: PriceHistoryRequest, kind: str|None = None) -> bool:
        path = self.get_path(request, kind)
        if not path.exists():
            return False
        modified_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc, )
        return datetime.now(timezone.utc) - modified_time <= self.ttl