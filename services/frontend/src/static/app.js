"use strict";


const DEFAULT_PERIOD = "10y";
const DEFAULT_INTERVAL = "1mo";
const DEFAULT_CURRENCY = "USD";


/*
 * Search elements
 */

const stockForm = document.getElementById("stock-form");
const tickerInput = document.getElementById("ticker");
const submitButton = stockForm.querySelector(
    'button[type="submit"]',
);
const statusElement = document.getElementById("status");


/*
 * Metadata elements
 */

const metadataSection = document.getElementById(
    "metadata-section",
);
const companyNameElement = document.getElementById(
    "company-name",
);
const metadataTickerElement = document.getElementById(
    "metadata-ticker",
);
const currencyElement = document.getElementById(
    "currency",
);
const industryElement = document.getElementById(
    "industry",
);
const countryElement = document.getElementById(
    "country",
);
const exchangeElement = document.getElementById(
    "exchange",
);


/*
 * Results elements
 */

const resultsSection = document.getElementById(
    "results-section",
);
const historyDescriptionElement = document.getElementById(
    "history-description",
);
const priceTableBody = document.getElementById(
    "price-table-body",
);


/*
 * Metric elements
 */

const cagrElement = document.getElementById("cagr");
const volatilityElement = document.getElementById(
    "volatility",
);
const maxDrawdownElement = document.getElementById(
    "max-drawdown",
);
const smaElement = document.getElementById("sma");
const emaElement = document.getElementById("ema");


stockForm.addEventListener(
    "submit",
    handleStockSearch,
);


async function handleStockSearch(event) {
    event.preventDefault();

    const ticker = tickerInput.value
        .trim()
        .toUpperCase();

    if (!ticker) {
        setStatus(
            "Enter a ticker symbol.",
            "error",
        );
        return;
    }

    setLoadingState(true);
    hideResults();

    try {
        setStatus(
            `Loading information for ${ticker}...`,
            "loading",
        );

        const metadataPromise = loadMetadata(ticker);
        const historyPromise = loadPrices(ticker);
        const analysisPromise = loadAnalysis(ticker);

        /*
         * Metadata should not prevent the price history and
         * analysis from displaying if metadata retrieval fails.
         */
        const metadata = await metadataPromise.catch(
            () => ({
                ticker,
                currency: DEFAULT_CURRENCY,
            }),
        );

        const [history, analysis] = await Promise.all([
            historyPromise,
            analysisPromise,
        ]);

        renderMetadata(
            metadata,
            ticker,
        );

        renderPriceHistory(
            history,
            metadata,
        );

        renderAnalysis(
            analysis,
            metadata,
        );

        metadataSection.hidden = false;
        resultsSection.hidden = false;

        setStatus(
            `Showing analysis for ${ticker}.`,
            "success",
        );
    } catch (error) {
        console.error(error);

        hideResults();

        setStatus(
            error.message ||
                `Unable to load information for ${ticker}.`,
            "error",
        );
    } finally {
        setLoadingState(false);
    }
}


async function loadMetadata(ticker) {
    return fetchJson(
        `/api/metadata/${encodeURIComponent(ticker)}`,
    );
}


async function loadPrices(ticker) {
    const query = new URLSearchParams({
        period: DEFAULT_PERIOD,
        interval: DEFAULT_INTERVAL,
    });

    return fetchJson(
        `/api/prices/${encodeURIComponent(ticker)}?${query}`,
    );
}


async function loadAnalysis(ticker) {
    const query = new URLSearchParams({
        period: DEFAULT_PERIOD,
        interval: DEFAULT_INTERVAL,
    });

    return fetchJson(
        `/api/analysis/${encodeURIComponent(ticker)}?${query}`,
    );
}


async function fetchJson(url) {
    const response = await fetch(
        url,
        {
            headers: {
                Accept: "application/json",
            },
        },
    );

    let payload;

    try {
        payload = await response.json();
    } catch {
        throw new Error(
            "The server returned an invalid response.",
        );
    }

    if (!response.ok) {
        throw new Error(
            payload.message ||
                payload.error ||
                "The request could not be completed.",
        );
    }

    return payload;
}


function renderMetadata(metadata, fallbackTicker) {
    companyNameElement.textContent =
        metadata.company_name ||
        metadata.name ||
        metadata.long_name ||
        "—";

    metadataTickerElement.textContent =
        metadata.ticker ||
        fallbackTicker;

    currencyElement.textContent =
        metadata.currency ||
        "—";

    industryElement.textContent =
        metadata.industry ||
        "—";
    exchangeElement.textContent = 
        metadata.exchange ||
        "—";
    countryElement.textContent = 
        metadata.country ||
        "—";
}


