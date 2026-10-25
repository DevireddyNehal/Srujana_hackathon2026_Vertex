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
};

export const portfolios: Portfolio[] = mockPortfolios.map((portfolio) => {
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
