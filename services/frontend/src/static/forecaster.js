"use strict";


/* =========================================================
   StockGuru Portfolio Forecaster
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {
        initializeForecaster();
    }
);


/* =========================================================
   State
   ========================================================= */

let nextHoldingId = 2;


/* =========================================================
   Initialization
   ========================================================= */

function initializeForecaster() {

    const addStockButton =
        document.getElementById("add-stock");

    const addStockBottomButton =
        document.getElementById("add-stock-bottom");

    const runForecastButton =
        document.getElementById("run-forecast");

    const projectionYears =
        document.getElementById("projection-years");

    const holdingsContainer =
        document.getElementById("holdings-container");

    const contributionAmount =
        document.getElementById("contribution-amount");


    if (addStockButton) {
        addStockButton.addEventListener(
            "click",
            addHolding
        );
    }


    if (addStockBottomButton) {
        addStockBottomButton.addEventListener(
            "click",
            addHolding
        );
    }


    if (runForecastButton) {
        runForecastButton.addEventListener(
            "click",
            runForecast
        );
    }


    if (projectionYears) {

        projectionYears.addEventListener(
            "input",
            updateProjectionHorizon
        );

        updateProjectionHorizon();
    }


    if (holdingsContainer) {

        holdingsContainer.addEventListener(
            "input",
            handleHoldingInput
        );

        holdingsContainer.addEventListener(
            "click",
            handleHoldingClick
        );
    }


    if (contributionAmount) {

        contributionAmount.addEventListener(
            "input",
            updateAllocationState
        );
    }


    initializePortfolioModeButtons();

    syncAllocations();
    updateRemoveButtons();
    updateAllocationState();
}


/* =========================================================
   Portfolio Mode
   ========================================================= */

function initializePortfolioModeButtons() {

    const modeButtons =
        document.querySelectorAll(".mode-button");


    modeButtons.forEach(
        (button) => {

            button.addEventListener(
                "click",
                () => {

                    modeButtons.forEach(
                        (item) => {
                            item.classList.remove("active");
                        }
                    );

                    button.classList.add("active");
                }
            );

        }
    );
}


/* =========================================================
   Holdings
   ========================================================= */

function addHolding() {

    const container =
        document.getElementById(
            "holdings-container"
        );

    if (!container) {
        return;
    }


    const holdingId =
        `holding-${nextHoldingId}`;

    nextHoldingId += 1;


    const row =
        document.createElement("div");

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
            step="0.01"
            aria-label="Shares owned"
        >

        <input
            class="holding-average-cost"
            type="number"
            placeholder="Latest close"
            min="0"
            step="0.01"
            aria-label="Average cost per share"
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


    syncAllocations();
    updateRemoveButtons();
    updateAllocationState();


    const tickerInput =
        row.querySelector(
            ".holding-ticker"
        );

    tickerInput?.focus();
}


function handleHoldingInput(event) {

    const target = event.target;


    if (
        target.classList.contains(
            "holding-ticker"
        )
    ) {

        target.value =
            target.value.toUpperCase();

        syncAllocations();
    }
}


function handleHoldingClick(event) {

    const button =
        event.target.closest(
            ".remove-holding"
        );

    if (!button) {
        return;
    }


    const row =
        button.closest(
            ".holding-row"
        );

    if (!row) {
        return;
    }


    row.remove();

    syncAllocations();
    updateRemoveButtons();
    updateAllocationState();
}


function updateRemoveButtons() {

    const rows =
        document.querySelectorAll(
            ".holding-row"
        );

    const shouldHide =
        rows.length <= 1;


    rows.forEach(
        (row) => {

            const button =
                row.querySelector(
                    ".remove-holding"
                );

            if (button) {
                button.hidden = shouldHide;
            }

        }
    );
}


/* =========================================================
   Contribution Allocation
   ========================================================= */

