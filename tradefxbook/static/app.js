/**
 * TradeFXBook Front-End Client Application.
 * Full-featured Trading Journal & Analytics Dashboard with 10 isolated demo users.
 */

// Application State
const state = {
  currentUserId: "demo_trader_01",
  currentUserName: "Demo Trader 01",
  currency: "USD",
  rangePreset: "all",
  customStart: null,
  customEnd: null,
  page: 1,
  pageSize: 25,
  sortBy: "exit_time",
  sortOrder: "desc",
  filters: {
    search: "",
    direction: "",
    outcome: "",
    session: "",
  },
  charts: {
    dailyPnL: null,
    equityCurve: null,
    strategy: null,
    session: null,
  },
};

// API Helpers with user isolation header
async function apiFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  headers["X-User-Id"] = state.currentUserId;
  headers["Content-Type"] = "application/json";

  const res = await fetch(endpoint, { ...options, headers });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `HTTP Error ${res.status}`);
  }
  return res.json();
}

// Formatting utilities
function formatMoney(val, currency = "USD") {
  if (val === null || val === undefined || isNaN(val)) return "N/A";
  const absVal = Math.abs(val);
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(absVal);
  return val < 0 ? `-${formatted}` : formatted;
}

function formatPercent(val) {
  if (val === null || val === undefined || isNaN(val)) return "N/A";
  return `${Number(val).toFixed(2)}%`;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "N/A";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 24) {
    const days = (hours / 24).toFixed(1);
    return `${days} days`;
  }
  return `${hours}h ${minutes}m`;
}

// Initialization
document.addEventListener("DOMContentLoaded", async () => {
  setupNavigation();
  setupFilterHandlers();
  setupModalHandlers();
  await loadDemoUsers();
  await reloadAllData();
});

// Navigation Tabs
function setupNavigation() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");

      if (targetId === "adminTab") {
        loadAdminHealth();
      }
    });
  });
}

// Control Event Handlers
function setupFilterHandlers() {
  const traderSelect = document.getElementById("traderSelect");
  traderSelect.addEventListener("change", async (e) => {
    state.currentUserId = e.target.value;
    state.page = 1;
    await apiFetch(`/api/v1/auth/switch-demo/${state.currentUserId}`, { method: "POST" });
    await reloadAllData();
  });

  const rangePreset = document.getElementById("rangePreset");
  rangePreset.addEventListener("change", (e) => {
    state.rangePreset = e.target.value;
    const customWrap = document.getElementById("customDateWrap");
    if (state.rangePreset === "custom") {
      customWrap.classList.remove("hidden");
    } else {
      customWrap.classList.add("hidden");
      state.customStart = null;
      state.customEnd = null;
      reloadAllData();
    }
  });

  document.getElementById("btnApplyCustomDates").addEventListener("click", () => {
    state.customStart = document.getElementById("customStartDate").value;
    state.customEnd = document.getElementById("customEndDate").value;
    if (state.customStart && state.customEnd) {
      reloadAllData();
    }
  });

  document.getElementById("btnRefreshData").addEventListener("click", () => {
    reloadAllData();
  });

  // Journal Search & Filters
  let searchTimeout = null;
  document.getElementById("journalSearch").addEventListener("input", (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      state.page = 1;
      loadJournalTrades();
    }, 300);
  });

  document.getElementById("filterDirection").addEventListener("change", (e) => {
    state.filters.direction = e.target.value;
    state.page = 1;
    loadJournalTrades();
  });

  document.getElementById("filterOutcome").addEventListener("change", (e) => {
    state.filters.outcome = e.target.value;
    state.page = 1;
    loadJournalTrades();
  });

  document.getElementById("filterSession").addEventListener("change", (e) => {
    state.filters.session = e.target.value;
    state.page = 1;
    loadJournalTrades();
  });

  // Table Sorting
  document.querySelectorAll("#tradesTable th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.getAttribute("data-sort");
      if (state.sortBy === col) {
        state.sortOrder = state.sortOrder === "asc" ? "desc" : "asc";
      } else {
        state.sortBy = col;
        state.sortOrder = "desc";
      }
      loadJournalTrades();
    });
  });

  // Pagination
  document.getElementById("btnPrevPage").addEventListener("click", () => {
    if (state.page > 1) {
      state.page--;
      loadJournalTrades();
    }
  });

  document.getElementById("btnNextPage").addEventListener("click", () => {
    state.page++;
    loadJournalTrades();
  });

  // CSV Export
  document.getElementById("btnExportCSV").addEventListener("click", () => {
    let url = `/api/v1/trades/export/csv?user_id=${state.currentUserId}`;
    if (state.filters.direction) url += `&direction=${state.filters.direction}`;
    if (state.filters.outcome) url += `&outcome=${state.filters.outcome}`;
    if (state.filters.session) url += `&session=${state.filters.session}`;
    if (state.filters.search) url += `&search=${encodeURIComponent(state.filters.search)}`;
    window.location.href = url;
  });
}

