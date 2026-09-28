"use strict";

/*
 * SAP Intelligence Dashboard
 *
 * API:
 *   GET /api/dashboard
 *
 * Expected structure:
 *
 * {
 *   success: true,
 *   data: {
 *     kpis: {...},
 *     inventory: {...},
 *     procurement: {...},
 *     suppliers: {...},
 *     forecast: {...},
 *     insights: [...]
 *   }
 * }
 */


/* =========================================================
   STATE
   ========================================================= */

let dashboardData = null;


/* =========================================================
   INITIALIZATION
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {
        setupNavigation();
        setupRefresh();

        loadDashboard();
    }
);


/* =========================================================
   NAVIGATION
   ========================================================= */

function setupNavigation() {

    const navItems =
        document.querySelectorAll(
            ".nav-item"
        );

    navItems.forEach(item => {

        item.addEventListener(
            "click",
            () => {

                navItems.forEach(
                    nav => nav.classList.remove(
                        "active"
                    )
                );

                item.classList.add(
                    "active"
                );

                const section =
                    item.dataset.section;

                showSection(section);

            }
        );

    });
}


function showSection(section) {

    const sections =
        document.querySelectorAll(
            ".dashboard-section"
        );

    sections.forEach(
        element => {
            element.classList.remove(
                "active"
            );
        }
    );

    const target =
        document.getElementById(
            `section-${section}`
        );

    if (target) {
        target.classList.add(
            "active"
        );
    }

    updatePageHeader(section);

    if (section === "inventory") {
        renderInventoryPage();
    }

    if (section === "procurement") {
        renderProcurementPage();
    }

    if (section === "suppliers") {
        renderSuppliersPage();
    }

    if (section === "forecast") {
        renderForecastPage();
    }

    if (section === "insights") {
        renderInsightsPage();
    }
}


function updatePageHeader(section) {

    const titles = {
        overview: "Procurement Overview",
        inventory: "Inventory Intelligence",
        procurement: "Procurement Intelligence",
        suppliers: "Supplier Intelligence",
        forecast: "Forecast & Planning",
        insights: "Procurement Insights",
    };

    const descriptions = {
        overview:
            "Current procurement, inventory and supplier position",

        inventory:
            "Inventory coverage, stock exposure and critical parts",

        procurement:
            "Shortfalls, priorities and procurement exposure",

        suppliers:
            "Supplier-level requirements, stock and shortfall exposure",

        forecast:
            "Monthly requirements and stock projection",

        insights:
            "Automated observations from the current dataset",
    };

    const title =
        document.getElementById(
            "page-title"
        );

    const description =
        document.getElementById(
            "page-description"
        );

    if (title) {
        title.textContent =
            titles[section] ||
            titles.overview;
    }

    if (description) {
        description.textContent =
            descriptions[section] ||
            descriptions.overview;
    }
}


/* =========================================================
   REFRESH
   ========================================================= */

function setupRefresh() {

    const button =
        document.getElementById(
            "refresh-button"
        );

    if (!button) {
        return;
    }

    button.addEventListener(
        "click",
        async () => {

            button.disabled = true;

            button.textContent =
                "↻ Loading...";

            await loadDashboard();

            button.disabled = false;

            button.textContent =
                "↻ Refresh";
        }
    );
}


/* =========================================================
   API
   ========================================================= */

async function loadDashboard() {

    try {

        setLoadingState();

        const response =
            await fetch(
                "/api/dashboard",
                {
                    cache: "no-store",
                }
            );

        const result =
            await response.json();

        if (
            !response.ok ||
            !result.success
        ) {

            throw new Error(
                result.message ||
                "Unable to load dashboard data."
            );
        }

        dashboardData =
            result.data || {};

        renderDashboard(
            dashboardData
        );

        await loadDatasetStatus();

    } catch (error) {

        console.error(
            "Dashboard loading failed:",
            error
        );

        showDashboardError(
            error.message
        );
    }
}


/* =========================================================
   DATASET STATUS
   ========================================================= */