function syncAllocations() {

    const container =
        document.getElementById(
            "allocation-container"
        );

    if (!container) {
        return;
    }


    const existingWeights =
        readExistingAllocationWeights();


    const holdings =
        Array.from(
            document.querySelectorAll(
                ".holding-row"
            )
        );


    container.innerHTML = "";


    holdings.forEach(
        (holding, index) => {

            const holdingId =
                holding.dataset.holdingId;


            const tickerInput =
                holding.querySelector(
                    ".holding-ticker"
                );


            const ticker =
                tickerInput?.value
                    .trim()
                    .toUpperCase() || "—";


            let weight =
                existingWeights.get(
                    holdingId
                );


            if (weight === undefined) {

                /*
                    The first stock begins at 100%.

                    Newly-added holdings start at 0%
                    so the user's existing allocation
                    is not silently changed.
                */

                weight =
                    holdings.length === 1
                        ? 100
                        : (
                            index === 0 &&
                            existingWeights.size === 0
                                ? 100
                                : 0
                        );
            }


            const allocationRow =
                document.createElement("div");

            allocationRow.className =
                "allocation-row";

            allocationRow.dataset.holdingId =
                holdingId;


            allocationRow.innerHTML = `
                <span class="allocation-ticker">
                    ${escapeHtml(ticker)}
                </span>

                <div class="percentage-input">

                    <input
                        class="contribution-weight"
                        type="number"
                        value="${weight}"
                        min="0"
                        max="100"
                        step="1"
                        aria-label="${escapeHtml(ticker)} contribution allocation"
                    >

                    <span>
                        %
                    </span>

                </div>
            `;


            container.appendChild(
                allocationRow
            );
        }
    );
}


function readExistingAllocationWeights() {

    const result =
        new Map();


    document
        .querySelectorAll(
            ".allocation-row"
        )
        .forEach(
            (row) => {

                const holdingId =
                    row.dataset.holdingId;


                const input =
                    row.querySelector(
                        ".contribution-weight"
                    );


                if (
                    !holdingId ||
                    !input
                ) {
                    return;
                }


                const value =
                    Number(input.value);


                if (
                    Number.isFinite(value)
                ) {

                    result.set(
                        holdingId,
                        value
                    );

                }

            }
        );


    return result;
}


function updateAllocationState() {

    const contributionAmount =
        readNumberInput(
            "contribution-amount",
            0
        );


    const allocationInputs =
        document.querySelectorAll(
            ".contribution-weight"
        );


    const disabled =
        contributionAmount <= 0;


    allocationInputs.forEach(
        (input) => {
            input.disabled = disabled;
        }
    );
}


/* =========================================================
   Horizon
   ========================================================= */

function updateProjectionHorizon() {

    const years =
        readNumberInput(
            "projection-years",
            20
        );


    const element =
        document.getElementById(
            "projection-horizon"
        );

    if (!element) {
        return;
    }


    const displayYears =
        Number.isFinite(years)
            ? Math.max(
                1,
                Math.round(years)
            )
            : 20;


    element.textContent =
        `${displayYears} ${
            displayYears === 1
                ? "YEAR"
                : "YEARS"
        }`;
}


/* =========================================================
   Request Building
   ========================================================= */

function buildForecastRequest() {

    const holdings =
        readHoldings();


    if (holdings.length === 0) {

        throw new Error(
            "Add at least one stock before running a projection."
        );

    }


    const years =
        readNumberInput(
            "projection-years"
        );


    if (
        !Number.isFinite(years) ||
        years <= 0
    ) {

        throw new Error(
            "Time horizon must be greater than zero."
        );

    }


    const contributionAmount =
        readNumberInput(
            "contribution-amount",
            0
        );


    if (
        !Number.isFinite(
            contributionAmount
        ) ||
        contributionAmount < 0
    ) {

        throw new Error(
            "Recurring investment cannot be negative."
        );

    }


    const contributionFrequency =
        document.getElementById(
            "contribution-frequency"
        )?.value || "monthly";


    const drip =
        Boolean(
            document.getElementById(
                "drip"
            )?.checked
        );


    applyContributionWeights(
        holdings,
        contributionAmount
    );


    return {
        holdings,

        years:
            Math.round(years),

        contribution_amount:
            contributionAmount,

        contribution_frequency:
            contributionFrequency,

        drip
    };
}