// Load Demo Users into dropdown
async function loadDemoUsers() {
  try {
    const users = await apiFetch("/api/v1/auth/demo-users");
    const select = document.getElementById("traderSelect");
    select.innerHTML = "";
    users.forEach((u) => {
      const opt = document.createElement("option");
      opt.value = u.id;
      opt.textContent = `${u.name} — ${u.profile_description || u.id}`;
      select.appendChild(opt);
    });
    if (users.length > 0) {
      select.value = state.currentUserId;
      state.currency = users[0].currency || "USD";
    }
  } catch (err) {
    console.error("Failed to load demo users:", err);
  }
}

// Master reload
async function reloadAllData() {
  await Promise.all([loadOverviewMetrics(), loadJournalTrades()]);
}

// Load Analytics Overview & Charts
async function loadOverviewMetrics() {
  try {
    let url = `/api/v1/analytics/overview?range_preset=${state.rangePreset}`;
    if (state.customStart) url += `&date_from=${state.customStart}`;
    if (state.customEnd) url += `&date_to=${state.customEnd}`;

    const data = await apiFetch(url);

    // Update Header
    document.getElementById("headerBalance").textContent = formatMoney(data.current_equity, data.account_currency);

    // KPI Cards
    const kpiNet = document.getElementById("kpiNetPnL");
    kpiNet.textContent = formatMoney(data.net_pnl, data.account_currency);
    kpiNet.className = "kpi-value " + (data.net_pnl >= 0 ? "text-win" : "text-loss");
    document.getElementById("kpiGrossBreakdown").textContent =
      `Profit: ${formatMoney(data.gross_profit, data.account_currency)} | Loss: ${formatMoney(data.gross_loss, data.account_currency)}`;

    document.getElementById("kpiWinRate").textContent = formatPercent(data.win_rate);
    document.getElementById("kpiWinLossRatio").textContent =
      `Wins: ${data.winning_trades.toLocaleString()} | Losses: ${data.losing_trades.toLocaleString()}`;

    document.getElementById("kpiProfitFactor").textContent =
      data.profit_factor !== null ? data.profit_factor.toFixed(2) : "N/A";
    document.getElementById("kpiExpectancy").textContent =
      `Expectancy: ${formatMoney(data.expectancy, data.account_currency)}`;

    document.getElementById("kpiMaxDrawdown").textContent = formatMoney(data.max_drawdown_currency, data.account_currency);
    document.getElementById("kpiDrawdownPct").textContent = `${data.max_drawdown_pct.toFixed(2)}% peak-to-trough`;

    const avgWinStr = formatMoney(data.average_win, data.account_currency);
    const avgLossStr = formatMoney(data.average_loss, data.account_currency);
    document.getElementById("kpiAvgWinLoss").textContent = `${avgWinStr} / ${avgLossStr}`;
    document.getElementById("kpiRRRatio").textContent =
      `Avg R:R: ${data.average_rr_ratio !== null ? data.average_rr_ratio.toFixed(2) : "N/A"}`;

    document.getElementById("kpiTotalTrades").textContent = data.total_closed_trades.toLocaleString();
    document.getElementById("kpiBreakeven").textContent = `Breakeven: ${data.breakeven_trades.toLocaleString()}`;

    document.getElementById("kpiCosts").textContent = formatMoney(data.total_trading_costs, data.account_currency);
    document.getElementById("kpiAvgDuration").textContent = formatDuration(data.average_holding_duration_seconds);
    document.getElementById("kpiDailyAvg").textContent =
      `Avg Daily: ${formatMoney(data.average_daily_pnl, data.account_currency)}`;

    // Extremes
    if (data.best_trade) {
      document.getElementById("exBestTrade").textContent = formatMoney(data.best_trade.net_pnl, data.account_currency);
      document.getElementById("exBestTradeMeta").textContent =
        `${data.best_trade.symbol} (${data.best_trade.direction}) on ${data.best_trade.exit_time.slice(0, 10)}`;
    } else {
      document.getElementById("exBestTrade").textContent = "N/A";
      document.getElementById("exBestTradeMeta").textContent = "--";
    }

    if (data.worst_trade) {
      document.getElementById("exWorstTrade").textContent = formatMoney(data.worst_trade.net_pnl, data.account_currency);
      document.getElementById("exWorstTradeMeta").textContent =
        `${data.worst_trade.symbol} (${data.worst_trade.direction}) on ${data.worst_trade.exit_time.slice(0, 10)}`;
    } else {
      document.getElementById("exWorstTrade").textContent = "N/A";
      document.getElementById("exWorstTradeMeta").textContent = "--";
    }

    if (data.best_trading_day) {
      document.getElementById("exBestDay").textContent = formatMoney(data.best_trading_day.net_pnl, data.account_currency);
      document.getElementById("exBestDayMeta").textContent =
        `${data.best_trading_day.date} (${data.best_trading_day.trades_count} trades)`;
    } else {
      document.getElementById("exBestDay").textContent = "N/A";
      document.getElementById("exBestDayMeta").textContent = "--";
    }

    if (data.worst_trading_day) {
      document.getElementById("exWorstDay").textContent = formatMoney(data.worst_trading_day.net_pnl, data.account_currency);
      document.getElementById("exWorstDayMeta").textContent =
        `${data.worst_trading_day.date} (${data.worst_trading_day.trades_count} trades)`;
    } else {
      document.getElementById("exWorstDay").textContent = "N/A";
      document.getElementById("exWorstDayMeta").textContent = "--";
    }

    document.getElementById("exStreaks").textContent =
      `Win: ${data.max_consecutive_wins} | Loss: ${data.max_consecutive_losses}`;

    // Render Charts
    await Promise.all([renderDailyPnLChart(), renderEquityCurveChart(), renderBreakdownCharts()]);
  } catch (err) {
    console.error("Failed to load overview metrics:", err);
  }
}

