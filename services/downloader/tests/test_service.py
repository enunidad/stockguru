# services/downloader/tests/test_service.py

from __future__ import annotations

from unittest.mock import Mock, patch

import pandas as pd
import pytest
import yfinance as yf

from src.service import DownloaderService
from src.schemas import PriceHistoryRequest, TickerMetadata


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def client():
    return Mock()


@pytest.fixture
def cache():
    return Mock()


@pytest.fixture
def service(client, cache):
    return DownloaderService(
        client=client,
        cache=cache,
    )


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
        raw={},
    )


@pytest.fixture
def price_history():
    index = pd.to_datetime(
        [
            "2015-01-01",
            "2018-01-01",
            "2020-01-01",
            "2022-01-01",
            "2023-01-01",
            "2024-01-01",
            "2025-01-01",
        ],
        utc=True,
    )

    data = pd.DataFrame(
        {
            "Open": [10, 20, 30, 40, 50, 60, 70],
            "High": [11, 21, 31, 41, 51, 61, 71],
            "Low": [9, 19, 29, 39, 49, 59, 69],
            "Close": [10.5, 20.5, 30.5, 40.5, 50.5, 60.5, 70.5],
            "Volume": [100] * 7,
        },
        index=index,
    )

    data.index.name = "Date"

    return data