function readHoldings() {

    const rows =
        document.querySelectorAll(
            ".holding-row"
        );


    const holdings = [];

    const seenTickers =
        new Set();


    rows.forEach(
        (row) => {

            const ticker =
                row
                    .querySelector(
                        ".holding-ticker"
                    )
                    ?.value
                    .trim()
                    .toUpperCase() || "";


            const shares =
                Number(
                    row.querySelector(
                        ".holding-shares"
                    )?.value
                );


            const averageCostInput =
                row.querySelector(
                    ".holding-average-cost"
                );


            const averageCostText =
                averageCostInput
                    ?.value
                    .trim() || "";


            if (!ticker) {

                throw new Error(
                    "Every portfolio row needs a ticker."
                );

            }


            if (
                seenTickers.has(ticker)
            ) {

                throw new Error(
                    `${ticker} appears more than once in the portfolio.`
                );

            }


            seenTickers.add(ticker);


            if (
                !Number.isFinite(shares) ||
                shares < 0
            ) {

                throw new Error(
                    `Shares for ${ticker} must be zero or greater.`
                );

            }


            let averageCost = null;


            if (
                averageCostText !== ""
            ) {

                averageCost =
                    Number(
                        averageCostText
                    );


                if (
                    !Number.isFinite(
                        averageCost
                    ) ||
                    averageCost <= 0
                ) {

                    throw new Error(
                        `Average cost for ${ticker} must be greater than zero.`
                    );

                }

            }


            holdings.push({
                holdingId:
                    row.dataset.holdingId,

                ticker,

                shares,

                average_cost:
                    averageCost,

                contribution_weight:
                    0
            });

        }
    );


    return holdings;
}


function applyContributionWeights(
    holdings,
    contributionAmount
) {

    /*
        If no contributions are being made,
        allocation has no effect.

        contribution_weight is explicitly zero
        and holdingId is removed because it is
        frontend-only state.
    */

    if (
        contributionAmount <= 0
    ) {

        holdings.forEach(
            (holding) => {

                holding.contribution_weight = 0;

                delete holding.holdingId;

            }
        );

        return;
    }


    let totalPercent = 0;


    holdings.forEach(
        (holding) => {

            const allocationRow =
                document.querySelector(
                    `.allocation-row[data-holding-id="${holding.holdingId}"]`
                );


            const weightInput =
                allocationRow?.querySelector(
                    ".contribution-weight"
                );


            const percent =
                Number(
                    weightInput?.value
                );


            if (
                !Number.isFinite(percent) ||
                percent < 0 ||
                percent > 100
            ) {

                throw new Error(
                    `Contribution allocation for ${holding.ticker} must be between 0% and 100%.`
                );

            }


            totalPercent += percent;


            /*
                Forecaster expects a decimal
                contribution weight between
                0 and 1.
            */

            holding.contribution_weight =
                percent / 100;
        }
    );


    if (
        Math.abs(
            totalPercent - 100
        ) > 0.001
    ) {

        throw new Error(
            `Contribution allocation must total 100%. It currently totals ${formatPercent(totalPercent, 1)}.`
        );

    }


    holdings.forEach(
        (holding) => {

            delete holding.holdingId;

        }
    );
}


/* =========================================================
   Forecast Request
   ========================================================= */

async function runForecast() {

    const button =
        document.getElementById(
            "run-forecast"
        );


    try {

        clearStatus();


        const payload =
            buildForecastRequest();


        setLoadingState(
            true,
            "Running projection..."
        );


        const response =
            await fetch(
                "/api/forecast",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(payload)
                }
            );


        let data = null;


        try {

            data =
                await response.json();

        }
        catch {

            data = null;

        }


        if (!response.ok) {

            const message =
                data?.message ||
                data?.error ||
                `Forecast request failed with status ${response.status}.`;


            throw new Error(
                message
            );

        }


        validateForecastResponse(
            data
        );


        /*
            Render the authoritative forecast
            results immediately.
        */

        renderForecast(
            data,
            payload
        );


        setStatus(
            "Projection complete.",
            "success"
        );


        /*
            ChartMgr is presentation-only.

            Do not make the successful forecast
            depend on the chart request succeeding.
        */

        void renderPortfolioChart(
            data.summary
        );

    }
    catch (error) {

        console.error(
            "Forecast failed:",
            error
        );


        setStatus(
            error instanceof Error
                ? error.message
                : "Unable to run projection.",
            "error"
        );

    }
    finally {

        if (button) {
            button.disabled = false;
        }


        setLoadingState(false);

    }
}


/* =========================================================
   Response Validation
   ========================================================= */

