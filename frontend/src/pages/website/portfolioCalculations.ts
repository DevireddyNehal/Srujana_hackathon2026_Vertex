import type { Holding, Portfolio, Scenario } from "./portfolioData";

export interface NormalizedHolding extends Holding {
  normalizedWeight: number;
  marketValue: number;
}

export interface ScenarioResult {
  returnPct: number;
  pnl: number;
  endingValue: number;
  contributions: Array<{ ticker: string; name: string; pnl: number }>;
}

export function normalizeHoldings(
  portfolio: Portfolio,
  weights: number[],
): { holdings: NormalizedHolding[]; totalWeight: number; valid: boolean } {
  const safeWeights = weights.map((weight) =>
    Number.isFinite(weight) ? Math.max(0, weight) : 0,
  );
  const totalWeight = safeWeights.reduce((sum, weight) => sum + weight, 0);
  const valid = Math.abs(totalWeight - 100) < 0.01 && totalWeight > 0;

  return {
    totalWeight,
    valid,
    holdings: portfolio.holdings.map((holding, index) => {
      const normalizedWeight =
        totalWeight > 0 ? (safeWeights[index] / totalWeight) * 100 : 0;
      return {
        ...holding,
        weight: safeWeights[index],
        normalizedWeight,
        marketValue: (portfolio.marketValue * normalizedWeight) / 100,
      };
    }),
  };
}

function assetShock(holding: Holding, scenario: Scenario): number {
  const isEquity = holding.assetClass === "Equity";
  const isTechnology = holding.sector === "IT";
  const beta = isTechnology ? 1.15 : holding.sector === "Banking" ? 1.2 : 1;
  const marketImpact = isEquity ? (scenario.marketPct * beta) / 100 : 0;
  const technologyImpact =
    isTechnology ? scenario.technologyPct / 100 : 0;
  const durationYears =
    holding.sector === "Government Bonds"
      ? 7.5
      : holding.sector === "Corporate Bonds"
        ? 3.2
        : holding.sector === "Real Estate"
          ? 4
          : holding.sector === "Liquid Debt"
            ? 0.1
            : 0;
  const rateImpact =
    -(durationYears * scenario.rateBps) / 10_000;
  const fxImpact = (holding.fxExposure * scenario.fxPct) / 100;

  return Math.max(-0.9, marketImpact + technologyImpact + rateImpact + fxImpact);
}

export function calculateScenario(
  portfolio: Portfolio,
  weights: number[],
  scenario: Scenario,
): ScenarioResult {
  const { holdings } = normalizeHoldings(portfolio, weights);
  const contributions = holdings.map((holding) => ({
    ticker: holding.ticker,
    name: holding.name,
    pnl: holding.marketValue * assetShock(holding, scenario),
  }));
  const pnl = contributions.reduce((sum, holding) => sum + holding.pnl, 0);
  const returnPct =
    portfolio.marketValue > 0 ? (pnl / portfolio.marketValue) * 100 : 0;

  return {
    returnPct,
    pnl,
    endingValue: portfolio.marketValue + pnl,
    contributions: contributions.sort((a, b) => a.pnl - b.pnl),
  };
}

export interface HedgedScenarioResult {
  hedgedPnl: number;
  hedgedReturnPct: number;
  hedgedEndingValue: number;
  drawdownSavedInr: number;
  isExpansion?: boolean;
  statusMessage?: string;
}

