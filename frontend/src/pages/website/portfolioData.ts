export interface InvestorProfile {
  horizon_years: number;
  risk_tolerance: "Low" | "Moderate" | "High";
  liquidity_need: "Low" | "Medium" | "High";
  target_goal_inr: number;
}

export interface Holding {
  ticker: string;
  name: string;
  assetClass: string;
  sector: string;
  weight: number;
  historicalReturn: number;
  volatility: number;
  liquidity: "High" | "Medium" | "Low";
  currencyExposure: string;
  fxExposure: number;
}

export interface Portfolio {
  id: string;
  name: string;
  owner: string;
  marketValue: number;
  investorProfile: InvestorProfile;
  holdings: Holding[];
  historicalMonthlyReturns?: number[];
  style?: string;
}

export interface Scenario {
  id: string;
  label: string;
  description: string;
  marketPct: number;
  rateBps: number;
  technologyPct: number;
  fxPct: number;
}

interface MockAsset {
  ticker: string;
  name: string;
  sector: string;
  asset_class: string;
  amount_inr: number;
  liquidity_tag: "High" | "Medium" | "Low";
  currency_exposure: string;
}

interface MockPortfolio {
  id: string;
  name: string;
  investor_profile: InvestorProfile;
  assets: MockAsset[];
}

const mockPortfolios: MockPortfolio[] = [
  {
    id: "tech-heavy",
    name: "Aggressive Growth (Hidden IT Concentration)",
    investor_profile: {
      horizon_years: 1,
      risk_tolerance: "Low",
      liquidity_need: "High",
      target_goal_inr: 1_000_000,
    },
    assets: [
      { ticker: "TCS.NS", name: "Tata Consultancy Services", sector: "IT", asset_class: "Equity", amount_inr: 400_000, liquidity_tag: "High", currency_exposure: "USD_INR" },
      { ticker: "INFY.NS", name: "Infosys Ltd", sector: "IT", asset_class: "Equity", amount_inr: 350_000, liquidity_tag: "High", currency_exposure: "USD_INR" },
      { ticker: "HDFCBANK.NS", name: "HDFC Bank", sector: "Banking", asset_class: "Equity", amount_inr: 150_000, liquidity_tag: "High", currency_exposure: "INR" },
      { ticker: "REALTY_LOCKED", name: "Commercial REIT / Locked Debt", sector: "Real Estate", asset_class: "Debt", amount_inr: 100_000, liquidity_tag: "Low", currency_exposure: "INR" },
    ],
  },
  {
    id: "conservative-retiree",
    name: "Conservative Retiree (Hidden Interest-Rate Risk)",
    investor_profile: {
      horizon_years: 5,
      risk_tolerance: "Low",
      liquidity_need: "Medium",
      target_goal_inr: 2_500_000,
    },
    assets: [
      { ticker: "GSEC10Y_MOCK", name: "10-Year Government Securities (Demo Asset)", sector: "Government Bonds", asset_class: "Debt", amount_inr: 1_250_000, liquidity_tag: "Medium", currency_exposure: "INR" },
      { ticker: "CORP_BOND_FUND_MOCK", name: "Corporate Bond Fund (Demo Asset)", sector: "Corporate Bonds", asset_class: "Debt", amount_inr: 750_000, liquidity_tag: "Medium", currency_exposure: "INR" },
      { ticker: "REIT_LOCKED_MOCK", name: "Real Estate REIT / Locked Asset (Demo Asset)", sector: "Real Estate", asset_class: "Alternative", amount_inr: 375_000, liquidity_tag: "Low", currency_exposure: "INR" },
      { ticker: "ITC.NS", name: "ITC Ltd", sector: "FMCG", asset_class: "Equity", amount_inr: 125_000, liquidity_tag: "High", currency_exposure: "INR" },
    ],
  },
  {
    id: "all-weather-balanced",
    name: "All-Weather Balanced (Resilient Benchmark)",
    investor_profile: {
      horizon_years: 3,
      risk_tolerance: "Moderate",
      liquidity_need: "Medium",
      target_goal_inr: 1_500_000,
    },
    assets: [
      { ticker: "NIFTYBEES.NS", name: "Nifty 50 ETF (Demo Holding)", sector: "Diversified Equity", asset_class: "Equity", amount_inr: 525_000, liquidity_tag: "High", currency_exposure: "INR" },
      { ticker: "LIQUIDBEES.NS", name: "Liquid ETF / Short-Duration Debt (Demo Holding)", sector: "Liquid Debt", asset_class: "Debt", amount_inr: 450_000, liquidity_tag: "High", currency_exposure: "INR" },
      { ticker: "GOLDBEES.NS", name: "Gold ETF (Demo Holding)", sector: "Gold", asset_class: "Commodity", amount_inr: 300_000, liquidity_tag: "High", currency_exposure: "INR" },
      { ticker: "HDFCBANK.NS", name: "HDFC Bank", sector: "Banking", asset_class: "Equity", amount_inr: 112_500, liquidity_tag: "High", currency_exposure: "INR" },
      { ticker: "ITC.NS", name: "ITC Ltd", sector: "FMCG", asset_class: "Equity", amount_inr: 112_500, liquidity_tag: "High", currency_exposure: "INR" },
    ],
  },
];