async function loadDatasetStatus() {

    try {

        const response =
            await fetch(
                "/api/dashboard/status",
                {
                    cache: "no-store",
                }
            );

        const result =
            await response.json();

        if (!result.success) {
            return;
        }

        const name =
            document.getElementById(
                "dataset-name"
            );

        const status =
            document.getElementById(
                "dataset-status"
            );

        if (result.available) {

            if (name) {
                name.textContent =
                    result.dataset ||
                    "Processed Dataset";
            }

            if (status) {
                status.textContent =
                    "Data ready";
            }

        } else {

            if (name) {
                name.textContent =
                    "No dataset";
            }

            if (status) {
                status.textContent =
                    "Analyze a workbook first";
            }
        }

    } catch (error) {

        console.error(
            "Dataset status failed:",
            error
        );
    }
}


/* =========================================================
   MAIN RENDER
   ========================================================= */

function renderDashboard(data) {

    renderKpis(
        data.kpis || {}
    );

    renderInventoryOverview(
        data.inventory || {}
    );

    renderPriorityChart(
        data.procurement || {}
    );

    renderSupplierChart(
        data.suppliers || {}
    );

    renderForecastChart(
        data.forecast || {}
    );

    renderInsights(
        data.insights || []
    );
}


/* =========================================================
   KPI CARDS
   ========================================================= */

   function renderKpis(kpis) {
   
       const container =
           document.getElementById("kpi-grid");
   
       if (!container) {
           return;
       }
   
       const cards = [
           {
               label: "Total Parts",
               value: findValue(kpis, [
                   "total_parts",
                   "parts",
                   "part_count",
               ]),
               meta: "Parts in current dataset",
           },
   
           {
               label: "Inventory Value",
               value: findValue(kpis, [
                   "total_inventory_value",
                   "inventory_value",
               ]),
               meta: "Current inventory value",
               money: true,
           },
   
           {
               label: "Monthly Requirement",
               value: findValue(kpis, [
                   "total_monthly_requirement",
                   "total_requirement",
                   "total_requirements",
                   "requirement",
               ]),
               meta: "Current planning requirement",
           },
   
           {
               label: "Total Shortfall",
               value: findValue(kpis, [
                   "total_shortfall",
                   "shortfall",
               ]),
               meta: "Requirement not covered",
           },
   
           {
               label: "Open PO",
               value: findValue(kpis, [
                   "total_open_po",
                   "open_po",
                   "open_purchase_orders",
               ]),
               meta: "Open purchase orders",
           },
   
           {
               label: "Open STO",
               value: findValue(kpis, [
                   "total_open_sto",
                   "open_sto",
                   "open_stock_transfer_orders",
               ]),
               meta: "Open stock transfers",
           },
       ];
   
       container.innerHTML =
           cards.map(
               card => `
                   <div class="kpi-card">
   
                       <div class="kpi-label">
                           ${escapeHtml(card.label)}
                       </div>
   
                       <div class="kpi-value">
                           ${
                               card.money
                                   ? formatCompactMoney(card.value)
                                   : formatCompactNumber(card.value)
                           }
                       </div>
   
                       <div class="kpi-meta">
                           ${escapeHtml(card.meta)}
                       </div>
   
                   </div>
               `
           ).join("");
   }


/* =========================================================
   INVENTORY OVERVIEW
   ========================================================= */

   function renderInventoryOverview(inventory) {
   
       const container =
           document.getElementById(
               "inventory-chart"
           );
   
       if (!container) {
           return;
       }
   
       const coverage =
           inventory.coverage_distribution ||
           [];
   
       if (
           Array.isArray(coverage) &&
           coverage.length
       ) {
   
           renderCoverageChart(
               container,
               coverage
           );
   
           return;
       }
   
   
       const data =
           inventory.inventory_by_category ||
           [];
   
       if (
           !Array.isArray(data) ||
           !data.length
       ) {
   
           renderEmpty(
               container,
               "No inventory distribution available."
           );
   
           return;
       }
   
   
       renderBarChart(
           container,
           data,
           {
               labelKeys: [
                   "category",
                   "name",
                   "label",
               ],
   
               valueKeys: [
                   "inventory",
                   "stock",
                   "current_stock",
                   "value",
                   "count",
               ],
   
               limit: 7,
           }
       );
   }