// Chart 1: Daily P&L Chart
async function renderDailyPnLChart() {
  try {
    let url = `/api/v1/analytics/daily-pnl?range_preset=${state.rangePreset}`;
    if (state.customStart) url += `&date_from=${state.customStart}`;
    if (state.customEnd) url += `&date_to=${state.customEnd}`;

    const series = await apiFetch(url);
    const ctx = document.getElementById("dailyPnLChart").getContext("2d");

    // Sampling if wide date range
    let displaySeries = series;
    if (series.length > 180) {
      const step = Math.ceil(series.length / 180);
      displaySeries = series.filter((_, idx) => idx % step === 0);
    }

    const labels = displaySeries.map((d) => d.date);
    const dataVals = displaySeries.map((d) => d.net_pnl);
    const backgroundColors = dataVals.map((v) => (v >= 0 ? "rgba(16, 185, 129, 0.85)" : "rgba(239, 68, 68, 0.85)"));

    if (state.charts.dailyPnL) {
      state.charts.dailyPnL.destroy();
    }

    state.charts.dailyPnL = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Daily Net P&L",
            data: dataVals,
            backgroundColor: backgroundColors,
            borderRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `Net P&L: ${formatMoney(item.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", maxTicksLimit: 12 },
          },
          y: {
            grid: { color: "rgba(30, 41, 59, 0.4)" },
            ticks: {
              color: "#64748b",
              callback: (val) => `$${val.toLocaleString()}`,
            },
          },
        },
      },
    });
  } catch (err) {
    console.error("Failed to render daily P&L chart:", err);
  }
}

// Chart 2: Realized Equity Curve
async function renderEquityCurveChart() {
  try {
    let url = `/api/v1/analytics/equity-curve?range_preset=${state.rangePreset}`;
    if (state.customStart) url += `&date_from=${state.customStart}`;
    if (state.customEnd) url += `&date_to=${state.customEnd}`;

    const curveData = await apiFetch(url);
    const ctx = document.getElementById("equityCurveChart").getContext("2d");

    // Downsample points if large for high FPS
    let points = curveData.points || [];
    if (points.length > 500) {
      const step = Math.ceil(points.length / 500);
      points = points.filter((_, idx) => idx % step === 0);
    }

    const labels = points.map((p) => (p.timestamp.length > 10 ? p.timestamp.slice(0, 10) : p.timestamp));
    const equityValues = points.map((p) => p.equity);
    const hwmValues = points.map((p) => p.high_water_mark);

    if (state.charts.equityCurve) {
      state.charts.equityCurve.destroy();
    }

    state.charts.equityCurve = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Realized Equity",
            data: equityValues,
            borderColor: "#06b6d4",
            backgroundColor: "rgba(6, 182, 212, 0.08)",
            borderWidth: 2,
            fill: true,
            pointRadius: 0,
            tension: 0.1,
          },
          {
            label: "High-Water Mark",
            data: hwmValues,
            borderColor: "rgba(148, 163, 184, 0.4)",
            borderWidth: 1,
            borderDash: [4, 4],
            fill: false,
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { color: "#94a3b8", boxWidth: 12 },
          },
          tooltip: {
            callbacks: {
              label: (item) => `${item.dataset.label}: ${formatMoney(item.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", maxTicksLimit: 10 },
          },
          y: {
            grid: { color: "rgba(30, 41, 59, 0.4)" },
            ticks: {
              color: "#64748b",
              callback: (val) => `$${val.toLocaleString()}`,
            },
          },
        },
      },
    });
  } catch (err) {
    console.error("Failed to render equity curve chart:", err);
  }
}

