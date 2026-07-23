"use strict";

const stockForm = document.getElementById("stock-form");
const tickerInput = document.getElementById("ticker");
const statusElement = document.getElementById("status");
const submitButton = stockForm.querySelector(
    'button[type="submit"]',
);

const summarySection = document.getElementById("summary");
const resultsSection = document.getElementById("results");

const summaryTitle = document.getElementById("summary-title");
const summaryPeriod = document.getElementById("summary-period");
const summaryInterval = document.getElementById(
    "summary-interval",
);
const summaryRows = document.getElementById("summary-rows");

const priceTableBody = document.getElementById(
    "price-table-body",
);

const metricsPlaceholder = document.getElementById(
    "metrics-placeholder",
);
const metricsGrid = document.getElementById("metrics-grid");


stockForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const ticker = tickerInput.value
        .trim()
        .toUpperCase();

    if (!ticker) {
        showStatus(
            "Enter a ticker symbol.",
            "error",
        );

        tickerInput.focus();
        return;
    }

    tickerInput.value = ticker;

    await loadTicker(ticker);
});


async function loadTicker(
    ticker,
    period = "10y",
    interval = "1mo",
) {
    setLoadingState(true);
    clearStatus();
    prepareResultsForLoading();

    const query = new URLSearchParams({
        period,
        interval,
    });

    try {
        const pricePromise = fetchJson(
            `/api/prices/${encodeURIComponent(ticker)}?${query}`,
        );

        const analysisPromise = fetchJson(
            `/api/analysis/${encodeURIComponent(ticker)}?${query}`,
        );

        const [
            priceResult,
            analysisResult,
        ] = await Promise.allSettled([
            pricePromise,
            analysisPromise,
        ]);

        if (priceResult.status === "rejected") {
            throw priceResult.reason;
        }

        renderPriceHistory(priceResult.value);

        /*
         * The historical data remains useful even if analysis fails.
         * In that case, display the table and show the metrics error
         * separately instead of discarding the successful price request.
         */
        if (analysisResult.status === "fulfilled") {
            renderAnalysis(analysisResult.value);

            showStatus(
                `Loaded ${ticker} historical prices and analysis.`,
                "success",
            );
        } else {
            renderAnalysisError(
                analysisResult.reason.message,
            );

            showStatus(
                `Loaded ${ticker} historical prices, but the `
                + "calculated metrics were unavailable.",
                "error",
            );
        }
    } catch (error) {
        hideResults();

        showStatus(
            error.message
            || "Unable to load ticker information.",
            "error",
        );
    } finally {
        setLoadingState(false);
    }
}


async function fetchJson(url) {
    let response;

    try {
        response = await fetch(url);
    } catch (error) {
        throw new Error(
            "Unable to connect to the frontend service.",
            {
                cause: error,
            },
        );
    }

    let payload;

    try {
        payload = await response.json();
    } catch (error) {
        throw new Error(
            "The server returned an invalid JSON response.",
            {
                cause: error,
            },
        );
    }

    if (!response.ok) {
        throw new Error(
            payload.message
            || payload.error
            || `Request failed with status ${response.status}.`,
        );
    }

    if (
        payload === null
        || typeof payload !== "object"
        || Array.isArray(payload)
    ) {
        throw new Error(
            "The server response had an unexpected format.",
        );
    }

    return payload;
}


function prepareResultsForLoading() {
    summarySection.hidden = true;
    resultsSection.hidden = false;

    metricsGrid.hidden = true;
    metricsPlaceholder.hidden = false;
    metricsPlaceholder.textContent =
        "Calculating metrics…";

    priceTableBody.replaceChildren(
        createMessageRow(
            "Loading historical prices…",
            "loading-row",
        ),
    );
}


function renderPriceHistory(history) {
    const rows = Array.isArray(history.data)
        ? history.data
        : [];

    if (rows.length === 0) {
        throw new Error(
            "The downloader returned no historical price rows.",
        );
    }

    summaryTitle.textContent =
        history.ticker || tickerInput.value;

    summaryPeriod.textContent =
        history.period || "—";

    summaryInterval.textContent =
        history.interval || "—";

    summaryRows.textContent =
        Number.isFinite(Number(history.rows))
            ? Number(history.rows).toLocaleString("en-CA")
            : rows.length.toLocaleString("en-CA");

    const fragment = document.createDocumentFragment();

    /*
     * The downloader typically returns oldest-to-newest rows.
     * Reverse a copy so the newest records display first.
     */
    const displayRows = [...rows].reverse();

    for (const row of displayRows) {
        fragment.appendChild(
            createPriceRow(row),
        );
    }

    priceTableBody.replaceChildren(fragment);

    summarySection.hidden = false;
    resultsSection.hidden = false;
}


