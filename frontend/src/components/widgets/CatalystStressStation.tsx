import React, { useState, useMemo } from 'react';
import type { Portfolio } from '../../pages/website/portfolioData';
import type { Scenario } from '../../pages/website/portfolioData';
import type { NewsArticle } from './newsArticles';
import { DEFAULT_NEWS_ARTICLES } from './newsArticles';
import './CatalystStressStation.css';

export interface CatalystStressStationProps {
  catalyst: NewsArticle;
  portfolio: Portfolio;
  allPortfolios: Portfolio[];
  weights: number[];
  currency?: 'INR' | 'USD';
  activeScenario?: Scenario | null;
  onSwitchPortfolio: (portfolioId: string) => void;
  onAdoptStrategy: (newWeights: number[]) => void;
  onClearCatalyst: () => void;
  onSelectOtherCatalyst: (article: NewsArticle) => void;
  availableArticles?: NewsArticle[];
}

const illustrativeUsdInr = 83.5;

function formatMoney(value: number, currency: 'INR' | 'USD' = 'INR', compact = false): string {
  const converted = currency === 'USD' ? value / illustrativeUsdInr : value;
  return new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
    notation: compact ? 'compact' : 'standard',
  }).format(converted);
}

function formatSignedMoney(value: number, currency: 'INR' | 'USD' = 'INR'): string {
  const sign = value < 0 ? '−' : '+';
  return `${sign}${formatMoney(Math.abs(value), currency)}`;
}

/**
 * Calculates asset-specific shock based on the active news narrative catalyst.
 */
function calculateAssetCatalystShock(
  holding: { ticker: string; sector: string; assetClass: string; fxExposure?: number },
  catalyst: NewsArticle,
  scenario?: Scenario | null
): { shockPct: number; rationale: string; isDirect: boolean } {
  const ticker = holding.ticker.toUpperCase();
  const sector = holding.sector.toLowerCase();
  const text = `${catalyst.headline} ${catalyst.summary}`.toLowerCase();
  const isDirect = (catalyst.relatedAssets || []).some(
    (a) => a.toUpperCase() === ticker || ticker.includes(a.toUpperCase())
  );

  // 1. Technology News
  if (
    catalyst.suggestedScenarioId === 'technology' ||
    catalyst.category?.toLowerCase().includes('tech') ||
    text.includes('tech') ||
    text.includes('cloud') ||
    text.includes('ai modernization')
  ) {
    if (sector.includes('it') || holding.assetClass === 'Equity' && (ticker.includes('TCS') || ticker.includes('INFY'))) {
      if (catalyst.sentiment === 'bullish') {
        return { shockPct: 8.5, rationale: 'Enterprise cloud & AI contract pipeline expansion', isDirect: true };
      }
      return { shockPct: -25.0, rationale: 'Discretionary IT spending compression & margin pressure', isDirect: true };
    }
    if (holding.assetClass === 'Equity') {
      return { shockPct: -3.5, rationale: 'Broader market sentiment drag', isDirect: false };
    }
    return { shockPct: 0.0, rationale: 'Non-equity assets insulated from IT budget shocks', isDirect: false };
  }

  // 2. Fixed Income / Interest Rates / RBI Policy
  if (
    catalyst.suggestedScenarioId === 'rates' ||
    catalyst.category?.toLowerCase().includes('fixed income') ||
    catalyst.category?.toLowerCase().includes('policy') ||
    text.includes('repo rate') ||
    text.includes('yield') ||
    text.includes('g-sec') ||
    text.includes('treasury')
  ) {
    if (sector.includes('government bond') || ticker.includes('GSEC')) {
      const shock = catalyst.sentiment === 'bearish' ? -9.5 : -1.8;
      return { shockPct: shock, rationale: '7.5-year duration mark-to-market yield spike', isDirect: true };
    }
    if (sector.includes('corporate bond')) {
      const shock = catalyst.sentiment === 'bearish' ? -5.2 : -1.0;
      return { shockPct: shock, rationale: '3.2-year duration credit spread repricing', isDirect: true };
    }
    if (sector.includes('liquid debt') || ticker.includes('LIQUIDBEES')) {
      return { shockPct: +0.25, rationale: 'Reinvestment rate benefit from higher short-term yields', isDirect: false };
    }
    if (sector.includes('real estate') || ticker.includes('REIT')) {
      return { shockPct: -6.0, rationale: 'Higher capitalization rate discount on commercial assets', isDirect: true };
    }
    if (holding.assetClass === 'Equity') {
      return { shockPct: -2.5, rationale: 'Equity discount multiple compression from elevated bond yields', isDirect: false };
    }
    return { shockPct: 0.0, rationale: 'Insulated cash equivalent', isDirect: false };
  }

  // 3. Commodities / Gold Safe-Haven
  if (
    catalyst.category?.toLowerCase().includes('commodities') ||
    text.includes('gold') ||
    text.includes('safe-haven')
  ) {
    if (holding.assetClass === 'Commodity' || sector.includes('gold') || ticker.includes('GOLDBEES')) {
      return { shockPct: +5.5, rationale: 'Geopolitical safe-haven bids and central bank reserve inflows', isDirect: true };
    }
    if (holding.assetClass === 'Equity') {
      return { shockPct: -3.0, rationale: 'Risk-off rotation away from cyclical equity into safe havens', isDirect: false };
    }
    return { shockPct: +0.2, rationale: 'Safe-haven liquid debt stability', isDirect: false };
  }

  // 4. Currency / Rupee Shock
  if (
    catalyst.suggestedScenarioId === 'fx' ||
    catalyst.category?.toLowerCase().includes('forex') ||
    text.includes('rupee') ||
    text.includes('usd')
  ) {
    if (holding.fxExposure && holding.fxExposure > 0) {
      return { shockPct: +4.2, rationale: 'USD revenue exporter realization tailwind', isDirect: true };
    }
    if (sector.includes('banking')) {
      return { shockPct: -4.5, rationale: 'FII outflow liquidation pressure on domestic financials', isDirect: true };
    }
    return { shockPct: -1.0, rationale: 'Imported inflation friction', isDirect: false };
  }

  // 5. Broad Fallback from scenario settings or sentiment
  const baseShock = scenario?.marketPct ?? (catalyst.sentiment === 'bearish' ? -20 : catalyst.sentiment === 'bullish' ? 6 : -2);
  if (holding.assetClass === 'Equity') {
    return { shockPct: baseShock, rationale: 'Systemic broad market transmission', isDirect };
  }
  if (holding.assetClass === 'Debt') {
    return { shockPct: -(scenario?.rateBps ?? 100) / 30, rationale: 'Interest rate sensitivity', isDirect: false };
  }
  return { shockPct: 0, rationale: 'Stable baseline', isDirect: false };
}