/* =========================================================
   PRIORITY
   ========================================================= */

function renderPriorityChart(
    procurement
) {

    const container =
        document.getElementById(
            "priority-chart"
        );

    if (!container) {
        return;
    }

    const data =
        procurement.priority_distribution ||
        [];

    if (!Array.isArray(data) || !data.length) {

        renderEmpty(
            container,
            "No priority data available."
        );

        return;
    }

    renderHorizontalBars(
        container,
        data,
        {
            labelKeys: [
                "priority",
                "name",
                "label",
                "category",
            ],

            valueKeys: [
                "count",
                "value",
                "quantity",
            ],
        }
    );
}


/* =========================================================
   SUPPLIER CHART
   ========================================================= */

function renderSupplierChart(
    suppliers
) {

    const container =
        document.getElementById(
            "supplier-chart"
        );

    if (!container) {
        return;
    }

    const data =
        suppliers.performance ||
        [];

    if (!Array.isArray(data) || !data.length) {

        renderEmpty(
            container,
            "No supplier performance data available."
        );

        return;
    }

    const topSuppliers =
        [...data]
            .sort(
                (a, b) =>
                    getNumber(
                        b,
                        [
                            "shortfall",
                            "shortfall_quantity",
                            "total_shortfall",
                        ]
                    )
                    -
                    getNumber(
                        a,
                        [
                            "shortfall",
                            "shortfall_quantity",
                            "total_shortfall",
                        ]
                    )
            )
            .slice(0, 8);

    renderBarChart(
        container,
        topSuppliers,
        {
            labelKeys: [
                "supplier",
                "supplier_name",
                "vendor",
            ],

            valueKeys: [
                "shortfall",
                "total_shortfall",
            ],
        }
    );
}


/* =========================================================
   FORECAST
   ========================================================= */

function renderForecastChart(
    forecast
) {

    const container =
        document.getElementById(
            "forecast-chart"
        );

    if (!container) {
        return;
    }

    const data =
        forecast.monthly_summary ||
        [];

    if (!Array.isArray(data) || !data.length) {

        renderEmpty(
            container,
            "No monthly forecast data available."
        );

        return;
    }

    renderLineChart(
        container,
        data,
        {
            labelKeys: [
                "month",
                "date",
                "period",
            ],

            valueKeys: [
                "requirement",
                "total_requirement",
                "monthly_requirement",
                "quantity",
            ],
        }
    );
}


/* =========================================================
   INSIGHTS
   ========================================================= */

   function renderInsights(insights) {
   
       const container =
           document.getElementById("insights-container");
   
       if (!container) {
           return;
       }
   
       insights = normalizeInsights(insights);
   
       if (!insights.length) {
           renderEmpty(
               container,
               "No automated insights available."
           );
   
           return;
       }
   
       container.innerHTML =
           insights
               .slice(0, 6)
               .map(
                   (item, index) =>
                       buildInsightCard(item, index)
               )
               .join("");
   }

/* =========================================================
   INVENTORY PAGE
   ========================================================= */

function renderInventoryPage() {

    const container =
        document.getElementById(
            "inventory-content"
        );

    if (!container || !dashboardData) {
        return;
    }

    const inventory =
        dashboardData.inventory || {};

    const critical =
        inventory.critical_parts ||
        [];

    const categories =
        inventory.inventory_by_category ||
        [];

    const coverage =
        inventory.coverage_distribution ||
        [];

    container.innerHTML = `

        <div class="data-card">

            <h3>
                Critical Parts
            </h3>

            ${renderTable(
                critical,
                [
                    ["part", "Part"],
                    ["part_number", "Part"],
                    ["shortfall", "Shortfall"],
                    ["current_stock", "Stock"],
                    ["coverage", "Coverage"],
                ]
            )}

        </div>


        <div class="data-card">

            <h3>
                Inventory by Category
            </h3>

            ${renderTable(
                categories,
                [
                    ["category", "Category"],
                    ["inventory", "Inventory"],
                    ["stock", "Stock"],
                    ["count", "Count"],
                ]
            )}

        </div>


        <div class="data-card">

            <h3>
                Coverage Distribution
            </h3>

            ${renderTable(
                coverage,
                [
                    ["bucket", "Coverage"],
                    ["coverage", "Coverage"],
                    ["count", "Count"],
                    ["value", "Value"],
                ]
            )}

        </div>
    `;
}


