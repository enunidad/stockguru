# services/downloader/tests/test_cache.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

import pandas as pd
import pytest
import yfinance as yf

from src.cache import DownloaderCache
from src.schemas import PriceHistoryRequest, TickerMetadata
from src.exceptions import CacheSaveError, CacheLoadError


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def cache(tmp_path):
    return DownloaderCache(
        cache_dir=tmp_path,
        ttl=timedelta(days=1),
    )


@pytest.fixture
def ticker():
    return yf.Ticker("AAPL")


@pytest.fixture
def price_request(ticker):
    return PriceHistoryRequest(
        ticker=ticker,
        period="10y",
        interval="1d",
        auto_adjust=True,
        aggregate=True,
    )


@pytest.fixture
def price_history():
    data = pd.DataFrame(
        {
            "Open": [100.0, 105.0],
            "High": [110.0, 115.0],
            "Low": [95.0, 100.0],
            "Close": [108.0, 112.0],
            "Volume": [1000, 1200],
        },
        index=pd.to_datetime(
            ["2026-01-01", "2026-01-02"],
            utc=True,
        ),
    )

    data.index.name = "Date"

    return data


@pytest.fixture
def metadata():
    return TickerMetadata(
        ticker="AAPL",
        currency="USD",
        exchange="NMS",
        timezone="America/New_York",
        quote_type="EQUITY",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        country="United States",
        raw={
            "fast_info": {
                "currency": "USD",
            },
            "info": {
                "longName": "Apple Inc.",
            },
        },
    )


@pytest.fixture
def dividends():
    data = pd.Series(
        [0.25, 0.25],
        index=pd.to_datetime(
            ["2026-01-01", "2026-04-01"],
            utc=True,
        ),
        name="Dividends",
    )

    data.index.name = "Date"

    return data


@pytest.fixture
def complete_payload(
    price_history,
    metadata,
    dividends,
):
    return {
        "price_history": price_history,
        "metadata": metadata,
        "dividends": dividends,
    }


# ---------------------------------------------------------------------
# get_path
# ---------------------------------------------------------------------


def test_get_path_for_price_history(
    cache,
    price_request,
    tmp_path,
):
    result = cache.get_path(price_request)

    assert result == (
        tmp_path
        / "AAPL"
        / "10y_1d_True.csv"
    )


def test_get_path_for_metadata(
    cache,
    price_request,
    tmp_path,
):
    result = cache.get_path(
        price_request,
        "metadata",
    )

    assert result == (
        tmp_path
        / "AAPL"
        / "AAPL_metadata.csv"
    )


def test_get_path_for_dividends(
    cache,
    price_request,
    tmp_path,
):
    result = cache.get_path(
        price_request,
        "dividends",
    )

    assert result == (
        tmp_path
        / "AAPL"
        / "AAPL_dividends.csv"
    )


def test_get_path_reflects_auto_adjust(
    cache,
    ticker,
    tmp_path,
):
    request = PriceHistoryRequest(
        ticker=ticker,
        period="10y",
        interval="1d",
        auto_adjust=False,
    )

    result = cache.get_path(request)

    assert result == (
        tmp_path
        / "AAPL"
        / "10y_1d_False.csv"
    )


# ---------------------------------------------------------------------
# _save
# ---------------------------------------------------------------------