export function calculateHedgedScenario(
  portfolio: Portfolio,
  weights: number[],
  scenario: Scenario,
  turnoverBudgetPct: number = 20,
  hedgePreference: string = "multi_asset",
): HedgedScenarioResult {
  const { holdings } = normalizeHoldings(portfolio, weights);
  const totalMarketVal = portfolio.marketValue || 1;
  const contributions = holdings.map((holding) => ({
    ticker: holding.ticker,
    marketValue: holding.marketValue,
    shock: assetShock(holding, scenario),
    pnl: holding.marketValue * assetShock(holding, scenario),
  }));

  const baselinePnl = contributions.reduce((sum, h) => sum + h.pnl, 0);
  const isExpansion = baselinePnl >= 0;

  if (isExpansion) {
    return {
      hedgedPnl: baselinePnl,
      hedgedReturnPct: (baselinePnl / totalMarketVal) * 100,
      hedgedEndingValue: totalMarketVal + baselinePnl,
      drawdownSavedInr: 0,
      isExpansion: true,
      statusMessage: "Bull market expansion · No defensive hedge triggered",
    };
  }

  const drags = contributions.filter((c) => c.shock < 0).sort((a, b) => a.shock - b.shock);
  const totalDragVal = drags.reduce((sum, d) => sum + d.marketValue, 0);

  const turnoverCapInr = totalMarketVal * (Math.min(Math.max(turnoverBudgetPct, 5), 50) / 100);
  const actualTrimInr = Math.min(turnoverCapInr, totalDragVal * 0.7);

  let safeHavenShock = 0.03;
  if (hedgePreference === "gold_focus") {
    safeHavenShock = 0.06;
  } else if (hedgePreference === "liquid_debt_focus") {
    safeHavenShock = 0.003;
  } else if (hedgePreference === "equity_defensive") {
    safeHavenShock = -0.03;
  }

  let trimmedLossAvoided = 0;
  if (totalDragVal > 0) {
    const avgDragShock = drags.reduce((sum, d) => sum + d.shock * (d.marketValue / totalDragVal), 0);
    trimmedLossAvoided = actualTrimInr * Math.abs(avgDragShock);
  }

  const safeHavenPnl = actualTrimInr * safeHavenShock;
  const drawdownSaved = Math.max(0, trimmedLossAvoided + safeHavenPnl);

  const hedgedPnl = baselinePnl + drawdownSaved;
  const hedgedReturnPct = (hedgedPnl / totalMarketVal) * 100;
  const hedgedEndingValue = totalMarketVal + hedgedPnl;

  const statusMessage = drawdownSaved > 0
    ? `Protected downside with ${turnoverBudgetPct}% defensive buffer`
    : "Baseline stress level aligns with current asset mix";

  return {
    hedgedPnl,
    hedgedReturnPct,
    hedgedEndingValue,
    drawdownSavedInr: Math.round(drawdownSaved),
    isExpansion: false,
    statusMessage,
  };
}

function dailyPortfolioReturns(holdings: NormalizedHolding[], monthlyReturns?: number[]): number[] {
  const monthlyMean = monthlyReturns && monthlyReturns.length > 0
    ? monthlyReturns.reduce((sum, r) => sum + r, 0) / monthlyReturns.length
    : 0.01;
  const dailyMean = monthlyMean / 21;
  const monthlyVariance = monthlyReturns && monthlyReturns.length > 1
    ? monthlyReturns.reduce((sum, r) => sum + (r - monthlyMean) ** 2, 0) / (monthlyReturns.length - 1)
    : 0.0001;
  const volFactor = Math.max(0.35, Math.min(2.8, Math.sqrt(monthlyVariance) / 0.008));

  return Array.from({ length: 252 }, (_, day) => {
    const monthIdx = Math.min(Math.floor(day / 21), (monthlyReturns?.length || 12) - 1);
    const monthDrift = (monthlyReturns && monthlyReturns[monthIdx] !== undefined)
      ? (monthlyReturns[monthIdx] / 21)
      : dailyMean;

    const market =
      monthDrift +
      volFactor * (0.00018 + 0.009 * Math.sin((day + 2) * 0.43) + 0.006 * Math.cos((day + 7) * 0.19));

    const returnForDay = holdings.reduce((sum, holding) => {
      const equityExposure =
        holding.assetClass === "Equity"
          ? holding.sector === "IT"
            ? 1.15
            : holding.sector === "Banking"
              ? 1.2
              : 1
          : holding.assetClass === "Commodity"
            ? -0.1
            : 0;
      const cyclical = Math.sin((day + 3) * (0.17 + holding.weight / 300));
      const dailyReturn =
        market * equityExposure +
        volFactor * (holding.volatility / 100 / Math.sqrt(252)) *
          cyclical *
          (holding.assetClass === "Equity" ? 0.38 : 0.16);
      return sum + (holding.normalizedWeight / 100) * dailyReturn;
    }, 0);
    return returnForDay;
  });
}

