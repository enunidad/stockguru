from unittest.mock import AsyncMock

import pytest

from src.client import AnalyzerApiClient, DownloaderApiClient
from src.exceptions import InvalidDownloaderResponseError
from src.schemas import ChartRequest, ChartResponse
from src.service import ChartMgrService


@pytest.fixture
def downloader_client():
    return AsyncMock(spec=DownloaderApiClient)


@pytest.fixture
def analyzer_client():
    return AsyncMock(spec=AnalyzerApiClient)


@pytest.fixture
def service(downloader_client, analyzer_client):
    return ChartMgrService(
        downloader_client=downloader_client,
        analyzer_client=analyzer_client,
    )


# =========================================================
# _validate_data
# =========================================================

def test_validate_data_accepts_valid_payload() -> None:
    payload = [
        {
            "Date": "2026-01",
            "Open": 100.0,
            "High": 110.0,
            "Low": 95.0,
            "Close": 108.0,
        },
    ]

    expected = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
    ]

    ChartMgrService._validate_data(payload, expected)


def test_validate_data_rejects_non_list() -> None:
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Data format is not recognized. Must be a list.",
    ):
        ChartMgrService._validate_data(
            {"Date": "2026-01"},
            ["Date"],
        )


def test_validate_data_rejects_empty_list() -> None:
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Data requested is empty.",
    ):
        ChartMgrService._validate_data(
            [],
            ["Date"],
        )


def test_validate_data_rejects_non_dict_item() -> None:
    payload = [
        {
            "Date": "2026-01",
        },
        "invalid",
    ]

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Data object is not recognized. Objects must be dictionaries.",
    ):
        ChartMgrService._validate_data(
            payload,
            ["Date"],
        )


def test_validate_data_rejects_missing_required_fields() -> None:
    payload = [
        {
            "Date": "2026-01",
            "Open": 100.0,
        },
    ]

    expected = [
        "Date",
        "Open",
        "Close",
    ]

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Some data missing required values.",
    ):
        ChartMgrService._validate_data(
            payload,
            expected,
        )


def test_validate_data_allows_extra_fields() -> None:
    payload = [
        {
            "Date": "2026-01",
            "Open": 100.0,
            "Close": 108.0,
            "Volume": 1000000,
            "Extra": "ignored",
        },
    ]

    ChartMgrService._validate_data(
        payload,
        ["Date", "Open", "Close"],
    )


# =========================================================
# _read_history
# =========================================================

@pytest.mark.asyncio
async def test_read_history_builds_chart_request(
    service,
    downloader_client,
) -> None:
    downloader_client.price_history.return_value = [
        {
            "Date": "2026-01",
            "Close": 100.0,
        },
    ]

    await service._read_history(
        "AAPL",
        ["Date", "Close"],
        period="5y",
        interval="1wk",
        auto_adjust=False,
        aggregate=False,
    )

    downloader_client.price_history.assert_awaited_once_with(
        ChartRequest(
            ticker="AAPL",
            period="5y",
            interval="1wk",
            auto_adjust=False,
            aggregate=False,
        )
    )


@pytest.mark.asyncio
async def test_read_history_returns_downloader_data(
    service,
    downloader_client,
) -> None:
    data = [
        {
            "Date": "2026-01",
            "Close": 100.0,
        },
        {
            "Date": "2026-02",
            "Close": 105.0,
        },
    ]

    downloader_client.price_history.return_value = data

    result = await service._read_history(
        "AAPL",
        ["Date", "Close"],
    )

    assert result == data


@pytest.mark.asyncio
async def test_read_history_validates_downloader_data(
    service,
    downloader_client,
) -> None:
    downloader_client.price_history.return_value = [
        {
            "Date": "2026-01",
        },
    ]

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Some data missing required values.",
    ):
        await service._read_history(
            "AAPL",
            ["Date", "Close"],
        )


# =========================================================
# _format_data
# =========================================================

