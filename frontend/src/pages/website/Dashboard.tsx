import { useEffect, useMemo, useState, type CSSProperties } from "react";
import "./dashboard.css";
import {
  calculateMetrics,
  calculateScenario,
  calculateWarnings,
  formatPercent,
  normalizeHoldings,
} from "./portfolioCalculations";
import {
  classCorrelations,
  portfolios,
  scenarios,
  type Portfolio,
  type Scenario,
} from "./portfolioData";

type Currency = "INR" | "USD";
type PageName = "overview" | "allocation" | "stresslab" | "compare";

const pages: Array<{ id: PageName; label: string; file: string; title: string; eyebrow: string }> = [
  { id: "overview", label: "Overview", file: "index.html?page=overview", title: "Risk overview", eyebrow: "Portfolio analytics" },
  { id: "allocation", label: "Allocation", file: "index.html?page=allocation", title: "Allocation analysis", eyebrow: "Portfolio structure" },
  { id: "stresslab", label: "Stress Lab", file: "index.html?page=stresslab", title: "Scenario stress lab", eyebrow: "Hypothetical analysis" },
  { id: "compare", label: "Compare", file: "index.html?page=compare", title: "Strategy comparison", eyebrow: "Allocation alternatives" },
];

interface SavedDashboardState {
  portfolioId: string;
  weights: number[];
  alternativeWeights: number[];
  period: 12 | 24;
  currency: Currency;
  activeScenario: Scenario | null;
  riskTolerance: string;
  horizon: number;
  liquidityNeed: number;
  lossLimit: number;
  darkMode: boolean;
}

function currentPage(): PageName {
  const page = new URLSearchParams(window.location.search).get("page");
  return pages.some((item) => item.id === page) ? (page as PageName) : "overview";
}

function loadSavedState(): SavedDashboardState | null {
  const raw = window.localStorage.getItem("aperture-risk-lab-state");
  if (!raw) return null;

  try {
    const saved = JSON.parse(raw) as Partial<SavedDashboardState>;
    const portfolio = portfolios.find((item) => item.id === saved.portfolioId);
    if (!portfolio) return null;
    const weights = Array.isArray(saved.weights) && saved.weights.length === portfolio.holdings.length
      ? saved.weights.map((weight) => (Number.isFinite(weight) ? Math.max(0, weight) : 0))
      : portfolio.holdings.map((holding) => holding.weight);
    const alternativeWeights = Array.isArray(saved.alternativeWeights) &&
      saved.alternativeWeights.length === portfolio.holdings.length
      ? saved.alternativeWeights.map((weight) => (Number.isFinite(weight) ? Math.max(0, weight) : 0))
      : createAlternativeWeights(portfolio);

    return {
      portfolioId: portfolio.id,
      weights,
      alternativeWeights,
      period: saved.period === 24 ? 24 : 12,
      currency: saved.currency === "USD" ? "USD" : "INR",
      activeScenario: scenarios.some((scenario) => scenario.id === saved.activeScenario?.id)
        ? saved.activeScenario ?? null
        : null,
      riskTolerance: ["Conservative", "Moderate", "Aggressive"].includes(saved.riskTolerance ?? "")
        ? saved.riskTolerance!
        : profileRisk(portfolio.investorProfile),
      horizon: [1, 3, 5, 10, 15].includes(saved.horizon ?? -1)
        ? saved.horizon!
        : portfolio.investorProfile.horizon_years,
      liquidityNeed: Number.isFinite(saved.liquidityNeed)
        ? Math.max(0, saved.liquidityNeed!)
        : demoLiquidityNeed(portfolio),
      lossLimit: [10, 15, 20, 30].includes(saved.lossLimit ?? -1) ? saved.lossLimit! : 15,
      darkMode: saved.darkMode === true,
    };
  } catch (error) {
    console.error("Could not read saved Vertex dashboard settings.", error);
    window.localStorage.removeItem("aperture-risk-lab-state");
    return null;
  }
}

const colors = [
  "var(--allocation-color-1)",
  "var(--allocation-color-2)",
  "var(--allocation-color-3)",
  "var(--allocation-color-4)",
  "var(--allocation-color-5)",
  "var(--allocation-color-6)",
];
const illustrativeUsdInr = 83.5;

function money(value: number, currency: Currency, compact = false): string {
  const converted = currency === "USD" ? value / illustrativeUsdInr : value;
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
    notation: compact ? "compact" : "standard",
  }).format(converted);
}

function signedMoney(value: number, currency: Currency): string {
  return `${value < 0 ? "−" : "+"}${money(Math.abs(value), currency)}`;
}

function profileRisk(profile: Portfolio["investorProfile"]): string {
  if (profile.risk_tolerance === "Low") return "Conservative";
  if (profile.risk_tolerance === "High") return "Aggressive";
  return "Moderate";
}

function demoLiquidityNeed(portfolio: Portfolio): number {
  const assumedShare =
    portfolio.investorProfile.liquidity_need === "High"
      ? 0.2
      : portfolio.investorProfile.liquidity_need === "Medium"
        ? 0.1
        : 0.05;
  return portfolio.investorProfile.target_goal_inr * assumedShare;
}

function createAlternativeWeights(portfolio: Portfolio): number[] {
  const bucketTarget: Record<string, number> = {
    Equity: 38,
    Debt: 32,
    Commodity: 16,
    Alternative: 14,
  };
  const byClass = portfolio.holdings.reduce<Record<string, number>>((map, holding) => {
    map[holding.assetClass] = (map[holding.assetClass] ?? 0) + holding.weight;
    return map;
  }, {});
  const availableTargetTotal = Object.keys(byClass).reduce(
    (sum, assetClass) => sum + (bucketTarget[assetClass] ?? 0),
    0,
  );
  return portfolio.holdings.map((holding) => {
    const classTotal = byClass[holding.assetClass] ?? 0;
    const desiredTotal =
      ((bucketTarget[holding.assetClass] ?? 0) / availableTargetTotal) * 100;
    return classTotal > 0 ? (desiredTotal * holding.weight) / classTotal : 0;
  });
}