function historicMonthlyReturns(holdings: NormalizedHolding[]): number[] {
  return Array.from({ length: 24 }, (_, month) =>
    holdings.reduce((sum, holding) => {
      const assetClassFactor =
        holding.assetClass === "Equity"
          ? 1
          : holding.assetClass === "Debt"
            ? 0.25
            : holding.assetClass === "Commodity"
              ? 0.42
              : 0.05;
      const seasonal =
        0.006 +
        0.037 * Math.sin((month + 2) * 0.61) +
        0.018 * Math.cos((month + 4) * 0.37);
      const assetReturn =
        (holding.historicalReturn / 100 / 12) * 0.72 +
        seasonal * assetClassFactor;
      return sum + (holding.normalizedWeight / 100) * assetReturn;
    }, 0),
  );
}

function maximumDrawdown(returns: number[]): number {
  let value = 1;
  let peak = 1;
  let maxDrawdown = 0;
  returns.forEach((monthlyReturn) => {
    value *= 1 + monthlyReturn;
    peak = Math.max(peak, value);
    maxDrawdown = Math.min(maxDrawdown, value / peak - 1);
  });
  return maxDrawdown * 100;
}

export function calculateMetrics(
  portfolio: Portfolio,
  weights: number[],
  months: 12 | 24,
) {
  const { holdings } = normalizeHoldings(portfolio, weights);
  const baseMonthlyReturns = (portfolio.historicalMonthlyReturns && portfolio.historicalMonthlyReturns.length >= months)
    ? portfolio.historicalMonthlyReturns.slice(-months)
    : historicMonthlyReturns(holdings).slice(-months);

  // If user adjusted weights, calculate delta adjustment from holdings
  const baseHoldingsWeightedReturn = portfolio.holdings.reduce(
    (sum, h) => sum + (h.weight / 100) * (h.historicalReturn / 100 / 12),
    0
  );
  const currentHoldingsWeightedReturn = holdings.reduce(
    (sum, h) => sum + (h.normalizedWeight / 100) * (h.historicalReturn / 100 / 12),
    0
  );
  const delta = currentHoldingsWeightedReturn - baseHoldingsWeightedReturn;
  const monthlyReturns = baseMonthlyReturns.map((r) => r + delta);

  const dailyReturns = dailyPortfolioReturns(holdings, monthlyReturns);
  const selectedReturns = dailyReturns.slice(-months * 21);
  const average = selectedReturns.reduce((sum, value) => sum + value, 0) /
    Math.max(selectedReturns.length, 1);
  const variance =
    selectedReturns.reduce((sum, value) => sum + (value - average) ** 2, 0) /
    Math.max(selectedReturns.length - 1, 1);
  const sortedReturns = [...selectedReturns].sort((a, b) => a - b);
  const fifthPercentile =
    sortedReturns[Math.floor((sortedReturns.length - 1) * 0.05)] ?? 0;

  // Reconstruct historical path:
  // Starts 12 or 24 months ago and compounds so that the final point is portfolio.marketValue:
  const cumulativeGrowth = monthlyReturns.reduce((acc, r) => acc * (1 + r), 1);
  const startingValue = (cumulativeGrowth > 0.05 && Number.isFinite(cumulativeGrowth))
    ? portfolio.marketValue / cumulativeGrowth
    : portfolio.marketValue;

  const historicalValues = monthlyReturns.reduce<number[]>(
    (values, monthlyReturn) => {
      values.push((values.at(-1) ?? startingValue) * (1 + monthlyReturn));
      return values;
    },
    [startingValue],
  );
  const annualizedVolatility = Math.sqrt(variance * 252) * 100;
  const weightedReturn = holdings.reduce(
    (sum, holding) =>
      sum + (holding.normalizedWeight / 100) * holding.historicalReturn,
    0,
  );
  const liquidWeight = holdings.reduce(
    (sum, holding) => sum + (holding.liquidity === "High" ? holding.normalizedWeight : 0),
    0,
  );
  const sectorWeights = holdings.reduce<Record<string, number>>((map, holding) => {
    map[holding.sector] = (map[holding.sector] ?? 0) + holding.normalizedWeight;
    return map;
  }, {});
  const topSector = Object.entries(sectorWeights).sort((a, b) => b[1] - a[1])[0];
  const topHolding = [...holdings].sort(
    (a, b) => b.normalizedWeight - a.normalizedWeight,
  )[0];

  return {
    dailyVaR: Math.max(0, -fifthPercentile * portfolio.marketValue),
    annualizedVolatility,
    maxDrawdown: maximumDrawdown(monthlyReturns),
    historicalValues,
    monthlyReturns,
    weightedReturn,
    liquidValue: (liquidWeight / 100) * portfolio.marketValue,
    liquidWeight,
    sectorWeights,
    topSector,
    topHolding,
  };
}

