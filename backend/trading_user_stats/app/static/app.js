const $ = (id) => document.getElementById(id);
const formatter = new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });

function safeText(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function metric(label, value, tone = "") {
  return `<article class="metric"><p class="metric-label">${safeText(label)}</p><p class="metric-value ${tone}">${safeText(value)}</p></article>`;
}

function renderTable(target, firstHeading, rows, firstKey) {
  if (!rows.length) {
    target.innerHTML = '<p class="chart-empty">No trades in this selection.</p>';
    return;
  }
  target.innerHTML = `<table><thead><tr><th>${safeText(firstHeading)}</th><th>Trades</th><th>Net P&amp;L</th></tr></thead><tbody>${
    rows.map((row) => `<tr><td>${safeText(row[firstKey])}</td><td>${number.format(row.trades)}</td><td class="${row.net_pnl >= 0 ? "positive" : "negative"}">${formatter.format(row.net_pnl)}</td></tr>`).join("")
  }</tbody></table>`;
}

function renderChart(points) {
  const chart = $("chart");
  if (!points.length) {
    chart.innerHTML = '<span class="chart-empty">No activity in this selection.</span>';
    return;
  }
  const values = points.map((point) => point.equity);
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const spread = max - min || 1;
  chart.innerHTML = points.slice(-100).map((point) => {
    const height = Math.max(2, Math.abs(point.equity) / spread * 100);
    const position = point.equity >= 0 ? "margin-top: auto" : "margin-bottom: auto";
    return `<span class="bar" title="${safeText(point.date)} · ${safeText(formatter.format(point.equity))}" style="height:${height}%;${position};${point.equity < 0 ? "background:#f07b85" : ""}"></span>`;
  }).join("");
}

async function loadStats() {
  const status = $("status");
  status.textContent = "Loading your statistics…";
  status.classList.remove("error");
  const query = new URLSearchParams({ user_id: "demo_01", range: $("range").value, session: $("session").value });
  if ($("range").value === "custom") {
    if (!$("start").value || !$("end").value) {
      status.textContent = "Choose both dates for a custom range.";
      status.classList.add("error");
      return;
    }
    query.set("start", $("start").value);
    query.set("end", $("end").value);
  }

  try {
    const response = await fetch(`/api/stats?${query}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
    const summary = payload.summary;
    $("metrics").innerHTML = [
      metric("Net P&L", formatter.format(summary.net_pnl), summary.net_pnl >= 0 ? "positive" : "negative"),
      metric("Win rate", `${number.format(summary.win_rate_pct)}%`),
      metric("Closed trades", number.format(summary.trade_count)),
      metric("Profit factor", summary.profit_factor === null ? "—" : number.format(summary.profit_factor)),
      metric("Max drawdown", formatter.format(summary.max_drawdown), "negative"),
    ].join("");
    renderChart(payload.equity_curve);
    renderTable($("sessions"), "Session", payload.by_session, "session");
    renderTable($("symbols"), "Symbol", payload.by_symbol.slice(0, 8), "symbol");
    status.textContent = `${payload.range.start || "All history"} – ${payload.range.end} · ${payload.filters.session} session`;
  } catch (error) {
    status.textContent = error.message || "Could not load trading statistics.";
    status.classList.add("error");
  }
}

function updateCustomDates() {
  const visible = $("range").value === "custom";
  document.querySelectorAll(".custom-date").forEach((element) => element.classList.toggle("visible", visible));
}

$("range").addEventListener("change", () => { updateCustomDates(); loadStats(); });
$("session").addEventListener("change", loadStats);
$("refresh").addEventListener("click", loadStats);
updateCustomDates();
loadStats();