const illustrativeAssumptions: Record<
  string,
  { historicalReturn: number; volatility: number; fxExposure: number }
> = {
  IT: { historicalReturn: 13.8, volatility: 26, fxExposure: 0.7 },
  Banking: { historicalReturn: 11.2, volatility: 22, fxExposure: 0 },
  "Real Estate": { historicalReturn: 8, volatility: 18, fxExposure: 0 },
  "Government Bonds": { historicalReturn: 6.8, volatility: 8, fxExposure: 0 },
  "Corporate Bonds": { historicalReturn: 7.2, volatility: 6.5, fxExposure: 0 },
  FMCG: { historicalReturn: 10, volatility: 17, fxExposure: 0 },
  "Diversified Equity": { historicalReturn: 11.8, volatility: 18, fxExposure: 0 },
  "Liquid Debt": { historicalReturn: 5.8, volatility: 1, fxExposure: 0 },
  Gold: { historicalReturn: 9.2, volatility: 15, fxExposure: 0 },
  Forex: { historicalReturn: 14.5, volatility: 16, fxExposure: 0.9 },
  Indices: { historicalReturn: 15.2, volatility: 19, fxExposure: 0.6 },
  Commodity: { historicalReturn: 12.0, volatility: 22, fxExposure: 0.5 },
  Crypto: { historicalReturn: 28.5, volatility: 48, fxExposure: 0.8 },
  Derivatives: { historicalReturn: 6.0, volatility: 38, fxExposure: 0.4 },
  Arbitrage: { historicalReturn: 8.5, volatility: 4, fxExposure: 0.1 },
  Quantitative: { historicalReturn: 13.0, volatility: 10, fxExposure: 0.3 },
  Global: { historicalReturn: 11.0, volatility: 14, fxExposure: 0.7 },
};

