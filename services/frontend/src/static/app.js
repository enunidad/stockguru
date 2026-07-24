"use strict";


const DEFAULT_CURRENCY = "USD";
const NUMBER_LOCALE = "en-CA";
const CURRENCY_LOCALE = "en-US";


const stockForm =
    document.getElementById("stock-form");

const tickerInput =
    document.getElementById("ticker");

const statusElement =
    document.getElementById("status");

const submitButton = stockForm.querySelector(
    'button[type="submit"]',
);


const summarySection =
    document.getElementById("summary");

const resultsSection =
    document.getElementById("results");

const summaryTitle =
    document.getElementById("summary-title");

const summaryPeriod =
    document.getElementById("summary-period");

const summaryInterval =
    document.getElementById("summary-interval");

const summaryRows =
    document.getElementById("summary-rows");


const priceTableBody =
    document.getElementById("price-table-body");

const metricsPlaceholder =
    document.getElementById("metrics-placeholder");

const metricsGrid =
    document.getElementById("metrics-grid");


/*
 * Store the active ticker metadata so all rendering functions
 * use the same currency and identifying information.
 */
let activeMetadata = createDefaultMetadata();


stockForm.addEventListener(
    "submit",
    async (event) => {
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
    },
);


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
        const [
            priceResult,
            analysisResult,
            metadataResult,
        ] = await Promise.allSettled([
            fetchJson(
                `/api/prices/${encodeURIComponent(ticker)}?${query}`,
            ),
            fetchJson(
                `/api/analysis/${encodeURIComponent(ticker)}?${query}`,
            ),
            fetchJson(
                `/api/metadata/${encodeURIComponent(ticker)}`,
            ),
        ]);

        /*
         * Metadata failure should not prevent the historical
         * prices from being displayed.
         */
        activeMetadata = createDefaultMetadata(ticker);

        if (metadataResult.status === "fulfilled") {
            activeMetadata = normalizeMetadata(
                metadataResult.value,
                ticker,
            );
        }

        if (priceResult.status !== "fulfilled") {
            throw new Error(
                getErrorMessage(
                    priceResult.reason,
                    "Unable to load price history.",
                ),
            );
        }

        renderPriceHistory(
            priceResult.value,
            activeMetadata,
        );

        if (analysisResult.status === "fulfilled") {
            renderAnalysis(
                analysisResult.value,
                activeMetadata,
            );

            showStatus(
                `Loaded ${ticker} historical prices and analysis.`,
                "success",
            );
        } else {
            renderAnalysisError(
                getErrorMessage(
                    analysisResult.reason,
                    "Calculated metrics are unavailable.",
                ),
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
            getErrorMessage(
                error,
                "Unable to load ticker information.",
            ),
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


function createDefaultMetadata(ticker = "") {
    return {
        ticker,
        currency: DEFAULT_CURRENCY,
        exchange: null,
        timezone: null,
        quote_type: null,
        name: null,
        sector: null,
        industry: null,
        country: null,
        raw: {},
    };
}


function normalizeMetadata(
    metadata,
    fallbackTicker,
) {
    return {
        ticker:
            metadata.ticker
            || fallbackTicker,

        currency:
            normalizeCurrency(metadata.currency),

        exchange:
            metadata.exchange
            || null,

        timezone:
            metadata.timezone
            || null,

        quote_type:
            metadata.quote_type
            || null,

        name:
            metadata.name
            || null,

        sector:
            metadata.sector
            || null,

        industry:
            metadata.industry
            || null,

        country:
            metadata.country
            || null,

        raw:
            isPlainObject(metadata.raw)
                ? metadata.raw
                : {},
    };
}


function normalizeCurrency(currency) {
    if (
        typeof currency !== "string"
        || currency.trim().length !== 3
    ) {
        return DEFAULT_CURRENCY;
    }

    return currency.trim().toUpperCase();
}


function isPlainObject(value) {
    return (
        value !== null
        && typeof value === "object"
        && !Array.isArray(value)
    );
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


function renderPriceHistory(
    history,
    metadata,
) {
    const rows = Array.isArray(history.data)
        ? history.data
        : [];

    if (rows.length === 0) {
        throw new Error(
            "The downloader returned no historical price rows.",
        );
    }

    renderMetadataSummary(
        history,
        metadata,
        rows.length,
    );

    const fragment =
        document.createDocumentFragment();

    /*
     * Downloader data is normally oldest-to-newest.
     * Reverse a copy so newest records display first.
     */
    const displayRows = [...rows].reverse();

    for (const row of displayRows) {
        fragment.appendChild(
            createPriceRow(
                row,
                metadata.currency,
            ),
        );
    }

    priceTableBody.replaceChildren(fragment);

    summarySection.hidden = false;
    resultsSection.hidden = false;
}


function renderMetadataSummary(
    history,
    metadata,
    fallbackRowCount,
) {
    /*
     * Until additional metadata elements are added to the HTML,
     * show the company name and ticker together in the title.
     */
    if (metadata.name) {
        summaryTitle.textContent =
            `${metadata.name} (${metadata.ticker})`;
    } else {
        summaryTitle.textContent =
            metadata.ticker
            || history.ticker
            || tickerInput.value;
    }

    summaryPeriod.textContent =
        history.period || "—";

    summaryInterval.textContent =
        history.interval || "—";

    const rowCount = Number(history.rows);

    summaryRows.textContent =
        Number.isFinite(rowCount)
            ? rowCount.toLocaleString(NUMBER_LOCALE)
            : fallbackRowCount.toLocaleString(
                NUMBER_LOCALE,
            );
}


function createPriceRow(
    row,
    currency,
) {
    const tableRow =
        document.createElement("tr");

    appendCell(
        tableRow,
        row.Date
        || row.date
        || "—",
    );

    appendCell(
        tableRow,
        formatCurrency(
            row.Open ?? row.open,
            currency,
        ),
    );

    appendCell(
        tableRow,
        formatCurrency(
            row.High ?? row.high,
            currency,
        ),
    );

    appendCell(
        tableRow,
        formatCurrency(
            row.Low ?? row.low,
            currency,
        ),
    );

    appendCell(
        tableRow,
        formatCurrency(
            row.Close ?? row.close,
            currency,
        ),
    );

    appendCell(
        tableRow,
        formatVolume(
            row.Volume ?? row.volume,
        ),
    );

    return tableRow;
}


function appendCell(
    row,
    value,
) {
    const cell =
        document.createElement("td");

    cell.textContent = value;
    row.appendChild(cell);
}


function createMessageRow(
    message,
    className,
) {
    const row =
        document.createElement("tr");

    row.className = className;

    const cell =
        document.createElement("td");

    cell.colSpan = 6;
    cell.textContent = message;

    row.appendChild(cell);

    return row;
}


function renderAnalysis(
    analysis,
    metadata,
) {
    metricsPlaceholder.hidden = true;
    metricsGrid.hidden = false;

    const currency =
        metadata.currency
        || DEFAULT_CURRENCY;

    setMetric(
        "current-price",
        formatCurrency(
            analysis.current_price,
            currency,
        ),
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
            currency,
        ),
    );

    setMetric(
        "moving-average-200",
        formatOptionalCurrency(
            analysis.moving_average_200,
            currency,
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
        message
        || "Calculated metrics are unavailable.";
}


function setMetric(
    elementId,
    displayValue,
) {
    const element =
        document.getElementById(elementId);

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
    const element =
        document.getElementById(elementId);

    if (!element) {
        return;
    }

    const numericValue =
        Number(value);

    element.textContent =
        formatPercentage(numericValue);

    element.classList.remove(
        "metric-positive",
        "metric-negative",
    );

    if (!Number.isFinite(numericValue)) {
        return;
    }

    if (numericValue > 0) {
        element.classList.add(
            "metric-positive",
        );
    } else if (numericValue < 0) {
        element.classList.add(
            "metric-negative",
        );
    }
}


function formatCurrency(
    value,
    currency = DEFAULT_CURRENCY,
) {
    const numericValue =
        Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    const normalizedCurrency =
        normalizeCurrency(currency);

    try {
        return new Intl.NumberFormat(
            CURRENCY_LOCALE,
            {
                style: "currency",
                currency: normalizedCurrency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            },
        ).format(numericValue);
    } catch {
        /*
         * Protect the whole page from an unexpected or unsupported
         * currency code returned by the metadata provider.
         */
        return `${normalizedCurrency} ${numericValue.toLocaleString(
            NUMBER_LOCALE,
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            },
        )}`;
    }
}


function formatOptionalCurrency(
    value,
    currency,
) {
    if (
        value === null
        || value === undefined
    ) {
        return "Not enough history";
    }

    return formatCurrency(
        value,
        currency,
    );
}


function formatPercentage(value) {
    const numericValue =
        Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return new Intl.NumberFormat(
        NUMBER_LOCALE,
        {
            style: "percent",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        },
    ).format(numericValue);
}


function formatVolume(value) {
    const numericValue =
        Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return Math.round(
        numericValue,
    ).toLocaleString(NUMBER_LOCALE);
}


function formatDateRange(
    startDate,
    endDate,
) {
    if (!startDate || !endDate) {
        return "—";
    }

    return `${startDate} to ${endDate}`;
}


function getErrorMessage(
    error,
    fallbackMessage,
) {
    if (
        error
        && typeof error.message === "string"
        && error.message.trim()
    ) {
        return error.message;
    }

    return fallbackMessage;
}


function setLoadingState(isLoading) {
    submitButton.disabled = isLoading;
    tickerInput.disabled = isLoading;

    submitButton.textContent = isLoading
        ? "Loading…"
        : "Search";
}


function showStatus(
    message,
    type,
) {
    statusElement.textContent = message;

    statusElement.classList.remove(
        "status-error",
        "status-success",
    );

    if (type === "error") {
        statusElement.classList.add(
            "status-error",
        );
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