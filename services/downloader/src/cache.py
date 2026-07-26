from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from typing import Optional
from dataclasses import asdict

import pandas as pd

from .schemas import PriceHistoryRequest, TickerMetadata


class PriceHistoryCache:
    def __init__(self, cache_dir: Path, ttl: timedelta = timedelta(days=1), ) -> None:
        """
        initializes price history cache
        
        Args:
            cache_dir (Path): the path object to the data folder
            ttl (timedelta): used for freshness. if cached and was cached less ttl, just
                                return the cache, otherwise return None.
        
        Returns:
            None
        """
        self.cache_dir = cache_dir
        self.ttl = ttl

    def get_path(self, request: PriceHistoryRequest) -> Path:
        """
        returns path for where the ticker cache goes in the data folder

        Args:
            request (PriceHistoryRequest): The request object. refer to schemas.PriceHistoryRequest
        
        Returns:
            Path: The directory path where the ticker data goes in the data folder
        """
        ticker = request.ticker.strip().upper()
        filename = f"{request.period}_{request.interval}_{str(request.auto_adjust)}.csv"
        return self.cache_dir / ticker / filename

    def exists(self, request: PriceHistoryRequest) -> bool:
        """
        helper to check a path exists
        
        Args:
            request (PriceHistoryRequest): the request object. refer to schemas.PriceHistoryRequest
        
        Returns:
            bool: True if the path already exists
        """
        return self.get_path(request).exists()

    def is_fresh(self, request: PriceHistoryRequest) -> bool:
        """
        checker if the cache is within self.ttl

        Args:
            request (PriceHistoryRequest): The request object. refer to schemas.PriceHistoryRequest
        
        Returns:
            bool: True if the cache is within self.ttl
        """
        path = self.get_path(request)

        if not path.exists():
            return False

        modified_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc, )

        return datetime.now(timezone.utc) - modified_time <= self.ttl

    def load(self, request: PriceHistoryRequest) -> pd.DataFrame:
        """
        loads the cache into the expected format

        Args:
            request (PriceHistoryRequest): The request object. refer to schemas.PriceHistoryRequest
        
        Returns:
            pd.DataFrame: stored cache as a dataframe
        """
        path = self.get_path(request)

        data = pd.read_csv(path, parse_dates=["Date"])
        data = data.set_index("Date")
        data.index.name = "Date"

        return data

    def save(self, request: PriceHistoryRequest, data: pd.DataFrame, ) -> Path:
        """
        saves requested dataframe into cache as a csv

        Args:
            request (PriceHistoryRequest): The request object. refer to schemas.PriceHistoryRequest
            data (pd.Dataframe): The data to be stored
        
        Returns:
            Path: The path where the data is stored
        """
        path = self.get_path(request)
        path.parent.mkdir(parents=True, exist_ok=True)

        output = data.copy()

        output.to_csv(path)

        return path

    def get_if_fresh(self, request: PriceHistoryRequest) -> Optional[pd.DataFrame]:
        """
        service calls this. if exist and fresh, return cache, otherwise return None.

        Args:
            request(PriceHistoryRequest): The request object. refer to schemas.PriceHistoryRequest
        
        Returns:
            pd.DataFrame (Optional): if None data requests either does not exist or is not fresh
        """
        if not self.is_fresh(request):
            return None

        return self.load(request)

class TickerMetadataCache:
    def __init__(self, cache_dir: Path, ttl: timedelta = timedelta(days=1), ) -> None:
        """
        initializes metadata cache object

        Args:
            cache_dir (Path): The path object to the data folder
            ttl (timedelta): used for freshness. if cached and was cached less ttl, just
                                return the cache, otherwise return None.
        
        Returns:
            None
        """
        self.cache_dir = cache_dir
        self.ttl = ttl

    def get_path(self, ticker: str) -> Path:
        """
        The path to where the metadata is stored in the data folder

        Args:
            ticker (str): The symbol for the metadata to be stored
        
        Returns:
            Path: The path object to where this ticker metadata is saved
        """
        symbol = ticker.strip().upper()
        return self.cache_dir / symbol / f"{symbol}_metadata.json"

    def is_fresh(self, ticker: str) -> bool:
        """
        Checker if the ticker cache is within self.ttl

        Args:
            ticker (str): The symbol for the ticker to be checked
        
        Returns:
            bool: True if cache exists and is within self.ttl
        """
        path = self.get_path(ticker)

        if not path.exists():
            return False

        modified_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc, )

        return datetime.now(timezone.utc) - modified_time <= self.ttl

    def load(self, ticker: str) -> TickerMetadata:
        """
        loads cached metadata into a TickerMetadata object

        Args:
            ticker (str): The symbol for the metadata to be loaded
        
        Returns:
            TickerMetadata: The metadata object. refer to schemas.TickerMetadata
        """
        path = self.get_path(ticker)

        with path.open("r", encoding="utf-8", ) as file:
            payload = json.load(file)

        return TickerMetadata(**payload)

    def save(self, metadata: TickerMetadata, ) -> Path:
        """
        Saves the metadata object into cache

        Args:
            metadata (TickerMetadata): The metadata object. refer to schemas.TickerMetadata
        
        Returns:
            Path: The path object where the metadata is stored in the data folder
        """
        path = self.get_path(metadata.ticker)
        path.parent.mkdir(parents=True, exist_ok=True, )

        with path.open("w", encoding="utf-8", ) as file:
            json.dump(asdict(metadata), file, indent=2, sort_keys=True, )

        return path

    def get_if_fresh(self, ticker: str, ) -> Optional[TickerMetadata]:
        """
        This is the function service calls.

        Args:
            ticker (str): the symbol for the requested metadata
        
        Returns:
            TickerMetadata (Optional): if ticker exists and is fresh, returns the cache.
                                        Otherwise return None.
        """
        if not self.is_fresh(ticker):
            return None

        return self.load(ticker)