/* =========================================================
   PROCUREMENT PAGE
   ========================================================= */

function renderProcurementPage() {

    const container =
        document.getElementById(
            "procurement-content"
        );

    if (!container || !dashboardData) {
        return;
    }

    const procurement =
        dashboardData.procurement || {};

    const shortfalls =
        procurement.shortfall_parts ||
        [];

    const supplierShortfalls =
        procurement.supplier_shortfalls ||
        [];

    const priorities =
        procurement.priority_distribution ||
        [];

    container.innerHTML = `

        <div class="data-card">

            <h3>
                Critical Shortfalls
            </h3>

            ${renderTable(
                shortfalls,
                [
                    ["part", "Part"],
                    ["part_number", "Part"],
                    ["shortfall", "Shortfall"],
                    ["priority", "Priority"],
                ]
            )}

        </div>


        <div class="data-card">

            <h3>
                Supplier Shortfalls
            </h3>

            ${renderTable(
                supplierShortfalls,
                [
                    ["supplier", "Supplier"],
                    ["supplier_name", "Supplier"],
                    ["shortfall", "Shortfall"],
                    ["requirement", "Requirement"],
                ]
            )}

        </div>


        <div class="data-card">

            <h3>
                Priority Distribution
            </h3>

            ${renderTable(
                priorities,
                [
                    ["priority", "Priority"],
                    ["count", "Count"],
                    ["value", "Value"],
                ]
            )}

        </div>
    `;
}


/* =========================================================
   SUPPLIERS PAGE
   ========================================================= */

function renderSuppliersPage() {

    const container =
        document.getElementById(
            "suppliers-content"
        );

    if (!container || !dashboardData) {
        return;
    }

    const suppliers =
        dashboardData.suppliers || {};

    const performance =
        suppliers.performance ||
        [];

    container.innerHTML = `

        <div
            class="data-card"
            style="grid-column: 1 / -1;"
        >

            <h3>
                Supplier Performance
            </h3>

            ${renderTable(
                performance,
                [
                    ["supplier", "Supplier"],
                    ["supplier_name", "Supplier"],
                    ["requirement", "Requirement"],
                    ["current_stock", "Stock"],
                    ["shortfall", "Shortfall"],
                    ["open_po", "Open PO"],
                    ["open_sto", "Open STO"],
                ],
                20
            )}

        </div>
    `;
}


/* =========================================================
   FORECAST PAGE
   ========================================================= */

function renderForecastPage() {

    const container =
        document.getElementById(
            "forecast-content"
        );

    if (!container || !dashboardData) {
        return;
    }

    const forecast =
        dashboardData.forecast || {};

    const monthly =
        forecast.monthly_summary ||
        [];

    const projection =
        forecast.stock_projection ||
        [];

    container.innerHTML = `

        <div class="data-card">

            <h3>
                Monthly Requirement
            </h3>

            ${renderTable(
                monthly,
                [
                    ["month", "Month"],
                    ["requirement", "Requirement"],
                    ["total_requirement", "Requirement"],
                    ["stock", "Stock"],
                ],
                20
            )}

        </div>


        <div class="data-card">

            <h3>
                Stock Projection
            </h3>

            ${renderTable(
                projection,
                [
                    ["month", "Month"],
                    ["stock", "Stock"],
                    ["projected_stock", "Projected Stock"],
                    ["requirement", "Requirement"],
                ],
                20
            )}

        </div>
    `;
}