function renderPriceHistory(history, metadata) {
    const rows = Array.isArray(history.data)
        ? history.data
        : [];

    if (rows.length === 0) {
        throw new Error(
            "The downloader returned no historical price rows.",
        );
    }

    const ticker =
        history.ticker ||
        metadata.ticker ||
        tickerInput.value.trim().toUpperCase();

    const period =
        history.period ||
        DEFAULT_PERIOD;

    const interval =
        history.interval ||
        DEFAULT_INTERVAL;

    historyDescriptionElement.textContent =
        `${ticker} · ${period} · ${interval} · ` +
        `${rows.length.toLocaleString("en-CA")} rows`;

    const fragment = document.createDocumentFragment();

    /*
     * The downloader normally returns oldest-to-newest data.
     * Reverse a copy so the newest row appears first.
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
}


function createPriceRow(row, currency) {
    const tableRow = document.createElement("tr");

    const values = [
        formatDate(
            getValue(
                row,
                "Date",
                "date",
            ),
        ),
        formatCurrency(
            getValue(
                row,
                "Open",
                "open",
            ),
            currency,
        ),
        formatCurrency(
            getValue(
                row,
                "High",
                "high",
            ),
            currency,
        ),
        formatCurrency(
            getValue(
                row,
                "Low",
                "low",
            ),
            currency,
        ),
        formatCurrency(
            getValue(
                row,
                "Close",
                "close",
            ),
            currency,
        ),
        formatCurrency(
            getValue(
                row,
                "Price",
                "price",
                "Average",
                "average",
            ),
            currency,
        ),
        formatNumber(
            getValue(
                row,
                "Volume",
                "volume",
            ),
            0,
        ),
    ];

    for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        tableRow.appendChild(cell);
    }

    return tableRow;
}


function renderAnalysis(analysis, metadata) {
    /*
     * This allows the analyzer to return the metrics either
     * directly or inside a "metrics" object.
     */
    const metrics = analysis.metrics || analysis;

    cagrElement.textContent = formatPercentage(
        getValue(
            metrics,
            "cagr",
            "CAGR",
        ),
    );

    volatilityElement.textContent = formatPercentage(
        getValue(
            metrics,
            "annualized_volatility",
            "volatility",
            "Volatility",
        ),
    );

    maxDrawdownElement.textContent = formatPercentage(
        getValue(
            metrics,
            "max_drawdown",
            "drawdown",
            "maximum_drawdown",
        ),
    );

    smaElement.textContent = formatCurrency(
        getValue(
            metrics,
            "moving_average_50",
        ),
        metadata.currency,
    );

    emaElement.textContent = formatCurrency(
        getValue(
            metrics,
            "moving_average_200",
        ),
        metadata.currency,
    );
}


function getValue(object, ...keys) {
    if (!object) {
        return null;
    }

    for (const key of keys) {
        if (
            Object.prototype.hasOwnProperty.call(
                object,
                key,
            )
        ) {
            return object[key];
        }
    }

    return null;
}


function formatCurrency(value, currency) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    const validCurrency =
        typeof currency === "string" &&
        currency.trim()
            ? currency.trim().toUpperCase()
            : DEFAULT_CURRENCY;

    try {
        return new Intl.NumberFormat(
            "en-CA",
            {
                style: "currency",
                currency: validCurrency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            },
        ).format(numericValue);
    } catch {
        return numericValue.toLocaleString(
            "en-CA",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            },
        );
    }
}


function formatPercentage(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    /*
     * Analyzer calculations usually return decimals:
     *
     * 0.0825 becomes 8.25%
     */
    return new Intl.NumberFormat(
        "en-CA",
        {
            style: "percent",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        },
    ).format(numericValue);
}


function formatNumber(value, decimalPlaces = 2) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "—";
    }

    return numericValue.toLocaleString(
        "en-CA",
        {
            minimumFractionDigits: decimalPlaces,
            maximumFractionDigits: decimalPlaces,
        },
    );
}


function formatDate(value) {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    /*
     * The downloader already formats daily rows as YYYY-MM-DD
     * and monthly rows as YYYY-MM. Do not reinterpret them as
     * JavaScript dates because that can create timezone shifts.
     */
    return String(value);
}


function setLoadingState(isLoading) {
    tickerInput.disabled = isLoading;
    submitButton.disabled = isLoading;

    submitButton.textContent = isLoading
        ? "Loading..."
        : "Analyze";
}


function setStatus(message, state) {
    statusElement.textContent = message;
    statusElement.dataset.state = state;
}


function hideResults() {
    metadataSection.hidden = true;
    resultsSection.hidden = true;

    priceTableBody.replaceChildren();

    companyNameElement.textContent = "—";
    metadataTickerElement.textContent = "—";
    currencyElement.textContent = "—";
    industryElement.textContent = "—";
    exchangeElement.textContent = "—";
    countryElement.textContent = "—";

    cagrElement.textContent = "—";
    volatilityElement.textContent = "—";
    maxDrawdownElement.textContent = "—";
    smaElement.textContent = "—";
    emaElement.textContent = "—";
}