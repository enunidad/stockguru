document.addEventListener("DOMContentLoaded", () => {
    const runButton = document.getElementById(
        "run-forecast"
    );

    const addStockButton = document.getElementById(
        "add-stock"
    );

    const status = document.getElementById(
        "forecast-status"
    );

    addStockButton.addEventListener(
        "click",
        addStock
    );

    document
        .getElementById("holdings-container")
        .addEventListener(
            "input",
            handleHoldingInput
        );

    document
        .getElementById("holdings-container")
        .addEventListener(
            "click",
            handleHoldingClick
        );

    runButton.addEventListener(
        "click",
        async () => {
            status.textContent =
                "Running projection...";

            runButton.disabled = true;

            try {
                const payload =
                    buildForecastRequest();

                const response = await fetch(
                    "/api/forecast",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                        body: JSON.stringify(
                            payload
                        ),
                    }
                );

                const result =
                    await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.message
                        || "Unable to generate forecast."
                    );
                }

                renderForecast(result);

                status.textContent = "";

            } catch (error) {
                status.textContent =
                    error.message;

            } finally {
                runButton.disabled = false;
            }
        }
    );
});

let nextHoldingId = 2;


function addStock() {
    const holdingId =
        `holding-${nextHoldingId++}`;

    addHoldingRow(
        holdingId
    );

    addAllocationRow(
        holdingId
    );

    updateRemoveButtons();
}

function addHoldingRow(holdingId) {
    const container = document.getElementById(
        "holdings-container"
    );

    const row = document.createElement(
        "div"
    );

    row.className = "holding-row";
    row.dataset.holdingId = holdingId;

    row.innerHTML = `
        <input
            class="holding-ticker"
            type="text"
            placeholder="Ticker"
            aria-label="Ticker"
        >

        <input
            class="holding-shares"
            type="number"
            value="0"
            min="0"
            aria-label="Shares"
        >

        <input
            class="holding-average-cost"
            type="number"
            placeholder="Latest close"
            min="0"
            step="0.01"
            aria-label="Average cost"
        >

        <button
            class="remove-holding"
            type="button"
            aria-label="Remove stock"
        >
            ×
        </button>
    `;

    container.appendChild(row);

    row.querySelector(
        ".holding-ticker"
    ).focus();
}

function addAllocationRow(holdingId) {
    const container = document.getElementById(
        "allocation-container"
    );

    const row = document.createElement(
        "div"
    );

    row.className = "allocation-row";
    row.dataset.holdingId = holdingId;

    row.innerHTML = `
        <span class="allocation-ticker">
            —
        </span>

        <input
            class="contribution-weight"
            type="number"
            value="0"
            min="0"
            max="100"
        >

        <span class="percentage-symbol">
            %
        </span>
    `;

    container.appendChild(row);
}

function handleHoldingInput(event) {
    if (
        !event.target.classList.contains(
            "holding-ticker"
        )
    ) {
        return;
    }

    const holdingRow =
        event.target.closest(
            "[data-holding-id]"
        );

    const holdingId =
        holdingRow.dataset.holdingId;

    const allocationRow =
        document.querySelector(
            `#allocation-container
             [data-holding-id="${holdingId}"]`
        );

    if (!allocationRow) {
        return;
    }

    const ticker = event.target
        .value
        .trim()
        .toUpperCase();

    allocationRow
        .querySelector(
            ".allocation-ticker"
        )
        .textContent = ticker || "—";
}

function handleHoldingClick(event) {
    if (
        !event.target.classList.contains(
            "remove-holding"
        )
    ) {
        return;
    }

    const holdingRow =
        event.target.closest(
            "[data-holding-id]"
        );

    const holdingId =
        holdingRow.dataset.holdingId;

    holdingRow.remove();

    const allocationRow =
        document.querySelector(
            `#allocation-container
             [data-holding-id="${holdingId}"]`
        );

    if (allocationRow) {
        allocationRow.remove();
    }

    updateRemoveButtons();
}

function updateRemoveButtons() {
    const rows = document.querySelectorAll(
        "#holdings-container .holding-row"
    );

    for (const row of rows) {
        const button = row.querySelector(
            ".remove-holding"
        );

        button.hidden = (
            rows.length === 1
        );
    }
}

