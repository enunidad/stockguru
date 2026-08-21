import pytest
from dataclasses import FrozenInstanceError

from src.schemas import (
    ChartRequest,
    ChartResponse,
    PortfolioOverviewRequest,
    PortfolioOverviewResponse,
)


def test_chart_request_required_ticker() -> None:
    request = ChartRequest(ticker="AAPL")

    assert request.ticker == "AAPL"


def test_chart_request_defaults() -> None:
    request = ChartRequest(ticker="AAPL")

    assert request.period == "10y"
    assert request.interval == "1mo"
    assert request.auto_adjust is True
    assert request.aggregate is True


def test_chart_request_accepts_custom_values() -> None:
    request = ChartRequest(
        ticker="MSFT",
        period="5y",
        interval="1wk",
        auto_adjust=False,
        aggregate=False,
    )

    assert request.ticker == "MSFT"
    assert request.period == "5y"
    assert request.interval == "1wk"
    assert request.auto_adjust is False
    assert request.aggregate is False


def test_chart_request_is_frozen() -> None:
    request = ChartRequest(ticker="AAPL")

    with pytest.raises(FrozenInstanceError):
        request.ticker = "MSFT"


def test_chart_response_required_fields() -> None:
    response = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
    )

    assert response.chart_type == "candlestick"
    assert response.title == "Monthly OHLC"


def test_chart_response_defaults() -> None:
    response = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
    )

    assert response.xaxis_label is None
    assert response.yaxis_label is None
    assert response.legend is False
    assert response.x_values == []
    assert response.y_values == {}


def test_chart_response_accepts_custom_values() -> None:
    response = ChartResponse(
        chart_type="line",
        title="Closing Price",
        xaxis_label="Date",
        yaxis_label="Price",
        legend=True,
        x_values=["2026-01", "2026-02"],
        y_values={
            "Close": [100.0, 105.0],
        },
    )

    assert response.chart_type == "line"
    assert response.title == "Closing Price"
    assert response.xaxis_label == "Date"
    assert response.yaxis_label == "Price"
    assert response.legend is True
    assert response.x_values == ["2026-01", "2026-02"]
    assert response.y_values == {
        "Close": [100.0, 105.0],
    }


def test_chart_response_mutable_defaults_are_independent() -> None:
    response_1 = ChartResponse(
        chart_type="line",
        title="Chart 1",
    )
    response_2 = ChartResponse(
        chart_type="line",
        title="Chart 2",
    )

    response_1.x_values.append("2026-01")
    response_1.y_values["Close"] = [100.0]

    assert response_2.x_values == []
    assert response_2.y_values == {}


def test_chart_response_to_dict() -> None:
    response = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
        xaxis_label="Date",
        yaxis_label="Price",
        legend=True,
        x_values=["2026-01", "2026-02"],
        y_values={
            "Open": [100.0, 105.0],
            "High": [110.0, 112.0],
            "Low": [95.0, 101.0],
            "Close": [108.0, 110.0],
        },
    )

    result = response.to_dict()

    assert result == {
        "chart_type": "candlestick",
        "title": "Monthly OHLC",
        "data": {
            "x_values": ["2026-01", "2026-02"],
            "y_values": {
                "Open": [100.0, 105.0],
                "High": [110.0, 112.0],
                "Low": [95.0, 101.0],
                "Close": [108.0, 110.0],
            },
        },
        "labels": {
            "x": "Date",
            "y": "Price",
        },
        "legend": True,
    }


def test_chart_response_is_frozen() -> None:
    response = ChartResponse(
        chart_type="candlestick",
        title="Monthly OHLC",
    )

    with pytest.raises(FrozenInstanceError):
        response.title = "New Title"

# =========================================================
# PortfolioOverviewRequest
# =========================================================