// Chart 3: Strategy & Session Breakdowns
async function renderBreakdownCharts() {
  try {
    const [strategies, sessions] = await Promise.all([
      apiFetch("/api/v1/analytics/breakdown?group_by=strategy"),
      apiFetch("/api/v1/analytics/breakdown?group_by=session"),
    ]);

    // Strategy Chart
    const ctxStrat = document.getElementById("strategyChart").getContext("2d");
    if (state.charts.strategy) state.charts.strategy.destroy();

    state.charts.strategy = new Chart(ctxStrat, {
      type: "bar",
      data: {
        labels: strategies.map((s) => s.key),
        datasets: [
          {
            label: "Net P&L",
            data: strategies.map((s) => s.net_pnl),
            backgroundColor: strategies.map((s) => (s.net_pnl >= 0 ? "rgba(16, 185, 129, 0.8)" : "rgba(239, 68, 68, 0.8)")),
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `Net P&L: ${formatMoney(item.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(30, 41, 59, 0.4)" },
            ticks: { color: "#64748b", callback: (val) => `$${val.toLocaleString()}` },
          },
          y: {
            grid: { display: false },
            ticks: { color: "#cbd5e1" },
          },
        },
      },
    });

    // Session Chart
    const ctxSess = document.getElementById("sessionChart").getContext("2d");
    if (state.charts.session) state.charts.session.destroy();

    state.charts.session = new Chart(ctxSess, {
      type: "bar",
      data: {
        labels: sessions.map((s) => s.key),
        datasets: [
          {
            label: "Net P&L",
            data: sessions.map((s) => s.net_pnl),
            backgroundColor: sessions.map((s) => (s.net_pnl >= 0 ? "rgba(99, 102, 241, 0.85)" : "rgba(239, 68, 68, 0.85)")),
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `Net P&L: ${formatMoney(item.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(30, 41, 59, 0.4)" },
            ticks: { color: "#64748b", callback: (val) => `$${val.toLocaleString()}` },
          },
          y: {
            grid: { display: false },
            ticks: { color: "#cbd5e1" },
          },
        },
      },
    });
  } catch (err) {
    console.error("Failed to render breakdown charts:", err);
  }
}

// Load Journal Trades
async function loadJournalTrades() {
  try {
    let url = `/api/v1/trades?page=${state.page}&page_size=${state.pageSize}&sort_by=${state.sortBy}&sort_order=${state.sortOrder}`;
    if (state.filters.search) url += `&search=${encodeURIComponent(state.filters.search)}`;
    if (state.filters.direction) url += `&direction=${state.filters.direction}`;
    if (state.filters.outcome) url += `&outcome=${state.filters.outcome}`;
    if (state.filters.session) url += `&session=${state.filters.session}`;

    const data = await apiFetch(url);
    const tbody = document.getElementById("tradesTableBody");
    tbody.innerHTML = "";

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">No trades found matching criteria.</td></tr>`;
      document.getElementById("paginationInfo").textContent = `Showing 0 of 0 trades`;
      return;
    }

    data.items.forEach((trade) => {
      const tr = document.createElement("tr");

      const netClass = trade.net_pnl > 0 ? "text-win" : trade.net_pnl < 0 ? "text-loss" : "text-warning";
      const dirBadge =
        trade.direction === "LONG"
          ? `<span class="badge badge-long">LONG</span>`
          : `<span class="badge badge-short">SHORT</span>`;

      const exitFormatted = trade.exit_time ? trade.exit_time.slice(0, 16).replace("T", " ") : "OPEN";
      const rMultipleStr = trade.realized_r_multiple !== null ? `${trade.realized_r_multiple.toFixed(2)}R` : "--";

      tr.innerHTML = `
        <td class="font-mono text-muted">${escapeHtml(trade.id)}</td>
        <td>${escapeHtml(exitFormatted)}</td>
        <td><strong>${escapeHtml(trade.symbol)}</strong></td>
        <td>${dirBadge}</td>
        <td class="font-mono">${trade.quantity.toFixed(2)}</td>
        <td class="font-mono">${trade.entry_price.toFixed(5)}</td>
        <td class="font-mono">${trade.exit_price ? trade.exit_price.toFixed(5) : "--"}</td>
        <td class="font-mono ${netClass}">${rMultipleStr}</td>
        <td class="font-mono ${netClass}"><strong>${formatMoney(trade.net_pnl, trade.account_currency)}</strong></td>
        <td>${escapeHtml(trade.strategy_or_setup || "--")}</td>
        <td>${escapeHtml(trade.trading_session || "--")}</td>
        <td>
          <button class="btn btn-secondary btn-xs btn-view" data-id="${escapeHtml(trade.id)}">View</button>
          <button class="btn btn-secondary btn-xs btn-edit" data-id="${escapeHtml(trade.id)}">Edit</button>
          <button class="btn btn-secondary btn-xs text-loss btn-delete" data-id="${escapeHtml(trade.id)}">✕</button>
        </td>
      `;

      tbody.appendChild(tr);
    });

    // Attach row button events
    tbody.querySelectorAll(".btn-view").forEach((b) => b.addEventListener("click", () => viewTrade(b.dataset.id)));
    tbody.querySelectorAll(".btn-edit").forEach((b) => b.addEventListener("click", () => editTrade(b.dataset.id)));
    tbody.querySelectorAll(".btn-delete").forEach((b) => b.addEventListener("click", () => deleteTradeConfirm(b.dataset.id)));

    // Pagination display
    const startIdx = (data.page - 1) * data.page_size + 1;
    const endIdx = Math.min(data.page * data.page_size, data.total);
    document.getElementById("paginationInfo").textContent =
      `Showing ${startIdx.toLocaleString()} to ${endIdx.toLocaleString()} of ${data.total.toLocaleString()} trades`;
    document.getElementById("currentPageDisplay").textContent = `Page ${data.page} of ${data.total_pages}`;

    document.getElementById("btnPrevPage").disabled = data.page <= 1;
    document.getElementById("btnNextPage").disabled = data.page >= data.total_pages;
  } catch (err) {
    console.error("Failed to load journal trades:", err);
  }
}

// Modal Handlers
function setupModalHandlers() {
  const modal = document.getElementById("tradeModal");
  const detailsModal = document.getElementById("detailsModal");

  document.getElementById("btnOpenNewTrade").addEventListener("click", () => {
    document.getElementById("tradeForm").reset();
    document.getElementById("formTradeId").value = "";
    document.getElementById("modalTitle").textContent = "New Journal Trade Entry";

    // Set default timestamps
    const now = new Date();
    const isoString = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById("formEntryTime").value = isoString;
    document.getElementById("formExitTime").value = isoString;

    modal.classList.remove("hidden");
  });

  document.getElementById("btnCloseModal").addEventListener("click", () => modal.classList.add("hidden"));
  document.getElementById("btnCancelModal").addEventListener("click", () => modal.classList.add("hidden"));
  document.getElementById("btnCloseDetailsModal").addEventListener("click", () => detailsModal.classList.add("hidden"));

  // Save Trade Submit
  document.getElementById("tradeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const tradeId = document.getElementById("formTradeId").value;

    const isClosed = document.getElementById("formStatus").value === "CLOSED";
    const exitPriceVal = document.getElementById("formExitPrice").value;
    const exitTimeVal = document.getElementById("formExitTime").value;

    if (isClosed && (!exitPriceVal || !exitTimeVal)) {
      alert("Exit price and exit time are required for CLOSED trades.");
      return;
    }

    const payload = {
      symbol: document.getElementById("formSymbol").value.trim().toUpperCase(),
      asset_class: document.getElementById("formAssetClass").value,
      direction: document.getElementById("formDirection").value,
      status: document.getElementById("formStatus").value,
      quantity: parseFloat(document.getElementById("formQuantity").value),
      entry_price: parseFloat(document.getElementById("formEntryPrice").value),
      exit_price: isClosed && exitPriceVal ? parseFloat(exitPriceVal) : null,
      entry_time: new Date(document.getElementById("formEntryTime").value).toISOString(),
      exit_time: isClosed && exitTimeVal ? new Date(exitTimeVal).toISOString() : null,
      stop_loss_price: document.getElementById("formStopLoss").value ? parseFloat(document.getElementById("formStopLoss").value) : null,
      take_profit_price: document.getElementById("formTakeProfit").value ? parseFloat(document.getElementById("formTakeProfit").value) : null,
      planned_risk_amount: document.getElementById("formPlannedRisk").value ? parseFloat(document.getElementById("formPlannedRisk").value) : null,
      commission: parseFloat(document.getElementById("formCommission").value || 0),
      other_fees: parseFloat(document.getElementById("formFees").value || 0),
      signed_swap_adjustment: parseFloat(document.getElementById("formSwap").value || 0),
      strategy_or_setup: document.getElementById("formStrategy").value.trim() || "Discretionary",
      trading_session: document.getElementById("formSession").value,
      emotional_state: document.getElementById("formEmotion").value,
      notes: document.getElementById("formNotes").value.trim(),
    };

    try {
      if (tradeId) {
        await apiFetch(`/api/v1/trades/${tradeId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/api/v1/trades", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      modal.classList.add("hidden");
      await reloadAllData();
    } catch (err) {
      alert(`Error saving trade: ${err.message}`);
    }
  });
}

// View Trade Details
async function viewTrade(tradeId) {
  try {
    const t = await apiFetch(`/api/v1/trades/${tradeId}`);
    const detailsBody = document.getElementById("detailsBody");

    const netClass = t.net_pnl >= 0 ? "text-win" : "text-loss";
    detailsBody.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:16px;">
        <div>
          <h2>${escapeHtml(t.symbol)} <span class="badge ${t.direction === "LONG" ? "badge-long" : "badge-short"}">${escapeHtml(t.direction)}</span></h2>
          <span class="text-muted font-mono">${escapeHtml(t.id)} (User: ${escapeHtml(t.user_id)})</span>
        </div>
        <div style="text-align:right;">
          <h2 class="${netClass}">${formatMoney(t.net_pnl, t.account_currency)}</h2>
          <span class="text-muted">${t.realized_r_multiple !== null ? t.realized_r_multiple.toFixed(2) + "R" : ""}</span>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:12px; margin-bottom:16px; font-size:13px;">
        <div><strong>Entry:</strong> ${escapeHtml(t.entry_time.replace("T", " ").slice(0, 19))} @ ${t.entry_price}</div>
        <div><strong>Exit:</strong> ${t.exit_time ? escapeHtml(t.exit_time.replace("T", " ").slice(0, 19)) : "OPEN"} @ ${t.exit_price || "--"}</div>
        <div><strong>Size / Lots:</strong> ${t.quantity} (${t.contract_size.toLocaleString()} contract size)</div>
        <div><strong>Asset Class:</strong> ${escapeHtml(t.asset_class)}</div>
        <div><strong>Gross P&L:</strong> ${formatMoney(t.gross_pnl, t.account_currency)}</div>
        <div><strong>Trading Costs:</strong> Comm: $${t.commission} | Fees: $${t.other_fees} | Swap: $${t.signed_swap_adjustment}</div>
        <div><strong>Strategy:</strong> ${escapeHtml(t.strategy_or_setup || "--")}</div>
        <div><strong>Session:</strong> ${escapeHtml(t.trading_session || "--")}</div>
        <div><strong>Emotional State:</strong> ${escapeHtml(t.emotional_state || "--")}</div>
        <div><strong>Plan Followed:</strong> ${t.plan_followed ? "✅ Yes" : "❌ No"}</div>
      </div>

      <div style="background:rgba(15,23,42,0.6); padding:12px; border-radius:8px; border:1px solid #1e293b;">
        <h4 style="font-size:12px; color:#94a3b8; text-transform:uppercase; margin-bottom:6px;">Journal Notes</h4>
        <p style="font-size:13px;">${escapeHtml(t.notes || "No notes recorded for this trade.")}</p>
      </div>
    `;

    document.getElementById("detailsModal").classList.remove("hidden");
  } catch (err) {
    alert(`Failed to load trade details: ${err.message}`);
  }
}

// Edit Trade Modal Open
async function editTrade(tradeId) {
  try {
    const t = await apiFetch(`/api/v1/trades/${tradeId}`);
    document.getElementById("formTradeId").value = t.id;
    document.getElementById("modalTitle").textContent = `Edit Trade: ${t.id}`;

    document.getElementById("formSymbol").value = t.symbol;
    document.getElementById("formAssetClass").value = t.asset_class;
    document.getElementById("formDirection").value = t.direction;
    document.getElementById("formStatus").value = t.status;
    document.getElementById("formQuantity").value = t.quantity;
    document.getElementById("formEntryPrice").value = t.entry_price;
    document.getElementById("formExitPrice").value = t.exit_price || "";

    if (t.entry_time) document.getElementById("formEntryTime").value = t.entry_time.slice(0, 16);
    if (t.exit_time) document.getElementById("formExitTime").value = t.exit_time.slice(0, 16);

    document.getElementById("formStopLoss").value = t.stop_loss_price || "";
    document.getElementById("formTakeProfit").value = t.take_profit_price || "";
    document.getElementById("formPlannedRisk").value = t.planned_risk_amount || "";
    document.getElementById("formCommission").value = t.commission || 0;
    document.getElementById("formFees").value = t.other_fees || 0;
    document.getElementById("formSwap").value = t.signed_swap_adjustment || 0;
    document.getElementById("formStrategy").value = t.strategy_or_setup || "";
    document.getElementById("formSession").value = t.trading_session || "London";
    document.getElementById("formEmotion").value = t.emotional_state || "Disciplined";
    document.getElementById("formNotes").value = t.notes || "";

    document.getElementById("tradeModal").classList.remove("hidden");
  } catch (err) {
    alert(`Failed to load trade for editing: ${err.message}`);
  }
}

// Delete Trade
async function deleteTradeConfirm(tradeId) {
  if (confirm(`Are you sure you want to delete trade ${tradeId}? This action cannot be undone.`)) {
    try {
      await apiFetch(`/api/v1/trades/${tradeId}`, { method: "DELETE" });
      await reloadAllData();
    } catch (err) {
      alert(`Failed to delete trade: ${err.message}`);
    }
  }
}

// Load Dataset Health Verification (Admin Tab)
async function loadAdminHealth() {
  const container = document.getElementById("healthChecksContainer");
  const tableBody = document.getElementById("traderBreakdownBody");
  try {
    const health = await apiFetch("/api/v1/admin/health");
    const users = await apiFetch("/api/v1/auth/demo-users");

    container.innerHTML = `
      <div class="health-grid">
        <div class="check-item">
          <span class="${health.checks.has_exact_10_users ? "check-pass" : "check-fail"}">
            ${health.checks.has_exact_10_users ? "✓" : "✗"}
          </span>
          <div>
            <div class="check-name">10 Demo Users</div>
            <small class="text-muted">${health.total_demo_users} verified</small>
          </div>
        </div>

        <div class="check-item">
          <span class="${health.checks.has_exact_100k_trades ? "check-pass" : "check-fail"}">
            ${health.checks.has_exact_100k_trades ? "✓" : "✗"}
          </span>
          <div>
            <div class="check-name">100,000 Total Trades</div>
            <small class="text-muted">${health.total_seeded_trades.toLocaleString()} verified</small>
          </div>
        </div>

        <div class="check-item">
          <span class="${health.checks.has_exact_100k_closed_trades ? "check-pass" : "check-fail"}">
            ${health.checks.has_exact_100k_closed_trades ? "✓" : "✗"}
          </span>
          <div>
            <div class="check-name">100,000 Closed Trades</div>
            <small class="text-muted">${health.total_closed_seeded_trades.toLocaleString()} verified</small>
          </div>
        </div>

        <div class="check-item">
          <span class="${health.checks.all_users_have_10k_trades ? "check-pass" : "check-fail"}">
            ${health.checks.all_users_have_10k_trades ? "✓" : "✗"}
          </span>
          <div>
            <div class="check-name">10,000 Trades / User</div>
            <small class="text-muted">Exact distribution verified</small>
          </div>
        </div>
      </div>
    `;

    tableBody.innerHTML = "";
    users.forEach((u) => {
      const tr = document.createElement("tr");
      const userTradeCount = health.trades_per_user[u.id] || 0;
      tr.innerHTML = `
        <td class="font-mono">${escapeHtml(u.id)}</td>
        <td><strong>${escapeHtml(u.name)}</strong></td>
        <td>${escapeHtml(u.profile_description || "--")}</td>
        <td class="font-mono">${formatMoney(u.starting_balance, u.currency)}</td>
        <td>${escapeHtml(u.timezone)}</td>
        <td class="font-mono text-win"><strong>${userTradeCount.toLocaleString()}</strong></td>
        <td><span class="badge badge-long">ISOLATED & SEEDED</span></td>
      `;
      tableBody.appendChild(tr);
    });
  } catch (err) {
    container.innerHTML = `<div class="text-loss">Failed to load health report: ${err.message}</div>`;
  }
}