def test_save_price_history_creates_file(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    assert cache.get_path(
        price_request,
    ).exists()


def test_save_price_history_rejects_wrong_type(
    cache,
    price_request,
):
    with pytest.raises(
        CacheSaveError,
        match="price_history object must be pandas.DataFrame",
    ):
        cache._save(
            price_request,
            "not-a-dataframe",
        )


def test_save_metadata_creates_file(
    cache,
    price_request,
    metadata,
):
    cache._save(
        price_request,
        metadata,
        "metadata",
    )

    assert cache.get_path(
        price_request,
        "metadata",
    ).exists()


def test_save_metadata_rejects_wrong_type(
    cache,
    price_request,
):
    with pytest.raises(
        CacheSaveError,
        match="metadata object must be of class TickerMetadata",
    ):
        cache._save(
            price_request,
            {},
            "metadata",
        )


def test_save_dividends_creates_file(
    cache,
    price_request,
    dividends,
):
    cache._save(
        price_request,
        dividends,
        "dividends",
    )

    assert cache.get_path(
        price_request,
        "dividends",
    ).exists()


def test_save_dividends_rejects_wrong_type(
    cache,
    price_request,
):
    with pytest.raises(
        CacheSaveError,
        match="dividends object must be pandas.Series",
    ):
        cache._save(
            price_request,
            [],
            "dividends",
        )


def test_save_unknown_kind_raises(
    cache,
    price_request,
):
    with pytest.raises(
        CacheSaveError,
        match="saving logic undefined",
    ):
        cache._save(
            price_request,
            "something",
            "unknown",
        )


# ---------------------------------------------------------------------
# save
# ---------------------------------------------------------------------


def test_save_creates_all_three_cache_files(
    cache,
    price_request,
    complete_payload,
):
    cache.save(
        price_request,
        complete_payload,
    )

    assert cache.get_path(
        price_request,
    ).exists()

    assert cache.get_path(
        price_request,
        "metadata",
    ).exists()

    assert cache.get_path(
        price_request,
        "dividends",
    ).exists()


def test_save_creates_ticker_directory(
    cache,
    price_request,
    complete_payload,
):
    ticker_directory = (
        cache.cache_dir / "AAPL"
    )

    assert not ticker_directory.exists()

    cache.save(
        price_request,
        complete_payload,
    )

    assert ticker_directory.exists()
    assert ticker_directory.is_dir()


def test_save_rejects_unexpected_object(
    cache,
    price_request,
    complete_payload,
):
    payload = {
        **complete_payload,
        "something_else": "bad",
    }

    with pytest.raises(
        CacheSaveError,
        match="Unexpected object to save",
    ):
        cache.save(
            price_request,
            payload,
        )


def test_save_rejects_missing_object(
    cache,
    price_request,
    price_history,
    metadata,
):
    payload = {
        "price_history": price_history,
        "metadata": metadata,
    }

    with pytest.raises(
        CacheSaveError,
        match="Missing objects to save",
    ):
        cache.save(
            price_request,
            payload,
        )


# ---------------------------------------------------------------------
# load - price history
# ---------------------------------------------------------------------


def test_load_price_history(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    result = cache.load(
        price_request,
    )

    assert isinstance(result, pd.DataFrame)

    pd.testing.assert_frame_equal(
        result,
        price_history,
    )


def test_load_price_history_has_datetime_index(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    result = cache.load(
        price_request,
    )

    assert isinstance(
        result.index,
        pd.DatetimeIndex,
    )

    assert result.index.name == "Date"


# ---------------------------------------------------------------------
# load - metadata
# ---------------------------------------------------------------------


def test_load_metadata(
    cache,
    price_request,
    metadata,
):
    cache._save(
        price_request,
        metadata,
        "metadata",
    )

    result = cache.load(
        price_request,
        "metadata",
    )

    assert isinstance(
        result,
        TickerMetadata,
    )

    assert result == metadata


# ---------------------------------------------------------------------
# load - dividends
# ---------------------------------------------------------------------


def test_load_dividends(
    cache,
    price_request,
    dividends,
):
    cache._save(
        price_request,
        dividends,
        "dividends",
    )

    result = cache.load(
        price_request,
        "dividends",
    )

    assert isinstance(
        result,
        pd.Series,
    )

    pd.testing.assert_series_equal(
        result,
        dividends,
    )


def test_load_empty_dividends(
    cache,
    price_request,
):
    dividends = pd.Series(
        dtype=float,
        name="Dividends",
    )

    dividends.index.name = "Date"

    cache._save(
        price_request,
        dividends,
        "dividends",
    )

    result = cache.load(
        price_request,
        "dividends",
    )

    assert isinstance(
        result,
        pd.Series,
    )

    assert result.empty
    assert result.name == "Dividends"
    assert result.index.name == "Date"


# ---------------------------------------------------------------------
# load errors
# ---------------------------------------------------------------------


def test_load_missing_price_history_raises(
    cache,
    price_request,
):
    with pytest.raises(
        CacheLoadError,
        match="does not exist",
    ):
        cache.load(price_request)


def test_load_missing_metadata_raises(
    cache,
    price_request,
):
    with pytest.raises(
        CacheLoadError,
        match="does not exist",
    ):
        cache.load(
            price_request,
            "metadata",
        )


def test_load_missing_dividends_raises(
    cache,
    price_request,
):
    with pytest.raises(
        CacheLoadError,
        match="does not exist",
    ):
        cache.load(
            price_request,
            "dividends",
        )


def test_load_unknown_kind_raises(
    cache,
    price_request,
):
    path = cache.get_path(
        price_request,
        "unknown",
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.touch()

    with pytest.raises(
        CacheLoadError,
        match="No data to load for unknown",
    ):
        cache.load(
            price_request,
            "unknown",
        )


# ---------------------------------------------------------------------
# is_fresh
# ---------------------------------------------------------------------


def test_is_fresh_returns_false_when_file_does_not_exist(
    cache,
    price_request,
):
    assert cache.is_fresh(
        price_request,
    ) is False


def test_is_fresh_returns_true_for_new_file(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    assert cache.is_fresh(
        price_request,
    ) is True


def test_is_fresh_returns_false_for_expired_file(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    path = cache.get_path(
        price_request,
    )

    old_time = (
        datetime.now(timezone.utc)
        - timedelta(days=2)
    ).timestamp()

    os.utime(
        path,
        (old_time, old_time),
    )

    assert cache.is_fresh(
        price_request,
    ) is False


def test_is_fresh_respects_custom_ttl(
    tmp_path,
    price_request,
    price_history,
):
    cache = DownloaderCache(
        cache_dir=tmp_path,
        ttl=timedelta(hours=1),
    )

    cache._save(
        price_request,
        price_history,
    )

    path = cache.get_path(
        price_request,
    )

    old_time = (
        datetime.now(timezone.utc)
        - timedelta(hours=2)
    ).timestamp()

    os.utime(
        path,
        (old_time, old_time),
    )

    assert cache.is_fresh(
        price_request,
    ) is False


# ---------------------------------------------------------------------
# get_if_fresh
# ---------------------------------------------------------------------


def test_get_if_fresh_returns_none_when_missing(
    cache,
    price_request,
):
    result = cache.get_if_fresh(
        price_request,
    )

    assert result is None


def test_get_if_fresh_returns_price_history_when_fresh(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    result = cache.get_if_fresh(
        price_request,
    )

    pd.testing.assert_frame_equal(
        result,
        price_history,
    )


def test_get_if_fresh_returns_none_when_expired(
    cache,
    price_request,
    price_history,
):
    cache._save(
        price_request,
        price_history,
    )

    path = cache.get_path(
        price_request,
    )

    old_time = (
        datetime.now(timezone.utc)
        - timedelta(days=2)
    ).timestamp()

    os.utime(
        path,
        (old_time, old_time),
    )

    result = cache.get_if_fresh(
        price_request,
    )

    assert result is None


def test_get_if_fresh_loads_metadata(
    cache,
    price_request,
    metadata,
):
    cache._save(
        price_request,
        metadata,
        "metadata",
    )

    result = cache.get_if_fresh(
        price_request,
        "metadata",
    )

    assert result == metadata


def test_get_if_fresh_loads_dividends(
    cache,
    price_request,
    dividends,
):
    cache._save(
        price_request,
        dividends,
        "dividends",
    )

    result = cache.get_if_fresh(
        price_request,
        "dividends",
    )

    pd.testing.assert_series_equal(
        result,
        dividends,
    )