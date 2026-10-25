import { useState, useEffect, useCallback, useMemo } from "react";
import type {
  PerformanceMetrics,
  DailyPnLPoint,
  BreakdownItem,
  UserProfile,
} from "../../types/trading";
import {
  getAnalyticsOverview,
  getDailyPnL,
  getBreakdown,
} from "../../api/client";

interface UserStatisticsWidgetProps {
  currentUser: UserProfile | null;
  authToken?: string | null;
  onOpenAuthModal?: () => void;
}

export function UserStatisticsWidget({
  currentUser,
  authToken,
  onOpenAuthModal,
}: UserStatisticsWidgetProps) {
  const [rangePreset, setRangePreset] = useState("all");
  const [sessionFilter, setSessionFilter] = useState("all");
  const [breakdownDim, setBreakdownDim] = useState<"strategy" | "session" | "symbol" | "direction">("strategy");

  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [dailyPnL, setDailyPnL] = useState<DailyPnLPoint[]>([]);
  const [breakdowns, setBreakdowns] = useState<BreakdownItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hover state for charts
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; label: string; value: string } | null>(null);

  const loadStats = useCallback(async () => {
    if (!currentUser) return;
    try {
      setLoading(true);
      setError(null);

      const [overviewData, dailyData, breakdownData] = await Promise.all([
        getAnalyticsOverview(
          rangePreset,
          currentUser.id,
          authToken || undefined,
          sessionFilter !== "all" ? { session: sessionFilter } : undefined
        ),
        getDailyPnL(rangePreset === "all" ? "90d" : rangePreset, currentUser.id, authToken || undefined),
        getBreakdown(breakdownDim, rangePreset, currentUser.id, authToken || undefined),
      ]);

      setMetrics(overviewData);
      setDailyPnL(dailyData);
      setBreakdowns(breakdownData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load statistics");
    } finally {
      setLoading(false);
    }
  }, [currentUser, authToken, rangePreset, sessionFilter, breakdownDim]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Equity Curve SVG calculation
  const equityChart = useMemo(() => {
    if (!dailyPnL || dailyPnL.length === 0) return null;
    const width = 800;
    const height = 260;
    const padding = 40;

    const values = dailyPnL.map((p) => p.cumulative_net_pnl ?? p.cumulative_pnl ?? 0);
    const minVal = Math.min(0, ...values);
    const maxVal = Math.max(...values, 100);
    const range = (maxVal - minVal) || 1;

    const points = dailyPnL.map((p, idx) => {
      const cum = p.cumulative_net_pnl ?? p.cumulative_pnl ?? 0;
      const x = padding + (idx / Math.max(1, dailyPnL.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((cum - minVal) / range) * (height - 2 * padding);
      return {
        x: Number.isFinite(x) ? x : padding,
        y: Number.isFinite(y) ? y : height / 2,
        p,
        cum,
      };
    });

    const pathD = points.map((pt, i) => `${i === 0 ? "M" : "L"} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`).join(" ");
    const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${(height - padding).toFixed(1)} L ${points[0].x.toFixed(1)} ${(height - padding).toFixed(1)} Z`;

    const zeroY = height - padding - ((0 - minVal) / range) * (height - 2 * padding);

    return {
      width,
      height,
      padding,
      points,
      pathD,
      areaD,
      zeroY: Number.isFinite(zeroY) ? zeroY : height - padding,
      minVal,
      maxVal,
    };
  }, [dailyPnL]);

  // Format Helpers
  const fmtCurrency = (val?: number | null) => {
    if (val === null || val === undefined) return "--";
    const sign = val > 0 ? "+" : "";
    return `${sign}$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const fmtPct = (val?: number | null) => {
    if (val === null || val === undefined) return "--";
    return `${val.toFixed(2)}%`;
  };

  return (
    <div className="user-statistics-container">
      {/* Top Banner */}
      <div className="stats-header-strip">
        <div className="stats-title-block">
          <h2>📊 Trading Performance Analytics & Statistics</h2>
          <p>
            Authoritative financial metrics and equity curve computed across{" "}
            <strong>{metrics?.total_closed_trades?.toLocaleString() || "10,000"}</strong> closed trades for{" "}
            <strong>{currentUser?.name || "Active Trader"}</strong>
          </p>
        </div>

        <div className="stats-header-actions">
          <button className="btn-user-badge" onClick={onOpenAuthModal}>
            👤 {currentUser?.name || "Switch Profile"} ({currentUser?.currency || "USD"}{" "}
            ${currentUser?.starting_balance?.toLocaleString() ?? "50,000"})
          </button>
          <button className="btn-refresh-stats" onClick={loadStats} title="Refresh analytics" disabled={loading}>
            {loading ? "⏳ Calculating..." : "🔄 Refresh"}
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="stats-toolbar">
        <div className="toolbar-group">
          <label>Date Range:</label>
          <div className="pill-group">
            {[
              { id: "all", label: "All Time" },
              { id: "7d", label: "7 Days" },
              { id: "30d", label: "30 Days" },
              { id: "90d", label: "90 Days" },
              { id: "ytd", label: "YTD" },
              { id: "1y", label: "1 Year" },
            ].map((p) => (
              <button
                key={p.id}
                className={`pill-btn ${rangePreset === p.id ? "active" : ""}`}
                onClick={() => setRangePreset(p.id)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-group">
          <label>Market Session:</label>
          <select
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="stats-select"
          >
            <option value="all">All Market Sessions</option>
            <option value="London">London Session</option>
            <option value="New York">New York Session</option>
            <option value="Asian">Asian Session</option>
            <option value="Off-hours">Off-hours</option>
          </select>
        </div>
      </div>

      {error && <div className="stats-error-alert">{error}</div>}

      {/* 22 METRICS KPI GRID */}
      <div className="kpi-macro-grid">
        {/* Net Realized P&L */}
        <div className="kpi-stat-card hero-kpi">
          <div className="kpi-lbl">Net Realized P&L</div>
          <div className={`kpi-val ${metrics && metrics.net_pnl >= 0 ? "positive" : "negative"}`}>
            {fmtCurrency(metrics?.net_pnl)}
          </div>
          <div className="kpi-sub-split">
            <span>Gross Profit: <strong className="positive">{fmtCurrency(metrics?.gross_profit)}</strong></span>
            <span>Gross Loss: <strong className="negative">{fmtCurrency(metrics?.gross_loss ? -metrics.gross_loss : 0)}</strong></span>
          </div>
        </div>

        {/* Win Rate % */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Win Rate (Excl. Breakeven)</div>
          <div className="kpi-val positive">{fmtPct(metrics?.win_rate)}</div>
          <div className="kpi-sub-split">
            <span>Wins: <strong className="positive">{metrics?.winning_trades?.toLocaleString() || 0}</strong></span>
            <span>Losses: <strong className="negative">{metrics?.losing_trades?.toLocaleString() || 0}</strong></span>
            <span>BE: <strong>{metrics?.breakeven_trades || 0}</strong></span>
          </div>
        </div>

        {/* Profit Factor */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Profit Factor</div>
          <div className="kpi-val">
            {metrics?.profit_factor !== null && metrics?.profit_factor !== undefined
              ? metrics.profit_factor.toFixed(2)
              : "N/A"}
          </div>
          <div className="kpi-sub-text">
            Ratio of gross profits to gross losses
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Maximum Drawdown</div>
          <div className="kpi-val negative">
            {metrics?.max_drawdown_pct ? `${metrics.max_drawdown_pct.toFixed(2)}%` : "0.00%"}
          </div>
          <div className="kpi-sub-text">
            Peak-to-trough: -${metrics?.max_drawdown_currency?.toLocaleString() || "0"}
          </div>
        </div>

        {/* Expectancy */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Trade Expectancy</div>
          <div className={`kpi-val ${metrics && (metrics.expectancy || 0) >= 0 ? "positive" : "negative"}`}>
            {fmtCurrency(metrics?.expectancy)}
          </div>
          <div className="kpi-sub-text">
            Average return per executed trade
          </div>
        </div>

        {/* Average Win / Loss Ratio */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Avg Win / Loss</div>
          <div className="kpi-val">
            {metrics?.average_rr_ratio ? `${metrics.average_rr_ratio.toFixed(2)}:1` : "--"}
          </div>
          <div className="kpi-sub-split">
            <span>Avg Win: <strong className="positive">{fmtCurrency(metrics?.average_win)}</strong></span>
            <span>Avg Loss: <strong className="negative">{fmtCurrency(metrics?.average_loss)}</strong></span>
          </div>
        </div>

        {/* Total Trading Costs */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Friction & Trading Costs</div>
          <div className="kpi-val negative">
            -${metrics?.total_trading_costs?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || "0.00"}
          </div>
          <div className="kpi-sub-text">
            Commissions, execution fees, & swaps
          </div>
        </div>

        {/* Average Trade Duration */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Avg Holding Duration</div>
          <div className="kpi-val">
            {metrics?.average_holding_duration_seconds
              ? `${(metrics.average_holding_duration_seconds / 3600).toFixed(1)} hrs`
              : "--"}
          </div>
          <div className="kpi-sub-text">
            Elapsed duration from entry to close
          </div>
        </div>

        {/* Best / Worst Trade */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Best Trade</div>
          <div className="kpi-val positive">
            {fmtCurrency(metrics?.best_trade?.net_pnl)}
          </div>
          <div className="kpi-sub-text">
            {metrics?.best_trade?.symbol} ({metrics?.best_trade?.direction})
          </div>
        </div>

        <div className="kpi-stat-card">
          <div className="kpi-lbl">Worst Trade</div>
          <div className="kpi-val negative">
            {fmtCurrency(metrics?.worst_trade?.net_pnl)}
          </div>
          <div className="kpi-sub-text">
            {metrics?.worst_trade?.symbol} ({metrics?.worst_trade?.direction})
          </div>
        </div>

        {/* Streaks & Consecutive Runs */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Max Consecutive Wins / Losses</div>
          <div className="kpi-val">
            <span className="positive">{metrics?.max_consecutive_wins || 0}W</span> /{" "}
            <span className="negative">{metrics?.max_consecutive_losses || 0}L</span>
          </div>
          <div className="kpi-sub-text">
            Peak winning & losing streaks
          </div>
        </div>

        {/* Daily Win/Loss Distribution */}
        <div className="kpi-stat-card">
          <div className="kpi-lbl">Profitable / Losing Days</div>
          <div className="kpi-val">
            <span className="positive">{metrics?.profitable_days_count || 0}</span> /{" "}
            <span className="negative">{metrics?.losing_days_count || 0}</span>
          </div>
          <div className="kpi-sub-text">
            Active trading calendar days
          </div>
        </div>
      </div>

      {/* VISUAL CHARTS SECTION */}
      <div className="charts-split-section">
        {/* Realized Cumulative Equity Curve */}
        <div className="chart-panel">
          <div className="panel-head">
            <div>
              <h3>📈 Realized Equity Curve</h3>
              <p>Continuous closed-trade cumulative account growth & drawdown trajectory</p>
            </div>
            <div className="panel-tag">Realized Closed P&L</div>
          </div>

          <div className="chart-body">
            {equityChart ? (
              <div className="svg-chart-container">
                <svg
                  viewBox={`0 0 ${equityChart.width} ${equityChart.height}`}
                  className="interactive-svg"
                >
                  <defs>
                    <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal zero reference */}
                  <line
                    x1={equityChart.padding}
                    y1={equityChart.zeroY}
                    x2={equityChart.width - equityChart.padding}
                    y2={equityChart.zeroY}
                    stroke="rgba(255,255,255,0.15)"
                    strokeDasharray="4 4"
                  />

                  {/* Shaded Area */}
                  <path d={equityChart.areaD} fill="url(#equityGrad)" />

                  {/* Line */}
                  <path
                    d={equityChart.pathD}
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Interactive Points */}
                  {equityChart.points.map((pt, i) => (
                    <circle
                      key={i}
                      cx={pt.x}
                      cy={pt.y}
                      r="4"
                      className="chart-circle"
                      onMouseEnter={() =>
                        setHoveredPoint({
                          x: pt.x,
                          y: pt.y,
                          label: pt.p.date,
                          value: `P&L: ${(pt.p.net_pnl ?? 0) >= 0 ? "+" : ""}${(pt.p.net_pnl ?? 0).toFixed(2)} · Cumulative: $${pt.cum.toFixed(2)}`,
                        })
                      }
                      onMouseLeave={() => setHoveredPoint(null)}
                    />
                  ))}
                </svg>

                {hoveredPoint && (
                  <div
                    className="chart-tooltip"
                    style={{ left: `${(hoveredPoint.x / equityChart.width) * 100}%`, top: `${hoveredPoint.y - 40}px` }}
                  >
                    <strong>{hoveredPoint.label}</strong>
                    <span>{hoveredPoint.value}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="no-chart-data">No equity curve data available for selected period.</div>
            )}
          </div>
        </div>

        {/* Continuous Daily P&L Series */}
        <div className="chart-panel">
          <div className="panel-head">
            <div>
              <h3>📊 Daily Net P&L Distribution</h3>
              <p>Chronological net returns per calendar day (zero-activity days included)</p>
            </div>
            <div className="panel-tag">{dailyPnL.length} Days</div>
          </div>

          <div className="chart-body">
            {dailyPnL.length > 0 ? (
              <div className="bar-chart-container">
                {dailyPnL.slice(-45).map((day, idx) => {
                  const isPositive = day.net_pnl > 0;
                  const isZero = day.net_pnl === 0;
                  const maxDayPnl = Math.max(...dailyPnL.map((d) => Math.abs(d.net_pnl)), 100);
                  const barHeight = Math.min(100, (Math.abs(day.net_pnl) / maxDayPnl) * 100);

                  return (
                    <div
                      key={idx}
                      className="day-bar-column"
                      title={`${day.date}: ${isPositive ? "+" : ""}$${day.net_pnl.toFixed(2)} (${day.closed_trades} trades)`}
                    >
                      <div className="bar-track">
                        {!isZero && (
                          <div
                            className={`pnl-bar ${isPositive ? "bar-green" : "bar-red"}`}
                            style={{ height: `${Math.max(6, barHeight)}%` }}
                          />
                        )}
                        {isZero && <div className="zero-dot" />}
                      </div>
                      <span className="bar-label">{day.date.slice(5)}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="no-chart-data">No daily P&L records for selected range.</div>
            )}
          </div>
        </div>
      </div>

      {/* PERFORMANCE BREAKDOWN TABLES */}
      <div className="breakdown-section">
        <div className="breakdown-header">
          <div>
            <h3>🔍 Performance Attribution & Breakdown</h3>
            <p>Categorical attribution across setups, market sessions, symbols, and directions</p>
          </div>
          <div className="breakdown-pills">
            {(["strategy", "session", "symbol", "direction"] as const).map((dim) => (
              <button
                key={dim}
                className={`dim-pill ${breakdownDim === dim ? "active" : ""}`}
                onClick={() => setBreakdownDim(dim)}
              >
                By {dim.charAt(0).toUpperCase() + dim.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="breakdown-table-wrap">
          <table className="breakdown-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Trades</th>
                <th>Win / Loss</th>
                <th>Win Rate %</th>
                <th>Gross Profit</th>
                <th>Gross Loss</th>
                <th>Net Realized P&L</th>
                <th>Profit Factor</th>
                <th>Avg Trade</th>
              </tr>
            </thead>
            <tbody>
              {breakdowns.length === 0 ? (
                <tr>
                  <td colSpan={9} className="empty-state">
                    No breakdown items found for this dimension.
                  </td>
                </tr>
              ) : (
                breakdowns.map((item, idx) => (
                  <tr key={idx}>
                    <td className="cell-cat">
                      <strong>{item.item_name || (item as any).key || "Unspecified"}</strong>
                    </td>
                    <td className="cell-num">{(item.trades_count ?? (item as any).trade_count ?? 0).toLocaleString()}</td>
                    <td className="cell-num">
                      <span className="positive">{item.winning_trades ?? 0}W</span> /{" "}
                      <span className="negative">{item.losing_trades ?? 0}L</span>
                    </td>
                    <td className="cell-num">
                      <div className="winrate-bar-cell">
                        <span className="positive">{item.win_rate != null ? `${item.win_rate.toFixed(1)}%` : "N/A"}</span>
                        <div className="progress-bg">
                          <div
                            className="progress-fill"
                            style={{ width: `${Math.min(100, item.win_rate || 0)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="cell-num positive">${(item.gross_profit ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="cell-num negative">-${(item.gross_loss ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className={`cell-num ${(item.net_pnl ?? 0) >= 0 ? "positive" : "negative"}`}>
                      <strong>{fmtCurrency(item.net_pnl)}</strong>
                    </td>
                    <td className="cell-num">
                      {item.profit_factor !== null && item.profit_factor !== undefined
                        ? item.profit_factor.toFixed(2)
                        : "N/A"}
                    </td>
                    <td className={`cell-num ${item.average_trade_pnl != null && item.average_trade_pnl >= 0 ? "positive" : "negative"}`}>
                      {fmtCurrency(item.average_trade_pnl ?? (item as any).avg_trade_pnl)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