function validateForecastResponse(
    data
) {

    if (
        !data ||
        typeof data !== "object"
    ) {

        throw new Error(
            "Forecaster returned an invalid response."
        );

    }


    if (
        !data.summary ||
        typeof data.summary !== "object"
    ) {

        throw new Error(
            "Forecaster response is missing the portfolio summary."
        );

    }


    if (
        !Array.isArray(
            data.holdings
        )
    ) {

        throw new Error(
            "Forecaster response is missing holding results."
        );

    }


    const requiredSummaryFields = [
        "initial_investment",
        "current_growth",
        "future_contributions",
        "stock_growth",
        "dividends",
        "future_value"
    ];


    requiredSummaryFields.forEach(
        (field) => {

            if (
                !Number.isFinite(
                    Number(
                        data.summary[field]
                    )
                )
            ) {

                throw new Error(
                    `Forecaster response is missing ${field}.`
                );

            }

        }
    );
}


/* =========================================================
   Main Renderer
   ========================================================= */

function renderForecast(
    data,
    request
) {

    renderProjectedValue(
        data.summary
    );


    renderPortfolioOverview(
        data.summary
    );


    renderHoldingsTable(
        data.holdings,
        request
    );


    updateProjectionHorizon();
}


/* =========================================================
   Projected Value / Ticker Delta
   ========================================================= */

function renderProjectedValue(
    summary
) {

    const futureValue =
        Number(
            summary.future_value
        );


    const initialInvestment =
        Number(
            summary.initial_investment
        );


    const futureContributions =
        Number(
            summary.future_contributions
        );


    /*
        Out-of-pocket money is only money
        actually supplied by the user.

        DRIP is not included because dividends
        are generated by the portfolio.
    */

    const outOfPocket =
        initialInvestment +
        futureContributions;


    const delta =
        futureValue -
        outOfPocket;


    const deltaPercent =
        outOfPocket > 0
            ? (
                delta /
                outOfPocket
            ) * 100
            : 0;


    setText(
        "projected-value",
        formatCurrency(
            futureValue
        )
    );


    setText(
        "projected-delta",
        formatSignedCurrency(
            delta
        )
    );


    setText(
        "projected-delta-percent",
        formatSignedPercent(
            deltaPercent
        )
    );


    const change =
        document.querySelector(
            ".projection-change"
        );


    if (!change) {
        return;
    }


    change.classList.remove(
        "positive",
        "negative",
        "neutral"
    );


    if (delta > 0) {

        change.classList.add(
            "positive"
        );

    }
    else if (delta < 0) {

        change.classList.add(
            "negative"
        );

    }
    else {

        change.classList.add(
            "neutral"
        );

    }
}


/* =========================================================
   Portfolio Overview Numbers
   ========================================================= */

function renderPortfolioOverview(
    summary
) {

    const invested =
        Number(
            summary.initial_investment
        );


    const currentGrowth =
        Number(
            summary.current_growth
        );


    const contributions =
        Number(
            summary.future_contributions
        );


    const stockGrowth =
        Number(
            summary.stock_growth
        );


    const dividends =
        Number(
            summary.dividends
        );


    const total =
        Number(
            summary.future_value
        );


    setText(
        "source-investment",
        formatCurrency(
            invested
        )
    );


    setText(
        "source-current-growth",
        formatCurrency(
            currentGrowth
        )
    );


    setText(
        "source-contributions",
        formatCurrency(
            contributions
        )
    );


    setText(
        "source-growth",
        formatCurrency(
            stockGrowth
        )
    );


    setText(
        "source-dividends",
        formatCurrency(
            dividends
        )
    );


    setText(
        "source-total",
        formatCurrency(
            total
        )
    );


    setText(
        "source-investment-percent",
        percentOfTotal(
            invested,
            total
        )
    );


    setText(
        "source-current-growth-percent",
        percentOfTotal(
            currentGrowth,
            total
        )
    );


    setText(
        "source-contributions-percent",
        percentOfTotal(
            contributions,
            total
        )
    );


    setText(
        "source-growth-percent",
        percentOfTotal(
            stockGrowth,
            total
        )
    );


    setText(
        "source-dividends-percent",
        percentOfTotal(
            dividends,
            total
        )
    );
}


/* =========================================================
   Portfolio Overview Chart
   ========================================================= */