export const demoTraderMonthlyReturns: Record<string, number[]> = {
  demo_trader_01: [
    0.0121, 0.0131, 0.0124, 0.0115, 0.0108, 0.0125, 0.0126, 0.0086, 0.0096, 0.0124, 0.0112, 0.0123,
    0.0102, 0.0140, 0.0129, 0.0126, 0.0129, 0.0132, 0.0119, 0.0124, 0.0107, 0.0109, 0.0097, 0.0096,
  ],
  demo_trader_02: [
    0.0163, 0.0189, 0.0161, 0.0208, 0.0222, 0.0177, 0.0202, 0.0151, 0.0203, 0.0242, 0.0159, 0.0292,
    0.0137, 0.0218, 0.0133, 0.0143, 0.0176, 0.0144, 0.0225, 0.0199, 0.0166, 0.0201, 0.0169, 0.0122,
  ],
  demo_trader_03: [
    0.0330, 0.0320, 0.0299, 0.0240, 0.0319, 0.0234, 0.0260, 0.0358, 0.0285, 0.0251, 0.0283, 0.0261,
    0.0324, 0.0254, 0.0178, 0.0244, 0.0224, 0.0218, 0.0260, 0.0276, 0.0246, 0.0240, 0.0254, 0.0242,
  ],
  demo_trader_04: [
    0.0242, 0.0194, 0.0242, 0.0245, 0.0211, 0.0252, 0.0196, 0.0133, 0.0233, 0.0320, 0.0171, 0.0221,
    0.0219, 0.0213, 0.0140, 0.0258, 0.0217, 0.0198, 0.0273, 0.0232, 0.0227, 0.0220, 0.0191, 0.0152,
  ],
  demo_trader_05: [
    0.0158, 0.0150, 0.0162, 0.0143, 0.0163, 0.0151, 0.0188, 0.0151, 0.0163, 0.0143, 0.0157, 0.0127,
    0.0129, 0.0153, 0.0176, 0.0105, 0.0173, 0.0156, 0.0150, 0.0159, 0.0151, 0.0134, 0.0145, 0.0113,
  ],
  demo_trader_06: [
    0.0296, 0.0299, 0.0392, 0.0333, 0.0237, 0.0343, 0.0382, 0.0251, 0.0419, 0.0232, 0.0207, 0.0292,
    0.0424, 0.0332, 0.0292, 0.0298, 0.0323, 0.0342, 0.0418, 0.0260, 0.0360, 0.0315, 0.0302, 0.0250,
  ],
  demo_trader_07: [
    -0.0292, -0.0693, 0.0146, -0.0607, -0.0039, -0.0233, -0.0037, -0.0316, -0.0297, -0.0135, -0.0137, -0.0044,
    -0.0170, -0.0207, -0.0253, -0.0435, -0.0065, -0.0179, -0.0035, -0.0252, -0.0407, -0.0400, -0.0190, -0.0323,
  ],
  demo_trader_08: [
    0.0137, 0.0122, 0.0130, 0.0124, 0.0122, 0.0129, 0.0094, 0.0116, 0.0112, 0.0147, 0.0085, 0.0088,
    0.0113, 0.0138, 0.0111, 0.0119, 0.0130, 0.0111, 0.0118, 0.0099, 0.0115, 0.0131, 0.0113, 0.0097,
  ],
  demo_trader_09: [
    0.0200, 0.0154, 0.0195, 0.0176, 0.0162, 0.0140, 0.0184, 0.0221, 0.0187, 0.0163, 0.0170, 0.0135,
    0.0153, 0.0174, 0.0123, 0.0133, 0.0216, 0.0182, 0.0136, 0.0160, 0.0142, 0.0190, 0.0174, 0.0131,
  ],
  demo_trader_10: [
    0.0163, 0.0150, 0.0132, 0.0151, 0.0168, 0.0144, 0.0158, 0.0134, 0.0130, 0.0136, 0.0158, 0.0145,
    0.0141, 0.0160, 0.0152, 0.0135, 0.0171, 0.0146, 0.0155, 0.0147, 0.0154, 0.0189, 0.0145, 0.0133,
  ],
};

const basePortfolios: Portfolio[] = mockPortfolios.map((portfolio) => {
  const marketValue = portfolio.assets.reduce((sum, asset) => sum + asset.amount_inr, 0);
  return {
    id: portfolio.id,
    name: portfolio.name,
    owner: "Hackathon demonstration profile",
    marketValue,
    investorProfile: portfolio.investor_profile,
    holdings: portfolio.assets.map((asset) => {
      const assumptions = illustrativeAssumptions[asset.sector] ?? {
        historicalReturn: 8,
        volatility: 12,
        fxExposure: 0,
      };
      return {
        ticker: asset.ticker,
        name: asset.name,
        assetClass: asset.asset_class,
        sector: asset.sector,
        weight: (asset.amount_inr / marketValue) * 100,
        historicalReturn: assumptions.historicalReturn,
        volatility: assumptions.volatility,
        liquidity: asset.liquidity_tag,
        currencyExposure: asset.currency_exposure,
        fxExposure: asset.currency_exposure === "USD_INR" ? assumptions.fxExposure : 0,
      };
    }),
  };
});

