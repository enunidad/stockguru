from datetime import timedelta
import os

import pandas as pd

from src.cache import PriceHistoryCache, TickerMetadataCache
from src.schemas import PriceHistoryRequest, TickerMetadata


def make_price_data() -> pd.DataFrame:
    data = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "Close": [110.0, 111.0],
        },
        index=pd.to_datetime(
            ["2024-01-01", "2024-01-02"]
        ),
    )
    data.index.name = "Date"
    return data


def test_price_history_get_path_normalizes_ticker(tmp_path):
    cache = PriceHistoryCache(cache_dir=tmp_path)

    request = PriceHistoryRequest(
        ticker=" aapl ",
        period="5y",
        interval="1wk",
        auto_adjust=True,
    )

    assert cache.get_path(request) == (
        tmp_path / "AAPL" / "5y_1wk_True.csv"
    )


def test_price_history_cache_separates_auto_adjust(tmp_path):
    cache = PriceHistoryCache(cache_dir=tmp_path)

    adjusted = PriceHistoryRequest(
        ticker="AAPL",
        auto_adjust=True,
    )
    unadjusted = PriceHistoryRequest(
        ticker="AAPL",
        auto_adjust=False,
    )

    assert cache.get_path(adjusted) != cache.get_path(
        unadjusted
    )


def test_price_history_save_creates_file(tmp_path):
    cache = PriceHistoryCache(cache_dir=tmp_path)
    request = PriceHistoryRequest(ticker="AAPL")
    data = make_price_data()

    path = cache.save(request, data)

    assert path.exists()
    assert path == cache.get_path(request)


def test_price_history_save_then_load(tmp_path):
    cache = PriceHistoryCache(cache_dir=tmp_path)
    request = PriceHistoryRequest(ticker="AAPL")
    expected = make_price_data()

    cache.save(request, expected)
    result = cache.load(request)

    pd.testing.assert_frame_equal(result, expected)
    assert result.index.name == "Date"


def test_price_history_is_not_fresh_when_missing(tmp_path):
    cache = PriceHistoryCache(cache_dir=tmp_path)
    request = PriceHistoryRequest(ticker="AAPL")

    assert cache.is_fresh(request) is False


def test_price_history_get_if_fresh_returns_data(
    tmp_path,
):
    cache = PriceHistoryCache(
        cache_dir=tmp_path,
        ttl=timedelta(days=1),
    )
    request = PriceHistoryRequest(ticker="AAPL")
    expected = make_price_data()

    cache.save(request, expected)

    result = cache.get_if_fresh(request)

    assert result is not None
    pd.testing.assert_frame_equal(result, expected)


def test_price_history_get_if_fresh_returns_none_when_expired(
    tmp_path,
):
    cache = PriceHistoryCache(
        cache_dir=tmp_path,
        ttl=timedelta(seconds=1),
    )
    request = PriceHistoryRequest(ticker="AAPL")
    path = cache.save(request, make_price_data())

    old_timestamp = path.stat().st_mtime - 60
    os.utime(path, (old_timestamp, old_timestamp))

    assert cache.get_if_fresh(request) is None


def test_metadata_get_path_normalizes_ticker(tmp_path):
    cache = TickerMetadataCache(cache_dir=tmp_path)

    assert cache.get_path(" aapl ") == (
        tmp_path / "AAPL" / "AAPL_metadata.json"
    )


def test_metadata_save_creates_json_file(tmp_path):
    cache = TickerMetadataCache(cache_dir=tmp_path)
    metadata = TickerMetadata(
        ticker="AAPL",
        currency="USD",
        exchange="NMS",
    )

    path = cache.save(metadata)

    assert path.exists()
    assert path == cache.get_path("AAPL")


def test_metadata_save_then_load(tmp_path):
    cache = TickerMetadataCache(cache_dir=tmp_path)
    expected = TickerMetadata(
        ticker="AAPL",
        currency="USD",
        exchange="NMS",
        timezone="America/New_York",
        quote_type="EQUITY",
        raw={
            "last_price": 200.0,
            "nested": {"value": 1},
        },
    )

    cache.save(expected)
    result = cache.load("aapl")

    assert result == expected


def test_metadata_is_not_fresh_when_missing(tmp_path):
    cache = TickerMetadataCache(cache_dir=tmp_path)

    assert cache.is_fresh("AAPL") is False


def test_metadata_get_if_fresh_returns_metadata(
    tmp_path,
):
    cache = TickerMetadataCache(
        cache_dir=tmp_path,
        ttl=timedelta(days=1),
    )
    expected = TickerMetadata(
        ticker="AAPL",
        currency="USD",
    )

    cache.save(expected)

    assert cache.get_if_fresh("AAPL") == expected


def test_metadata_get_if_fresh_returns_none_when_expired(
    tmp_path,
):
    cache = TickerMetadataCache(
        cache_dir=tmp_path,
        ttl=timedelta(seconds=1),
    )
    path = cache.save(
        TickerMetadata(ticker="AAPL")
    )

    old_timestamp = path.stat().st_mtime - 60
    os.utime(path, (old_timestamp, old_timestamp))

    assert cache.get_if_fresh("AAPL") is None