/* =========================================================
   INSIGHTS PAGE
   ========================================================= */

   function renderInsightsPage() {
   
       const container =
           document.getElementById("insights-page");
   
       if (!container || !dashboardData) {
           return;
       }
   
       const insights =
           normalizeInsights(
               dashboardData.insights || []
           );
   
       if (!insights.length) {
   
           container.innerHTML = `
               <div class="empty-state">
                   No procurement insights available.
               </div>
           `;
   
           return;
       }
   
       container.innerHTML =
           insights
               .map(
                   (item, index) =>
                       buildInsightCard(
                           item,
                           index,
                           true
                       )
               )
               .join("");
   }

/* =========================================================
   BAR CHART
   ========================================================= */

   function renderCoverageChart(
       container,
       data
   ) {
   
       if (
           !Array.isArray(data) ||
           !data.length
       ) {
   
           renderEmpty(
               container,
               "No inventory coverage data available."
           );
   
           return;
       }
   
   
       const items =
           data
               .map(item => ({
                   label: getValue(
                       item,
                       [
                           "bucket",
                           "coverage",
                           "status",
                           "label",
                           "name",
                       ]
                   ),
   
                   value: getNumber(
                       item,
                       [
                           "count",
                           "value",
                           "parts",
                           "quantity",
                       ]
                   ),
               }))
               .filter(
                   item =>
                       item.label !== null &&
                       item.label !== undefined
               );
   
   
       const total =
           items.reduce(
               (sum, item) =>
                   sum + item.value,
               0
           );
   
   
       if (!total) {
   
           renderEmpty(
               container,
               "Inventory coverage contains no measurable values."
           );
   
           return;
       }
   
   
       const colors = [
           "#dc2626",
           "#f59e0b",
           "#16a34a",
           "#64748b",
           "#2563eb",
       ];
   
   
       const size = 180;
       const center = size / 2;
       const radius = 62;
   
       const circumference =
           2 * Math.PI * radius;
   
       let offset = 0;
   
   
       const segments =
           items.map(
               (item, index) => {
   
                   const length =
                       (
                           item.value /
                           total
                       ) * circumference;
   
   
                   const segment = `
                       <circle
                           cx="${center}"
                           cy="${center}"
                           r="${radius}"
                           fill="none"
                           stroke="${
                               colors[
                                   index %
                                   colors.length
                               ]
                           }"
                           stroke-width="28"
                           stroke-dasharray="
                               ${length}
                               ${circumference - length}
                           "
                           stroke-dashoffset="${-offset}"
                           transform="
                               rotate(
                                   -90
                                   ${center}
                                   ${center}
                               )
                           "
                       />
                   `;
   
   
                   offset += length;
   
                   return segment;
               }
           )
           .join("");
   
   
       container.innerHTML = `
   
           <div class="coverage-chart">
   
               <div class="coverage-donut">
   
                   <svg
                       viewBox="0 0 ${size} ${size}"
                       class="dashboard-donut"
                   >
   
                       <circle
                           cx="${center}"
                           cy="${center}"
                           r="${radius}"
                           fill="none"
                           stroke="#eef2f7"
                           stroke-width="28"
                       />
   
                       ${segments}
   
   
                       <text
                           x="${center}"
                           y="${center - 3}"
                           text-anchor="middle"
                           class="donut-total"
                       >
                           ${formatCompactNumber(total)}
                       </text>
   
   
                       <text
                           x="${center}"
                           y="${center + 17}"
                           text-anchor="middle"
                           class="donut-label"
                       >
                           parts
                       </text>
   
                   </svg>
   
               </div>
   
   
               <div class="coverage-legend">
   
                   ${
                       items.map(
                           (item, index) => {
   
                               const percentage =
                                   (
                                       item.value /
                                       total
                                   ) * 100;
   
                               return `
                                   <div
                                       class="legend-row"
                                   >
   
                                       <span
                                           class="legend-dot"
                                           style="
                                               background:
                                               ${
                                                   colors[
                                                       index %
                                                       colors.length
                                                   ]
                                               };
                                           "
                                       ></span>
   
                                       <span
                                           class="legend-name"
                                       >
                                           ${escapeHtml(
                                               item.label
                                           )}
                                       </span>
   
                                       <strong>
                                           ${formatCompactNumber(
                                               item.value
                                           )}
                                       </strong>
   
                                       <small>
                                           ${percentage.toFixed(1)}%
                                       </small>
   
                                   </div>
                               `;
                           }
                       ).join("")
                   }
   
               </div>
   
           </div>
       `;
   }
   
