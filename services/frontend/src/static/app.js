const form = document.querySelector("#stock-form");
const tickerInput = document.querySelector("#ticker");
const statusElement = document.querySelector("#status");
const summaryElement = document.querySelector("#summary");
const resultsElement = document.querySelector("#results");
const tableBody = document.querySelector("#price-table-body");

const summaryTitle = document.querySelector("#summary-title");
const summaryPeriod = document.querySelector("#summary-period");
const summaryInterval = document.querySelector("#summary-interval");
const summaryRows = document.querySelector("#summary-rows");

function formatNumber(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    return Number(value).toLocaleString();
}

function formatPrice(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    return Number(value).toFixed(2);
}

function renderRows(rows) {
    tableBody.innerHTML = "";

    rows.forEach((row) => {
        const tableRow = document.createElement("tr");

        tableRow.innerHTML = `
            <td>${row.Date ?? "—"}</td>
            <td>${formatPrice(row.Open)}</td>
            <td>${formatPrice(row.High)}</td>
            <td>${formatPrice(row.Low)}</td>
            <td>${formatPrice(row.Close)}</td>
            <td>${formatNumber(row.Volume)}</td>
        `;

        tableBody.appendChild(tableRow);
    });
}

async function loadPrices(ticker) {
    statusElement.textContent = `Loading ${ticker}...`;
    summaryElement.hidden = true;
    resultsElement.hidden = true;

    try {
        const response = await fetch(
            `/api/prices/${encodeURIComponent(ticker)}?period=10y&interval=1d`
        );

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(
                payload.message ||
                payload.error ||
                "Unable to load stock data."
            );
        }

        summaryTitle.textContent = payload.ticker;
        summaryPeriod.textContent = payload.period;
        summaryInterval.textContent = payload.interval;
        summaryRows.textContent = formatNumber(payload.rows);

        renderRows(payload.data);

        summaryElement.hidden = false;
        resultsElement.hidden = false;
        statusElement.textContent = "";
    } catch (error) {
        statusElement.textContent =
            error instanceof Error
                ? error.message
                : "Unable to load stock data.";
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();

    const ticker = tickerInput.value.trim().toUpperCase();

    if (!ticker) {
        statusElement.textContent = "Please enter a ticker.";
        return;
    }

    loadPrices(ticker);
});