def test_format_data_builds_chart_response() -> None:
    data = [
        {
            "Date": "2026-01",
            "Open": 100.0,
            "High": 110.0,
            "Low": 95.0,
            "Close": 108.0,
        },
        {
            "Date": "2026-02",
            "Open": 108.0,
            "High": 115.0,
            "Low": 102.0,
            "Close": 112.0,
        },
    ]

    result = ChartMgrService._format_data(
        data,
        ["Date", "Open", "High", "Low", "Close"],
        "candlestick",
        "OHLC Price History",
        "Date",
        "Value",
        True,
    )

    assert result == ChartResponse(
        chart_type="candlestick",
        title="OHLC Price History",
        xaxis_label="Date",
        yaxis_label="Value",
        legend=True,
        x_values=[
            "2026-01",
            "2026-02",
        ],
        y_values={
            "Open": [100.0, 108.0],
            "High": [110.0, 115.0],
            "Low": [95.0, 102.0],
            "Close": [108.0, 112.0],
        },
    )


def test_format_data_uses_first_expected_field_for_x_axis() -> None:
    data = [
        {
            "Date": "2026-01",
            "Volume": 1000000,
        },
        {
            "Date": "2026-02",
            "Volume": 1200000,
        },
    ]

    result = ChartMgrService._format_data(
        data,
        ["Date", "Volume"],
        "bar",
        "Volume History",
        "Date",
        "Volume",
        True,
    )

    assert result.x_values == [
        "2026-01",
        "2026-02",
    ]

    assert result.y_values == {
        "Volume": [
            1000000,
            1200000,
        ],
    }


# =========================================================
# get_price_history
# =========================================================

@pytest.mark.asyncio
async def test_get_price_history_returns_candlestick_chart(
    service,
    downloader_client,
) -> None:
    downloader_client.price_history.return_value = [
        {
            "Date": "2026-01",
            "Open": 100.0,
            "High": 110.0,
            "Low": 95.0,
            "Close": 108.0,
        },
        {
            "Date": "2026-02",
            "Open": 108.0,
            "High": 115.0,
            "Low": 102.0,
            "Close": 112.0,
        },
    ]

    result = await service.get_price_history("AAPL")

    assert result == ChartResponse(
        chart_type="candlestick",
        title="OHLC Price History",
        xaxis_label="Date",
        yaxis_label="Value",
        legend=True,
        x_values=[
            "2026-01",
            "2026-02",
        ],
        y_values={
            "Open": [100.0, 108.0],
            "High": [110.0, 115.0],
            "Low": [95.0, 102.0],
            "Close": [108.0, 112.0],
        },
    )


@pytest.mark.asyncio
async def test_get_price_history_passes_request_options(
    service,
    downloader_client,
) -> None:
    downloader_client.price_history.return_value = [
        {
            "Date": "2026-01",
            "Open": 100.0,
            "High": 110.0,
            "Low": 95.0,
            "Close": 108.0,
        },
    ]

    await service.get_price_history(
        "AAPL",
        period="5y",
        interval="1wk",
        auto_adjust=False,
        aggregate=False,
    )

    downloader_client.price_history.assert_awaited_once_with(
        ChartRequest(
            ticker="AAPL",
            period="5y",
            interval="1wk",
            auto_adjust=False,
            aggregate=False,
        )
    )


# =========================================================
# get_volume_history
# =========================================================

@pytest.mark.asyncio
async def test_get_volume_history_returns_bar_chart(
    service,
    downloader_client,
) -> None:
    downloader_client.price_history.return_value = [
        {
            "Date": "2026-01",
            "Volume": 1000000,
        },
        {
            "Date": "2026-02",
            "Volume": 1200000,
        },
    ]

    result = await service.get_volume_history("AAPL")

    assert result == ChartResponse(
        chart_type="bar",
        title="Volume History",
        xaxis_label="Date",
        yaxis_label="Volume",
        legend=True,
        x_values=[
            "2026-01",
            "2026-02",
        ],
        y_values={
            "Volume": [
                1000000,
                1200000,
            ],
        },
    )


@pytest.mark.asyncio
async def test_get_volume_history_passes_request_options(
    service,
    downloader_client,
) -> None:
    downloader_client.price_history.return_value = [
        {
            "Date": "2026-01",
            "Volume": 1000000,
        },
    ]

    await service.get_volume_history(
        "MSFT",
        period="1y",
        interval="1wk",
        auto_adjust=False,
        aggregate=False,
    )

    downloader_client.price_history.assert_awaited_once_with(
        ChartRequest(
            ticker="MSFT",
            period="1y",
            interval="1wk",
            auto_adjust=False,
            aggregate=False,
        )
    )