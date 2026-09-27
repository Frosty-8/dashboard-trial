"use strict";


/* =========================================================
   STATE
========================================================= */

let dashboardData = null;


/* =========================================================
   HELPERS
========================================================= */

function formatNumber(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    return new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 0,
    }).format(value);
}


function formatCurrency(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    const crore = Number(value) / 10000000;

    if (Math.abs(crore) >= 1) {
        return `₹${crore.toLocaleString("en-IN", {
            maximumFractionDigits: 1,
        })} Cr`;
    }

    return `₹${Number(value).toLocaleString("en-IN", {
        maximumFractionDigits: 0,
    })}`;
}


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================================================
   API
========================================================= */

async function fetchDashboard() {

    const response = await fetch("/api/dashboard", {
        method: "GET",
        headers: {
            "Accept": "application/json",
        },
    });

    const payload = await response.json();

    if (!response.ok || !payload.success) {
        throw new Error(
            payload.message || "Dashboard API request failed."
        );
    }

    return payload.data;
}


/* =========================================================
   KPI
========================================================= */

function renderKPIs(kpis) {

    setText(
        "total-parts",
        formatNumber(kpis.total_parts)
    );

    setText(
        "inventory-value",
        formatCurrency(kpis.total_inventory_value)
    );

    setText(
        "critical-parts",
        formatNumber(kpis.critical_parts)
    );

    setText(
        "total-shortfall",
        formatNumber(kpis.total_shortfall)
    );

    setText(
        "open-po",
        formatNumber(kpis.total_open_po)
    );

    setText(
        "sto-intransit",
        formatNumber(kpis.total_sto_intransit)
    );


    setText(
        "risk-critical",
        formatNumber(kpis.critical_parts)
    );

    setText(
        "risk-low",
        formatNumber(kpis.low_coverage_parts)
    );

    setText(
        "risk-healthy",
        formatNumber(kpis.healthy_parts)
    );

    setText(
        "risk-excess",
        formatNumber(kpis.excess_parts)
    );
}


/* =========================================================
   BAR CHART
========================================================= */

function renderBarChart(
    containerId,
    items,
    labelKey,
    valueKey,
    formatter = formatNumber
) {

    const container = document.getElementById(containerId);

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!items || items.length === 0) {
        container.innerHTML =
            '<div class="empty-state">No data available.</div>';

        return;
    }

    const maxValue = Math.max(
        ...items.map(
            item => Number(item[valueKey]) || 0
        )
    );

    items.forEach(item => {

        const value = Number(item[valueKey]) || 0;

        const percentage =
            maxValue > 0
                ? (value / maxValue) * 100
                : 0;

        const row = document.createElement("div");

        row.className = "bar-row";

        row.innerHTML = `
            <div class="bar-label"
                 title="${escapeHtml(item[labelKey])}">
                ${escapeHtml(item[labelKey])}
            </div>

            <div class="bar-track">
                <div
                    class="bar-fill"
                    style="width: ${percentage}%"
                ></div>
            </div>

            <div class="bar-value">
                ${formatter(value)}
            </div>
        `;

        container.appendChild(row);
    });
}


/* =========================================================
   INVENTORY
========================================================= */

function renderInventory(inventory) {

    if (!inventory) {
        return;
    }


    if (inventory.coverage_distribution) {

        renderBarChart(
            "coverage-chart",
            inventory.coverage_distribution,
            "status",
            "parts"
        );

    }


    if (inventory.inventory_by_category) {

        renderBarChart(
            "category-chart",
            inventory.inventory_by_category,
            "category",
            "inventory_value",
            formatCurrency
        );

    }
}


/* =========================================================
   PROCUREMENT
========================================================= */

function renderProcurement(procurement) {

    if (!procurement) {
        return;
    }


    if (procurement.supplier_shortfalls) {

        const suppliers =
            procurement.supplier_shortfalls
                .slice(0, 8);

        renderBarChart(
            "supplier-chart",
            suppliers,
            "supplier_name",
            "shortfall"
        );

    }


    if (procurement.priority_distribution) {

        renderBarChart(
            "priority-chart",
            procurement.priority_distribution,
            "priority",
            "parts"
        );

    }
}


/* =========================================================
   SUPPLIERS
========================================================= */