function renderBarChart(
    container,
    data,
    options = {}
) {

    const labelKeys =
        options.labelKeys || [];

    const valueKeys =
        options.valueKeys || [];

    const items =
        data
            .map(item => ({
                label:
                    getValue(
                        item,
                        labelKeys
                    ),

                value:
                    getNumber(
                        item,
                        valueKeys
                    ),
            }))
            .filter(
                item =>
                    item.label !== null &&
                    item.label !== undefined
            )
            .slice(0, 10);

    if (!items.length) {

        renderEmpty(
            container,
            "No chart data available."
        );

        return;
    }

    const maxValue =
        Math.max(
            ...items.map(
                item => item.value
            ),
            1
        );

    container.innerHTML =
        `
        <div
            style="
                display:flex;
                flex-direction:column;
                gap:12px;
                padding-top:5px;
            "
        >

            ${
                items
                    .map(
                        item => {

                            const width =
                                Math.max(
                                    2,
                                    (
                                        item.value /
                                        maxValue
                                    ) * 100
                                );

                            return `
                                <div>

                                    <div
                                        style="
                                            display:flex;
                                            justify-content:space-between;
                                            gap:10px;
                                            margin-bottom:5px;
                                            font-size:10px;
                                        "
                                    >
                                        <span
                                            style="
                                                color:var(--muted);
                                                overflow:hidden;
                                                text-overflow:ellipsis;
                                                white-space:nowrap;
                                            "
                                        >
                                            ${escapeHtml(
                                                item.label
                                            )}
                                        </span>

                                        <strong>
                                            ${formatNumber(
                                                item.value
                                            )}
                                        </strong>
                                    </div>

                                    <div
                                        style="
                                            height:8px;
                                            border-radius:20px;
                                            background:#edf1f7;
                                            overflow:hidden;
                                        "
                                    >

                                        <div
                                            style="
                                                height:100%;
                                                width:${width}%;
                                                background:var(--primary);
                                                border-radius:20px;
                                            "
                                        ></div>

                                    </div>

                                </div>
                            `;
                        }
                    )
                    .join("")
            }

        </div>
        `;
}


/* =========================================================
   HORIZONTAL BARS
   ========================================================= */

function renderHorizontalBars(
    container,
    data,
    options = {}
) {

    renderBarChart(
        container,
        data,
        options
    );
}


/* =========================================================
   LINE CHART
   ========================================================= */