function createPriceRow(row) {
    const tableRow = document.createElement("tr");

    tableRow.appendChild(
        createTableCell(
            row.Date ?? row.date ?? "—",
        ),
    );

    tableRow.appendChild(
        createTableCell(
            formatPrice(row.Open ?? row.open),
        ),
    );

    tableRow.appendChild(
        createTableCell(
            formatPrice(row.High ?? row.high),
        ),
    );

    tableRow.appendChild(
        createTableCell(
            formatPrice(row.Low ?? row.low),
        ),
    );

    tableRow.appendChild(
        createTableCell(
            formatPrice(row.Close ?? row.close),
        ),
    );

    tableRow.appendChild(
        createTableCell(
            formatVolume(row.Volume ?? row.volume),
        ),
    );

    return tableRow;
}


function createTableCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value;

    return cell;
}


function createMessageRow(message, className) {
    const row = document.createElement("tr");
    row.className = className;

    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.textContent = message;

    row.appendChild(cell);

    return row;
}


function renderAnalysis(analysis) {
    metricsPlaceholder.hidden = true;
    metricsGrid.hidden = false;

    setMetric(
        "current-price",
        formatCurrency(analysis.current_price),
    );

    setDirectionalPercentageMetric(
        "total-return",
        analysis.total_return,
    );

    setDirectionalPercentageMetric(
        "cagr",
        analysis.cagr,
    );

    setMetric(
        "volatility",
        formatPercentage(
            analysis.annualized_volatility,
        ),
    );

    setDirectionalPercentageMetric(
        "max-drawdown",
        analysis.max_drawdown,
    );

    setMetric(
        "moving-average-50",
        formatOptionalCurrency(
            analysis.moving_average_50,
        ),
    );

    setMetric(
        "moving-average-200",
        formatOptionalCurrency(
            analysis.moving_average_200,
        ),
    );

    setMetric(
        "analysis-date-range",
        formatDateRange(
            analysis.start_date,
            analysis.end_date,
        ),
    );
}


function renderAnalysisError(message) {
    metricsGrid.hidden = true;
    metricsPlaceholder.hidden = false;
    metricsPlaceholder.textContent =
        message || "Calculated metrics are unavailable.";
}


function setMetric(elementId, displayValue) {
    const element = document.getElementById(elementId);

    if (!element) {
        return;
    }

    element.textContent = displayValue;

    element.classList.remove(
        "metric-positive",
        "metric-negative",
    );
}


function setDirectionalPercentageMetric(
    elementId,
    value,
) {
    const element = document.getElementById(elementId);

    if (!element) {
        return;
    }

    const numericValue = Number(value);

    element.textContent = formatPercentage(
        numericValue,
    );

    element.classList.remove(
        "metric-positive",
        "metric-negative",
    );

    if (!Number.isFinite(numericValue)) {
        return;
    }

    if (numericValue > 0) {
        element.classList.add("metric-positive");
    } else if (numericValue < 0) {
        element.classList.add("metric-negative");
    }
}


function formatPrice(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return numericValue.toLocaleString(
        "en-CA",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        },
    );
}


function formatCurrency(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return new Intl.NumberFormat(
        "en-CA",
        {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        },
    ).format(numericValue);
}


function formatOptionalCurrency(value) {
    if (value === null || value === undefined) {
        return "Not enough history";
    }

    return formatCurrency(value);
}


function formatPercentage(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return new Intl.NumberFormat(
        "en-CA",
        {
            style: "percent",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        },
    ).format(numericValue);
}


function formatVolume(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return Math.round(numericValue).toLocaleString(
        "en-CA",
    );
}


function formatDateRange(startDate, endDate) {
    if (!startDate || !endDate) {
        return "—";
    }

    return `${startDate} to ${endDate}`;
}


function setLoadingState(isLoading) {
    submitButton.disabled = isLoading;
    tickerInput.disabled = isLoading;

    submitButton.textContent = isLoading
        ? "Loading…"
        : "Search";
}


function showStatus(message, type) {
    statusElement.textContent = message;

    statusElement.classList.remove(
        "status-error",
        "status-success",
    );

    if (type === "error") {
        statusElement.classList.add("status-error");
    }

    if (type === "success") {
        statusElement.classList.add(
            "status-success",
        );
    }
}


function clearStatus() {
    statusElement.textContent = "";

    statusElement.classList.remove(
        "status-error",
        "status-success",
    );
}


function hideResults() {
    summarySection.hidden = true;
    resultsSection.hidden = true;

    metricsGrid.hidden = true;
    metricsPlaceholder.hidden = false;

    priceTableBody.replaceChildren();
}