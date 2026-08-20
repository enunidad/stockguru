import pandas as pd
import pytest

from src.aggregator import HistoricalAggregator
from src.exceptions import PriceAggregationError


# =========================================================
# Helpers
# =========================================================


def make_history() -> pd.DataFrame:
    data = pd.DataFrame(
        {
            "Open": [
                100.0,
                102.0,
                104.0,
                110.0,
                112.0,
                114.0,
            ],
            "High": [
                105.0,
                108.0,
                109.0,
                115.0,
                118.0,
                119.0,
            ],
            "Low": [
                98.0,
                100.0,
                101.0,
                108.0,
                109.0,
                111.0,
            ],
            "Close": [
                103.0,
                106.0,
                107.0,
                113.0,
                116.0,
                117.0,
            ],
            "Volume": [
                1000,
                1200,
                1400,
                1600,
                1800,
                2000,
            ],
        },
        index=pd.to_datetime(
            [
                "2026-01-05",
                "2026-01-15",
                "2026-01-28",
                "2026-02-05",
                "2026-02-16",
                "2026-02-25",
            ],
            utc=True,
        ),
    )

    data.index.name = "Date"

    return data


# =========================================================
# Validation
# =========================================================


def test_aggregate_rejects_empty_dataframe() -> None:
    data = pd.DataFrame()

    aggregator = HistoricalAggregator()

    with pytest.raises(
        PriceAggregationError,
        match="Dataframe is empty",
    ):
        aggregator.aggregate(
            data,
            interval="1mo",
        )


def test_aggregate_rejects_unsupported_interval() -> None:
    data = make_history()

    aggregator = HistoricalAggregator()

    with pytest.raises(
        PriceAggregationError,
        match='Interval "1y" is not supported',
    ):
        aggregator.aggregate(
            data,
            interval="1y",
        )


def test_aggregate_requires_date_index_name() -> None:
    data = make_history()

    data.index.name = None

    aggregator = HistoricalAggregator()

    with pytest.raises(
        PriceAggregationError,
        match='Index must be a named "Date"',
    ):
        aggregator.aggregate(
            data,
            interval="1mo",
        )


def test_aggregate_requires_datetime_index() -> None:
    data = make_history().reset_index()

    data = data.set_index(
        data["Date"].dt.strftime(
            "%Y-%m-%d"
        )
    )

    data.index.name = "Date"

    aggregator = HistoricalAggregator()

    with pytest.raises(
        PriceAggregationError,
        match=(
            "Index must be of class "
            "pandas.DatetimeIndex."
        ),
    ):
        aggregator.aggregate(
            data,
            interval="1mo",
        )


# =========================================================
# Daily
# =========================================================


def test_daily_aggregation_preserves_rows() -> None:
    data = make_history()

    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        data,
        interval="1d",
    )

    assert len(result) == len(data)

    assert list(result.index) == [
        "2026-01-05",
        "2026-01-15",
        "2026-01-28",
        "2026-02-05",
        "2026-02-16",
        "2026-02-25",
    ]


def test_daily_aggregation_sets_price_equal_to_close() -> None:
    data = make_history()

    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        data,
        interval="1d",
    )

    pd.testing.assert_series_equal(
        result["Price"],
        result["Close"],
        check_names=False,
    )


def test_daily_aggregation_does_not_modify_source_dataframe() -> None:
    data = make_history()

    original = data.copy(
        deep=True
    )

    aggregator = HistoricalAggregator()

    aggregator.aggregate(
        data,
        interval="1d",
    )

    pd.testing.assert_frame_equal(
        data,
        original,
    )


# =========================================================
# Monthly Aggregation
# =========================================================


def test_monthly_aggregation_uses_ohlcv_rules() -> None:
    data = make_history()

    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        data,
        interval="1mo",
    )

    assert list(result.index) == [
        "2026-01",
        "2026-02",
    ]


    january = result.loc[
        "2026-01"
    ]

    assert january["Open"] == pytest.approx(
        100.0
    )

    assert january["High"] == pytest.approx(
        109.0
    )

    assert january["Low"] == pytest.approx(
        98.0
    )

    assert january["Close"] == pytest.approx(
        107.0
    )

    assert january["Price"] == pytest.approx(
        (
            103.0
            + 106.0
            + 107.0
        )
        / 3.0
    )

    assert january["Volume"] == pytest.approx(
        3600
    )


    february = result.loc[
        "2026-02"
    ]

    assert february["Open"] == pytest.approx(
        110.0
    )

    assert february["High"] == pytest.approx(
        119.0
    )

    assert february["Low"] == pytest.approx(
        108.0
    )

    assert february["Close"] == pytest.approx(
        117.0
    )

    assert february["Price"] == pytest.approx(
        (
            113.0
            + 116.0
            + 117.0
        )
        / 3.0
    )

    assert february["Volume"] == pytest.approx(
        5400
    )


def test_monthly_aggregation_sets_date_index_name() -> None:
    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        make_history(),
        interval="1mo",
    )

    assert result.index.name == "Date"


# =========================================================
# Sorting
# =========================================================


def test_aggregation_sorts_history_before_resampling() -> None:
    data = make_history()

    data = data.sort_index(
        ascending=False
    )

    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        data,
        interval="1mo",
    )

    january = result.loc[
        "2026-01"
    ]

    # Must use Jan 5 as the first Open even though
    # the source DataFrame was supplied backwards.
    assert january["Open"] == pytest.approx(
        100.0
    )

    # Must use Jan 28 as the final Close.
    assert january["Close"] == pytest.approx(
        107.0
    )


# =========================================================
# Supported Resampling Intervals
# =========================================================


@pytest.mark.parametrize(
    "interval",
    [
        "1wk",
        "2wk",
        "1mo",
        "2mo",
        "3mo",
    ],
)
def test_supported_resampling_intervals_return_data(
    interval,
) -> None:
    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        make_history(),
        interval=interval,
    )

    assert not result.empty

    assert result.index.name == "Date"

    assert list(result.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Price",
        "Volume",
    ]


# =========================================================
# Date Formatting
# =========================================================


def test_monthly_intervals_use_year_month_dates() -> None:
    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        make_history(),
        interval="1mo",
    )

    assert all(
        len(date) == 7
        for date in result.index
    )

    assert all(
        date[4] == "-"
        for date in result.index
    )


def test_weekly_intervals_use_full_dates() -> None:
    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        make_history(),
        interval="1wk",
    )

    assert all(
        len(date) == 10
        for date in result.index
    )


# =========================================================
# Missing OHLC Periods
# =========================================================


def test_aggregation_drops_period_without_valid_ohlc() -> None:
    data = make_history()

    data.loc[
        pd.Timestamp(
            "2026-03-10",
            tz="UTC",
        )
    ] = {
        "Open": float("nan"),
        "High": float("nan"),
        "Low": float("nan"),
        "Close": float("nan"),
        "Volume": 1000,
    }

    aggregator = HistoricalAggregator()

    result = aggregator.aggregate(
        data,
        interval="1mo",
    )

    assert list(result.index) == [
        "2026-01",
        "2026-02",
    ]