@pytest.fixture
def dividends():
    data = pd.Series(
        [0.10, 0.20, 0.30, 0.40, 0.50],
        index=pd.to_datetime(
            [
                "2015-01-01",
                "2020-01-01",
                "2022-01-01",
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        ),
        name="Dividends",
    )

    data.index.name = "Date"

    return data


@pytest.fixture
def complete_download(
    metadata,
    price_history,
    dividends,
):
    return {
        "metadata": metadata,
        "price_history": price_history,
        "dividends": dividends,
    }


# ---------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------


def test_init_uses_injected_dependencies(
    client,
    cache,
):
    service = DownloaderService(
        client=client,
        cache=cache,
    )

    assert service.client is client
    assert service.cache is cache


# ---------------------------------------------------------------------
# _filter_period
# ---------------------------------------------------------------------


def test_filter_period_10y_returns_original_data(
    price_history,
):
    result = DownloaderService._filter_period(
        price_history,
        "10y",
    )

    assert result is price_history


def test_filter_period_1y(
    price_history,
):
    result = DownloaderService._filter_period(
        price_history,
        "1y",
    )

    assert result.index.min() >= pd.Timestamp(
        "2024-01-01",
        tz="UTC",
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_filter_period_2y(
    price_history,
):
    result = DownloaderService._filter_period(
        price_history,
        "2y",
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2023-01-01",
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_filter_period_5y(
    price_history,
):
    result = DownloaderService._filter_period(
        price_history,
        "5y",
    )

    assert result.index.min() >= pd.Timestamp(
        "2020-01-01",
        tz="UTC",
    )


def test_filter_period_unsupported_raises(
    price_history,
):
    with pytest.raises(
        ValueError,
        match="Unsupported period '3y'",
    ):
        DownloaderService._filter_period(
            price_history,
            "3y",
        )


# ---------------------------------------------------------------------
# _filter_dividend_period
# ---------------------------------------------------------------------


def test_filter_dividend_period_empty_returns_empty():
    dividends = pd.Series(
        dtype=float,
        name="Dividends",
    )

    result = DownloaderService._filter_dividend_period(
        dividends,
        "1y",
    )

    assert result.empty


def test_filter_dividend_period_1y(
    dividends,
):
    result = DownloaderService._filter_dividend_period(
        dividends,
        "1y",
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_filter_dividend_period_2y(
    dividends,
):
    result = DownloaderService._filter_dividend_period(
        dividends,
        "2y",
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_filter_dividend_period_5y(
    dividends,
):
    result = DownloaderService._filter_dividend_period(
        dividends,
        "5y",
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2020-01-01",
                "2022-01-01",
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_filter_dividend_period_10y(
    dividends,
):
    result = DownloaderService._filter_dividend_period(
        dividends,
        "10y",
    )

    assert list(result.index) == list(dividends.index)


def test_filter_dividend_period_unsupported_raises(
    dividends,
):
    with pytest.raises(
        ValueError,
        match="Unsupported period '3y'",
    ):
        DownloaderService._filter_dividend_period(
            dividends,
            "3y",
        )


# ---------------------------------------------------------------------
# _download_and_save
# ---------------------------------------------------------------------


def test_download_and_save(
    service,
    client,
    cache,
    complete_download,
    metadata,
):
    request = PriceHistoryRequest(
        ticker="AAPL",
        period="10y",
        interval="1d",
    )

    client.download.return_value = complete_download
    cache.load.return_value = metadata

    result = service._download_and_save(
        request,
        "metadata",
    )

    client.download.assert_called_once_with(
        request,
    )

    cache.save.assert_called_once_with(
        request,
        complete_download,
    )

    cache.load.assert_called_once_with(
        request,
        "metadata",
    )

    assert result is metadata


def test_download_and_save_price_history_uses_none_kind(
    service,
    client,
    cache,
    complete_download,
    price_history,
):
    request = PriceHistoryRequest(
        ticker="AAPL",
        period="10y",
        interval="1d",
    )

    client.download.return_value = complete_download
    cache.load.return_value = price_history

    result = service._download_and_save(
        request,
    )

    cache.load.assert_called_once_with(
        request,
        None,
    )

    assert result is price_history


# ---------------------------------------------------------------------
# get_metadata
# ---------------------------------------------------------------------


def test_get_metadata_returns_cached_metadata(
    service,
    cache,
    metadata,
):
    cache.get_if_fresh.return_value = metadata

    result = service.get_metadata("AAPL")

    assert result["ticker"] == "AAPL"
    assert result["currency"] == "USD"
    assert result["name"] == "Apple Inc."

    cache.get_if_fresh.assert_called_once()

    service.client.download.assert_not_called()


def test_get_metadata_downloads_when_cache_miss(
    service,
    client,
    cache,
    metadata,
    complete_download,
):
    cache.get_if_fresh.return_value = None
    client.download.return_value = complete_download
    cache.load.return_value = metadata

    result = service.get_metadata("AAPL")

    assert result["ticker"] == "AAPL"
    assert result["name"] == "Apple Inc."

    client.download.assert_called_once()
    cache.save.assert_called_once()
    cache.load.assert_called_once()


def test_get_metadata_uses_canonical_download_request(
    service,
    cache,
    metadata,
):
    cache.get_if_fresh.return_value = metadata

    service.get_metadata(
        ticker="aapl",
        period="2y",
        interval="2wk",
        auto_adjust=False,
        aggregate=False,
    )

    request = cache.get_if_fresh.call_args.args[0]

    assert request.ticker.ticker == "AAPL"
    assert request.period == "10y"
    assert request.interval == "1d"
    assert request.auto_adjust is False
    assert request.aggregate is False


# ---------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------


def test_get_price_history_returns_cached_history(
    service,
    cache,
    price_history,
):
    cache.get_if_fresh.return_value = price_history

    result = service.get_price_history(
        ticker="AAPL",
        period="10y",
        interval="1d",
        aggregate=False,
    )

    pd.testing.assert_frame_equal(
        result,
        price_history,
    )

    service.client.download.assert_not_called()


def test_get_price_history_downloads_on_cache_miss(
    service,
    client,
    cache,
    price_history,
    complete_download,
):
    cache.get_if_fresh.return_value = None
    client.download.return_value = complete_download
    cache.load.return_value = price_history

    result = service.get_price_history(
        ticker="AAPL",
        period="10y",
        interval="1d",
        aggregate=False,
    )

    client.download.assert_called_once()
    cache.save.assert_called_once()
    cache.load.assert_called_once()

    pd.testing.assert_frame_equal(
        result,
        price_history,
    )


def test_get_price_history_download_request_is_always_10y_1d(
    service,
    cache,
    price_history,
):
    cache.get_if_fresh.return_value = price_history

    service.get_price_history(
        ticker="AAPL",
        period="2y",
        interval="2wk",
        auto_adjust=True,
        aggregate=False,
    )

    request = cache.get_if_fresh.call_args.args[0]

    assert request.period == "10y"
    assert request.interval == "1d"
    assert request.auto_adjust is True


def test_get_price_history_filters_requested_period(
    service,
    cache,
    price_history,
):
    cache.get_if_fresh.return_value = price_history

    result = service.get_price_history(
        ticker="AAPL",
        period="2y",
        interval="1d",
        aggregate=False,
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2023-01-01",
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_get_price_history_does_not_aggregate_when_false(
    service,
    cache,
    price_history,
):
    cache.get_if_fresh.return_value = price_history

    with patch(
        "src.service.HistoricalAggregator"
    ) as aggregator_class:

        result = service.get_price_history(
            ticker="AAPL",
            period="10y",
            interval="2wk",
            aggregate=False,
        )

    aggregator_class.assert_not_called()

    pd.testing.assert_frame_equal(
        result,
        price_history,
    )


def test_get_price_history_aggregates_requested_interval(
    service,
    cache,
    price_history,
):
    cache.get_if_fresh.return_value = price_history

    aggregated = pd.DataFrame(
        {
            "Close": [123.45],
        },
        index=pd.to_datetime(
            ["2025-01-01"],
            utc=True,
        ),
    )

    with patch(
        "src.service.HistoricalAggregator"
    ) as aggregator_class:

        aggregator = aggregator_class.return_value
        aggregator.aggregate.return_value = aggregated

        result = service.get_price_history(
            ticker="AAPL",
            period="2y",
            interval="2wk",
            aggregate=True,
        )

        call = aggregator.aggregate.call_args

        assert call.kwargs["interval"] == "2wk"

        filtered_data = call.kwargs["df"]

        assert filtered_data.index.min() >= pd.Timestamp(
            "2023-01-01",
            tz="UTC",
        )

    assert result is aggregated


# ---------------------------------------------------------------------
# get_dividends
# ---------------------------------------------------------------------


def test_get_dividends_returns_cached_dividends(
    service,
    cache,
    dividends,
):
    cache.get_if_fresh.return_value = dividends

    result = service.get_dividends(
        ticker="AAPL",
        period="10y",
    )

    pd.testing.assert_series_equal(
        result,
        dividends,
    )

    service.client.download.assert_not_called()


def test_get_dividends_downloads_on_cache_miss(
    service,
    client,
    cache,
    dividends,
    complete_download,
):
    cache.get_if_fresh.return_value = None
    client.download.return_value = complete_download
    cache.load.return_value = dividends

    result = service.get_dividends(
        ticker="AAPL",
        period="10y",
    )

    client.download.assert_called_once()
    cache.save.assert_called_once()
    cache.load.assert_called_once()

    pd.testing.assert_series_equal(
        result,
        dividends,
    )


def test_get_dividends_filters_requested_period(
    service,
    cache,
    dividends,
):
    cache.get_if_fresh.return_value = dividends

    result = service.get_dividends(
        ticker="AAPL",
        period="1y",
    )

    assert list(result.index) == list(
        pd.to_datetime(
            [
                "2024-01-01",
                "2025-01-01",
            ],
            utc=True,
        )
    )


def test_get_dividends_uses_canonical_download_request(
    service,
    cache,
    dividends,
):
    cache.get_if_fresh.return_value = dividends

    service.get_dividends(
        ticker="AAPL",
        period="2y",
        interval="2wk",
        auto_adjust=False,
        aggregate=False,
    )

    request = cache.get_if_fresh.call_args.args[0]

    assert request.period == "10y"
    assert request.interval == "1d"
    assert request.auto_adjust is False
    assert request.aggregate is False