def test_portfolio_overview_request_stores_values() -> None:
    request = PortfolioOverviewRequest(
        initial_investment=10000.0,
        current_growth=1500.0,
        future_contributions=12000.0,
        stock_growth=8000.0,
        dividends=2500.0,
    )

    assert request.initial_investment == pytest.approx(
        10000.0
    )

    assert request.current_growth == pytest.approx(
        1500.0
    )

    assert request.future_contributions == pytest.approx(
        12000.0
    )

    assert request.stock_growth == pytest.approx(
        8000.0
    )

    assert request.dividends == pytest.approx(
        2500.0
    )


def test_portfolio_overview_request_allows_negative_growth() -> None:
    request = PortfolioOverviewRequest(
        initial_investment=10000.0,
        current_growth=-500.0,
        future_contributions=0.0,
        stock_growth=-250.0,
        dividends=100.0,
    )

    assert request.current_growth == pytest.approx(
        -500.0
    )

    assert request.stock_growth == pytest.approx(
        -250.0
    )


def test_portfolio_overview_request_is_frozen() -> None:
    request = PortfolioOverviewRequest(
        initial_investment=10000.0,
        current_growth=1000.0,
        future_contributions=5000.0,
        stock_growth=3000.0,
        dividends=500.0,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        request.initial_investment = 20000.0


# =========================================================
# PortfolioOverviewResponse
# =========================================================


def test_portfolio_overview_response_stores_values() -> None:
    response = PortfolioOverviewResponse(
        chart_type="donut",
        title="Portfolio Overview",
        labels=[
            "Total Invested",
            "Current Growth",
            "Future Contributions",
            "Stock Growth",
            "Dividends / DRIP",
        ],
        values=[
            10000.0,
            1000.0,
            5000.0,
            3000.0,
            500.0,
        ],
        total=19500.0,
    )

    assert response.chart_type == "donut"
    assert response.title == "Portfolio Overview"

    assert response.labels == [
        "Total Invested",
        "Current Growth",
        "Future Contributions",
        "Stock Growth",
        "Dividends / DRIP",
    ]

    assert response.values == [
        10000.0,
        1000.0,
        5000.0,
        3000.0,
        500.0,
    ]

    assert response.total == pytest.approx(
        19500.0
    )

    assert response.legend is True


def test_portfolio_overview_response_accepts_bar_chart() -> None:
    response = PortfolioOverviewResponse(
        chart_type="bar",
        title="Portfolio Overview",
        labels=[
            "Total Invested",
            "Current Growth",
        ],
        values=[
            10000.0,
            -1000.0,
        ],
        total=9000.0,
    )

    assert response.chart_type == "bar"


def test_portfolio_overview_response_to_dict() -> None:
    response = PortfolioOverviewResponse(
        chart_type="donut",
        title="Portfolio Overview",
        labels=[
            "Total Invested",
            "Current Growth",
            "Future Contributions",
            "Stock Growth",
            "Dividends / DRIP",
        ],
        values=[
            10000.0,
            1000.0,
            5000.0,
            3000.0,
            500.0,
        ],
        total=19500.0,
        legend=True,
    )

    assert response.to_dict() == {
        "chart_type": "donut",
        "title": "Portfolio Overview",
        "labels": [
            "Total Invested",
            "Current Growth",
            "Future Contributions",
            "Stock Growth",
            "Dividends / DRIP",
        ],
        "values": [
            10000.0,
            1000.0,
            5000.0,
            3000.0,
            500.0,
        ],
        "total": 19500.0,
        "legend": True,
    }


def test_portfolio_overview_response_legend_defaults_true() -> None:
    response = PortfolioOverviewResponse(
        chart_type="donut",
        title="Portfolio Overview",
        labels=[],
        values=[],
        total=0.0,
    )

    assert response.legend is True


def test_portfolio_overview_response_is_frozen() -> None:
    response = PortfolioOverviewResponse(
        chart_type="donut",
        title="Portfolio Overview",
        labels=[],
        values=[],
        total=1000.0,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        response.chart_type = "bar"