function pathFor(values: number[], width: number, height: number, min: number, max: number) {
  const span = Math.max(max - min, 1);
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function riskColor(value: number): string {
  if (value < -0.05) return "rgba(var(--risk-negative), 0.16)";
  if (value < 0.1) return "rgba(var(--risk-neutral), 0.09)";
  return `rgba(var(--risk-positive), ${0.12 + Math.min(value, 1) * 0.25})`;
}

function Header({
  activePage,
  portfolioId,
  onPortfolioChange,
  currency,
  onCurrencyChange,
  period,
  onPeriodChange,
  darkMode,
  onToggleDarkMode,
  onReset,
}: {
  activePage: PageName;
  portfolioId: string;
  onPortfolioChange: (id: string) => void;
  currency: Currency;
  onCurrencyChange: (currency: Currency) => void;
  period: 12 | 24;
  onPeriodChange: (period: 12 | 24) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onReset: () => void;
}) {
  const activeIndex = pages.findIndex((page) => page.id === activePage);

  return (
    <header className="app-header">
      <a className="brand" href="index.html?page=overview" aria-label="Vertex portfolio risk lab home">
        <span className="brand-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        <span className="brand-name">Vertex<span className="brand-divider">/</span><small>RISK LAB</small></span>
      </a>
      <nav className="top-nav" aria-label="Main navigation" style={{ "--active-tab": activeIndex } as CSSProperties}>
        {pages.map((page) => (
          <a
            key={page.id}
            href={page.file}
            className={activePage === page.id ? "active" : ""}
            aria-current={activePage === page.id ? "page" : undefined}
          >
            {page.label}
          </a>
        ))}
      </nav>
      <div className="header-controls">
        <label className="header-select">
          <span className="sr-only">Portfolio</span>
          <select value={portfolioId} onChange={(event) => onPortfolioChange(event.target.value)}>
            {portfolios.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        </label>
        <label className="header-select currency-select">
          <span className="sr-only">Reporting currency</span>
          <select
            value={currency}
            onChange={(event) => onCurrencyChange(event.target.value as Currency)}
          >
            <option value="INR">INR ₹</option>
            <option value="USD">USD $</option>
          </select>
        </label>
        <label className="header-select period-select">
          <span className="sr-only">Historical analysis period</span>
          <select
            value={period}
            onChange={(event) => onPeriodChange(Number(event.target.value) as 12 | 24)}
          >
            <option value={12}>12 months</option>
            <option value={24}>24 months</option>
          </select>
        </label>
        <span className="data-status"><i /> Sample data</span>
        <button type="button" className="reset-view" onClick={onReset}>Reset view</button>
        <button
          type="button"
          className="theme-toggle"
          onClick={onToggleDarkMode}
          aria-label={`Switch to ${darkMode ? "light" : "dark"} mode`}
          title={`Switch to ${darkMode ? "light" : "dark"} mode`}
          aria-pressed={darkMode}
        >
          <span aria-hidden="true">{darkMode ? "☀" : "☾"}</span>
          <span>{darkMode ? "Light mode" : "Dark mode"}</span>
        </button>
      </div>
    </header>
  );
}

type MetricTone = "safe-1" | "safe-2" | "watch-1" | "watch-2" | "danger-1" | "danger-2";

function riskTone(
  value: number,
  thresholds: readonly [number, number, number, number, number],
): MetricTone {
  if (value <= thresholds[0]) return "safe-1";
  if (value <= thresholds[1]) return "safe-2";
  if (value <= thresholds[2]) return "watch-1";
  if (value <= thresholds[3]) return "watch-2";
  if (value <= thresholds[4]) return "danger-1";
  return "danger-2";
}

function coverageTone(value: number): MetricTone {
  if (value >= 85) return "safe-1";
  if (value >= 70) return "safe-2";
  if (value >= 50) return "watch-1";
  if (value >= 30) return "watch-2";
  if (value >= 15) return "danger-1";
  return "danger-2";
}

function riskToneLabel(tone: MetricTone, lowerIsBetter: string, higherIsBetter: string): string {
  if (tone === "safe-1" || tone === "safe-2") {
    return lowerIsBetter;
  }
  if (tone === "watch-1" || tone === "watch-2") {
    return "Watch";
  }
  return higherIsBetter;
}

function MetricStrip({
  portfolio,
  weights,
  period,
  currency,
  metrics,
}: {
  portfolio: Portfolio;
  weights: number[];
  period: 12 | 24;
  currency: Currency;
  metrics: ReturnType<typeof calculateMetrics>;
}) {
  const { holdings } = normalizeHoldings(portfolio, weights);
  const allocationTotal = weights.reduce((sum, weight) => sum + weight, 0);
  const vaRPct = portfolio.marketValue > 0
    ? (metrics.dailyVaR / portfolio.marketValue) * 100
    : 0;
  const vaRTone = riskTone(vaRPct, [0.5, 1, 1.75, 2.5, 4]);
  const volatilityTone = riskTone(metrics.annualizedVolatility, [10, 16, 22, 28, 35]);
  const drawdownTone = riskTone(Math.abs(metrics.maxDrawdown), [2, 5, 10, 18, 30]);
  const liquidityTone = coverageTone(metrics.liquidWeight);

  return (
    <section className="metric-strip" aria-label="Portfolio risk metrics">
      <article className={`metric-card var-card metric-tone-${vaRTone}`}>
        <div className="metric-label">
          95% one-day VaR
          <span className="info-dot" title="Historical loss-tail estimate from a deterministic illustrative 252-day sample. Losses can exceed VaR.">i</span>
          <span className="metric-state">{riskToneLabel(vaRTone, "Lower", "High")}</span>
        </div>
        <div className="metric-value" key={`${metrics.dailyVaR}-${currency}`}>{money(metrics.dailyVaR, currency, true)}</div>
        <div className="metric-foot"><span className="metric-dot violet" />Potential daily loss · {formatPercent(vaRPct, 2)} of value</div>
      </article>
      <article className="metric-card metric-tone-neutral">
        <div className="metric-label">Market value <span className="metric-state">Portfolio</span></div>
        <div className="metric-value" key={`${portfolio.marketValue}-${currency}`}>{money(portfolio.marketValue, currency, true)}</div>
        <div className="metric-foot">Current portfolio · {holdings.length} holdings</div>
      </article>
      <article className={`metric-card metric-tone-${volatilityTone}`}>
        <div className="metric-label">
          Annualized volatility
          <span className="metric-state">{riskToneLabel(volatilityTone, "Lower", "High")}</span>
        </div>
        <div className="metric-value" key={metrics.annualizedVolatility}>{formatPercent(metrics.annualizedVolatility)}</div>
        <div className="metric-foot">Daily sample · √252 annualization</div>
      </article>
      <article className={`metric-card metric-tone-${drawdownTone}`}>
        <div className="metric-label">
          Max historical drawdown
          <span className="metric-state">{riskToneLabel(drawdownTone, "Shallow", "Severe")}</span>
        </div>
        <div className="metric-value negative-value" key={metrics.maxDrawdown}>{formatPercent(metrics.maxDrawdown)}</div>
        <div className="metric-foot">Peak-to-trough · trailing {period} months</div>
      </article>
      <article className={`metric-card metric-tone-${liquidityTone}`}>
        <div className="metric-label">
          Liquid asset coverage
          <span className="metric-state">{riskToneLabel(liquidityTone, "Strong", "Low")}</span>
        </div>
        <div className="metric-value" key={metrics.liquidWeight}>{formatPercent(metrics.liquidWeight)}</div>
        <div className="metric-foot">{money(metrics.liquidValue, currency, true)} classified high liquidity</div>
      </article>
      {Math.abs(allocationTotal - 100) >= 0.01 && (
        <div className="allocation-alert" role="status">
          Allocation totals {formatPercent(allocationTotal)}; figures are proportionally rebased for analysis.
        </div>
      )}
    </section>
  );
}

function AllocationPanel({
  portfolio,
  weights,
  currency,
  onWeightChange,
  onRestore,
}: {
  portfolio: Portfolio;
  weights: number[];
  currency: Currency;
  onWeightChange: (index: number, value: number) => void;
  onRestore: () => void;
}) {
  const { holdings, totalWeight, valid } = normalizeHoldings(portfolio, weights);
  const groups = holdings.reduce<Record<string, number>>((map, holding) => {
    map[holding.assetClass] = (map[holding.assetClass] ?? 0) + holding.normalizedWeight;
    return map;
  }, {});
  const topHolding = [...holdings].sort((a, b) => b.normalizedWeight - a.normalizedWeight)[0];

  return (
    <section className="panel allocation-panel" id="allocation">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">Portfolio structure</div>
          <h2>Allocation</h2>
        </div>
        <button type="button" className="text-button" onClick={onRestore}>Restore</button>
      </div>
      <div className="allocation-total">
        <div className="donut-wrap">
          <div
            key={weights.join("-")}
            className="allocation-donut"
            style={{
              background: totalWeight > 0 ? `conic-gradient(${holdings.map((holding, index) => {
                const start = holdings
                  .slice(0, index)
                  .reduce((sum, item) => sum + item.normalizedWeight, 0);
                return `${colors[index % colors.length]} ${start}% ${start + holding.normalizedWeight}%`;
              }).join(", ")})` : "#DFE6E0",
            }}
            role="img"
            aria-label="Portfolio allocation by asset class"
          />
          <div className="donut-center"><strong>{formatPercent(totalWeight, 0)}</strong><span>entered</span></div>
        </div>
        <div className="allocation-legend">
          {Object.entries(groups).map(([name, value], index) => (
            <div className="legend-row" key={name}>
              <span className="legend-color" style={{ background: colors[index % colors.length] }} />
              <span>{name}</span><strong>{formatPercent(value, 0)}</strong>
            </div>
          ))}
        </div>
      </div>
      {!valid && (
        <div className="inline-notice" role="status">
          Weights total {formatPercent(totalWeight, 1)}. Analysis rebases the entered weights proportionally to 100%.
        </div>
      )}
      <div className="holding-table-wrap">
        <table className="holding-table">
          <thead>
            <tr><th>Holding</th><th>Weight</th><th>Value</th><th>Return / vol.</th><th>Liquidity</th></tr>
          </thead>
          <tbody>
            {holdings.map((holding, index) => (
              <tr key={holding.ticker}>
                <td>
                  <div className="holding-name">{holding.ticker}</div>
                  <div className="holding-sub">
                    {holding.sector}{holding.currencyExposure === "USD_INR" ? " · USD-linked" : ""}
                  </div>
                </td>
                <td>
                  <label className="weight-field">
                    <input
                      aria-label={`${holding.ticker} allocation percentage`}
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      value={Number.isFinite(weights[index]) ? weights[index] : 0}
                      onChange={(event) => onWeightChange(index, Number(event.target.value))}
                    />
                    <span>%</span>
                  </label>
                </td>
                <td className="number-cell">{money(holding.marketValue, currency, true)}</td>
                <td className="history-cell">
                  <span>{formatPercent(holding.historicalReturn)}</span>
                  <small>{formatPercent(holding.volatility)} vol.</small>
                </td>
                <td><span className={`liquidity-pill ${holding.liquidity.toLowerCase()}`}>{holding.liquidity}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="allocation-foot">
        <span>Largest position</span>
        <strong>{topHolding?.ticker} <span>{formatPercent(topHolding?.normalizedWeight ?? 0)}</span></strong>
      </div>
      <div className="liquidity-note">
        <span className="status-mark" />
        Cash need estimates rely on holding labels, not live redemption terms.
      </div>
    </section>
  );
}

function PerformancePanel({
  portfolio,
  weights,
  period,
  currency,
  scenario,
  scenarioResult,
}: {
  portfolio: Portfolio;
  weights: number[];
  period: 12 | 24;
  currency: Currency;
  scenario: Scenario | null;
  scenarioResult: ReturnType<typeof calculateScenario> | null;
}) {
  const metrics = calculateMetrics(portfolio, weights, period);
  const values = metrics.historicalValues;
  const displayValues = values.slice(-period - 1);
  const width = 720;
  const height = 246;
  const historyWidth = scenarioResult ? width * 0.78 : width;
  const projectionWidth = width - historyWidth;
  const scenarioValues = scenarioResult
    ? [
        displayValues.at(-1) ?? portfolio.marketValue,
        scenarioResult.endingValue,
      ]
    : [];
  const plottedValues = [...displayValues, ...scenarioValues];
  const minValue = Math.min(...plottedValues) * 0.96;
  const maxValue = Math.max(...plottedValues) * 1.035;
  const historyPath = pathFor(displayValues, historyWidth, height, minValue, maxValue);
  const drawdowns = displayValues.map((value, index) => {
    const peakAtPoint = Math.max(...displayValues.slice(0, index + 1));
    return ((value / peakAtPoint) - 1) * 100;
  });
  const maximumDrawdown = Math.min(...drawdowns, -0.01);
  const drawdownPath = drawdowns
    .map((value, index) => {
      const x = (index / Math.max(drawdowns.length - 1, 1)) * width;
      const y = 5 + (Math.abs(value / Math.min(maximumDrawdown, -0.01)) * 43);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const scenarioPath = scenarioValues.length
    ? pathFor(
        scenarioValues,
        projectionWidth,
        height,
        minValue,
        maxValue,
      )
    : "";
  const yTicks = [0, 1, 2, 3].map((tick) => maxValue - ((maxValue - minValue) * tick) / 3);

  return (
    <section className="panel performance-panel" id="overview">
      <div className="panel-heading performance-heading">
        <div>
          <div className="eyebrow">Risk &amp; performance <span className="historical-tag">HISTORICAL SAMPLE</span></div>
          <h2>Portfolio path</h2>
        </div>
        <div className="period-stamp">Trailing {period} months <span>·</span> monthly observations</div>
      </div>
      <div className="chart-legend">
        <span><i className="legend-line historic-line" /> Historical observation</span>
        {scenario && <span><i className="legend-line simulated-line" /> Hypothetical simulation</span>}
        <span className="chart-unit">Value ({currency})</span>
      </div>
      <div className="performance-chart">
        <div className="y-axis-labels" aria-hidden="true">
          {yTicks.map((tick) => <span key={tick}>{money(tick, currency, true)}</span>)}
        </div>
        <svg
          key={`${historyPath}-${scenarioPath}`}
          className="main-chart-svg"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${period} month illustrative historical portfolio value chart${scenario ? " with a hypothetical scenario path" : ""}`}
          preserveAspectRatio="none"
        >
          {yTicks.map((tick, index) => (
            <line
              key={tick}
              x1="0"
              x2={width}
              y1={(index / 3) * height}
              y2={(index / 3) * height}
              className="chart-gridline"
            />
          ))}
          <path d={historyPath} className="history-path" />
          {displayValues.map((value, index) => {
            const y = height - ((value - minValue) / Math.max(maxValue - minValue, 1)) * height;
            return (
              <circle
                key={`${index}-${value}`}
                cx={(index / Math.max(displayValues.length - 1, 1)) * historyWidth}
                cy={y}
                r="3.4"
                className="history-point"
              >
                <title>{`Month ${index + 1}: ${money(value, currency)} — deterministic illustrative observation`}</title>
              </circle>
            );
          })}
          {scenario && scenarioResult && (
            <>
              <path
                d={scenarioPath}
                className="scenario-path"
                transform={`translate(${historyWidth}, 0)`}
              />
              <circle
                cx={width}
                cy={height - ((scenarioResult.endingValue - minValue) / Math.max(maxValue - minValue, 1)) * height}
                r="5"
                className="scenario-point"
              >
                <title>{`Hypothetical scenario value: ${money(scenarioResult.endingValue, currency)}`}</title>
              </circle>
            </>
          )}
        </svg>
      </div>
      <div className={`x-axis-labels${scenario ? " simulation-active" : ""}`}>
        <span>{period} months ago</span><span>−{Math.round(period * 0.66)}m</span><span>−{Math.round(period * 0.33)}m</span><span>Now</span>
        {scenario && <strong>Shock point</strong>}
      </div>
      <div className="drawdown-section">
        <div className="drawdown-heading">
          <span>Historical drawdown <span className="subtle-copy">from prior peak</span></span>
          <strong className="negative-value">{formatPercent(maximumDrawdown)}</strong>
        </div>
        <svg viewBox={`0 0 ${width} 64`} className="drawdown-svg" role="img" aria-label={`Illustrative historical drawdown, maximum ${formatPercent(maximumDrawdown)}`}>
          <line x1="0" x2={width} y1="5" y2="5" className="zero-line" />
          <path d={drawdownPath} className="drawdown-path" />
        </svg>
      </div>
      <div className="chart-disclaimer">
        <span className="disclaimer-icon">i</span>
        <p>Illustrative deterministic sample data, not current market history. Scenario lines are model outputs, not forecasts. Historical patterns and correlations can change.</p>
      </div>
      <div className="correlation-block">
        <div className="correlation-head">
          <div>
            <div className="eyebrow">Diversification lens</div>
            <h3>Asset-class correlation</h3>
          </div>
          <span className="correlation-window">Illustrative sample</span>
        </div>
        <div className="heatmap-wrap">
          <div className="heatmap-row heatmap-labels">
            <span />
            {classCorrelations.map((item) => <span key={item.name}>{item.name}</span>)}
          </div>
          {classCorrelations.map((row) => (
            <div className="heatmap-row" key={row.name}>
              <strong>{row.name}</strong>
              {row.values.map((value, index) => (
                <span
                  key={`${row.name}-${index}`}
                  className="heat-cell"
                  title={`${row.name} and ${classCorrelations[index].name}: illustrative correlation ${value.toFixed(2)}`}
                  style={{ background: riskColor(value) }}
                >
                  {value.toFixed(2)}
                </span>
              ))}
            </div>
          ))}
        </div>
        <div className="correlation-footer">
          <span><i className="corr-key negative-corr" /> Negative</span>
          <span><i className="corr-key neutral-corr" /> Near zero</span>
          <span><i className="corr-key positive-corr" /> Positive</span>
        </div>
        <p className="microcopy">Relationships are illustrative only; historical correlations can shift sharply during market stress.</p>
      </div>
    </section>
  );
}

function ScenarioPanel({
  activeScenario,
  scenarioResult,
  onSelect,
  onCustomChange,
  portfolio,
  currency,
}: {
  activeScenario: Scenario | null;
  scenarioResult: ReturnType<typeof calculateScenario> | null;
  onSelect: (scenario: Scenario | null) => void;
  onCustomChange: (key: "marketPct" | "rateBps" | "technologyPct" | "fxPct", value: number) => void;
  portfolio: Portfolio;
  currency: Currency;
}) {
  const canUseFx = portfolio.holdings.some((holding) => holding.fxExposure > 0);
  const isCustom = activeScenario?.id === "custom";
  const lossPct = scenarioResult ? Math.abs(Math.min(scenarioResult.returnPct, 0)) : 0;
  const worstContributors = scenarioResult?.contributions.filter((item) => item.pnl < 0).slice(0, 3) ?? [];
  const custom = activeScenario ?? scenarios.find((item) => item.id === "custom")!;

  return (
    <section className="panel scenario-panel" id="scenarios">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">Macro stress lab</div>
          <h2>Test a scenario</h2>
        </div>
        {activeScenario && <button type="button" className="text-button" onClick={() => onSelect(null)}>Clear</button>}
      </div>
      <p className="panel-intro">Explore hypothetical shocks against current weights. Outputs are sensitivity estimates, not forecasts.</p>
      <div className="scenario-list" role="group" aria-label="Choose a stress scenario">
        {scenarios.map((item) => {
          const selected = activeScenario?.id === item.id;
          return (
            <button
              type="button"
              key={item.id}
              className={`scenario-choice${selected ? " selected" : ""}`}
              aria-pressed={selected}
              onClick={() => onSelect(item.id === "custom" ? { ...item } : item)}
            >
              <span className="scenario-radio" />
              <span className="scenario-text"><strong>{item.label}</strong><small>{item.description}</small></span>
              <span className="scenario-chevron">↗</span>
            </button>
          );
        })}
      </div>
      {isCustom && (
        <div className="custom-controls">
          <RangeControl label="Broad equity market" value={custom.marketPct} min={-50} max={0} suffix="%" onChange={(value) => onCustomChange("marketPct", value)} />
          <RangeControl label="Rate change" value={custom.rateBps} min={-100} max={300} suffix=" bps" onChange={(value) => onCustomChange("rateBps", value)} />
          <RangeControl label="Technology sector" value={custom.technologyPct} min={-40} max={10} suffix="%" onChange={(value) => onCustomChange("technologyPct", value)} />
          <RangeControl label={`FX vs ${currency}`} value={custom.fxPct} min={-20} max={20} suffix="%" onChange={(value) => onCustomChange("fxPct", value)} disabled={!canUseFx} />
          {!canUseFx && <p className="microcopy">This portfolio has no foreign-currency exposure; FX changes have no modeled effect.</p>}
        </div>
      )}
      {activeScenario && scenarioResult ? (
        <div className="scenario-result" key={`${activeScenario.id}-${scenarioResult.returnPct}`} aria-live="polite">
          <div className="result-topline"><span>Estimated portfolio impact</span><span className="hypothetical-badge">SIMULATED</span></div>
              <div className={`result-value ${scenarioResult.pnl < 0 ? "negative-value" : "positive-value"}`}>
                {signedMoney(scenarioResult.pnl, currency)}
              </div>
          <div className="result-subline">{formatPercent(scenarioResult.returnPct)} <span>·</span> ending value {money(scenarioResult.endingValue, currency, true)}</div>
          <div className="loss-meter"><span style={{ width: `${Math.min(lossPct * 2.6, 100)}%` }} /></div>
          <div className="meter-caption"><span>Estimated loss severity</span><span>{formatPercent(lossPct)}</span></div>
          <div className="contributors">
            <div className="contributors-title">Largest modeled loss contributors</div>
            {worstContributors.length ? worstContributors.map((item) => (
              <div className="contributor-row" key={item.ticker}>
                <span><b>{item.ticker}</b><small>{item.name}</small></span>
                <strong className={item.pnl < 0 ? "negative-value" : "positive-value"}>{signedMoney(item.pnl, currency)}</strong>
              </div>
            )) : <p className="microcopy">No negative holding-level impact under these assumptions.</p>}
          </div>
          <div className="assumption-note"><strong>Model assumptions</strong><span>Equity beta · bond duration · stated FX exposure. No hedging, transaction costs, or cross-factor interactions included.</span></div>
        </div>
      ) : (
        <div className="scenario-idle">
          <span className="idle-icon">↗</span>
          <strong>No stress active</strong>
          <span>Select a scenario to view its modeled impact.</span>
        </div>
      )}
      <div className="scenario-actions">
        <button type="button" className="quiet-action" onClick={() => onSelect(scenarios[0])}>Run broad sell-off</button>
        <span>Impacts are illustrative, not advice.</span>
      </div>
    </section>
  );
}

function RangeControl({
  label,
  value,
  min,
  max,
  suffix,
  onChange,
  disabled = false,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <label className={`range-control${disabled ? " disabled-control" : ""}`}>
      <span><span>{label}</span><strong>{value}{suffix}</strong></span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function DiagnosticsPanel({
  portfolio,
  weights,
  riskTolerance,
  onRiskToleranceChange,
  horizon,
  onHorizonChange,
  liquidityNeed,
  onLiquidityNeedChange,
  lossLimit,
  onLossLimitChange,
  scenarioResult,
  currency,
}: {
  portfolio: Portfolio;
  weights: number[];
  riskTolerance: string;
  onRiskToleranceChange: (value: string) => void;
  horizon: number;
  onHorizonChange: (value: number) => void;
  liquidityNeed: number;
  onLiquidityNeedChange: (value: number) => void;
  lossLimit: number;
  onLossLimitChange: (value: number) => void;
  scenarioResult: ReturnType<typeof calculateScenario> | null;
  currency: Currency;
}) {
  const { holdings } = normalizeHoldings(portfolio, weights);
  const warnings = calculateWarnings(holdings, riskTolerance, horizon, liquidityNeed, scenarioResult, lossLimit);

  return (
    <section className="panel diagnostics-panel">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">Objective alignment</div>
          <h2>Risk diagnostics</h2>
        </div>
        <span className={`warning-count${warnings.length ? "" : " clear"}`}>{warnings.length} {warnings.length === 1 ? "review" : "reviews"}</span>
      </div>
      <div className="objective-controls">
        <label>Risk preference
          <select value={riskTolerance} onChange={(event) => onRiskToleranceChange(event.target.value)}>
            <option>Conservative</option><option>Moderate</option><option>Aggressive</option>
          </select>
        </label>
        <label>Horizon
          <select value={horizon} onChange={(event) => onHorizonChange(Number(event.target.value))}>
            <option value={1}>1 year</option><option value={3}>3 years</option><option value={5}>5 years</option><option value={10}>10 years</option><option value={15}>15 years</option>
          </select>
        </label>
        <label>Near-term cash need ({currency})
          <input
            type="number"
            min="0"
            step="25000"
            value={currency === "USD" ? Math.round(liquidityNeed / illustrativeUsdInr) : liquidityNeed}
            onChange={(event) => onLiquidityNeedChange(
              Math.max(0, Number(event.target.value)) * (currency === "USD" ? illustrativeUsdInr : 1),
            )}
          />
        </label>
        <label>Loss review threshold
          <select value={lossLimit} onChange={(event) => onLossLimitChange(Number(event.target.value))}>
            <option value={10}>10% loss</option><option value={15}>15% loss</option><option value={20}>20% loss</option><option value={30}>30% loss</option>
          </select>
        </label>
      </div>
      <div className="diagnostics-list" aria-live="polite">
        {warnings.length ? warnings.map((warning, index) => (
          <article className={`diagnostic-item ${warning.severity}`} key={`${warning.title}-${index}`}>
            <span className="diagnostic-symbol">{warning.severity === "review" ? "!" : "↗"}</span>
            <div><strong>{warning.title}</strong><p>{warning.detail}</p><small>Review your objective or allocation inputs.</small></div>
          </article>
        )) : (
          <article className="diagnostic-item clear-item">
            <span className="diagnostic-symbol">✓</span>
            <div><strong>No rule-based conflicts detected</strong><p>Based on the visible risk and liquidity rules, no current threshold is crossed.</p></div>
          </article>
        )}
      </div>
      <div className="diagnostic-footnote">
        Starting cash need is a demo assumption (20% of target for high, 10% medium, 5% low liquidity); adjust it above. High-liquidity labels do not model settlement time or redemption limits.
      </div>
    </section>
  );
}

function ComparisonPanel({
  portfolio,
  currentWeights,
  alternativeWeights,
  onAlternativeWeightChange,
  onResetAlternative,
  period,
  scenario,
  currency,
}: {
  portfolio: Portfolio;
  currentWeights: number[];
  alternativeWeights: number[];
  onAlternativeWeightChange: (index: number, value: number) => void;
  onResetAlternative: () => void;
  period: 12 | 24;
  scenario: Scenario | null;
  currency: Currency;
}) {
  const currentMetrics = calculateMetrics(portfolio, currentWeights, period);
  const alternativeMetrics = calculateMetrics(portfolio, alternativeWeights, period);
  const currentScenario = scenario ? calculateScenario(portfolio, currentWeights, scenario) : null;
  const alternativeScenario = scenario ? calculateScenario(portfolio, alternativeWeights, scenario) : null;
  const currentHoldings = normalizeHoldings(portfolio, currentWeights).holdings;
  const alternativeHoldings = normalizeHoldings(portfolio, alternativeWeights).holdings;
  const currentEquity = currentHoldings.reduce((sum, item) => sum + (item.assetClass === "Equity" ? item.normalizedWeight : 0), 0);
  const alternativeEquity = alternativeHoldings.reduce((sum, item) => sum + (item.assetClass === "Equity" ? item.normalizedWeight : 0), 0);
  const comparisonRows = [
    { label: "Equity allocation", current: formatPercent(currentEquity), alternative: formatPercent(alternativeEquity) },
    { label: "Annualized volatility", current: formatPercent(currentMetrics.annualizedVolatility), alternative: formatPercent(alternativeMetrics.annualizedVolatility) },
    { label: "95% one-day VaR", current: money(currentMetrics.dailyVaR, currency, true), alternative: money(alternativeMetrics.dailyVaR, currency, true) },
    {
      label: "High-liquidity share",
      current: formatPercent(currentMetrics.liquidWeight),
      alternative: formatPercent(alternativeMetrics.liquidWeight),
    },
    ...(scenario && currentScenario && alternativeScenario
      ? [{ label: "Scenario impact", current: formatPercent(currentScenario.returnPct), alternative: formatPercent(alternativeScenario.returnPct) }]
      : []),
  ];

  return (
    <section className="panel comparison-panel" id="comparison">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">Allocation alternatives</div>
          <h2>Compare the trade-offs</h2>
        </div>
        <button type="button" className="text-button" onClick={onResetAlternative}>Reset alternative</button>
      </div>
      <p className="panel-intro">Edit the alternative weights to compare risk and liquidity using the same sample returns and scenario assumptions.</p>
      <div className="comparison-layout">
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead><tr><th>Measure</th><th>Current</th><th>Alternative</th></tr></thead>
            <tbody>
              {comparisonRows.map((row) => (
                <tr key={row.label}><th>{row.label}</th><td>{row.current}</td><td>{row.alternative}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="alternative-editor">
          <div className="alternative-heading"><span className="alt-indicator" />Alternative mix <small>Adjust weights</small></div>
          <div className="alternative-weights">
            {alternativeHoldings.map((holding, index) => (
              <label key={holding.ticker}>
                <span>{holding.ticker}</span>
                <input
                  type="number"
                  aria-label={`${holding.ticker} alternative allocation percentage`}
                  min="0"
                  max="100"
                  step="1"
                  value={Number.isFinite(alternativeWeights[index]) ? alternativeWeights[index] : 0}
                  onChange={(event) => onAlternativeWeightChange(index, Number(event.target.value))}
                />
                <i>%</i>
              </label>
            ))}
          </div>
          {Math.abs(alternativeWeights.reduce((sum, weight) => sum + weight, 0) - 100) >= 0.01 && (
            <div className="inline-notice compact-notice">Alternative weights are proportionally rebased to 100% for comparison.</div>
          )}
        </div>
      </div>
      <div className="tradeoff-note">
        <span>↔</span>
        <p><strong>Different allocations express different trade-offs.</strong> The alternative is not a recommendation. Sample return assumptions are historical illustrations and do not imply expected future performance.</p>
      </div>
    </section>
  );
}

export default function Dashboard() {
  const [savedState] = useState(loadSavedState);
  const [activePage] = useState(currentPage);
  const [portfolioId, setPortfolioId] = useState(savedState?.portfolioId ?? portfolios[0].id);
  const portfolio = portfolios.find((item) => item.id === portfolioId) ?? portfolios[0];
  const [weights, setWeights] = useState(savedState?.weights ?? portfolio.holdings.map((holding) => holding.weight));
  const [alternativeWeights, setAlternativeWeights] = useState(savedState?.alternativeWeights ?? createAlternativeWeights(portfolio));
  const [period, setPeriod] = useState<12 | 24>(savedState?.period ?? 12);
  const [currency, setCurrency] = useState<Currency>(savedState?.currency ?? "INR");
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(savedState?.activeScenario ?? scenarios[0]);
  const [riskTolerance, setRiskTolerance] = useState(savedState?.riskTolerance ?? profileRisk(portfolio.investorProfile));
  const [horizon, setHorizon] = useState(savedState?.horizon ?? portfolio.investorProfile.horizon_years);
  const [liquidityNeed, setLiquidityNeed] = useState(savedState?.liquidityNeed ?? demoLiquidityNeed(portfolio));
  const [lossLimit, setLossLimit] = useState(savedState?.lossLimit ?? 15);
  const [darkMode, setDarkMode] = useState(savedState?.darkMode ?? false);
  const pageMeta = pages.find((page) => page.id === activePage) ?? pages[0];

  useEffect(() => {
    try {
      window.localStorage.setItem("aperture-risk-lab-state", JSON.stringify({
        portfolioId,
        weights,
        alternativeWeights,
        period,
        currency,
        activeScenario,
        riskTolerance,
        horizon,
        liquidityNeed,
        lossLimit,
        darkMode,
      } satisfies SavedDashboardState));
    } catch (error) {
      console.error("Could not save Vertex dashboard settings.", error);
    }
  }, [
    portfolioId,
    weights,
    alternativeWeights,
    period,
    currency,
    activeScenario,
    riskTolerance,
    horizon,
    liquidityNeed,
    lossLimit,
    darkMode,
  ]);

  useEffect(() => {
    document.title = `Vertex | ${pageMeta.title}`;
  }, [pageMeta.title]);

  useEffect(() => {
    const themeColor = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    if (themeColor) {
      themeColor.content = darkMode ? "#151A1D" : "#F4F2EB";
    }
  }, [darkMode]);

  const metrics = useMemo(
    () => calculateMetrics(portfolio, weights, period),
    [portfolio, weights, period],
  );
  const scenarioResult = useMemo(
    () => activeScenario ? calculateScenario(portfolio, weights, activeScenario) : null,
    [portfolio, weights, activeScenario],
  );

  const changePortfolio = (id: string) => {
    const next = portfolios.find((item) => item.id === id);
    if (!next) return;
    setPortfolioId(id);
    setWeights(next.holdings.map((holding) => holding.weight));
    setAlternativeWeights(createAlternativeWeights(next));
    setRiskTolerance(profileRisk(next.investorProfile));
    setHorizon(next.investorProfile.horizon_years);
    setLiquidityNeed(demoLiquidityNeed(next));
  };
  const updateWeight = (
    setValue: (weights: number[]) => void,
    current: number[],
    index: number,
    value: number,
  ) => {
    setValue(current.map((weight, itemIndex) => itemIndex === index
      ? (Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0)
      : weight));
  };
  const resetView = () => {
    setWeights(portfolio.holdings.map((holding) => holding.weight));
    setAlternativeWeights(createAlternativeWeights(portfolio));
    setActiveScenario(null);
    setPeriod(12);
    setCurrency("INR");
    setRiskTolerance(profileRisk(portfolio.investorProfile));
    setHorizon(portfolio.investorProfile.horizon_years);
    setLiquidityNeed(demoLiquidityNeed(portfolio));
    setLossLimit(15);
  };
  const customScenarioChange = (
    key: "marketPct" | "rateBps" | "technologyPct" | "fxPct",
    value: number,
  ) => {
    const custom = scenarios.find((item) => item.id === "custom")!;
    setActiveScenario((current) => ({
      ...(current?.id === "custom" ? current : custom),
      [key]: value,
    }));
  };

  return (
    <main className="aperture-app" data-theme={darkMode ? "dark" : "light"}>
      <Header
        activePage={activePage}
        portfolioId={portfolioId}
        onPortfolioChange={changePortfolio}
        currency={currency}
        onCurrencyChange={setCurrency}
        period={period}
        onPeriodChange={setPeriod}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode((enabled) => !enabled)}
        onReset={resetView}
      />
      <div className="workspace">
        <div className="workspace-intro">
          <div>
            <div className="breadcrumb">{pageMeta.eyebrow.toUpperCase()} <span>/</span> {pageMeta.title.toUpperCase()}</div>
            <h1>{portfolio.name}<span className="title-separator">·</span><small>{portfolio.owner}</small></h1>
            <div className="profile-metadata">
              <span>Goal <strong>{money(portfolio.investorProfile.target_goal_inr, currency, true)}</strong></span>
              <i />
              <span>Horizon <strong>{portfolio.investorProfile.horizon_years} year{portfolio.investorProfile.horizon_years === 1 ? "" : "s"}</strong></span>
              <i />
              <span>Risk <strong>{portfolio.investorProfile.risk_tolerance}</strong></span>
              <i />
              <span>Liquidity need <strong>{portfolio.investorProfile.liquidity_need}</strong></span>
            </div>
          </div>
          <div className="as-of"><span className="live-indicator" />DEMO MODE <span>·</span> Illustrative sample data</div>
        </div>
        <MetricStrip portfolio={portfolio} weights={weights} period={period} currency={currency} metrics={metrics} />
        {currency === "USD" && <p className="fx-disclosure">USD amounts use an illustrative ₹{illustrativeUsdInr.toFixed(2)}/$ conversion for display only; calculations remain in INR.</p>}
        <div className={`page-content page-${activePage}`} key={activePage}>
          {activePage === "overview" && (
            <div className="analysis-grid overview-grid">
              <PerformancePanel
                portfolio={portfolio}
                weights={weights}
                period={period}
                currency={currency}
                scenario={activeScenario}
                scenarioResult={scenarioResult}
              />
              <div className="right-column">
                <ScenarioPanel
                  activeScenario={activeScenario}
                  scenarioResult={scenarioResult}
                  onSelect={setActiveScenario}
                  onCustomChange={customScenarioChange}
                  portfolio={portfolio}
                  currency={currency}
                />
                <DiagnosticsPanel
                  portfolio={portfolio}
                  weights={weights}
                  riskTolerance={riskTolerance}
                  onRiskToleranceChange={setRiskTolerance}
                  horizon={horizon}
                  onHorizonChange={setHorizon}
                  liquidityNeed={liquidityNeed}
                  onLiquidityNeedChange={setLiquidityNeed}
                  lossLimit={lossLimit}
                  onLossLimitChange={setLossLimit}
                  scenarioResult={scenarioResult}
                  currency={currency}
                />
              </div>
            </div>
          )}
          {activePage === "allocation" && (
            <div className="page-grid allocation-page-grid">
              <AllocationPanel
                portfolio={portfolio}
                weights={weights}
                currency={currency}
                onWeightChange={(index, value) => updateWeight(setWeights, weights, index, value)}
                onRestore={() => setWeights(portfolio.holdings.map((holding) => holding.weight))}
              />
              <DiagnosticsPanel
                portfolio={portfolio}
                weights={weights}
                riskTolerance={riskTolerance}
                onRiskToleranceChange={setRiskTolerance}
                horizon={horizon}
                onHorizonChange={setHorizon}
                liquidityNeed={liquidityNeed}
                onLiquidityNeedChange={setLiquidityNeed}
                lossLimit={lossLimit}
                onLossLimitChange={setLossLimit}
                scenarioResult={scenarioResult}
                currency={currency}
              />
            </div>
          )}
          {activePage === "stresslab" && (
            <div className="page-grid stress-page-grid">
              <ScenarioPanel
                activeScenario={activeScenario}
                scenarioResult={scenarioResult}
                onSelect={setActiveScenario}
                onCustomChange={customScenarioChange}
                portfolio={portfolio}
                currency={currency}
              />
              <PerformancePanel
                portfolio={portfolio}
                weights={weights}
                period={period}
                currency={currency}
                scenario={activeScenario}
                scenarioResult={scenarioResult}
              />
              <DiagnosticsPanel
                portfolio={portfolio}
                weights={weights}
                riskTolerance={riskTolerance}
                onRiskToleranceChange={setRiskTolerance}
                horizon={horizon}
                onHorizonChange={setHorizon}
                liquidityNeed={liquidityNeed}
                onLiquidityNeedChange={setLiquidityNeed}
                lossLimit={lossLimit}
                onLossLimitChange={setLossLimit}
                scenarioResult={scenarioResult}
                currency={currency}
              />
            </div>
          )}
          {activePage === "compare" && (
            <div className="page-grid compare-page-grid">
              <ComparisonPanel
                portfolio={portfolio}
                currentWeights={weights}
                alternativeWeights={alternativeWeights}
                onAlternativeWeightChange={(index, value) => updateWeight(setAlternativeWeights, alternativeWeights, index, value)}
                onResetAlternative={() => setAlternativeWeights(createAlternativeWeights(portfolio))}
                period={period}
                scenario={activeScenario}
                currency={currency}
              />
              <ScenarioPanel
                activeScenario={activeScenario}
                scenarioResult={scenarioResult}
                onSelect={setActiveScenario}
                onCustomChange={customScenarioChange}
                portfolio={portfolio}
                currency={currency}
              />
            </div>
          )}
          {activePage === "overview" && (
            <div className="overview-allocation-teaser">
              <div><span className="eyebrow">Portfolio composition</span><strong>Review the holdings and concentration behind this risk profile.</strong></div>
              <a href="index.html?page=allocation">Explore allocation <span>→</span></a>
            </div>
          )}
          {activePage === "overview" && activeScenario && scenarioResult && (
            <div className="overview-compare-teaser">
              <span><strong>{activeScenario.label}</strong> models an impact of {signedMoney(scenarioResult.pnl, currency)}.</span>
              <a href="index.html?page=stresslab">Open Stress Lab <span>→</span></a>
            </div>
          )}
        </div>
        <footer className="app-footer">
          <span><span className="footer-mark">V</span> VERTEX <span>PORTFOLIO RISK LAB</span></span>
          <p>DEMO MODE · Mock data only · Scenario outputs are not forecasts or guarantees.</p>
          <a href="index.html?page=overview">Overview ↑</a>
        </footer>
      </div>
    </main>
  );
}
