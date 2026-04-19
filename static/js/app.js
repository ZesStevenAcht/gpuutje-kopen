/* ── Global state ─────────────────────────────────────── */
let currentGpuList = [];

/* ── Helpers ──────────────────────────────────────────── */
function fmtDate(d) {
    const dd = String(d.getDate()).padStart(2, "0");
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const yyyy = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${dd}/${mm}/${yyyy} ${hh}:${mi}`;
}

/* ── Load GPU list ────────────────────────────────────── */
async function loadGpus() {
    const resp = await fetch("/api/gpus");
    currentGpuList = await resp.json();

    const select = document.getElementById("gpuSelect");
    select.innerHTML = currentGpuList
        .map((gpu) => `<option value="${gpu.id}">${gpu.name}</option>`)
        .join("");

    // Default to RTX 3070 if available
    const rtx3070 = currentGpuList.find(
        (g) => g.name.includes("3070") && !g.name.includes("Ti")
    );
    if (rtx3070) select.value = rtx3070.id;

    select.addEventListener("change", updatePriceGraph);
    updatePriceGraph();
}

/* ── Stats ────────────────────────────────────────────── */
async function updateStats() {
    const resp = await fetch("/api/stats");
    const stats = await resp.json();

    const date = new Date(stats.last_updated);
    document.getElementById("lastUpdate").textContent =
        `Last updated: ${fmtDate(date)}`;

    let gpuInfo = Object.entries(stats.gpu_counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([id, count]) => {
            const gpu = currentGpuList.find((g) => g.id === id);
            return `${gpu ? gpu.name : id} (${count})`;
        })
        .join(" | ");

    document.getElementById("statsText").textContent =
        `Total Results: ${stats.total_results} | Top: ${gpuInfo}`;
}

/* ── Price history chart ──────────────────────────────── */
async function updatePriceGraph() {
    const gpu = document.getElementById("gpuSelect").value;
    const gpuName = currentGpuList.find((g) => g.id === gpu)?.name || gpu;
    const span = document.getElementById("priceGroupSelect").value || "30d";
    const resp = await fetch(
        `/api/price-history/${encodeURIComponent(gpu)}?agg=min&span=${span}`
    );
    const data = await resp.json();

    const trace = {
        x: data.dates,
        y: data.prices,
        type: "scatter",
        mode: "lines+markers",
        fill: "tozeroy",
        line: { color: "#8a9a5b", width: 2 },
        marker: { size: 6, color: "#8a9a5b" },
        hovertemplate: "<b>%{x|%d/%m/%Y}</b><br>€%{y:.2f}<extra></extra>",
    };

    const layout = {
        title: `Price History: ${gpuName}`,
        xaxis: { title: "Date", type: "date", tickformat: "%d/%m/%Y", gridcolor: "#555" },
        yaxis: { title: "Price (€)", gridcolor: "#555" },
        font: { color: "#e0e0e0" },
        hovermode: "x unified",
        margin: { l: 50, r: 20, t: 40, b: 40 },
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
    };

    Plotly.newPlot("priceGraph", [trace], layout, { responsive: true });
}

/* ── Scatter chart (Tokens/s or VRAM vs price) ────────── */
async function updateScatterGraph(graphId, metric, daysSelect) {
    const days = document.getElementById(daysSelect).value || "30";
    const resp = await fetch(`/api/scatter-data?metric=${metric}&days=${days}`);
    const data = await resp.json();
    const points = data.points;

    // Discrete VRAM colour palette
    const vramColorMap = {
        4: "#e6194b", 6: "#f58231", 8: "#ffe119", 10: "#bfef45",
        12: "#3cb44b", 16: "#42d4f4", 20: "#4363d8", 24: "#911eb4",
        32: "#f032e6", 48: "#a9a9a9", 80: "#ffffff",
    };
    function vramColor(v) { return vramColorMap[v] || "#888"; }

    function createHoverText(p) {
        const tokensLabel = p.tokens_tested
            ? `${p.tokens.toFixed(2)} tokens/s`
            : `${p.tokens.toFixed(2)} tokens/s (est.)`;
        const metricValue = metric === "vram" ? `${p.vram} GB vram` : tokensLabel;
        const otherValue  = metric === "vram" ? tokensLabel : `${p.vram} GB vram`;
        return `<b>${p.gpu}</b><br>${otherValue}<br>${metricValue}`;
    }

    const vramValues = [...new Set(points.map((p) => p.vram))].sort((a, b) => a - b);
    const traces = [];
    const half = Math.ceil(vramValues.length / 2);

    for (let i = 0; i < vramValues.length; i++) {
        const vram = vramValues[i];
        const group = points.filter((p) => p.vram === vram);
        traces.push({
            x: group.map((p) => p.quality),
            y: group.map((p) => p.price),
            customdata: group.map((p) => (p.lowest ? p.lowest.link : null)),
            text: group.map((p) => createHoverText(p)),
            mode: "markers",
            type: "scatter",
            marker: {
                size: 7,
                symbol: group.map((p) => (p.tokens_tested ? "circle" : "square")),
                color: vramColor(vram),
                opacity: 0.85,
                line: { width: 0.5, color: "#333" },
            },
            hovertemplate: "%{text}<extra></extra>",
            name: `${vram} GB`,
            legend: i < half ? "legend" : "legend2",
            visible: metric === "tokens" && vram > 32 ? "legendonly" : true,
        });
    }

    const xLabel = metric === "vram" ? "VRAM (GB)" : "Tokens/s";
    const layout = {
        xaxis: { title: xLabel, gridcolor: "#555" },
        yaxis: { title: "Avg Price (€)", gridcolor: "#555" },
        font: { color: "#e0e0e0" },
        hovermode: "closest",
        margin: { l: 50, r: 20, t: 40, b: 40 },
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
        showlegend: true,
        legend: {
            title: { text: " Press to add or remove entries ", font: { size: 12, color: "#b0b0b0" } },
            orientation: "v", yanchor: "top", y: 0.99,
            xanchor: "left", x: 0.01,
            font: { size: 13, color: "#e0e0e0" }, tracegroupgap: 5, itemwidth: 20,
            bgcolor: "rgba(50,50,50,0.92)", bordercolor: "rgba(0,0,0,0)", borderwidth: 0,
        },
        legend2: {
            title: { text: " ", font: { size: 12, color: "rgba(0,0,0,0)" } },
            orientation: "v", yanchor: "top", y: 0.99,
            xanchor: "left", x: 0.15,
            font: { size: 13, color: "#e0e0e0" }, tracegroupgap: 5, itemwidth: 20,
            bgcolor: "rgba(0,0,0,0)", bordercolor: "rgba(0,0,0,0)", borderwidth: 0,
        },
    };

    await Plotly.newPlot(graphId, traces, layout, { responsive: true });

    // Open lowest listing when user clicks a point
    document.getElementById(graphId).on("plotly_click", function (ev) {
        if (!ev || !ev.points || !ev.points.length) return;
        const pt = ev.points[0];
        const link = pt.customdata || (pt.data && pt.data.customdata && pt.data.customdata[pt.pointNumber]);
        if (link) window.open(link, "_blank");
    });
}

/* ── Results table ────────────────────────────────────── */
async function loadResults() {
    const minVram   = document.getElementById("minVram").value;
    const minTokens = document.getElementById("minTokens").value;
    const maxPrice  = document.getElementById("maxPrice").value;
    const search    = document.getElementById("searchBox").value;
    const sortBy    = document.getElementById("sortBySelect").value;
    const sortOrder = document.getElementById("sortOrderSelect").value;

    const params = new URLSearchParams({
        min_vram: minVram, min_tokens: minTokens,
        max_price: maxPrice, search: search,
        sort_by: sortBy, order: sortOrder,
    });

    const resp = await fetch(`/api/results?${params}`);
    let results = await resp.json();

    const showActiveOnly = document.getElementById("showActiveOnly").checked;
    if (showActiveOnly) results = results.filter((r) => r.active === true);

    const pageSize = parseInt(document.getElementById("pageSizeSelect")?.value || "10", 10);
    const limited = results.slice(0, pageSize);

    const tbody = document.getElementById("resultsTable");
    if (results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No results found</td></tr>';
        return;
    }

    tbody.innerHTML = limited
        .map((r) => `
            <tr>
                <td><strong>${r.gpu}</strong><br><small class="text-muted">VRAM: ${r.vram}GB, Tokens/s: ${r.tokens}</small></td>
                <td>${r.title.substring(0, 60)}</td>
                <td><strong>€${r.price}</strong></td>
                <td><a href="${r.link}" target="_blank" class="link-btn">View</a></td>
                <td><small>${fmtDate(new Date(r.timestamp))}</small></td>
            </tr>`)
        .join("");
}

/* ── Event listeners ──────────────────────────────────── */
document.getElementById("filterBtn").addEventListener("click", loadResults);
document.getElementById("priceGroupSelect").addEventListener("change", updatePriceGraph);
document.getElementById("showActiveOnly").addEventListener("change", loadResults);
document.getElementById("tokensDaysSelect").addEventListener("change", () =>
    updateScatterGraph("tokensGraph", "tokens", "tokensDaysSelect")
);
const pageSizeElem = document.getElementById("pageSizeSelect");
if (pageSizeElem) pageSizeElem.addEventListener("change", loadResults);

/* ── Bootstrap init ───────────────────────────────────── */
async function init() {
    await loadGpus();
    await updateStats();
    await updateScatterGraph("tokensGraph", "tokens", "tokensDaysSelect");
    await loadResults();
    setInterval(updateStats, 10000);
}
init();