function buildForecastRequest() {
    const holdingRows = document.querySelectorAll(
        "#holdings-container .holding-row"
    );

    const holdings = [];

    for (const row of holdingRows) {
        const holdingId =
            row.dataset.holdingId;

        const ticker = row
            .querySelector(
                ".holding-ticker"
            )
            .value
            .trim()
            .toUpperCase();

        const shares = Number(
            row.querySelector(
                ".holding-shares"
            ).value
        );

        const averageCostRaw = row
            .querySelector(
                ".holding-average-cost"
            )
            .value;

        const allocationRow =
            document.querySelector(
                `#allocation-container
                 [data-holding-id="${holdingId}"]`
            );

        const contributionWeight = Number(
            allocationRow
                .querySelector(
                    ".contribution-weight"
                )
                .value
        ) / 100;

        holdings.push({
            ticker: ticker,
            shares: shares,
            average_cost: (
                averageCostRaw === ""
                    ? null
                    : Number(
                        averageCostRaw
                    )
            ),
            contribution_weight:
                contributionWeight,
        });
    }

    validateHoldings(
        holdings
    );

    const contributionAmount = Number(
        document.getElementById(
            "contribution-amount"
        ).value
    );

    validateContributionWeights(
        holdings,
        contributionAmount
    );

    return {
        holdings: holdings,

        years: Number(
            document.getElementById(
                "projection-years"
            ).value
        ),

        contribution_amount:
            contributionAmount,

        contribution_frequency:
            document.getElementById(
                "contribution-frequency"
            ).value,

        drip:
            document.getElementById(
                "drip"
            ).checked,
    };
}

function validateHoldings(holdings) {
    for (const holding of holdings) {
        if (!holding.ticker) {
            throw new Error(
                "Every holding needs a ticker."
            );
        }

        if (
            !Number.isFinite(
                holding.shares
            )
            || holding.shares < 0
        ) {
            throw new Error(
                `${holding.ticker}: shares must be zero or greater.`
            );
        }
    }
}


function validateContributionWeights(
    holdings,
    contributionAmount
) {
    if (contributionAmount <= 0) {
        return;
    }

    const totalWeight = holdings.reduce(
        (total, holding) =>
            total
            + holding.contribution_weight,
        0
    );

    if (
        Math.abs(
            totalWeight - 1
        ) > 0.000001
    ) {
        throw new Error(
            "Contribution allocation must total 100%."
        );
    }
}

function renderForecast(result) {
    const summary = result.summary;

    document.getElementById(
        "projected-value"
    ).textContent = formatMoney(
        summary.future_value
    );

    const years = document.getElementById(
        "projection-years"
    ).value;

    document.getElementById(
        "projection-horizon"
    ).textContent = `${years} years`;

    setMoney(
        "source-investment",
        summary.initial_investment
    );

    setMoney(
        "source-contributions",
        summary.future_contributions
    );

    setMoney(
        "source-growth",
        summary.stock_growth
    );

    setMoney(
        "source-dividends",
        summary.dividends
    );

    setMoney(
        "key-initial-investment",
        summary.initial_investment
    );

    setMoney(
        "key-contributions",
        summary.future_contributions
    );

    setMoney(
        "key-growth",
        summary.stock_growth
    );

    setMoney(
        "key-dividends",
        summary.dividends
    );

    renderHoldings(
        result.holdings
    );

    renderTimeline(
        result.timeline
    );
}


function renderHoldings(holdings) {
    const body = document.getElementById(
        "holdings-body"
    );

    body.innerHTML = "";

    for (const holding of holdings) {
        const row = document.createElement("tr");

        const values = [
            holding.ticker,
            formatMoney(
                holding.initial_investment
            ),
            formatMoney(
                holding.contributions
            ),
            formatMoney(
                holding.growth
            ),
            formatMoney(
                holding.dividends
            ),
            formatMoney(
                holding.future_value
            ),
        ];

        for (const value of values) {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        }

        body.appendChild(row);
    }
}


function renderTimeline(timeline) {
    const container = document.querySelector(
        ".placeholder-chart"
    );

    if (!timeline || timeline.length < 2) {
        return;
    }

    const width = 600;
    const height = 220;
    const padding = 20;

    const maxValue = Math.max(
        ...timeline.map(point => point.value)
    );

    const points = timeline.map(
        (point, index) => {
            const x = padding + (
                index
                / (timeline.length - 1)
            ) * (
                width - padding * 2
            );

            const y = height - padding - (
                point.value / maxValue
            ) * (
                height - padding * 2
            );

            return `${x},${y}`;
        }
    ).join(" ");

    container.innerHTML = "";

    const svg = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "svg"
    );

    svg.setAttribute(
        "viewBox",
        `0 0 ${width} ${height}`
    );

    svg.setAttribute(
        "preserveAspectRatio",
        "none"
    );

    const line = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "polyline"
    );

    line.setAttribute(
        "points",
        points
    );

    line.setAttribute(
        "fill",
        "none"
    );

    line.setAttribute(
        "stroke",
        "currentColor"
    );

    line.setAttribute(
        "stroke-width",
        "3"
    );

    line.setAttribute(
        "stroke-linejoin",
        "round"
    );

    line.setAttribute(
        "stroke-linecap",
        "round"
    );

    svg.appendChild(line);
    container.appendChild(svg);
}


function setMoney(
    id,
    value
) {
    document.getElementById(
        id
    ).textContent = formatMoney(value);
}


function formatMoney(value) {
    return `$${Number(value).toLocaleString(
        "en-CA",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }
    )}`;
}