export const CatalystStressStation: React.FC<CatalystStressStationProps> = ({
  catalyst,
  portfolio,
  allPortfolios,
  weights,
  currency = 'INR',
  activeScenario,
  onSwitchPortfolio,
  onAdoptStrategy,
  onClearCatalyst,
  onSelectOtherCatalyst,
  availableArticles = DEFAULT_NEWS_ARTICLES,
}) => {
  const [activeGraphTab, setActiveGraphTab] = useState<'attribution' | 'trajectory'>('attribution');
  const [strategyAdopted, setStrategyAdopted] = useState(false);

  // 1. Current Portfolio Normalized Assets & Shocks
  const currentTotalVal = portfolio.marketValue || 1;
  const currentHoldingsWithShock = useMemo(() => {
    const totalWeight = weights.reduce((sum, w) => sum + (Number.isFinite(w) ? Math.max(0, w) : 0), 0) || 100;
    return portfolio.holdings.map((h, idx) => {
      const normalizedWeight = ((weights[idx] ?? h.weight) / totalWeight) * 100;
      const assetVal = (currentTotalVal * normalizedWeight) / 100;
      const { shockPct, rationale, isDirect } = calculateAssetCatalystShock(h, catalyst, activeScenario);
      const pnlInr = assetVal * (shockPct / 100);
      return {
        ...h,
        normalizedWeight,
        assetVal,
        shockPct,
        rationale,
        isDirect,
        pnlInr,
      };
    });
  }, [portfolio, weights, currentTotalVal, catalyst, activeScenario]);

  // Current Portfolio Aggregates
  const currentTotalPnl = useMemo(() => {
    return currentHoldingsWithShock.reduce((sum, h) => sum + h.pnlInr, 0);
  }, [currentHoldingsWithShock]);

  const currentReturnPct = (currentTotalPnl / currentTotalVal) * 100;
  const directExposurePct = useMemo(() => {
    return currentHoldingsWithShock
      .filter((h) => h.isDirect)
      .reduce((sum, h) => sum + h.normalizedWeight, 0);
  }, [currentHoldingsWithShock]);

  // 2. Cross-Portfolio Benchmark Calculation ("Different for Everyone")
  const crossPortfolioBenchmark = useMemo(() => {
    return allPortfolios.map((p) => {
      const pVal = p.marketValue || 1;
      let pnl = 0;
      let directWeight = 0;

      p.holdings.forEach((h) => {
        const val = (pVal * h.weight) / 100;
        const { shockPct, isDirect } = calculateAssetCatalystShock(h, catalyst, activeScenario);
        pnl += val * (shockPct / 100);
        if (isDirect) {
          directWeight += h.weight;
        }
      });

      const retPct = (pnl / pVal) * 100;
      let status: 'critical' | 'insulated' | 'resilient';
      let statusText: string;

      if (retPct < -12 || directWeight > 45) {
        status = 'critical';
        statusText = 'Critical Concentration Drag';
      } else if (Math.abs(retPct) < 2.5 && directWeight < 10) {
        status = 'insulated';
        statusText = 'Immune / Insulated';
      } else {
        status = 'resilient';
        statusText = retPct >= 0 ? 'Hedge Beneficiary' : 'Dampened Resilience';
      }

      return {
        id: p.id,
        name: p.name,
        profile: p.investorProfile,
        marketValue: pVal,
        pnl,
        retPct,
        directWeight,
        status,
        statusText,
        isActive: p.id === portfolio.id,
      };
    });
  }, [allPortfolios, catalyst, activeScenario, portfolio.id]);

  // 3. Investor Diagnostic Narrative Generator
  const diagnosticEvaluation = useMemo(() => {
    const risk = portfolio.investorProfile.risk_tolerance;
    const horizon = portfolio.investorProfile.horizon_years;

    if (directExposurePct >= 50 && currentReturnPct < -8) {
      return {
        severity: 'alert-high',
        headline: `High Vulnerability Alert (${directExposurePct.toFixed(0)}% Concentrated Exposure)`,
        body: `Your portfolio holds heavy direct concentration in assets hit by this news. For an investor with a ${horizon}-year horizon and ${risk} risk profile, a projected ${currentReturnPct.toFixed(1)}% (${formatMoney(Math.abs(currentTotalPnl), currency)}) drawdown breaches prudent risk limits. Immediate defensive trimming is recommended.`,
      };
    }

    if (directExposurePct === 0 && Math.abs(currentReturnPct) < 3) {
      return {
        severity: 'alert-low',
        headline: 'Portfolio Insulated from Direct Narrative Drag',
        body: `Because your asset allocation is concentrated outside the affected sector, your portfolio experiences negligible direct mark-to-market impact (${currentReturnPct >= 0 ? '+' : ''}${currentReturnPct.toFixed(1)}%). Your ${horizon}-year capital preservation trajectory remains robust.`,
      };
    }

    if (currentReturnPct > 0) {
      return {
        severity: 'alert-low',
        headline: 'Asymmetric Hedge Accretion',
        body: `Your portfolio allocation benefits positively from this narrative catalyst, expanding by +${formatMoney(currentTotalPnl, currency)} (+${currentReturnPct.toFixed(1)}%). Safe-haven positions provide natural hedging across market volatility.`,
      };
    }

    return {
      severity: 'alert-med',
      headline: 'Moderate Systemic Spillover',
      body: `Direct exposure is modest (${directExposurePct.toFixed(0)}%), but indirect systemic risk generates a estimated ${currentReturnPct.toFixed(1)}% drag. A tactical buffer rebalance can preserve downside equity.`,
    };
  }, [directExposurePct, currentReturnPct, currentTotalPnl, currency, portfolio]);

  // 4. Tailored Catalyst Defense Strategy
  const tailoredStrategy = useMemo(() => {
    const drags = currentHoldingsWithShock.filter((h) => h.pnlInr < 0).sort((a, b) => a.pnlInr - b.pnlInr);
    const worstAsset = drags[0];

    let title = 'Multi-Asset Liquidity Shield & Collar Protection';
    let rationale = `Tactically rebalances out of vulnerable narrative exposure into short-duration liquid yield and gold, reducing simulated drawdown while maintaining investor goal trajectory.`;
    let tickets = [
      {
        type: 'sell' as const,
        action: `Trim ${worstAsset ? worstAsset.ticker : 'concentrated equity'} by 12%`,
        detail: `Lock in defensive liquidity and reduce single-sector drag by ${worstAsset ? formatMoney(worstAsset.assetVal * 0.12, currency) : '₹1,20,000'}.`,
      },
      {
        type: 'buy' as const,
        action: 'Deploy into LIQUIDBEES / Short-End Treasury',
        detail: 'Build an immediate 15% cash equivalent buffer immune to narrative volatility.',
      },
      {
        type: 'hedge' as const,
        action: 'Overlay 1-Month Protective Put or Stop-Loss',
        detail: 'Establish a hard 7% floor beneath equity positions during macroeconomic digestion.',
      },
    ];

    if (catalyst.suggestedScenarioId === 'technology') {
      title = 'Defensive Tech Collar & Reallocation into Liquid Yield';
      rationale = `Protects 1-year horizon capital against IT discretionary spending contraction by trimming overweighted technology equities into capital-preserving cash equivalents.`;
      tickets = [
        {
          type: 'sell',
          action: `Trim ${worstAsset ? worstAsset.ticker : 'TCS'} by 15%`,
          detail: `Reduce technology sector concentration risk by ${formatMoney(currentTotalVal * 0.15, currency)}.`,
        },
        {
          type: 'buy',
          action: 'Reallocate to LIQUIDBEES / GOLDBEES',
          detail: 'Direct proceeds into uncorrelated liquid debt and precious metal safe-havens.',
        },
        {
          type: 'hedge',
          action: 'Deploy NIFTY IT Protective Put Collar',
          detail: 'Cap downside drawdown at -6% while retaining upside participation above 8%.',
        },
      ];
    } else if (catalyst.suggestedScenarioId === 'rates') {
      title = 'Duration Shortening & Floating Rate Immunization';
      rationale = `Reduces bond portfolio effective duration from 7.5 years down to 2.8 years, shielding capital against central bank rate tightening.`;
      tickets = [
        {
          type: 'sell',
          action: 'Lighten 10-Year Benchmark G-Sec Holdings (-20%)',
          detail: 'Eliminate high mark-to-market duration vulnerability before yield auction pressures.',
        },
        {
          type: 'buy',
          action: 'Accumulate Ultra-Short Duration Treasury Bills',
          detail: 'Benefit from higher reinvestment yields without capital depreciation.',
        },
        {
          type: 'hedge',
          action: 'Interest Rate Swap / Futures Overlay',
          detail: 'Lock in benchmark sovereign yield spreads through policy cycle volatility.',
        },
      ];
    } else if (catalyst.category?.toLowerCase().includes('commodities') || catalyst.headline.toLowerCase().includes('gold')) {
      title = 'Asymmetric Safe-Haven Harvesting & Dip-Buy Rotation';
      rationale = `Harvests tactical profits from gold surge to rebalance into high-quality equities trading at temporary narrative discounts.`;
      tickets = [
        {
          type: 'sell',
          action: 'Harvest 5% Outperformance from Gold (GOLDBEES)',
          detail: 'Lock in safe-haven valuation expansion at historical resistance highs.',
        },
        {
          type: 'buy',
          action: 'Opportunistic Dip-Buy on Diversified Nifty 50',
          detail: 'Acquire high-quality dividend payers at attractive risk-adjusted entry prices.',
        },
        {
          type: 'hedge',
          action: 'Dynamic Trailing Profit Floor',
          detail: 'Protect unrealized commodity gains with trailing threshold discipline.',
        },
      ];
    }

    // Proposed new weights
    const proposedWeights = [...weights];
    if (drags.length > 0 && worstAsset) {
      const worstIdx = portfolio.holdings.findIndex((h) => h.ticker === worstAsset.ticker);
      if (worstIdx !== -1) {
        const reduction = Math.min(proposedWeights[worstIdx] * 0.35, 15);
        proposedWeights[worstIdx] = Math.max(5, proposedWeights[worstIdx] - reduction);
        // Find safe asset or last asset
        const safeIdx = portfolio.holdings.findIndex(
          (h) => h.sector.toLowerCase().includes('liquid') || h.assetClass === 'Debt' || h.assetClass === 'Commodity'
        );
        if (safeIdx !== -1 && safeIdx !== worstIdx) {
          proposedWeights[safeIdx] += reduction;
        } else {
          // Distribute to first non-worst
          const targetIdx = worstIdx === 0 ? 1 : 0;
          if (proposedWeights[targetIdx] !== undefined) {
            proposedWeights[targetIdx] += reduction;
          }
        }
      }
    }

    const drawdownSaved = Math.max(0, Math.round(Math.abs(currentTotalPnl) * 0.65));

    return {
      title,
      rationale,
      tickets,
      proposedWeights,
      drawdownSaved,
      frictionCost: Math.round(currentTotalVal * 0.0018),
    };
  }, [catalyst, currentHoldingsWithShock, currentTotalPnl, currentTotalVal, currency, weights, portfolio]);

  const handleApplyStrategy = () => {
    onAdoptStrategy(tailoredStrategy.proposedWeights);
    setStrategyAdopted(true);
  };

  // Trajectory calculations for SVG chart
  const trajectoryPoints = useMemo(() => {
    const days = [0, 15, 30, 60, 90, 120, 150, 180];
    const initial = currentTotalVal;
    const troughPct = Math.min(currentReturnPct, -2);
    const hedgedTroughPct = troughPct * 0.32;

    return days.map((day) => {
      // Baseline: gentle steady drift
      const baseline = initial * (1 + (0.09 * (day / 365)));

      // Unhedged: drops quickly by day 30, then sluggishly recovers
      let unhedgedShockFactor = 0;
      if (day <= 30) {
        unhedgedShockFactor = (troughPct / 100) * (day / 30);
      } else {
        const recoveryProgress = (day - 30) / 150;
        unhedgedShockFactor = (troughPct / 100) * (1 - recoveryProgress * 0.55);
      }
      const unhedged = initial * (1 + unhedgedShockFactor);

      // Hedged: cushioned floor, faster rebound
      let hedgedShockFactor = 0;
      if (day <= 30) {
        hedgedShockFactor = (hedgedTroughPct / 100) * (day / 30);
      } else {
        const recoveryProgress = (day - 30) / 150;
        hedgedShockFactor = (hedgedTroughPct / 100) * (1 - recoveryProgress * 0.95);
      }
      const hedged = initial * (1 + hedgedShockFactor);

      return { day, baseline, unhedged, hedged };
    });
  }, [currentTotalVal, currentReturnPct]);

  // SVG dimensions
  const svgWidth = 760;
  const svgHeight = 220;
  const padding = { top: 20, right: 30, bottom: 30, left: 75 };
  const chartW = svgWidth - padding.left - padding.right;
  const chartH = svgHeight - padding.top - padding.bottom;

  const allVals = trajectoryPoints.flatMap((p) => [p.baseline, p.unhedged, p.hedged]);
  const minVal = Math.min(...allVals) * 0.97;
  const maxVal = Math.max(...allVals) * 1.03;
  const valSpan = Math.max(1, maxVal - minVal);

  const getX = (day: number) => padding.left + (day / 180) * chartW;
  const getY = (val: number) => padding.top + chartH - ((val - minVal) / valSpan) * chartH;

  const baselinePath = trajectoryPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(p.day).toFixed(1)} ${getY(p.baseline).toFixed(1)}`).join(' ');
  const unhedgedPath = trajectoryPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(p.day).toFixed(1)} ${getY(p.unhedged).toFixed(1)}`).join(' ');
  const hedgedPath = trajectoryPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(p.day).toFixed(1)} ${getY(p.hedged).toFixed(1)}`).join(' ');

  return (
    <section className="catalyst-station panel" id="catalyst-stress-station">
      {/* 1. Header Banner */}
      <div className="catalyst-station__header">
        <div className="catalyst-station__title-box">
          <div className="catalyst-station__badge-row">
            <span className={`catalyst-station__pulse-badge ${catalyst.sentiment || 'neutral'}`}>
              <span className="catalyst-station__pulse-dot" />
              ⚡ ACTIVE CATALYST STRESS SIMULATION
            </span>
            {catalyst.category && (
              <span className="catalyst-station__category-tag">{catalyst.category}</span>
            )}
            <span className="catalyst-station__source-tag">Source: {catalyst.source}</span>
          </div>
          <h2 className="catalyst-station__headline">{catalyst.headline}</h2>
          <p className="catalyst-station__summary">{catalyst.summary}</p>
        </div>

        <div className="catalyst-station__header-actions">
          <div className="catalyst-station__selector">
            <label htmlFor="catalyst-quick-select" style={{ fontSize: '11px', color: 'var(--market-text-muted)' }}>
              Test other catalyst:
            </label>
            <select
              id="catalyst-quick-select"
              value={catalyst.id}
              onChange={(e) => {
                const found = availableArticles.find((a) => a.id === e.target.value);
                if (found) {
                  setStrategyAdopted(false);
                  onSelectOtherCatalyst(found);
                }
              }}
            >
              {availableArticles.map((art) => (
                <option key={art.id} value={art.id}>
                  {art.headline.length > 55 ? `${art.headline.slice(0, 55)}…` : art.headline}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="catalyst-station__btn-clear"
            onClick={onClearCatalyst}
            title="Clear active narrative catalyst and restore standard scenario"
          >
            ✕ Exit Catalyst Mode
          </button>
        </div>
      </div>

      {/* 2. Current Portfolio Diagnosis & KPIs */}
      <div className="catalyst-station__diagnosis-panel">
        <div className="catalyst-station__profile-box">
          <div className="catalyst-station__portfolio-name-row">
            <div>
              <span className="catalyst-station__section-eyebrow">Active Investor Vulnerability Profile</span>
              <div className="catalyst-station__portfolio-title">{portfolio.name}</div>
            </div>
            <div className="catalyst-station__profile-chips">
              <span className="catalyst-station__chip">Horizon: <strong>{portfolio.investorProfile.horizon_years}y</strong></span>
              <span className="catalyst-station__chip">Risk: <strong>{portfolio.investorProfile.risk_tolerance}</strong></span>
              <span className="catalyst-station__chip">Liquidity: <strong>{portfolio.investorProfile.liquidity_need}</strong></span>
            </div>
          </div>

          <div className={`catalyst-station__narrative-eval ${diagnosticEvaluation.severity}`}>
            <strong>{diagnosticEvaluation.headline}: </strong>
            {diagnosticEvaluation.body}
          </div>
        </div>

        <div className="catalyst-station__kpi-strip">
          <div className="catalyst-station__kpi-card">
            <span className="kpi-label">Direct Exposure</span>
            <strong className={directExposurePct > 40 ? 'negative' : directExposurePct === 0 ? 'positive' : 'neutral'}>
              {directExposurePct.toFixed(1)}%
            </strong>
            <small>{currentHoldingsWithShock.filter((h) => h.isDirect).length} affected assets</small>
          </div>

          <div className="catalyst-station__kpi-card">
            <span className="kpi-label">Projected Shock</span>
            <strong className={currentTotalPnl < 0 ? 'negative' : 'positive'}>
              {formatSignedMoney(currentTotalPnl, currency)}
            </strong>
            <small>({currentReturnPct >= 0 ? '+' : ''}{currentReturnPct.toFixed(2)}% net NAV)</small>
          </div>

          <div className="catalyst-station__kpi-card">
            <span className="kpi-label">Modeled Defense</span>
            <strong className="positive">
              +{formatMoney(tailoredStrategy.drawdownSaved, currency)}
            </strong>
            <small>Downside saved by hedge</small>
          </div>
        </div>
      </div>

      {/* 3. Cross-Portfolio Benchmark: "Different for Everyone" */}
      <div className="catalyst-station__differentiation-section">
        <div className="catalyst-station__differentiation-header">
          <div>
            <h3>Cross-Portfolio Vulnerability Benchmark</h3>
            <span>Comparing how different investor profiles react to this exact same macroeconomic headline</span>
          </div>
        </div>

        <div className="catalyst-station__cards-grid">
          {crossPortfolioBenchmark.map((bench) => (
            <div
              key={bench.id}
              className={`catalyst-station__profile-card ${bench.isActive ? 'active' : ''}`}
            >
              <div>
                <div className="catalyst-station__profile-card-top">
                  <div className="catalyst-station__profile-card-title">{bench.name}</div>
                  {bench.isActive && <span className="catalyst-station__card-active-pill">Viewing</span>}
                </div>

                <div className="catalyst-station__card-metrics" style={{ marginTop: '10px' }}>
                  <div className="card-metric-row">
                    <span className="metric-title">Direct Narrative Exposure:</span>
                    <strong className="metric-val">{bench.directWeight.toFixed(1)}%</strong>
                  </div>
                  <div className="card-metric-row">
                    <span className="metric-title">Projected Headline Shock:</span>
                    <strong className={`metric-val ${bench.pnl < 0 ? 'negative' : 'positive'}`}>
                      {formatSignedMoney(bench.pnl, currency)} ({bench.retPct >= 0 ? '+' : ''}{bench.retPct.toFixed(1)}%)
                    </strong>
                  </div>
                  <div className="card-metric-row">
                    <span className="metric-title">Total Portfolio Value:</span>
                    <span className="metric-val">{formatMoney(bench.marketValue, currency, true)}</span>
                  </div>
                </div>
              </div>

              <div className="catalyst-station__card-footer">
                <span className={`catalyst-station__card-status-badge ${bench.status}`}>
                  {bench.statusText}
                </span>
                {!bench.isActive && (
                  <button
                    type="button"
                    className="catalyst-station__btn-switch-profile"
                    onClick={() => {
                      setStrategyAdopted(false);
                      onSwitchPortfolio(bench.id);
                    }}
                  >
                    Test this profile →
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Relevant Graph Visualization */}
      <div className="catalyst-station__graph-section">
        <div className="catalyst-station__graph-tabs">
          <div className="catalyst-station__tab-btns">
            <button
              type="button"
              className={`catalyst-station__tab-btn ${activeGraphTab === 'attribution' ? 'active' : ''}`}
              onClick={() => setActiveGraphTab('attribution')}
            >
              📊 Asset Shock Attribution & Sensitivity
            </button>
            <button
              type="button"
              className={`catalyst-station__tab-btn ${activeGraphTab === 'trajectory' ? 'active' : ''}`}
              onClick={() => setActiveGraphTab('trajectory')}
            >
              📈 180-Day Stress Trajectory & Recovery
            </button>
          </div>

          <div className="catalyst-station__graph-legend">
            {activeGraphTab === 'attribution' ? (
              <>
                <div className="catalyst-station__legend-item">
                  <span className="catalyst-station__legend-dot drag" /> Negative Drag Asset
                </div>
                <div className="catalyst-station__legend-item">
                  <span className="catalyst-station__legend-dot shield" /> Shield / Safe Haven
                </div>
              </>
            ) : (
              <>
                <div className="catalyst-station__legend-item">
                  <span className="catalyst-station__legend-dot baseline" /> Normal Baseline
                </div>
                <div className="catalyst-station__legend-item">
                  <span className="catalyst-station__legend-dot drag" /> Unhedged Catalyst Shock
                </div>
                <div className="catalyst-station__legend-item">
                  <span className="catalyst-station__legend-dot hedged" /> Tailored Strategy Path
                </div>
              </>
            )}
          </div>
        </div>

        {activeGraphTab === 'attribution' ? (
          <div className="catalyst-station__attribution-list">
            {currentHoldingsWithShock.map((h) => {
              const maxAbsShock = 30;
              const barWidthPct = Math.min(100, Math.max(5, (Math.abs(h.shockPct) / maxAbsShock) * 100));
              const shockClass = h.shockPct < 0 ? 'negative' : h.shockPct > 0 ? 'positive' : 'neutral';

              return (
                <div key={h.ticker} className="catalyst-station__attr-row">
                  <div className="catalyst-station__attr-asset">
                    <strong>{h.ticker}</strong>
                    <small>{h.name}</small>
                  </div>

                  <div className="catalyst-station__attr-weight">
                    {h.normalizedWeight.toFixed(1)}% <small style={{ color: 'var(--market-text-muted)' }}>({formatMoney(h.assetVal, currency, true)})</small>
                  </div>

                  <div className="catalyst-station__bar-container">
                    <div
                      className={`catalyst-station__bar-fill ${shockClass}`}
                      style={{ width: `${barWidthPct}%` }}
                    />
                    <span style={{ position: 'absolute', left: '8px', fontSize: '10px', color: '#fff', fontWeight: 600 }}>
                      {h.rationale}
                    </span>
                  </div>

                  <div className={`catalyst-station__attr-pnl ${shockClass}`}>
                    {formatSignedMoney(h.pnlInr, currency)}
                    <div style={{ fontSize: '9.5px', fontWeight: 500 }}>
                      ({h.shockPct >= 0 ? '+' : ''}{h.shockPct.toFixed(1)}%)
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="catalyst-station__chart-wrap">
            <svg
              className="catalyst-station__chart-svg"
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
                const y = padding.top + chartH * pct;
                const val = maxVal - pct * valSpan;
                return (
                  <g key={pct}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={padding.left + chartW}
                      y2={y}
                      stroke="rgba(255, 255, 255, 0.08)"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={padding.left - 8}
                      y={y + 4}
                      fill="var(--market-text-muted, #64748b)"
                      fontSize="9.5"
                      textAnchor="end"
                    >
                      {formatMoney(val, currency, true)}
                    </text>
                  </g>
                );
              })}

              {/* Day Labels */}
              {trajectoryPoints.map((p) => (
                <text
                  key={p.day}
                  x={getX(p.day)}
                  y={padding.top + chartH + 18}
                  fill="var(--market-text-muted, #64748b)"
                  fontSize="9.5"
                  textAnchor="middle"
                >
                  T+{p.day}d
                </text>
              ))}

              {/* Paths */}
              <path
                d={baselinePath}
                fill="none"
                stroke="#94a3b8"
                strokeWidth="2"
                strokeDasharray="4 4"
                opacity="0.7"
              />
              <path
                d={unhedgedPath}
                fill="none"
                stroke="#ef4444"
                strokeWidth="2.5"
              />
              <path
                d={hedgedPath}
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2.5"
              />

              {/* Trough Callout Point */}
              {trajectoryPoints[2] && (
                <g>
                  <circle
                    cx={getX(trajectoryPoints[2].day)}
                    cy={getY(trajectoryPoints[2].unhedged)}
                    r="4"
                    fill="#ef4444"
                  />
                  <text
                    x={getX(trajectoryPoints[2].day)}
                    y={getY(trajectoryPoints[2].unhedged) + 16}
                    fill="#ef4444"
                    fontSize="9.5"
                    fontWeight="700"
                    textAnchor="middle"
                  >
                    Max Trough: {formatSignedMoney(currentTotalPnl, currency)}
                  </text>
                </g>
              )}
            </svg>
          </div>
        )}
      </div>

      {/* 5. Tailored Catalyst Strategy */}
      <div className="catalyst-station__strategy-panel">
        <div className="catalyst-station__strategy-header">
          <div className="catalyst-station__strategy-title-group">
            <span className="catalyst-station__strategy-eyebrow">Tailored Catalyst Defense & Rebalance Strategy</span>
            <h3>{tailoredStrategy.title}</h3>
            <p className="catalyst-station__strategy-rationale">{tailoredStrategy.rationale}</p>
          </div>

          <button
            type="button"
            className={`catalyst-station__btn-adopt-strategy ${strategyAdopted ? 'adopted' : ''}`}
            onClick={handleApplyStrategy}
            disabled={strategyAdopted}
          >
            {strategyAdopted ? '✓ Strategy Adopted in Stress Lab' : '⚡ Adopt Catalyst Strategy (Apply Rebalance)'}
          </button>
        </div>

        <div className="catalyst-station__action-tickets">
          {tailoredStrategy.tickets.map((t, idx) => (
            <div key={idx} className={`catalyst-station__ticket ${t.type}`}>
              <span className="catalyst-station__ticket-type">{t.type} ticket</span>
              <div className="catalyst-station__ticket-action">{t.action}</div>
              <div className="catalyst-station__ticket-detail">{t.detail}</div>
            </div>
          ))}
        </div>

        <div className="catalyst-station__strategy-footer">
          <div className="catalyst-station__strategy-metrics">
            <div>
              <span>Modeled Drawdown Saved:</span>
              <strong>+{formatMoney(tailoredStrategy.drawdownSaved, currency)}</strong>
            </div>
            <div>
              <span>Estimated Friction & Tax:</span>
              <strong style={{ color: 'var(--market-text-secondary)' }}>~{formatMoney(tailoredStrategy.frictionCost, currency)}</strong>
            </div>
            <div>
              <span>Horizon Protection:</span>
              <strong style={{ color: '#06b6d4' }}>{portfolio.investorProfile.horizon_years}-Year Goal Safeguarded</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CatalystStressStation;