export function calculateWarnings(
  holdings: NormalizedHolding[],
  riskTolerance: string,
  horizonYears: number,
  requiredLiquidity: number,
  scenarioResult: ScenarioResult | null,
  lossLimitPct: number,
) {
  const warnings: Array<{ severity: "review" | "watch"; title: string; detail: string }> = [];
  const equityWeight = holdings.reduce(
    (sum, holding) =>
      sum + (holding.assetClass === "Equity" ? holding.normalizedWeight : 0),
    0,
  );
  const liquidValue = holdings.reduce(
    (sum, holding) =>
      sum +
      (holding.liquidity === "High" ? holding.marketValue : 0),
    0,
  );
  const sectorWeights = holdings.reduce<Record<string, number>>((map, holding) => {
    map[holding.sector] = (map[holding.sector] ?? 0) + holding.normalizedWeight;
    return map;
  }, {});
  const largestSector = Object.entries(sectorWeights).sort((a, b) => b[1] - a[1])[0];

  if (
    (riskTolerance === "Conservative" && equityWeight > 40) ||
    (horizonYears <= 2 && equityWeight > 55)
  ) {
    warnings.push({
      severity: "review",
      title: "Equity exposure may not fit the stated objective",
      detail: `${equityWeight.toFixed(1)}% is in equities with a ${horizonYears}-year horizon and ${riskTolerance.toLowerCase()} risk setting.`,
    });
  }
  if (liquidValue < requiredLiquidity) {
    warnings.push({
      severity: "review",
      title: "Liquid assets are below the cash requirement",
      detail: `High-liquidity holdings total ${formatCurrency(liquidValue)}, below the ${formatCurrency(requiredLiquidity)} requirement.`,
    });
  }
  if (largestSector && largestSector[1] > 40) {
    warnings.push({
      severity: "watch",
      title: `${largestSector[0]} concentration`,
      detail: `${largestSector[1].toFixed(1)}% of the portfolio is exposed to one sector or asset grouping.`,
    });
  }
  if (scenarioResult && scenarioResult.returnPct < -lossLimitPct) {
    warnings.push({
      severity: "review",
      title: "Scenario loss exceeds your review threshold",
      detail: `Estimated loss is ${Math.abs(scenarioResult.returnPct).toFixed(1)}%, above your ${lossLimitPct}% threshold.`,
    });
  }

  return warnings;
}

export function formatCurrency(value: number, compact = false): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
    notation: compact ? "compact" : "standard",
  }).format(value);
}

export function formatSignedCurrency(value: number): string {
  return `${value < 0 ? "−" : "+"}${formatCurrency(Math.abs(value))}`;
}

export function formatPercent(value: number, digits = 1): string {
  return `${value < 0 ? "−" : ""}${Math.abs(value).toFixed(digits)}%`;
}

export interface RateRecoveryHorizon {
  cagrPct: number;
  cagrLabel: string;
  recoveryYears: number;
}