export const demoTraderPortfolios: Portfolio[] = [
  {
    id: "demo-trader-01",
    name: "Conservative Swing Trader (Macro FX & Low-Beta Debt)",
    owner: "Demo Trader 01",
    marketValue: 4_166_500,
    investorProfile: { horizon_years: 3, risk_tolerance: "Low", liquidity_need: "Medium", target_goal_inr: 5_500_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_01,
    holdings: [
      { ticker: "GSEC10Y_MOCK", name: "10-Year Government Securities", assetClass: "Debt", sector: "Government Bonds", weight: 45, historicalReturn: 7.2, volatility: 7.5, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "CORP_BOND_FUND_MOCK", name: "AAA Corporate Bond Fund", assetClass: "Debt", sector: "Corporate Bonds", weight: 25, historicalReturn: 8.0, volatility: 6.0, liquidity: "Medium", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "EURUSD_HEDGE", name: "EUR/USD Macro Swing Hedge", assetClass: "Alternative", sector: "Forex", weight: 15, historicalReturn: 14.5, volatility: 15.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "ITC.NS", name: "ITC Ltd Defensive Bluechip", assetClass: "Equity", sector: "FMCG", weight: 15, historicalReturn: 11.0, volatility: 16.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-02",
    name: "High-Frequency Scalper (Liquid High-Beta FX & Tech)",
    owner: "Demo Trader 02",
    marketValue: 2_083_250,
    investorProfile: { horizon_years: 1, risk_tolerance: "High", liquidity_need: "High", target_goal_inr: 3_500_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_02,
    holdings: [
      { ticker: "USDJPY_FX", name: "USD/JPY Intraday FX Spread", assetClass: "Alternative", sector: "Forex", weight: 35, historicalReturn: 16.5, volatility: 18.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "EURUSD_FX", name: "EUR/USD Liquid Scalp Asset", assetClass: "Alternative", sector: "Forex", weight: 30, historicalReturn: 15.0, volatility: 16.5, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "NIFTY_BETA", name: "High-Beta Momentum Equity Basket", assetClass: "Equity", sector: "Diversified Equity", weight: 25, historicalReturn: 18.0, volatility: 24.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "LIQUIDBEES.NS", name: "Instant Overnight Margin Reserve", assetClass: "Debt", sector: "Liquid Debt", weight: 10, historicalReturn: 5.8, volatility: 1.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-03",
    name: "Trend Follower & Index Runner (Global Indices & Gold)",
    owner: "Demo Trader 03",
    marketValue: 8_333_000,
    investorProfile: { horizon_years: 2, risk_tolerance: "High", liquidity_need: "Medium", target_goal_inr: 15_000_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_03,
    holdings: [
      { ticker: "US30_INDEX", name: "Dow Jones / US30 Index Momentum", assetClass: "Equity", sector: "Indices", weight: 45, historicalReturn: 22.0, volatility: 21.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.7 },
      { ticker: "GOLDBEES.NS", name: "Physical Gold / XAU Asset", assetClass: "Commodity", sector: "Gold", weight: 30, historicalReturn: 14.0, volatility: 16.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "TCS.NS", name: "Largecap Technology Exporter", assetClass: "Equity", sector: "IT", weight: 15, historicalReturn: 15.5, volatility: 25.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.7 },
      { ticker: "LIQUIDBEES.NS", name: "Cash Reserve Buffer", assetClass: "Debt", sector: "Liquid Debt", weight: 10, historicalReturn: 5.8, volatility: 1.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-04",
    name: "Breakout Specialist (Midcap Momentum & GBP Breakouts)",
    owner: "Demo Trader 04",
    marketValue: 4_166_500,
    investorProfile: { horizon_years: 2, risk_tolerance: "Moderate", liquidity_need: "High", target_goal_inr: 7_000_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_04,
    holdings: [
      { ticker: "GBPUSD_BREAKOUT", name: "GBP/USD London Volatility Asset", assetClass: "Alternative", sector: "Forex", weight: 40, historicalReturn: 17.5, volatility: 19.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.8 },
      { ticker: "MIDCAP_MOMENTUM", name: "Nifty Midcap 100 Momentum ETF", assetClass: "Equity", sector: "Diversified Equity", weight: 30, historicalReturn: 19.0, volatility: 22.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "INFY.NS", name: "Infosys Ltd Breakout Play", assetClass: "Equity", sector: "IT", weight: 20, historicalReturn: 14.0, volatility: 26.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.7 },
      { ticker: "LIQUIDBEES.NS", name: "Margin Buffer", assetClass: "Debt", sector: "Liquid Debt", weight: 10, historicalReturn: 5.8, volatility: 1.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-05",
    name: "Mean Reversion Range Trader (Multi-Asset Arbitrage)",
    owner: "Demo Trader 05",
    marketValue: 2_500_000,
    investorProfile: { horizon_years: 3, risk_tolerance: "Moderate", liquidity_need: "Medium", target_goal_inr: 4_000_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_05,
    holdings: [
      { ticker: "RANGE_FX_BASKET", name: "EUR/GBP & AUD/NZD Range Basket", assetClass: "Alternative", sector: "Forex", weight: 35, historicalReturn: 12.0, volatility: 9.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.6 },
      { ticker: "ARBITRAGE_FUND", name: "Equity Arbitrage Low-Beta", assetClass: "Equity", sector: "Arbitrage", weight: 30, historicalReturn: 9.0, volatility: 4.5, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "HDFCBANK.NS", name: "HDFC Bank Value Accumulation", assetClass: "Equity", sector: "Banking", weight: 20, historicalReturn: 13.0, volatility: 20.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "GOLDBEES.NS", name: "Gold Range Channel Holding", assetClass: "Commodity", sector: "Gold", weight: 15, historicalReturn: 10.0, volatility: 14.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-06",
    name: "Crypto & Momentum Trader (Digital Assets & High-Beta Tech)",
    owner: "Demo Trader 06",
    marketValue: 1_666_600,
    investorProfile: { horizon_years: 1, risk_tolerance: "High", liquidity_need: "High", target_goal_inr: 4_500_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_06,
    holdings: [
      { ticker: "BTC_USD_ASSET", name: "Bitcoin Digital Asset", assetClass: "Alternative", sector: "Crypto", weight: 45, historicalReturn: 32.0, volatility: 52.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "ETH_USD_ASSET", name: "Ethereum Momentum Asset", assetClass: "Alternative", sector: "Crypto", weight: 30, historicalReturn: 28.0, volatility: 56.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "TCS.NS", name: "Tech Growth Equities", assetClass: "Equity", sector: "IT", weight: 15, historicalReturn: 14.0, volatility: 26.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.7 },
      { ticker: "LIQUIDBEES.NS", name: "Dry Powder Liquidity", assetClass: "Debt", sector: "Liquid Debt", weight: 10, historicalReturn: 5.8, volatility: 1.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-07",
    name: "Emotional / Inconsistent Trader (Distressed High-Risk Speculative)",
    owner: "Demo Trader 07",
    marketValue: 4_166_500,
    investorProfile: { horizon_years: 1, risk_tolerance: "High", liquidity_need: "Low", target_goal_inr: 6_000_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_07,
    holdings: [
      { ticker: "SPEC_LEVERAGED", name: "Overleveraged High-Beta Derivatives", assetClass: "Alternative", sector: "Derivatives", weight: 50, historicalReturn: -15.0, volatility: 65.0, liquidity: "Low", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "DISTRESSED_EQUITY", name: "Smallcap High-Volatility Speculative", assetClass: "Equity", sector: "Diversified Equity", weight: 30, historicalReturn: -8.0, volatility: 45.0, liquidity: "Low", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "REALTY_LOCKED", name: "Illiquid Locked Real Estate Debt", assetClass: "Debt", sector: "Real Estate", weight: 20, historicalReturn: 4.0, volatility: 18.0, liquidity: "Low", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-08",
    name: "Institutional Systematic Trader (Global Sovereign & Core Endowment)",
    owner: "Demo Trader 08",
    marketValue: 20_832_500,
    investorProfile: { horizon_years: 5, risk_tolerance: "Low", liquidity_need: "Low", target_goal_inr: 30_000_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_08,
    holdings: [
      { ticker: "GSEC10Y_MOCK", name: "Sovereign Debt G-Sec Benchmark", assetClass: "Debt", sector: "Government Bonds", weight: 35, historicalReturn: 7.2, volatility: 7.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "NIFTYBEES.NS", name: "Nifty 50 Core Index", assetClass: "Equity", sector: "Diversified Equity", weight: 25, historicalReturn: 12.5, volatility: 16.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "GLOBAL_MULTI_ASSET", name: "Global Diversified Equities & Bonds", assetClass: "Equity", sector: "Global", weight: 20, historicalReturn: 11.5, volatility: 14.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.7 },
      { ticker: "CORP_BOND_FUND_MOCK", name: "High-Grade Corporate Debt", assetClass: "Debt", sector: "Corporate Bonds", weight: 10, historicalReturn: 7.8, volatility: 6.0, liquidity: "Medium", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "GOLDBEES.NS", name: "Gold Strategic Reserve", assetClass: "Commodity", sector: "Gold", weight: 10, historicalReturn: 9.5, volatility: 14.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-09",
    name: "News Event Volatility Trader (Macro Catalyst & Energy)",
    owner: "Demo Trader 09",
    marketValue: 3_333_200,
    investorProfile: { horizon_years: 2, risk_tolerance: "Moderate", liquidity_need: "High", target_goal_inr: 5_500_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_09,
    holdings: [
      { ticker: "EVENT_STRADDLE_FX", name: "USD Event Volatility Basket", assetClass: "Alternative", sector: "Forex", weight: 40, historicalReturn: 16.0, volatility: 23.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.9 },
      { ticker: "ENERGY_COMMODITY", name: "Crude Oil & Energy Commodity ETF", assetClass: "Commodity", sector: "Commodity", weight: 30, historicalReturn: 13.5, volatility: 28.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.6 },
      { ticker: "TCS.NS", name: "Tech Export FX Sensitive", assetClass: "Equity", sector: "IT", weight: 20, historicalReturn: 14.0, volatility: 25.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.7 },
      { ticker: "LIQUIDBEES.NS", name: "Cash Reserve for Event Shocks", assetClass: "Debt", sector: "Liquid Debt", weight: 10, historicalReturn: 5.8, volatility: 1.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
  {
    id: "demo-trader-10",
    name: "Algorithmic Grid/Session Trader (Quantitative Factor & Session Neutral)",
    owner: "Demo Trader 10",
    marketValue: 4_999_800,
    investorProfile: { horizon_years: 4, risk_tolerance: "Moderate", liquidity_need: "Medium", target_goal_inr: 8_500_000 },
    historicalMonthlyReturns: demoTraderMonthlyReturns.demo_trader_10,
    holdings: [
      { ticker: "QUANT_FACTOR_ETF", name: "Quantitative Multi-Factor Index", assetClass: "Equity", sector: "Quantitative", weight: 35, historicalReturn: 15.0, volatility: 13.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "STAT_ARB_FX", name: "Cross-Currency Statistical Arbitrage", assetClass: "Alternative", sector: "Forex", weight: 30, historicalReturn: 13.5, volatility: 11.0, liquidity: "High", currencyExposure: "USD_INR", fxExposure: 0.8 },
      { ticker: "CORP_BOND_FUND_MOCK", name: "Yield Anchor Corporate Debt", assetClass: "Debt", sector: "Corporate Bonds", weight: 20, historicalReturn: 7.8, volatility: 6.0, liquidity: "Medium", currencyExposure: "INR", fxExposure: 0 },
      { ticker: "GOLDBEES.NS", name: "Hedging Reserve", assetClass: "Commodity", sector: "Gold", weight: 15, historicalReturn: 9.5, volatility: 14.0, liquidity: "High", currencyExposure: "INR", fxExposure: 0 },
    ],
  },
];

export const portfolios: Portfolio[] = [...basePortfolios, ...demoTraderPortfolios];

export const scenarios: Scenario[] = [
  {
    id: "crash",
    label: "2008-style broad crash",
    description: "Equities -30% · rates +100 bps",
    marketPct: -30,
    rateBps: 100,
    technologyPct: -8,
    fxPct: 0,
  },
  {
    id: "rates",
    label: "Rate shock",
    description: "Policy rates rise by 200 bps",
    marketPct: -3,
    rateBps: 200,
    technologyPct: 0,
    fxPct: 0,
  },
  {
    id: "technology",
    label: "Technology reset",
    description: "Tech -25% · market -5%",
    marketPct: -5,
    rateBps: 0,
    technologyPct: -25,
    fxPct: 0,
  },
  {
    id: "fx",
    label: "Adverse FX move",
    description: "INR strengthens 15% vs USD",
    marketPct: 0,
    rateBps: 0,
    technologyPct: 0,
    fxPct: -15,
  },
  {
    id: "custom",
    label: "Custom scenario",
    description: "Set your own assumptions",
    marketPct: -12,
    rateBps: 75,
    technologyPct: -10,
    fxPct: -5,
  },
];

export const classCorrelations = [
  { name: "Equity", values: [1, -0.18, 0.12, 0.06] },
  { name: "Bonds", values: [-0.18, 1, 0.08, 0.2] },
  { name: "Gold", values: [0.12, 0.08, 1, 0.05] },
  { name: "Cash", values: [0.06, 0.2, 0.05, 1] },
];