async function renderPortfolioChart(
    summary
) {

    const container =
        document.getElementById(
            "portfolio-overview-chart"
        );


    if (!container) {
        return;
    }


    const payload = {

        initial_investment:
            Number(
                summary.initial_investment
            ),

        current_growth:
            Number(
                summary.current_growth
            ),

        future_contributions:
            Number(
                summary.future_contributions
            ),

        stock_growth:
            Number(
                summary.stock_growth
            ),

        dividends:
            Number(
                summary.dividends
            )
    };


    try {

        const response =
            await fetch(
                "/api/charting/portfolio_overview",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        let data = null;


        try {

            data =
                await response.json();

        }
        catch {

            data = null;

        }


        if (!response.ok) {

            throw new Error(
                data?.message ||
                "Unable to load portfolio overview chart."
            );

        }


        validatePortfolioChartResponse(
            data
        );


        drawPortfolioChart(
            container,
            data, summary
        );

    }
    catch (error) {

        /*
            Chart failure must not invalidate
            the forecast itself.
        */

        console.error(
            "Portfolio overview chart failed:",
            error
        );


        renderPortfolioChartFallback(
            container,
            summary
        );

    }
}


/* =========================================================
   Chart Response Validation
   ========================================================= */

function validatePortfolioChartResponse(
    data
) {

    if (
        !data ||
        typeof data !== "object"
    ) {

        throw new Error(
            "ChartMgr returned an invalid portfolio chart."
        );

    }


    if (
        data.chart_type !== "donut" &&
        data.chart_type !== "bar"
    ) {

        throw new Error(
            "ChartMgr returned an unsupported chart type."
        );

    }


    if (
        !Array.isArray(
            data.labels
        ) ||
        !Array.isArray(
            data.values
        )
    ) {

        throw new Error(
            "Portfolio chart is missing labels or values."
        );

    }


    if (
        data.labels.length !==
        data.values.length
    ) {

        throw new Error(
            "Portfolio chart labels and values do not match."
        );

    }


    if (
        data.values.some(
            (value) =>
                !Number.isFinite(
                    Number(value)
                )
        )
    ) {

        throw new Error(
            "Portfolio chart contains invalid values."
        );

    }


    if (
        !Number.isFinite(
            Number(data.total)
        )
    ) {

        throw new Error(
            "Portfolio chart is missing its total."
        );

    }
}


/* =========================================================
   Chart Dispatcher
   ========================================================= */

function drawPortfolioChart(
    container,
    chart,
    summary
) {

    /*
        Remove the placeholder class because its
        CSS contains the fake conic-gradient donut
        and ::after center hole.
    */

    container.className =
        "portfolio-chart-rendered";


    container.innerHTML = "";


    const canvas =
        document.createElement(
            "canvas"
        );


    canvas.setAttribute(
        "aria-label",
        chart.title ||
        "Portfolio Overview"
    );


    canvas.setAttribute(
        "role",
        "img"
    );


    container.appendChild(
        canvas
    );


    const colors =
        getPortfolioChartColors();


    if (
        chart.chart_type === "bar"
    ) {

        drawPortfolioBarChart(
            canvas,
            chart,
            colors
        );

        return;
    }


    drawPortfolioDonutChart(
        canvas,
        chart,
        colors,
        summary
    );
}


/* =========================================================
   Donut Chart
   ========================================================= */

function drawPortfolioDonutChart(
    canvas,
    chart,
    colors,
    summary
) {

    const isMobile =
        window.innerWidth <= 700;

    const size =
        isMobile ? 240 : 320;

    const dpr =
        window.devicePixelRatio || 1;


    canvas.width =
        size * dpr;

    canvas.height =
        size * dpr;


    canvas.style.width =
        `${size}px`;

    canvas.style.height =
        `${size}px`;


    const context =
        canvas.getContext("2d");


    if (!context) {
        return;
    }


    context.scale(
        dpr,
        dpr
    );


    const values =
        chart.values.map(
            Number
        );


    const total =
        Number(
            chart.total
        );


    if (
        !Number.isFinite(total) ||
        total <= 0
    ) {
        return;
    }


    const center =
        size / 2;


    const radius =
        isMobile ? 94 : 126;


    const lineWidth =
        isMobile ? 38 : 52;


    let angle =
        -Math.PI / 2;


    values.forEach(
        (value, index) => {

            if (
                value <= 0
            ) {
                return;
            }


            const slice =
                (
                    value /
                    total
                ) *
                Math.PI *
                2;


            context.beginPath();


            context.arc(
                center,
                center,
                radius,
                angle,
                angle + slice
            );


            context.strokeStyle =
                colors[
                    index %
                    colors.length
                ];


            context.lineWidth =
                lineWidth;


            context.stroke();


            angle += slice;

        }
    );


   /* -----------------------------------------------------
    Center Value
    ----------------------------------------------------- */

    const initialInvestment =
        Number(
            summary.initial_investment
        );


    const futureContributions =
        Number(
            summary.future_contributions
        );


    const outOfPocket =
        initialInvestment +
        futureContributions;


    const delta =
        total -
        outOfPocket;


    const totalGrowthPercent =
        outOfPocket > 0
            ? (
                delta /
                outOfPocket
            ) * 100
            : 0;


    const years =
        Math.max(
            1,
            Math.round(
                readNumberInput(
                    "projection-years",
                    20
                )
            )
        );


    const averageAnnualGrowth =
        (
            outOfPocket > 0 &&
            total > 0
        )
            ? (
                Math.pow(
                    total / outOfPocket,
                    1 / years
                ) - 1
            ) * 100
            : 0;


    /* -----------------------------------------------------
    Center Text
    ----------------------------------------------------- */

    const deltaSymbol =
        "Δ";

    const growthSymbol =
        totalGrowthPercent >= 0
            ? "▲"
            : "▼";

    const annualSymbol =
        averageAnnualGrowth >= 0
            ? "↗"
            : "↘";


    context.textAlign =
        "center";


    context.textBaseline =
        "middle";


    /* Projected portfolio value */

    context.fillStyle =
        getCssColor(
            "--sg-text",
            "#102a3a"
        );

    context.font =
        isMobile
            ? "800 22px Inter, sans-serif"
            : "800 28px Inter, sans-serif";

    context.fillText(
        formatCompactCurrency(
            total
        ),
        center,
        center - (isMobile ? 34 : 42)
    );


    /* Dollar delta */

    context.fillStyle =
        delta >= 0
            ? getCssColor(
                "--sg-teal",
                "#4f8f88"
            )
            : getCssColor(
                "--sg-orange",
                "#d66b3d"
            );

    context.font =
        isMobile
            ? "700 10px Inter, sans-serif"
            : "700 12px Inter, sans-serif";

    context.fillText(
        `${deltaSymbol} ${formatSignedCompactCurrency(delta)}`,
        center,
        center - (isMobile ? 10 : 14)
    );


    /* Total growth % */

    context.fillText(
        `${growthSymbol} ${formatSignedPercent(totalGrowthPercent).replace("+", "").replace("-", "")}`,
        center,
        center + (isMobile ? 10 : 12)
    );


    /* Avg annual growth */

    context.fillStyle =
        getCssColor(
            "--sg-text-muted",
            "#69757c"
        );

    context.font =
        isMobile
            ? "600 9px Inter, sans-serif"
            : "600 11px Inter, sans-serif";

    context.fillText(
        `${annualSymbol} ${formatSignedPercent(averageAnnualGrowth).replace("+", "").replace("-", "")}/yr`,
        center,
        center + (isMobile ? 26 : 32)
    );
}


/* =========================================================
   Bar Chart
   ========================================================= */

function drawPortfolioBarChart(
    canvas,
    chart,
    colors
) {

    /*
        ChartMgr returns bar when one of the
        composition values is negative.

        Pie/donut charts cannot meaningfully
        represent a negative slice.
    */

    const width = 300;
    const height = 240;

    const dpr =
        window.devicePixelRatio || 1;


    canvas.width =
        width * dpr;

    canvas.height =
        height * dpr;


    canvas.style.width =
        `${width}px`;

    canvas.style.height =
        `${height}px`;


    const context =
        canvas.getContext("2d");


    if (!context) {
        return;
    }


    context.scale(
        dpr,
        dpr
    );


    const values =
        chart.values.map(
            Number
        );


    const maximum =
        Math.max(
            ...values.map(
                (value) =>
                    Math.abs(value)
            ),
            1
        );


    const chartTop = 12;
    const chartBottom = height - 18;


    const availableHeight =
        chartBottom -
        chartTop;


    const barWidth = 36;


    const gap =
        (
            width -
            (
                barWidth *
                values.length
            )
        ) /
        (
            values.length +
            1
        );


    const zeroY =
        height / 2;


    /* -----------------------------------------------------
       Zero line
       ----------------------------------------------------- */

    context.beginPath();


    context.moveTo(
        10,
        zeroY
    );


    context.lineTo(
        width - 10,
        zeroY
    );


    context.strokeStyle =
        getCssColor(
            "--sg-border",
            "#d9d1c4"
        );


    context.lineWidth = 1;


    context.stroke();


    /* -----------------------------------------------------
       Bars
       ----------------------------------------------------- */

    values.forEach(
        (value, index) => {

            const magnitude =
                (
                    Math.abs(value) /
                    maximum
                ) *
                (
                    availableHeight /
                    2 -
                    15
                );


            const x =
                gap +
                index *
                (
                    barWidth +
                    gap
                );


            const y =
                value >= 0
                    ? zeroY - magnitude
                    : zeroY;


            context.fillStyle =
                value < 0
                    ? getCssColor(
                        "--sg-orange",
                        "#d66b3d"
                    )
                    : colors[
                        index %
                        colors.length
                    ];


            context.fillRect(
                x,
                y,
                barWidth,
                magnitude
            );

        }
    );
}


/* =========================================================
   Chart Fallback
   ========================================================= */

function renderPortfolioChartFallback(
    container,
    summary
) {

    container.className =
        "portfolio-chart-rendered";


    container.innerHTML = `
        <div class="chart-empty-state">

            <span>
                ${escapeHtml(
                    formatCompactCurrency(
                        Number(
                            summary.future_value
                        )
                    )
                )}
            </span>

            <small>
                Projected Value
            </small>

        </div>
    `;
}


/* =========================================================
   Chart Theme Colors
   ========================================================= */

function getPortfolioChartColors() {

    /*
        Ordering matches the Portfolio Overview
        rows:

        1. Total Invested
        2. Current Growth
        3. Future Contributions
        4. Stock Growth
        5. Dividends / DRIP
    */

    return [

        getCssColor(
            "--sg-navy",
            "#102a3a"
        ),

        getCssColor(
            "--sg-gold",
            "#d9a441"
        ),

        getCssColor(
            "--sg-teal",
            "#4f8f88"
        ),

        getCssColor(
            "--sg-orange",
            "#d66b3d"
        ),

        getCssColor(
            "--sg-border-strong",
            "#b9afa0"
        )
    ];
}


function getCssColor(
    variable,
    fallback
) {

    const value =
        getComputedStyle(
            document.documentElement
        )
            .getPropertyValue(
                variable
            )
            .trim();


    return value || fallback;
}


/* =========================================================
   Holdings Detail Table
   ========================================================= */

function renderHoldingsTable(
    holdings,
    request
) {

    const tbody =
        document.getElementById(
            "holdings-body"
        );


    if (!tbody) {
        return;
    }


    tbody.innerHTML = "";


    if (
        holdings.length === 0
    ) {

        tbody.innerHTML = `
            <tr class="empty-table-row">

                <td colspan="9">
                    No holding results were returned.
                </td>

            </tr>
        `;

        return;
    }


    holdings.forEach(
        (holding) => {

            const purchasedShares =
                readOptionalNumber(
                    holding,
                    "purchased_shares"
                );


            const dripShares =
                readOptionalNumber(
                    holding,
                    "drip_shares"
                );


            const dividendYield =
                readOptionalNumber(
                    holding,
                    "dividend_yield"
                );


            const endingPrice =
                readOptionalNumber(
                    holding,
                    "ending_price"
                );


            const backendTotalShares =
                readOptionalNumber(
                    holding,
                    "total_shares"
                );


            let totalShares =
                backendTotalShares;


            /*
                Fall back to deriving total shares
                if an older backend response does
                not provide it directly.
            */

            if (
                totalShares === null &&
                purchasedShares !== null &&
                dripShares !== null
            ) {

                totalShares =
                    purchasedShares +
                    dripShares;

            }


            let purchasedProportion = null;
            let dripProportion = null;


            if (
                purchasedShares !== null &&
                dripShares !== null &&
                totalShares !== null &&
                totalShares > 0
            ) {

                purchasedProportion =
                    (
                        purchasedShares /
                        totalShares
                    ) * 100;


                dripProportion =
                    (
                        dripShares /
                        totalShares
                    ) * 100;

            }


            const row =
                document.createElement(
                    "tr"
                );


            row.innerHTML = `

                <td>
                    ${escapeHtml(
                        holding.ticker
                    )}
                </td>

                <td>
                    ${
                        dividendYield === null
                            ? "—"
                            : formatPercent(
                                dividendYield * 100,
                                2
                            )
                    }
                </td>

                <td>
                    ${
                        purchasedShares === null
                            ? "—"
                            : formatShares(
                                purchasedShares
                            )
                    }
                </td>

                <td>
                    ${
                        dripShares === null
                            ? "—"
                            : formatShares(
                                dripShares
                            )
                    }
                </td>

                <td>
                    ${
                        purchasedProportion === null
                            ? "—"
                            : formatPercent(
                                purchasedProportion,
                                1
                            )
                    }
                </td>

                <td>
                    ${
                        dripProportion === null
                            ? "—"
                            : formatPercent(
                                dripProportion,
                                1
                            )
                    }
                </td>

                <td>
                    ${
                        totalShares === null
                            ? "—"
                            : formatShares(
                                totalShares
                            )
                    }
                </td>

                <td>
                    ${
                        endingPrice === null
                            ? "—"
                            : formatCurrency(
                                endingPrice
                            )
                    }
                </td>

                <td>
                    ${formatCurrency(
                        Number(
                            holding.future_value
                        )
                    )}
                </td>
            `;


            tbody.appendChild(
                row
            );

        }
    );
}


/* =========================================================
   Loading / Status
   ========================================================= */

function setLoadingState(
    loading,
    message = ""
) {

    const button =
        document.getElementById(
            "run-forecast"
        );


    if (button) {

        button.disabled =
            loading;


        button.textContent =
            loading
                ? "Running Projection..."
                : "Run Projection";

    }


    if (
        loading &&
        message
    ) {

        setStatus(
            message,
            "loading"
        );

    }
}


function setStatus(
    message,
    type = ""
) {

    const status =
        document.getElementById(
            "forecast-status"
        );


    if (!status) {
        return;
    }


    status.textContent =
        message;


    status.classList.remove(
        "success",
        "error",
        "loading"
    );


    if (type) {
        status.classList.add(type);
    }
}


function clearStatus() {

    setStatus("");
}


/* =========================================================
   DOM Helpers
   ========================================================= */

function setText(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (element) {
        element.textContent = value;
    }
}


function readNumberInput(
    id,
    fallback = NaN
) {

    const element =
        document.getElementById(
            id
        );


    if (!element) {
        return fallback;
    }


    const value =
        Number(
            element.value
        );


    return Number.isFinite(value)
        ? value
        : fallback;
}


function readOptionalNumber(
    object,
    key
) {

    if (
        !object ||
        object[key] === undefined ||
        object[key] === null ||
        object[key] === ""
    ) {
        return null;
    }


    const value =
        Number(
            object[key]
        );


    return Number.isFinite(value)
        ? value
        : null;
}


/* =========================================================
   Formatting
   ========================================================= */

function formatCurrency(
    value
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }


    return new Intl.NumberFormat(
        "en-CA",
        {
            style: "currency",
            currency: "CAD",

            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    ).format(value);
}


function formatCompactCurrency(
    value
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }


    return new Intl.NumberFormat(
        "en-CA",
        {
            style: "currency",
            currency: "CAD",

            notation: "compact",

            maximumFractionDigits: 1
        }
    ).format(value);
}