export interface PortfolioRecoveryEstimate {
  initialValue: number;
  postValue: number;
  isDrawdown: boolean;
  lossInr: number;
  lossPct: number;
  returnNeededPct: number;
  driftImpliedYears: number | null;
  driftImpliedDisplay: string;
  probRecoveringWithinHorizonPct: number;
  probRecoveredAtHorizonPct: number;
  horizonYears: number;
  annualVolPct: number;
  annualDriftPct: number;
  rateTable: RateRecoveryHorizon[];
  statusLabel: string;
  disclaimer: string;
}

export interface RecoveryAnalysisResult {
  unhedged: PortfolioRecoveryEstimate;
  hedged: PortfolioRecoveryEstimate;
  capitalPreservedInr: number;
  yearsSaved: number;
  probBoostPct: number;
  isDrawdown: boolean;
}

export function normalCdf(x: number): number {
  if (x < 0) {
    return 1.0 - normalCdf(-x);
  }
  const p = 0.2316419;
  const b1 = 0.31938153;
  const b2 = -0.356563782;
  const b3 = 1.781477937;
  const b4 = -1.821255978;
  const b5 = 1.330274429;
  const t = 1.0 / (1.0 + p * x);
  const z = (1.0 / Math.sqrt(2.0 * Math.PI)) * Math.exp(-0.5 * x * x);
  const poly = ((((b5 * t + b4) * t + b3) * t + b2) * t + b1) * t;
  return 1.0 - z * poly;
}