function renderLineChart(
    container,
    data,
    options = {}
) {

    const labels =
        options.labelKeys || [];

    const values =
        options.valueKeys || [];

    const points =
        data
            .map(item => ({
                label:
                    getValue(
                        item,
                        labels
                    ),

                value:
                    getNumber(
                        item,
                        values
                    ),
            }))
            .slice(0, 12);

    if (!points.length) {

        renderEmpty(
            container,
            "No trend data available."
        );

        return;
    }

    const max =
        Math.max(
            ...points.map(
                point => point.value
            ),
            1
        );

    const min =
        Math.min(
            ...points.map(
                point => point.value
            ),
            0
        );

    const range =
        Math.max(
            max - min,
            1
        );

    const width = 700;
    const height = 220;

    const padding = 25;

    const usableWidth =
        width -
        padding * 2;

    const usableHeight =
        height -
        padding * 2;

    const pointWidth =
        points.length > 1
            ? usableWidth /
              (points.length - 1)
            : usableWidth;

    const coordinates =
        points.map(
            (point, index) => {

                const x =
                    padding +
                    index * pointWidth;

                const y =
                    padding +
                    usableHeight -
                    (
                        (
                            point.value -
                            min
                        ) /
                        range
                    ) *
                    usableHeight;

                return {
                    x,
                    y,
                    ...point,
                };
            }
        );

    const polyline =
        coordinates
            .map(
                point =>
                    `${point.x},${point.y}`
            )
            .join(" ");

    container.innerHTML =
        `
        <svg
            viewBox="0 0 ${width} ${height}"
            preserveAspectRatio="none"
        >

            <polyline
                points="${polyline}"
                fill="none"
                stroke="#2563eb"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
            />

            ${
                coordinates
                    .map(
                        point =>
                            `
                            <circle
                                cx="${point.x}"
                                cy="${point.y}"
                                r="4"
                                fill="#ffffff"
                                stroke="#2563eb"
                                stroke-width="2"
                            />
                            `
                    )
                    .join("")
            }

            ${
                coordinates
                    .map(
                        point =>
                            `
                            <text
                                x="${point.x}"
                                y="${height - 4}"
                                text-anchor="middle"
                                font-size="9"
                                fill="#6b7280"
                            >
                                ${escapeHtml(
                                    truncate(
                                        point.label,
                                        10
                                    )
                                )}
                            </text>
                            `
                    )
                    .join("")
            }

        </svg>
        `;
}


/* =========================================================
   TABLE
   ========================================================= */

function renderTable(
    rows,
    columns,
    maxRows = 10
) {

    if (
        !Array.isArray(rows) ||
        !rows.length
    ) {

        return `
            <div class="empty-state">
                No data available.
            </div>
        `;
    }

    const visibleRows =
        rows.slice(
            0,
            maxRows
        );

    const header =
        columns
            .map(
                column =>
                    `<th>
                        ${escapeHtml(
                            column[1]
                        )}
                    </th>`
            )
            .join("");

    const body =
        visibleRows
            .map(
                row => {

                    const cells =
                        columns
                            .map(
                                column => {

                                    const value =
                                        getValue(
                                            row,
                                            [column[0]]
                                        );

                                    return `
                                        <td>
                                            ${formatCell(
                                                value
                                            )}
                                        </td>
                                    `;
                                }
                            )
                            .join("");

                    return `<tr>${cells}</tr>`;
                }
            )
            .join("");

    return `
        <table class="data-table">

            <thead>
                <tr>
                    ${header}
                </tr>
            </thead>

            <tbody>
                ${body}
            </tbody>

        </table>
    `;
}


/* =========================================================
   HELPERS
   ========================================================= */

function findValue(
    object,
    keys
) {

    for (const key of keys) {

        if (
            object &&
            object[key] !== undefined &&
            object[key] !== null
        ) {
            return object[key];
        }
    }

    return 0;
}


function getValue(
    object,
    keys
) {

    if (!object) {
        return null;
    }

    for (const key of keys) {

        if (
            object[key] !== undefined &&
            object[key] !== null
        ) {
            return object[key];
        }
    }

    return null;
}


function getNumber(
    object,
    keys
) {

    const value =
        getValue(
            object,
            keys
        );

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return 0;
    }

    const number =
        Number(
            String(value)
                .replaceAll(",", "")
                .replace("%", "")
        );

    return Number.isFinite(number)
        ? number
        : 0;
}

function formatCompactNumber(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return new Intl.NumberFormat(
        "en-IN",
        {
            notation: "compact",
            maximumFractionDigits: 1,
        }
    ).format(number);
}


function formatCompactMoney(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "₹0";
    }

    return (
        "₹" +
        new Intl.NumberFormat(
            "en-IN",
            {
                notation: "compact",
                maximumFractionDigits: 1,
            }
        ).format(number)
    );
}


function formatNumber(
    value
) {

    const number =
        Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return new Intl.NumberFormat(
        "en-IN",
        {
            maximumFractionDigits: 2,
        }
    ).format(number);
}


function formatCell(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {
        return "-";
    }

    if (
        typeof value === "number"
    ) {
        return formatNumber(
            value
        );
    }

    return escapeHtml(
        String(value)
    );
}

