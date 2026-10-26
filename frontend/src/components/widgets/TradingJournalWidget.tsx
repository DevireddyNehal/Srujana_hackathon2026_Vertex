import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import type { TradeRecord, PaginatedTrades, UserProfile } from "../../types/trading";
import {
  getJournalTrades,
  createJournalTrade,
  updateJournalTrade,
  deleteJournalTrade,
  getTradeReview,
  importJournalTradesCsv,
  getDeviceId,
} from "../../api/client";

interface TradingJournalWidgetProps {
  currentUser: UserProfile | null;
  authToken?: string | null;
  onOpenAuthModal?: () => void;
  currency?: "INR" | "USD";
  conversionRate?: number;
}

function toLocalISOString(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function TradingJournalWidget({
  currentUser,
  authToken,
  onOpenAuthModal,
  currency = "INR",
  conversionRate = 83.5,
}: TradingJournalWidgetProps) {
  const formatMoney = useCallback(
    (val: number | null | undefined, showSign = false) => {
      if (val === null || val === undefined) return "--";
      const isINR = currency === "INR";
      const rate = isINR ? conversionRate : 1;
      const converted = val * rate;
      const sign = showSign && converted >= 0 ? "+" : converted < 0 ? "-" : "";
      const absVal = Math.abs(converted);
      if (isINR) {
        return `${sign}₹${absVal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      }
      return `${sign}$${absVal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    [currency, conversionRate]
  );

  const formatBalance = useCallback(
    (val: number | null | undefined) => {
      if (val === null || val === undefined) return "--";
      const isINR = currency === "INR";
      const rate = isINR ? conversionRate : 1;
      const converted = Math.round(val * rate);
      if (isINR) {
        return `₹${converted.toLocaleString("en-IN")}`;
      }
      return `$${converted.toLocaleString("en-US")}`;
    },
    [currency, conversionRate]
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [data, setData] = useState<PaginatedTrades>({
    items: [],
    total: 0,
    page: 1,
    page_size: 25,
    total_pages: 1,
  });
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [searchQuery, setSearchQuery] = useState("");
  const [directionFilter, setDirectionFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("exit_time");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");

  // Trade Modal (Add / Edit)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTrade, setEditingTrade] = useState<TradeRecord | null>(null);

  // Form State
  const [formSymbol, setFormSymbol] = useState("EUR/USD");
  const [formAssetClass, setFormAssetClass] = useState("Forex");
  const [formDirection, setFormDirection] = useState<"LONG" | "SHORT">("LONG");
  const [formStatus, setFormStatus] = useState<"OPEN" | "CLOSED">("CLOSED");
  const [formEntryTime, setFormEntryTime] = useState(() =>
    toLocalISOString(new Date(Date.now() - 3600000))
  );
  const [formExitTime, setFormExitTime] = useState(() =>
    toLocalISOString(new Date())
  );
  const [formEntryPrice, setFormEntryPrice] = useState("1.0850");
  const [formExitPrice, setFormExitPrice] = useState("1.0920");
  const [formQuantity, setFormQuantity] = useState("1.0");
  const [formContractSize, setFormContractSize] = useState("100000");
  const [formStopLoss, setFormStopLoss] = useState("1.0800");
  const [formTakeProfit, setFormTakeProfit] = useState("1.0950");
  const [formStrategy, setFormStrategy] = useState("Trend Pullback");
  const [formSession, setFormSession] = useState("London");
  const [formNotes, setFormNotes] = useState("");
  const [formTags, setFormTags] = useState("");

  // Review Drawer Modal
  const [reviewTrade, setReviewTrade] = useState<TradeRecord | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewData, setReviewData] = useState<{
    status: string;
    trade_id: string;
    symbol: string;
    direction: string;
    net_pnl: number;
    observations: string[];
    suggestions: string[];
    disclaimer: string;
  } | null>(null);

  const loadTrades = useCallback(async () => {
    if (!currentUser) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getJournalTrades(
        {
          page,
          page_size: pageSize,
          search: searchQuery || undefined,
          direction: directionFilter || undefined,
          status: statusFilter === "all" ? undefined : statusFilter,
          sort_by: sortBy,
          sort_order: sortOrder,
        },
        currentUser.id,
        authToken || undefined
      );
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trades");
    } finally {
      setLoading(false);
    }
  }, [currentUser, authToken, page, pageSize, searchQuery, directionFilter, statusFilter, sortBy, sortOrder]);

  useEffect(() => {
    void Promise.resolve().then(() => {
      loadTrades();
    });
  }, [loadTrades]);

  function handleOpenAddModal() {
    setEditingTrade(null);
    setFormSymbol("EUR/USD");
    setFormAssetClass("Forex");
    setFormDirection("LONG");
    setFormStatus("CLOSED");
    setFormEntryTime(toLocalISOString(new Date(Date.now() - 3600000)));
    setFormExitTime(toLocalISOString(new Date()));
    setFormEntryPrice("1.0850");
    setFormExitPrice("1.0920");
    setFormQuantity("1.0");
    setFormContractSize("100000");
    setFormStopLoss("1.0800");
    setFormTakeProfit("1.0950");
    setFormStrategy("Trend Pullback");
    setFormSession("London");
    setFormNotes("");
    setFormTags("momentum,trend");
    setIsModalOpen(true);
  }

  function handleOpenEditModal(trade: TradeRecord) {
    setEditingTrade(trade);
    setFormSymbol(trade.symbol);
    setFormAssetClass(trade.asset_class);
    setFormDirection(trade.direction === "SHORT" ? "SHORT" : "LONG");
    setFormStatus(trade.status === "OPEN" ? "OPEN" : "CLOSED");
    setFormEntryTime(trade.entry_time ? trade.entry_time.slice(0, 16) : "");
    setFormExitTime(trade.exit_time ? trade.exit_time.slice(0, 16) : "");
    setFormEntryPrice(String(trade.entry_price));
    setFormExitPrice(trade.exit_price ? String(trade.exit_price) : "");
    setFormQuantity(String(trade.quantity));
    setFormContractSize(String(trade.contract_size || 100000));
    setFormStopLoss(trade.stop_loss_price ? String(trade.stop_loss_price) : "");
    setFormTakeProfit(trade.take_profit_price ? String(trade.take_profit_price) : "");
    setFormStrategy(trade.strategy_or_setup || "");
    setFormSession(trade.trading_session || "London");
    setFormNotes(trade.notes || "");
    setFormTags(trade.tags || "");
    setIsModalOpen(true);
  }

  async function handleSaveTrade(e: React.FormEvent) {
    e.preventDefault();
    if (!currentUser) return;
    try {
      setLoading(true);
      const payload: Partial<TradeRecord> = {
        symbol: formSymbol.trim().toUpperCase(),
        asset_class: formAssetClass,
        direction: formDirection,
        status: formStatus,
        entry_time: new Date(formEntryTime).toISOString(),
        exit_time: formStatus === "CLOSED" ? new Date(formExitTime).toISOString() : null,
        entry_price: parseFloat(formEntryPrice) || 0,
        exit_price: formStatus === "CLOSED" ? parseFloat(formExitPrice) || null : null,
        quantity: parseFloat(formQuantity) || 1.0,
        contract_size: parseFloat(formContractSize) || 100000.0,
        account_currency: currentUser.currency || "USD",
        stop_loss_price: formStopLoss ? parseFloat(formStopLoss) : null,
        take_profit_price: formTakeProfit ? parseFloat(formTakeProfit) : null,
        strategy_or_setup: formStrategy.trim() || "Manual",
        trading_session: formSession,
        notes: formNotes.trim(),
        tags: formTags.trim(),
      };

      if (editingTrade) {
        await updateJournalTrade(editingTrade.id, payload, currentUser.id, authToken || undefined);
      } else {
        await createJournalTrade(payload, currentUser.id, authToken || undefined);
        setPage(1);
        if (statusFilter !== "all" && statusFilter !== formStatus.toLowerCase()) {
          setStatusFilter("all");
        }
        if (directionFilter && directionFilter !== formDirection) {
          setDirectionFilter("");
        }
      }
      setIsModalOpen(false);
      loadTrades();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to save trade");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteTrade(tradeId: string) {
    if (!currentUser) return;
    if (!confirm("Are you sure you want to delete this trade record?")) return;
    try {
      setLoading(true);
      await deleteJournalTrade(tradeId, currentUser.id, authToken || undefined);
      loadTrades();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete trade");
    } finally {
      setLoading(false);
    }
  }

  async function handleOpenReview(trade: TradeRecord) {
    setReviewTrade(trade);
    setReviewLoading(true);
    setReviewData(null);
    try {
      const res = await getTradeReview(trade.id, currentUser?.id, authToken || undefined);
      setReviewData(res);
    } catch (err) {
      console.warn("Backend review fetch failed, falling back to client evaluation:", err);
    } finally {
      setReviewLoading(false);
    }
  }

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !currentUser) return;
    try {
      setImporting(true);
      const res = await importJournalTradesCsv(file, currentUser.id, authToken || undefined);
      alert(`CSV Import: Successfully imported ${res.imported_count} trades!${res.error_count > 0 ? ` (${res.error_count} skipped)` : ""}`);
      loadTrades();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to import CSV");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleExportCsv() {
    if (!currentUser) return;
    const query = new URLSearchParams();
    if (searchQuery) query.append("search", searchQuery);
    if (directionFilter) query.append("direction", directionFilter);
    if (statusFilter !== "all") query.append("status", statusFilter);

    const token = authToken || localStorage.getItem("vertex_auth_token") || "";
    const url = `/api/v1/trades/export/csv?${query.toString()}`;
    const link = document.createElement("a");
    link.href = url;
    // Use fetch with auth header to trigger download
    fetch(url, {
      headers: {
        "X-User-Id": currentUser.id,
        "X-Device-Id": getDeviceId(),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        link.href = downloadUrl;
        link.download = `trades_${currentUser.id}_${Date.now()}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      })
      .catch((e) => alert("Failed to export CSV: " + e.message));
  }

  // Summary figures from active page items
  const winningCount = data.items.filter((t) => t.net_pnl > 0).length;
  const losingCount = data.items.filter((t) => t.net_pnl < 0).length;
  const pageNetPnL = data.items.reduce((sum, t) => sum + (t.net_pnl || 0), 0);

  return (
    <div className="trading-journal-container">
      {/* Top Banner with User Switcher & Info */}
      <div className="journal-header-strip">
        <div className="header-meta">
          <h2>📓 Professional Trade Journal</h2>
          <p>
            Systematic trade execution logging, execution reviews, and performance attribution for{" "}
            <strong>{currentUser?.name || "Active Trader"}</strong>
          </p>
        </div>

        <div className="header-actions">
          <button className="btn-secondary-action" onClick={onOpenAuthModal}>
            👤 {currentUser?.name || "Switch User"} ({currency || "INR"}{" "}
            {formatBalance(currentUser?.starting_balance ?? 50000)})
          </button>
          <button className="btn-primary-action btn-log-trade" onClick={handleOpenAddModal}>
            + Log New Trade
          </button>
          <button
            className="btn-secondary-action"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            title="Import trades from CSV"
          >
            {importing ? "⏳ Importing..." : "📤 Import CSV"}
          </button>
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv"
            style={{ display: "none" }}
            onChange={handleFileSelected}
          />
          <button className="btn-export-action" onClick={handleExportCsv} title="Export filtered trades to CSV">
            📥 Export CSV
          </button>
        </div>
      </div>

      {/* KPI Micro-Strip */}
      <div className="journal-kpi-strip">
        <div className="kpi-mini-card">
          <span className="lbl">Total Trades (Database)</span>
          <span className="val">{(data?.total ?? 0).toLocaleString()}</span>
        </div>
        <div className="kpi-mini-card">
          <span className="lbl">Page Net P&L</span>
          <span className={`val ${pageNetPnL >= 0 ? "positive" : "negative"}`}>
            {formatMoney(pageNetPnL, true)}
          </span>
        </div>
        <div className="kpi-mini-card">
          <span className="lbl">Page Win/Loss</span>
          <span className="val">
            <span className="positive">{winningCount}W</span> / <span className="negative">{losingCount}L</span>
          </span>
        </div>
        <div className="kpi-mini-card">
          <span className="lbl">Page Win Rate</span>
          <span className="val">
            {winningCount + losingCount > 0
              ? `${((winningCount / (winningCount + losingCount)) * 100).toFixed(1)}%`
              : "N/A"}
          </span>
        </div>
      </div>

      {/* Control Bar: Filters, Search, Sort */}
      <div className="journal-control-bar">
        <div className="search-wrap">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search by Symbol, Notes, Strategy, or Tags..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            className="filter-input"
          />
        </div>

        <div className="filter-group">
          <label>Direction:</label>
          <select
            value={directionFilter}
            onChange={(e) => {
              setDirectionFilter(e.target.value);
              setPage(1);
            }}
            className="filter-select"
          >
            <option value="">All Directions</option>
            <option value="LONG">LONG Only</option>
            <option value="SHORT">SHORT Only</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="filter-select"
          >
            <option value="all">All Status</option>
            <option value="closed">Closed</option>
            <option value="open">Open</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Sort By:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="filter-select"
          >
            <option value="exit_time">Exit Date (Most Recent)</option>
            <option value="created_at">Recently Logged</option>
            <option value="entry_time">Entry Date</option>
            <option value="net_pnl">Net Realized P&L</option>
            <option value="realized_r_multiple">R-Multiple</option>
            <option value="symbol">Symbol</option>
          </select>
          <button
            className="btn-sort-toggle"
            onClick={() => setSortOrder(sortOrder === "desc" ? "asc" : "desc")}
            title="Toggle sort direction"
          >
            {sortOrder === "desc" ? "▼ DESC" : "▲ ASC"}
          </button>
        </div>

        <button className="btn-refresh" onClick={loadTrades} title="Reload trades">
          🔄
        </button>
      </div>

      {error && <div className="journal-error-alert">{error}</div>}

      {/* Main Trades Table */}
      <div className="trades-table-wrap">
        {loading && <div className="table-loader-overlay">Loading trades...</div>}
        <table className="trades-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Side</th>
              <th>Status</th>
              <th>Entry Price</th>
              <th>Exit Price</th>
              <th>Quantity</th>
              <th>Net P&L</th>
              <th>R-Mult</th>
              <th>Strategy / Session</th>
              <th>Closed Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 ? (
              <tr>
                <td colSpan={11} className="empty-table-state">
                  No trades found matching criteria. Click <strong>"+ Log New Trade"</strong> to record an execution.
                </td>
              </tr>
            ) : (
              data.items.map((trade) => {
                const isWin = trade.net_pnl > 0;
                const isLoss = trade.net_pnl < 0;
                return (
                  <tr key={trade.id} className={isWin ? "row-win" : isLoss ? "row-loss" : ""}>
                    <td className="cell-symbol">
                      <strong>{trade.symbol}</strong>
                      <span className="sub-asset">{trade.asset_class}</span>
                    </td>
                    <td>
                      <span className={`direction-pill ${trade.direction.toLowerCase()}`}>
                        {trade.direction}
                      </span>
                    </td>
                    <td>
                      <span className={`status-pill ${trade.status.toLowerCase()}`}>
                        {trade.status}
                      </span>
                    </td>
                    <td className="cell-num">{trade.entry_price.toFixed(4)}</td>
                    <td className="cell-num">{trade.exit_price ? trade.exit_price.toFixed(4) : "--"}</td>
                    <td className="cell-num">{trade.quantity.toFixed(2)}</td>
                    <td className={`cell-num cell-pnl ${isWin ? "positive" : isLoss ? "negative" : ""}`}>
                      {trade.net_pnl !== null ? (
                        <>
                          {formatMoney(trade.net_pnl, true)}
                        </>
                      ) : (
                        "--"
                      )}
                    </td>
                    <td className="cell-num cell-rmult">
                      {trade.realized_r_multiple !== null && trade.realized_r_multiple !== undefined ? (
                        <span className={trade.realized_r_multiple > 0 ? "positive" : "negative"}>
                          {trade.realized_r_multiple.toFixed(2)}R
                        </span>
                      ) : (
                        "--"
                      )}
                    </td>
                    <td>
                      <div className="strategy-tag">{trade.strategy_or_setup || "Standard"}</div>
                      <span className="session-sub">{trade.trading_session || "General"}</span>
                    </td>
                    <td className="cell-date">
                      {trade.exit_time
                        ? new Date(trade.exit_time).toLocaleDateString() + " " + new Date(trade.exit_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : trade.entry_time
                        ? new Date(trade.entry_time).toLocaleDateString()
                        : "--"}
                    </td>
                    <td className="cell-actions">
                      <button
                        className="btn-tbl-action btn-review"
                        onClick={() => handleOpenReview(trade)}
                        title="AI Checklist Review"
                      >
                        🧠 Review
                      </button>
                      <button
                        className="btn-tbl-action btn-edit"
                        onClick={() => handleOpenEditModal(trade)}
                        title="Edit trade"
                      >
                        ✏️
                      </button>
                      <button
                        className="btn-tbl-action btn-delete"
                        onClick={() => handleDeleteTrade(trade.id)}
                        title="Delete trade"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="journal-pagination-footer">
        <div className="page-size-selector">
          <span>Show:</span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span>records per page</span>
        </div>

        <div className="pagination-controls">
          <span>
            Page <strong>{data.page}</strong> of <strong>{data.total_pages || 1}</strong> (
            {(data?.total ?? 0).toLocaleString()} total trades)
          </span>
          <button
            className="btn-page-nav"
            disabled={page <= 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            ◀ Previous
          </button>
          <button
            className="btn-page-nav"
            disabled={page >= data.total_pages || loading}
            onClick={() => setPage(page + 1)}
          >
            Next ▶
          </button>
        </div>
      </div>

      {/* ADD / EDIT TRADE MODAL */}
      {isModalOpen && createPortal(
        <div className="auth-modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <div className="journal-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="auth-modal-header">
              <h3>{editingTrade ? "✏️ Edit Journal Trade" : "+ Log New Trade Execution"}</h3>
              <button className="auth-close-btn" onClick={() => setIsModalOpen(false)}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveTrade} className="trade-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Ticker / Symbol</label>
                  <input
                    type="text"
                    required
                    value={formSymbol}
                    onChange={(e) => setFormSymbol(e.target.value)}
                    placeholder="e.g. EUR/USD, AAPL, BTC/USD"
                    className="auth-input"
                  />
                </div>
                <div className="form-group">
                  <label>Asset Class</label>
                  <select
                    value={formAssetClass}
                    onChange={(e) => setFormAssetClass(e.target.value)}
                    className="auth-input"
                  >
                    <option value="Forex">Forex</option>
                    <option value="Equity">Equity</option>
                    <option value="Commodity">Commodity</option>
                    <option value="Crypto">Crypto</option>
                    <option value="Index">Index</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Direction</label>
                  <select
                    value={formDirection}
                    onChange={(e) => setFormDirection(e.target.value as "LONG" | "SHORT")}
                    className="auth-input"
                  >
                    <option value="LONG">LONG (Buy)</option>
                    <option value="SHORT">SHORT (Sell)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Trade Status</label>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as "OPEN" | "CLOSED")}
                    className="auth-input"
                  >
                    <option value="CLOSED">CLOSED (Realized)</option>
                    <option value="OPEN">OPEN</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Entry Price</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formEntryPrice}
                    onChange={(e) => setFormEntryPrice(e.target.value)}
                    className="auth-input"
                  />
                </div>
                {formStatus === "CLOSED" && (
                  <div className="form-group">
                    <label>Exit Price</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={formExitPrice}
                      onChange={(e) => setFormExitPrice(e.target.value)}
                      className="auth-input"
                    />
                  </div>
                )}
                <div className="form-group">
                  <label>Lot / Quantity</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formQuantity}
                    onChange={(e) => setFormQuantity(e.target.value)}
                    className="auth-input"
                  />
                </div>
                <div className="form-group">
                  <label>Contract Size</label>
                  <input
                    type="number"
                    step="any"
                    value={formContractSize}
                    onChange={(e) => setFormContractSize(e.target.value)}
                    className="auth-input"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Entry Date & Time</label>
                  <input
                    type="datetime-local"
                    required
                    value={formEntryTime}
                    onChange={(e) => setFormEntryTime(e.target.value)}
                    className="auth-input"
                  />
                </div>
                {formStatus === "CLOSED" && (
                  <div className="form-group">
                    <label>Exit Date & Time</label>
                    <input
                      type="datetime-local"
                      required
                      value={formExitTime}
                      onChange={(e) => setFormExitTime(e.target.value)}
                      className="auth-input"
                    />
                  </div>
                )}
                <div className="form-group">
                  <label>Planned Stop Loss</label>
                  <input
                    type="number"
                    step="any"
                    value={formStopLoss}
                    onChange={(e) => setFormStopLoss(e.target.value)}
                    placeholder="Optional"
                    className="auth-input"
                  />
                </div>
                <div className="form-group">
                  <label>Planned Take Profit</label>
                  <input
                    type="number"
                    step="any"
                    value={formTakeProfit}
                    onChange={(e) => setFormTakeProfit(e.target.value)}
                    placeholder="Optional"
                    className="auth-input"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Setup / Strategy</label>
                  <input
                    type="text"
                    value={formStrategy}
                    onChange={(e) => setFormStrategy(e.target.value)}
                    placeholder="e.g. Order Block, Trend Pullback"
                    className="auth-input"
                  />
                </div>
                <div className="form-group">
                  <label>Session</label>
                  <select
                    value={formSession}
                    onChange={(e) => setFormSession(e.target.value)}
                    className="auth-input"
                  >
                    <option value="London">London</option>
                    <option value="New York">New York</option>
                    <option value="Asian">Asian</option>
                    <option value="Off-hours">Off-hours</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Tags (comma separated)</label>
                  <input
                    type="text"
                    value={formTags}
                    onChange={(e) => setFormTags(e.target.value)}
                    placeholder="reversal, breakout, fvg"
                    className="auth-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Trade Notes / Thesis / Psychology</label>
                <textarea
                  rows={3}
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  placeholder="Record trade thesis, market context, execution discipline, or lessons learned..."
                  className="auth-input"
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn-save-trade">
                  {loading ? "Saving..." : editingTrade ? "Update Trade" : "Save Journal Entry"}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* AI CHECKLIST REVIEW DRAWER */}
      {reviewTrade && createPortal(
        <div className="auth-modal-backdrop" onClick={() => setReviewTrade(null)}>
          <div className="review-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="auth-modal-header">
              <div className="review-title">
                <span className="brain-icon">🧠</span>
                <div>
                  <h3>Trade Execution & Discipline Review</h3>
                  <p>
                    {reviewTrade.symbol} {reviewTrade.direction} · Net P&L:{" "}
                    <span className={reviewTrade.net_pnl >= 0 ? "positive" : "negative"}>
                      {formatMoney(reviewTrade.net_pnl, true)}
                    </span>
                  </p>
                </div>
              </div>
              <button className="auth-close-btn" onClick={() => setReviewTrade(null)}>
                ✕
              </button>
            </div>

            <div className="review-content">
              {reviewLoading && (
                <div style={{ textAlign: "center", padding: "24px 0", color: "#9ca3af" }}>
                  <span>⏳ Analyzing trade execution parameters & discipline rules...</span>
                </div>
              )}

              {reviewData && !reviewLoading && (
                <>
                  <div className="review-section">
                    <h4>📋 Execution Analysis & Observations</h4>
                    <div className="checklist-items">
                      {reviewData.observations.map((obs, idx) => (
                        <div key={idx} className="chk-item pass">
                          <span className="icon">✓</span>
                          <div>
                            <p>{obs}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="review-section">
                    <h4>💡 Discipline Recommendations & Coaching</h4>
                    <div className="checklist-items">
                      {reviewData.suggestions.map((sug, idx) => (
                        <div key={idx} className="chk-item info">
                          <span className="icon">💡</span>
                          <div>
                            <p>{sug}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {!reviewData && !reviewLoading && (
                <div className="review-section">
                  <h4>📋 Risk Management & Execution Checklist</h4>
                  <div className="checklist-items">
                    <div className={`chk-item ${reviewTrade.stop_loss_price ? "pass" : "warn"}`}>
                      <span className="icon">{reviewTrade.stop_loss_price ? "✓" : "⚠️"}</span>
                      <div>
                        <strong>Stop Loss Protocol</strong>
                        <p>
                          {reviewTrade.stop_loss_price
                            ? `Defined at ${reviewTrade.stop_loss_price.toFixed(4)}. Planned risk was constrained.`
                            : "No stop loss was recorded. Unmanaged risk exposure detected."}
                        </p>
                      </div>
                    </div>

                    <div className={`chk-item ${reviewTrade.realized_r_multiple && reviewTrade.realized_r_multiple >= 1.0 ? "pass" : reviewTrade.realized_r_multiple && reviewTrade.realized_r_multiple < 0 ? "fail" : "info"}`}>
                      <span className="icon">
                        {reviewTrade.realized_r_multiple && reviewTrade.realized_r_multiple >= 1.0
                          ? "✓"
                          : reviewTrade.realized_r_multiple && reviewTrade.realized_r_multiple < 0
                          ? "✕"
                          : "ℹ️"}
                      </span>
                      <div>
                        <strong>Risk-to-Reward Attainment</strong>
                        <p>
                          {reviewTrade.realized_r_multiple !== null && reviewTrade.realized_r_multiple !== undefined
                            ? `Trade realized ${reviewTrade.realized_r_multiple.toFixed(2)}R. ${reviewTrade.realized_r_multiple >= 2.0 ? "High positive expectancy capture!" : "Within expected statistical distribution."}`
                            : "Trade is either open or risk parameters were unmetered."}
                        </p>
                      </div>
                    </div>

                    <div className={`chk-item ${reviewTrade.strategy_or_setup ? "pass" : "warn"}`}>
                      <span className="icon">{reviewTrade.strategy_or_setup ? "✓" : "⚠️"}</span>
                      <div>
                        <strong>Strategy Consistency</strong>
                        <p>
                          {reviewTrade.strategy_or_setup
                            ? `Classified under '${reviewTrade.strategy_or_setup}' during the ${reviewTrade.trading_session || "Standard"} session.`
                            : "No trading strategy assigned. Ensure trades follow a cataloged model."}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="review-section">
                <h4>📝 Trader Notes & Reflection</h4>
                <div className="notes-display">
                  {reviewTrade.notes ? (
                    <p>{reviewTrade.notes}</p>
                  ) : (
                    <p className="no-notes">No execution notes recorded for this trade.</p>
                  )}
                </div>
              </div>

              <div className="review-disclaimer">
                {reviewData?.disclaimer || "Disclaimer: Descriptive algorithmic checklist generated from recorded trade parameters. Does not constitute financial advice."}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
