from unittest.mock import AsyncMock

import pytest

from src.exceptions import InvalidPriceHistoryError
from src.schemas import PriceHistory, PriceRecord
from src.service import AnalyzerService


def make_history(*, interval: str = "1d", rows=None, ) -> PriceHistory:
    return PriceHistory(
        ticker="AAPL",
        period="2y",
        interval=interval,
        rows=rows
        or (
            PriceRecord(
                date="2024-01-01",
                close=100.0,
            ),
            PriceRecord(
                date="2025-01-01",
                close=110.0,
            ),
            PriceRecord(
                date="2026-01-01",
                close=121.0,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_analyze_ticker_calls_downloader_and_returns_analysis():
    client = AsyncMock()
    client.get_price_history.return_value = make_history()

    service = AnalyzerService(downloader_client=client, )

    result = await service.analyze_ticker("aapl", period="2y", )

    client.get_price_history.assert_awaited_once_with("aapl", period="2y", interval="1d", aggregate=False, auto_adjust=False, )

    assert result.ticker == "AAPL"
    assert result.observations == 3
    assert result.start_date == "2024-01-01"
    assert result.end_date == "2026-01-01"
    assert result.start_price == 100.0
    assert result.current_price == 121.0
    assert result.total_return == pytest.approx(0.21)
    assert result.cagr == pytest.approx(0.10, rel=1e-3, )
    assert result.max_drawdown == pytest.approx(0.0)
    assert result.moving_average_50 is None
    assert result.moving_average_200 is None


def test_analyze_history_calculates_available_moving_averages():
    rows = tuple(
        PriceRecord(
            date=(
                f"{2000 + ((index - 1) // 12):04d}-"
                f"{((index - 1) % 12) + 1:02d}-01"
            ),
            close=float(index),
        )
        for index in range(1, 201)
    )

    service = AnalyzerService(downloader_client=AsyncMock(), )

    result = service._analyze_history(make_history(interval="1mo", rows=rows, ) )

    assert result.moving_average_50 == pytest.approx(sum(range(151, 201)) / 50 )
    assert result.moving_average_200 == pytest.approx(sum(range(1, 201)) / 200 )


def test_analyze_history_rejects_fewer_than_three_rows():
    service = AnalyzerService(downloader_client=AsyncMock(), )

    history = make_history(
        rows=(
            PriceRecord(
                date="2024-01-01",
                close=100.0,
            ),
            PriceRecord(
                date="2025-01-01",
                close=110.0,
            ),
        )
    )

    with pytest.raises(InvalidPriceHistoryError):
        service._analyze_history(history)


@pytest.mark.parametrize("value", ["not-a-date", "", None, ], )
def test_parse_date_rejects_invalid_dates(value):
    with pytest.raises(InvalidPriceHistoryError):
        AnalyzerService._parse_date(value)


def test_calculate_years_rejects_non_increasing_dates():
    parsed = AnalyzerService._parse_date("2024-01-01" )

    with pytest.raises(InvalidPriceHistoryError):
        AnalyzerService._calculate_years(start_date=parsed, end_date=parsed, )


@pytest.mark.parametrize(("interval", "expected", ), 
                        [("1d", 252), ("5d", 52), ("1wk", 52), ("1mo", 12), ("3mo", 4), ], )
def test_get_trading_periods(interval, expected, ):
    assert (AnalyzerService._get_trading_periods(interval) == expected )


def test_get_trading_periods_rejects_unsupported_interval():
    with pytest.raises(InvalidPriceHistoryError):
        AnalyzerService._get_trading_periods("1h")