function normalizeInsights(insights) {

    if (Array.isArray(insights)) {
        return insights.filter(Boolean);
    }

    if (
        insights &&
        typeof insights === "object"
    ) {
        return Object.values(insights).filter(Boolean);
    }

    return [];
}


function buildInsightCard(
    item,
    index = 0,
    detailed = false
) {

    const severity =
        String(
            item?.severity ||
            item?.level ||
            "info"
        ).toLowerCase();

    const safeSeverity =
        [
            "critical",
            "warning",
            "info",
            "success"
        ].includes(severity)
            ? severity
            : "info";

    const title =
        extractInsightTitle(
            item,
            index
        );

    const description =
        extractInsightText(item);

    const affected =
        getNumber(
            item,
            [
                "affected_records",
                "affected",
                "records",
                "count",
            ]
        );

    const rule =
        item?.rule_id ||
        item?.rule ||
        "";

    const severityLabel =
        safeSeverity === "critical"
            ? "Critical"
            : safeSeverity === "warning"
                ? "Warning"
                : safeSeverity === "success"
                    ? "Resolved"
                    : "Information";

    return `
        <article
            class="
                insight-card
                insight-${safeSeverity}
                ${detailed ? "insight-card-detailed" : ""}
            "
        >

            <div class="insight-card-top">

                <span class="insight-severity">

                    <span
                        class="insight-severity-dot"
                    ></span>

                    ${severityLabel}

                </span>

                ${
                    rule
                        ? `
                            <span class="insight-rule">
                                ${escapeHtml(rule)}
                            </span>
                        `
                        : ""
                }

            </div>


            <h3>
                ${escapeHtml(title)}
            </h3>


            <p>
                ${escapeHtml(description)}
            </p>


            ${
                affected
                    ? `
                        <div class="insight-footer">

                            <span>
                                Affected records
                            </span>

                            <strong>
                                ${formatCompactNumber(
                                    affected
                                )}
                            </strong>

                        </div>
                    `
                    : ""
            }

        </article>
    `;
}


function extractInsightTitle(
    item,
    index = 0
) {

    if (typeof item === "string") {
        return `Insight ${index + 1}`;
    }

    return (
        item?.title ||
        item?.name ||
        item?.type ||
        item?.rule_id ||
        `Insight ${index + 1}`
    );
}


function extractInsightText(item) {

    if (typeof item === "string") {
        return item;
    }

    return (
        item?.description ||
        item?.message ||
        item?.insight ||
        item?.text ||
        item?.recommendation ||
        "No description available."
    );
}


function truncate(
    value,
    length
) {

    const text =
        String(
            value ?? ""
        );

    if (
        text.length <= length
    ) {
        return text;
    }

    return (
        text.slice(
            0,
            length - 1
        ) + "…"
    );
}


function escapeHtml(
    value
) {

    return String(
        value ?? ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


function renderEmpty(
    container,
    message
) {

    container.innerHTML =
        `
        <div class="empty-state">
            ${escapeHtml(message)}
        </div>
        `;
}


function setLoadingState() {

    const containers = [
        "kpi-grid",
        "inventory-chart",
        "priority-chart",
        "supplier-chart",
        "forecast-chart",
        "insights-container",
    ];

    containers.forEach(
        id => {

            const element =
                document.getElementById(id);

            if (!element) {
                return;
            }

            element.innerHTML =
                `
                <div class="loading">
                    Loading analytics...
                </div>
                `;
        }
    );
}


function showDashboardError(
    message
) {

    const container =
        document.getElementById(
            "kpi-grid"
        );

    if (!container) {
        return;
    }

    container.innerHTML =
        `
        <div
            class="data-card"
            style="grid-column:1 / -1;"
        >

            <h3>
                Dashboard data unavailable
            </h3>

            <p
                style="
                    color:var(--muted);
                    font-size:12px;
                "
            >
                ${escapeHtml(message)}
            </p>

            <p
                style="
                    color:var(--muted);
                    font-size:11px;
                "
            >
                Analyze a workbook first or
                check the Flask server logs.
            </p>

        </div>
        `;
}