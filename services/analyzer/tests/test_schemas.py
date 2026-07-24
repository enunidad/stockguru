from src.schemas import AnalysisResult, PriceHistory, PriceRecord


def test_price_record_from_dict_converts_values():
    record = PriceRecord.from_dict(
        {
            "Date": "2024-01-31",
            "Close": "110.5",
            "Adj Close": "109.5",
            "Open": "100.0",
            "High": "112.0",
            "Low": "98.0",
            "Volume": "12345",
        }
    )

    assert record == PriceRecord(
        date="2024-01-31",
        close=110.5,
        adjusted_close=109.5,
        open=100.0,
        high=112.0,
        low=98.0,
        volume=12345,
    )


def test_price_record_from_dict_allows_missing_optional_values():
    record = PriceRecord.from_dict(
        {
            "Date": "2024-01-31",
            "Close": 110.5,
        }
    )

    assert record.adjusted_close is None
    assert record.open is None
    assert record.high is None
    assert record.low is None
    assert record.volume is None


def test_price_history_from_dict_builds_rows_and_closing_prices():
    history = PriceHistory.from_dict(
        {
            "ticker": "AAPL",
            "period": "1y",
            "interval": "1mo",
            "data": [
                {"Date": "2024-01-31", "Close": 100.0},
                {"Date": "2024-02-29", "Close": 110.0},
            ],
        }
    )

    assert history.ticker == "AAPL"
    assert history.period == "1y"
    assert history.interval == "1mo"
    assert len(history.rows) == 2
    assert history.closing_prices == (100.0, 110.0)


def test_analysis_result_to_dict():
    result = AnalysisResult(
        ticker="AAPL",
        period="10y",
        interval="1mo",
        observations=120,
        start_date="2016-01-31",
        end_date="2026-01-31",
        start_price=100.0,
        current_price=200.0,
        total_return=1.0,
        cagr=0.0718,
        annualized_volatility=0.20,
        max_drawdown=-0.30,
        moving_average_50=180.0,
        moving_average_200=None,
    )

    assert result.to_dict() == {
        "ticker": "AAPL",
        "period": "10y",
        "interval": "1mo",
        "observations": 120,
        "start_date": "2016-01-31",
        "end_date": "2026-01-31",
        "start_price": 100.0,
        "current_price": 200.0,
        "total_return": 1.0,
        "cagr": 0.0718,
        "annualized_volatility": 0.20,
        "max_drawdown": -0.30,
        "moving_average_50": 180.0,
        "moving_average_200": None,
    }
