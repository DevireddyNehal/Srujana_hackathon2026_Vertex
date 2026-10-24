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

function dailyPortfolioReturns(holdings: NormalizedHolding[]): number[] {
  return Array.from({ length: 252 }, (_, day) => {
    const market =
      0.00018 +
      0.009 * Math.sin((day + 2) * 0.43) +
      0.006 * Math.cos((day + 7) * 0.19);
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
        (holding.volatility / 100 / Math.sqrt(252)) *
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
  const dailyReturns = dailyPortfolioReturns(holdings);
  const selectedReturns = dailyReturns.slice(-months * 21);
  const average = selectedReturns.reduce((sum, value) => sum + value, 0) /
    Math.max(selectedReturns.length, 1);
  const variance =
    selectedReturns.reduce((sum, value) => sum + (value - average) ** 2, 0) /
    Math.max(selectedReturns.length - 1, 1);
  const sortedReturns = [...selectedReturns].sort((a, b) => a - b);
  const fifthPercentile =
    sortedReturns[Math.floor((sortedReturns.length - 1) * 0.05)] ?? 0;
  const monthlyReturns = historicMonthlyReturns(holdings).slice(-months);
  const historicalValues = monthlyReturns.reduce<number[]>(
    (values, monthlyReturn) => {
      values.push((values.at(-1) ?? portfolio.marketValue) * (1 + monthlyReturn));
      return values;
    },
    [portfolio.marketValue],
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