function formatSignedCurrency(
    value
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }


    const absolute =
        formatCurrency(
            Math.abs(value)
        );


    if (value > 0) {
        return `+${absolute}`;
    }


    if (value < 0) {
        return `-${absolute}`;
    }


    return absolute;
}

function formatSignedCompactCurrency(
    value
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }

    const absolute =
        formatCompactCurrency(
            Math.abs(value)
        );

    if (value > 0) {
        return `+${absolute}`;
    }

    if (value < 0) {
        return `-${absolute}`;
    }

    return absolute;
}

function formatSignedPercent(
    value
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }


    const absolute =
        Math.abs(value)
            .toFixed(1);


    if (value > 0) {
        return `+${absolute}%`;
    }


    if (value < 0) {
        return `-${absolute}%`;
    }


    return `${absolute}%`;
}


function formatPercent(
    value,
    decimals = 1
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }


    return (
        `${value.toFixed(decimals)}%`
    );
}


function percentOfTotal(
    value,
    total
) {

    if (
        !Number.isFinite(value) ||
        !Number.isFinite(total) ||
        total === 0
    ) {
        return "—";
    }


    return formatPercent(
        (
            value /
            total
        ) * 100,
        1
    );
}


function formatShares(
    value
) {

    if (
        !Number.isFinite(value)
    ) {
        return "—";
    }


    return new Intl.NumberFormat(
        "en-CA",
        {
            minimumFractionDigits: 0,
            maximumFractionDigits: 4
        }
    ).format(value);
}


/* =========================================================
   HTML Escaping
   ========================================================= */

function escapeHtml(
    value
) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}