function renderSuppliers(suppliers) {

    const table =
        document.getElementById("supplier-table");

    if (!table) {
        return;
    }

    table.innerHTML = "";


    /*
     * Backend response:
     *
     * suppliers = {
     *     performance: [...]
     * }
     *
     * Extract the actual supplier list.
     */

    const supplierList =
        Array.isArray(suppliers)
            ? suppliers
            : Array.isArray(suppliers?.performance)
                ? suppliers.performance
                : [];


    if (supplierList.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="6">
                    No supplier data available.
                </td>
            </tr>
        `;

        return;
    }


    supplierList
        .slice(0, 10)
        .forEach(supplier => {

            const row =
                document.createElement("tr");


            row.innerHTML = `
                <td>
                    ${escapeHtml(
                        supplier.supplier_name
                    )}
                </td>

                <td>
                    ${formatNumber(
                        supplier.parts
                    )}
                </td>

                <td>
                    ${formatNumber(
                        supplier.monthly_requirement
                    )}
                </td>

                <td>
                    ${formatNumber(
                        supplier.shortfall
                    )}
                </td>

                <td>
                    ${formatCurrency(
                        supplier.inventory_value
                    )}
                </td>

                <td>
                    ${formatNumber(
                        supplier.open_po
                    )}
                </td>
            `;

            table.appendChild(row);
        });
}


/* =========================================================
   FORECAST
========================================================= */

function renderForecast(forecast) {

    const container =
        document.getElementById("forecast-chart");

    if (!container || !forecast) {
        return;
    }

    container.innerHTML = "";


    const monthlyData =
        forecast.monthly_summary || forecast.monthly || [];


    if (!monthlyData.length) {

        container.innerHTML =
            '<div class="empty-state">No forecast data available.</div>';

        return;
    }


    const values =
        monthlyData.map(
            item => Number(
                item.forecast ??
                item.total_forecast ??
                item.value ??
                0
            )
        );


    const maxValue =
        Math.max(...values, 1);


    monthlyData.forEach((item, index) => {

        const value = values[index];

        const percentage =
            (value / maxValue) * 100;

        const month =
            item.month ??
            item.period ??
            `M${index + 1}`;


        const column =
            document.createElement("div");

        column.className =
            "forecast-column";

        column.innerHTML = `
            <div class="forecast-value">
                ${formatNumber(value)}
            </div>

            <div class="forecast-bar-wrapper">

                <div
                    class="forecast-bar"
                    style="height: ${Math.max(
                        percentage,
                        2
                    )}%"
                ></div>

            </div>

            <div class="forecast-month">
                ${escapeHtml(month)}
            </div>
        `;

        container.appendChild(column);
    });
}


/* =========================================================
   INSIGHTS
========================================================= */

function renderInsights(insights) {

    const container =
        document.getElementById("insight-grid");

    if (!container) {
        return;
    }

    container.innerHTML = "";


    if (!insights) {
        return;
    }


    const items =
        insights.items || [];


    setText(
        "insight-count",
        `${items.length} insights detected`
    );


    if (!items.length) {

        container.innerHTML = `
            <div class="panel">
                No business insights detected.
            </div>
        `;

        return;
    }


    items.forEach(insight => {

        const severity =
            String(
                insight.severity || "info"
            ).toLowerCase();


        const card =
            document.createElement("article");

        card.className =
            `insight-card ${severity}`;


        card.innerHTML = `
            <div class="insight-top">

                <span class="severity ${severity}">
                    ${escapeHtml(severity)}
                </span>

                <span>
                    ${formatNumber(
                        insight.affected_records
                    )} records
                </span>

            </div>

            <h4>
                ${escapeHtml(
                    insight.title
                )}
            </h4>

            <p>
                ${escapeHtml(
                    insight.description
                )}
            </p>
        `;

        container.appendChild(card);
    });
}


/* =========================================================
   MAIN RENDER
========================================================= */

function renderDashboard(data) {

    dashboardData = data;

    renderKPIs(data.kpis);

    renderInventory(data.inventory);

    renderProcurement(data.procurement);

    renderSuppliers(data.suppliers);

    renderForecast(data.forecast);

    renderInsights(data.insights);


    setText(
        "last-updated",
        `Updated ${new Date().toLocaleTimeString()}`
    );
}


/* =========================================================
   LOAD
========================================================= */

async function refreshDashboard() {

    const loading =
        document.getElementById("loading");

    const dashboard =
        document.getElementById("dashboard");

    const error =
        document.getElementById("error");

    const errorMessage =
        document.getElementById("error-message");


    loading.classList.remove("hidden");

    dashboard.classList.add("hidden");

    error.classList.add("hidden");


    try {

        const data =
            await fetchDashboard();

        renderDashboard(data);

        loading.classList.add("hidden");

        dashboard.classList.remove("hidden");

    } catch (exception) {

        console.error(exception);

        loading.classList.add("hidden");

        error.classList.remove("hidden");

        errorMessage.textContent =
            exception.message ||
            "Unable to load dashboard.";
    }
}


/* =========================================================
   NAVIGATION
========================================================= */

document
    .querySelectorAll(".nav-item")
    .forEach(link => {

        link.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(".nav-item")
                    .forEach(item => {
                        item.classList.remove(
                            "active"
                        );
                    });

                link.classList.add("active");
            }
        );
    });


/* =========================================================
   INITIAL LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    refreshDashboard
);