export function calculateRecoveryEstimate(
  vInitial: number,
  vPost: number,
  annualVolPct: number,
  annualDriftPct = 10.0,
  horizonYears = 3.0,
): PortfolioRecoveryEstimate {
  const v0 = vInitial > 0 ? vInitial : 1000000;
  const vp = vPost;
  const sigma = Math.max(0, annualVolPct) / 100.0;
  const mu = annualDriftPct / 100.0;
  const H = Math.max(0.1, horizonYears);

  const lossInr = Math.max(0, v0 - vp);
  const lossPct = Number(((lossInr / v0) * 100).toFixed(2));
  const isDrawdown = vp < v0 - 1;

  if (!isDrawdown) {
    return {
      initialValue: Math.round(v0),
      postValue: Math.round(vp),
      isDrawdown: false,
      lossInr: 0,
      lossPct: 0,
      returnNeededPct: 0,
      driftImpliedYears: 0,
      driftImpliedDisplay: "0.0 yrs (No drawdown)",
      probRecoveringWithinHorizonPct: 100,
      probRecoveredAtHorizonPct: 100,
      horizonYears: H,
      annualVolPct: Number(annualVolPct.toFixed(1)),
      annualDriftPct: Number(annualDriftPct.toFixed(1)),
      rateTable: [
        { cagrPct: 5, cagrLabel: "5% CAGR (Conservative)", recoveryYears: 0 },
        { cagrPct: 8, cagrLabel: "8% CAGR (Balanced)", recoveryYears: 0 },
        { cagrPct: 12, cagrLabel: "12% CAGR (Historical Nifty)", recoveryYears: 0 },
        { cagrPct: 15, cagrLabel: "15% CAGR (Aggressive)", recoveryYears: 0 },
      ],
      statusLabel: "Expansion (No drawdown)",
      disclaimer: "Under positive shock scenarios, portfolio value expands beyond baseline, so no capital recovery period is required.",
    };
  }

  if (vp <= 0) {
    return {
      initialValue: Math.round(v0),
      postValue: 0,
      isDrawdown: true,
      lossInr: Math.round(v0),
      lossPct: 100,
      returnNeededPct: 999,
      driftImpliedYears: null,
      driftImpliedDisplay: "Indefinite (100% loss)",
      probRecoveringWithinHorizonPct: 0,
      probRecoveredAtHorizonPct: 0,
      horizonYears: H,
      annualVolPct: Number(annualVolPct.toFixed(1)),
      annualDriftPct: Number(annualDriftPct.toFixed(1)),
      rateTable: [],
      statusLabel: "Total Capital Loss",
      disclaimer: "Total capital depletion cannot be recovered through compounding alone.",
    };
  }

  const returnNeededPct = Number((((v0 - vp) / vp) * 100).toFixed(2));
  const a = Math.log(v0 / vp);

  const benchmarkRates = [
    { cagrPct: 5, cagrLabel: "5% CAGR (Conservative)" },
    { cagrPct: 8, cagrLabel: "8% CAGR (Balanced)" },
    { cagrPct: 12, cagrLabel: "12% CAGR (Historical Nifty)" },
    { cagrPct: 15, cagrLabel: "15% CAGR (Aggressive)" },
  ];
  const rateTable: RateRecoveryHorizon[] = benchmarkRates.map(({ cagrPct, cagrLabel }) => {
    const r = cagrPct / 100.0;
    const tYears = a / Math.log(1.0 + r);
    return {
      cagrPct,
      cagrLabel,
      recoveryYears: Number(tYears.toFixed(1)),
    };
  });

  let driftImpliedYears: number | null = null;
  let driftImpliedDisplay = "Indefinite (Drift <= 0%)";
  if (mu > 0) {
    driftImpliedYears = Number((a / mu).toFixed(1));
    driftImpliedDisplay = `${driftImpliedYears} yrs`;
  }

  let pFirstPassage = 0;
  let pTerminal = 0;

  if (sigma <= 1e-4) {
    if (mu > 0 && mu * H >= a) {
      pFirstPassage = 100;
      pTerminal = 100;
    }
  } else {
    const denom = sigma * Math.sqrt(H);
    const z1 = (mu * H - a) / denom;
    const z2 = (-mu * H - a) / denom;

    const pTermVal = normalCdf(z1);
    pTerminal = Number((Math.min(1.0, Math.max(0.0, pTermVal)) * 100).toFixed(1));

    const exponent = Math.min(500.0, (2.0 * mu * a) / (sigma * sigma));
    const expTerm = Math.exp(exponent);
    const firstPassageVal = normalCdf(z1) + expTerm * normalCdf(z2);
    pFirstPassage = Number((Math.min(1.0, Math.max(0.0, firstPassageVal)) * 100).toFixed(1));
  }

  return {
    initialValue: Math.round(v0),
    postValue: Math.round(vp),
    isDrawdown: true,
    lossInr: Math.round(lossInr),
    lossPct,
    returnNeededPct,
    driftImpliedYears,
    driftImpliedDisplay,
    probRecoveringWithinHorizonPct: pFirstPassage,
    probRecoveredAtHorizonPct: pTerminal,
    horizonYears: H,
    annualVolPct: Number(annualVolPct.toFixed(1)),
    annualDriftPct: Number(annualDriftPct.toFixed(1)),
    rateTable,
    statusLabel: `Drawdown: -${lossPct}%`,
    disclaimer: "Model-derived estimate assuming geometric Brownian motion with constant drift and volatility. Capital preserved under simulated shock is a model result, not a guaranteed outcome.",
  };
}

export function calculateRecoveryComparison(
  vInitial: number,
  unhedgedEndingValue: number,
  hedgedEndingValue: number,
  unhedgedVol = 13.5,
  hedgedVol = 10.5,
  annualDriftPct = 10.0,
  horizonYears = 3.0,
): RecoveryAnalysisResult {
  const unhedged = calculateRecoveryEstimate(vInitial, unhedgedEndingValue, unhedgedVol, annualDriftPct, horizonYears);
  const hedged = calculateRecoveryEstimate(vInitial, hedgedEndingValue, hedgedVol, annualDriftPct, horizonYears);
  const capitalPreservedInr = Math.max(0, Math.round(hedgedEndingValue - unhedgedEndingValue));
  const yearsSaved =
    unhedged.driftImpliedYears !== null && hedged.driftImpliedYears !== null
      ? Number((unhedged.driftImpliedYears - hedged.driftImpliedYears).toFixed(1))
      : 0;
  const probBoostPct = Number((hedged.probRecoveringWithinHorizonPct - unhedged.probRecoveringWithinHorizonPct).toFixed(1));

  return {
    unhedged,
    hedged,
    capitalPreservedInr,
    yearsSaved,
    probBoostPct,
    isDrawdown: unhedged.isDrawdown,
  };
}

