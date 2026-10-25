import React, { useState, useEffect, useMemo } from 'react';
import './NewsIntelligenceWidget.css';
import type { Portfolio } from '../../pages/website/portfolioData';

export interface NewsArticle {
  id: string;
  headline: string;
  summary: string;
  source: string;
  publishedAt: string;
  url?: string;
  relatedAssets?: string[];
  sentiment?: 'bullish' | 'bearish' | 'neutral';
  impactEstimate?: string;
  category?: string;
  suggestedScenarioId?: 'crash' | 'rates' | 'technology' | 'fx' | 'custom';
}

export interface NewsIntelligenceWidgetProps {
  articles?: NewsArticle[];
  portfolio?: Portfolio;
  currency?: 'INR' | 'USD';
  onNavigateToStressLab?: (headline: string, affectedTicker?: string, scenarioId?: string) => void;
}

const DEFAULT_NEWS_ARTICLES: NewsArticle[] = [
  {
    id: 'news-1',
    headline: 'RBI Maintains Repo Rate at 6.50% Amid Lingering Food Price Pressures and Global Inflation Risks',
    summary: 'The Reserve Bank of India Monetary Policy Committee voted to keep benchmark repo rates unchanged at 6.50%, reiterating its stance of withdrawal of accommodation. Governor Das highlighted persistent volatility in vegetable and food prices while pointing to steady domestic GDP growth.',
    source: 'Bloomberg / Mint',
    publishedAt: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    url: 'https://www.livemint.com/economy',
    relatedAssets: ['GSEC10Y_MOCK', 'CORP_BOND_FUND_MOCK', 'LIQUIDBEES.NS'],
    sentiment: 'neutral',
    impactEstimate: '+0.12% Yield Stability',
    category: 'Macro & Policy',
    suggestedScenarioId: 'rates',
  },
  {
    id: 'news-2',
    headline: 'TCS Secures $1.2B Enterprise Cloud & AI Modernization Contract with European Telecom Leader',
    summary: 'Tata Consultancy Services announced a multi-year digital transformation mandate to overhaul IT core infrastructure, migrate workloads to hybrid cloud platforms, and implement generative AI governance workflows across customer service centers.',
    source: 'Economic Times',
    publishedAt: new Date(Date.now() - 75 * 60 * 1000).toISOString(),
    url: 'https://economictimes.indiatimes.com/tech',
    relatedAssets: ['TCS.NS', 'USD_INR'],
    sentiment: 'bullish',
    impactEstimate: '+2.4% Revenue Growth',
    category: 'Information Technology',
    suggestedScenarioId: 'technology',
  },
  {
    id: 'news-3',
    headline: 'US Enterprise Tech Budgets Tighten as CFOs Extend Approval Cycles for Discretionary Cloud Projects',
    summary: 'Industry survey indicates North American Fortune 500 corporations are delaying non-critical digital transformation renewals, creating near-term revenue visibility headwinds for tier-1 Indian software service exporters.',
    source: 'Reuters Financial',
    publishedAt: new Date(Date.now() - 140 * 60 * 1000).toISOString(),
    url: 'https://www.reuters.com/technology',
    relatedAssets: ['TCS.NS', 'INFY.NS', 'USD_INR'],
    sentiment: 'bearish',
    impactEstimate: '-2.8% IT Margin Scrutiny',
    category: 'Information Technology',
    suggestedScenarioId: 'technology',
  },
  {
    id: 'news-4',
    headline: 'HDFC Bank Deposits Expand 18.2% YoY, Narrowing Credit-to-Deposit Gap Across Retail Branches',
    summary: 'Private banking heavyweight HDFC Bank reported strong sequential growth in low-cost CASA deposits, alleviating investor concerns regarding wholesale funding costs and stabilizing net interest margins.',
    source: 'Business Standard',
    publishedAt: new Date(Date.now() - 210 * 60 * 1000).toISOString(),
    url: 'https://www.business-standard.com/finance',
    relatedAssets: ['HDFCBANK.NS', 'NIFTYBEES.NS'],
    sentiment: 'bullish',
    impactEstimate: '+1.9% NIM Support',
    category: 'Banking & Financials',
    suggestedScenarioId: 'crash',
  },
  {
    id: 'news-5',
    headline: 'India 10-Year Benchmark G-Sec Yield Tests 7.18% Following US Treasury Sell-Off and Crude Oil Rebound',
    summary: 'Domestic sovereign debt yields edged higher tracking elevated US 10-year Treasury yields above 4.35%. Bond dealers noted institutional caution ahead of upcoming government bond auctions and weekly liquidity deficits.',
    source: 'Financial Express',
    publishedAt: new Date(Date.now() - 320 * 60 * 1000).toISOString(),
    url: 'https://www.financialexpress.com/market',
    relatedAssets: ['GSEC10Y_MOCK', 'CORP_BOND_FUND_MOCK'],
    sentiment: 'bearish',
    impactEstimate: '-0.7% Duration Mark-to-Market',
    category: 'Fixed Income',
    suggestedScenarioId: 'rates',
  },
  {
    id: 'news-6',
    headline: 'Domestic Gold Prices Surge Past ₹72,500/10g on Geopolitical Safe-Haven Bids and Central Bank Reserves',
    summary: 'Spot and futures gold contracts touched fresh highs in Mumbai and Delhi bullion markets as geopolitical frictions along key shipping lanes accelerated portfolio hedging demand from institutional and retail asset allocators.',
    source: 'Moneycontrol',
    publishedAt: new Date(Date.now() - 430 * 60 * 1000).toISOString(),
    url: 'https://www.moneycontrol.com/commodity',
    relatedAssets: ['GOLDBEES.NS'],
    sentiment: 'bullish',
    impactEstimate: '+3.5% Hedge Outperformance',
    category: 'Commodities',
    suggestedScenarioId: 'crash',
  },
  {
    id: 'news-7',
    headline: 'Indian Rupee Stabilizes Near 83.42 Against USD as RBI Active Liquidity Operations Check Volatility',
    summary: 'The central bank maintained active interventions in non-deliverable forward markets and onshore spot desks, curbing speculative pressure on the rupee despite dollar strength and foreign institutional rebalancing outflows.',
    source: 'CNBC-TV18',
    publishedAt: new Date(Date.now() - 560 * 60 * 1000).toISOString(),
    url: 'https://www.cnbctv18.com/market',
    relatedAssets: ['USD_INR', 'TCS.NS', 'INFY.NS'],
    sentiment: 'neutral',
    impactEstimate: 'FX Volatility Dampened',
    category: 'Forex & Currencies',
    suggestedScenarioId: 'fx',
  },
  {
    id: 'news-8',
    headline: 'ITC Highlights Non-Cigarette FMCG Margin Expansion and Robust Rural Demand Signals',
    summary: 'Consumer goods bellwether ITC reported resilient rural volume traction across packaged foods and personal care divisions, supported by normalized agricultural commodity input costs and integrated supply chains.',
    source: 'The Hindu BusinessLine',
    publishedAt: new Date(Date.now() - 690 * 60 * 1000).toISOString(),
    url: 'https://www.thehindubusinessline.com',
    relatedAssets: ['ITC.NS', 'NIFTYBEES.NS'],
    sentiment: 'bullish',
    impactEstimate: '+1.6% Operating Resilience',
    category: 'Consumer Staples',
    suggestedScenarioId: 'crash',
  },
  {
    id: 'news-9',
    headline: 'SEBI Enforces Rigorous Valuation and Disclosure Frameworks for Locked Real Estate and Illiquid Debt',
    summary: 'Capital markets regulator SEBI introduced tightened periodic valuation guidelines for alternative investment funds holding illiquid commercial real estate and structured debt assets to ensure transparency in retail fund redemptions.',
    source: 'Livemint',
    publishedAt: new Date(Date.now() - 840 * 60 * 1000).toISOString(),
    url: 'https://www.livemint.com/mutual-fund',
    relatedAssets: ['REALTY_LOCKED', 'REIT_LOCKED_MOCK'],
    sentiment: 'bearish',
    impactEstimate: '-2.9% Liquidity Valuation Haircut',
    category: 'Real Estate & Credit',
    suggestedScenarioId: 'crash',
  },
  {
    id: 'news-10',
    headline: 'Infosys Expands Enterprise Generative AI Platform ‘Topaz’ with Over 300 Global Engagements',
    summary: 'Infosys highlighted rapid scaling of its Topaz generative AI capabilities across global financial services and life sciences clients, unlocking productivity improvements and boosting higher-margin digital contract bookings.',
    source: 'TechCircle',
    publishedAt: new Date(Date.now() - 980 * 60 * 1000).toISOString(),
    url: 'https://www.techcircle.in',
    relatedAssets: ['INFY.NS', 'TCS.NS'],
    sentiment: 'bullish',
    impactEstimate: '+1.8% Digital Margin Expansion',
    category: 'Information Technology',
    suggestedScenarioId: 'technology',
  },
  {
    id: 'news-11',
    headline: 'Corporate Bond Spreads Compress to 3-Year Lows on Sustained Institutional Mutual Fund Liquidity',
    summary: 'Yield spreads on AAA-rated corporate debt contracted relative to government benchmarks as domestic mutual funds deployed strong debt SIP inflows into high-grade corporate bonds and short-duration liquid assets.',
    source: 'Crisil Research',
    publishedAt: new Date(Date.now() - 1140 * 60 * 1000).toISOString(),
    url: 'https://www.crisil.com',
    relatedAssets: ['CORP_BOND_FUND_MOCK', 'LIQUIDBEES.NS'],
    sentiment: 'bullish',
    impactEstimate: '+0.5% Credit Spread Carry',
    category: 'Fixed Income',
    suggestedScenarioId: 'rates',
  },
  {
    id: 'news-12',
    headline: 'Nifty 50 Navigates Intraday Swings as FIIs Rotate Capital Toward Defensive and Large-Cap Counters',
    summary: 'The benchmark Nifty 50 consolidated in a tight range as institutional investors balanced broader global macroeconomic headwinds with robust domestic retail equity participation and sound corporate balance sheets.',
    source: 'NDTV Profit',
    publishedAt: new Date(Date.now() - 1320 * 60 * 1000).toISOString(),
    url: 'https://www.ndtvprofit.com/markets',
    relatedAssets: ['NIFTYBEES.NS', 'HDFCBANK.NS', 'ITC.NS'],
    sentiment: 'neutral',
    impactEstimate: 'Market Beta Neutral',
    category: 'Equities',
    suggestedScenarioId: 'crash',
  },
];

function analyzeSentiment(text: string): 'bullish' | 'bearish' | 'neutral' {
  const lower = text.toLowerCase();
  const bearishTerms = [
    'plunge', 'drop', 'slump', 'down', 'crisis', 'inflation', 'hike', 'war',
    'fall', 'probe', 'risk', 'recession', 'miss', 'headwind', 'deficit',
    'scrutiny', 'freeze', 'slows', 'tighten', 'volatility', 'weakness', 'haircut',
  ];
  const bullishTerms = [
    'surge', 'jump', 'gain', 'growth', 'record', 'soar', 'beat', 'rally',
    'profit', 'optimism', 'expansion', 'accelerate', 'resilient', 'win',
    'upgrade', 'contract', 'deal', 'momentum', 'inflow', 'stability', 'tighten spreads',
  ];

  const bearishHits = bearishTerms.filter((word) => lower.includes(word)).length;
  const bullishHits = bullishTerms.filter((word) => lower.includes(word)).length;

  if (bearishHits > bullishHits) return 'bearish';
  if (bullishHits > bearishHits) return 'bullish';
  return 'neutral';
}

function safeArticleUrl(value?: string): string | undefined {
  if (!value) return undefined;

  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : undefined;
  } catch {
    return undefined;
  }
}

function formatPublishedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

const REFRESH_INTERVAL_SECONDS = 300;
const illustrativeUsdInr = 83.5;

export const NewsIntelligenceWidget: React.FC<NewsIntelligenceWidgetProps> = ({
  articles,
  portfolio,
  currency = 'INR',
  onNavigateToStressLab,
}) => {
  const activeArticles = useMemo(() => {
    if (articles !== undefined) {
      return articles;
    }
    return DEFAULT_NEWS_ARTICLES;
  }, [articles]);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<string>('ALL');
  const [selectedSentiment, setSelectedSentiment] = useState<'ALL' | 'bullish' | 'bearish' | 'neutral'>('ALL');
  const [userSelectedArticleId, setUserSelectedArticleId] = useState<string | null>(null);

  const [lastSyncedTime, setLastSyncedTime] = useState<number>(() => Date.now());
  const [now, setNow] = useState<number>(() => Date.now());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Available asset filters derived from active portfolio holdings or fallback to article assets
  const availableAssetFilters = useMemo(() => {
    if (portfolio?.holdings && portfolio.holdings.length > 0) {
      const tickers = portfolio.holdings.map((h) => h.ticker);
      return ['ALL', ...Array.from(new Set(tickers))];
    }
    const derived = new Set<string>();
    activeArticles.forEach((article) => {
      article.relatedAssets?.forEach((asset) => derived.add(asset));
    });
    return ['ALL', ...Array.from(derived).slice(0, 6)];
  }, [portfolio, activeArticles]);

  // Derive effective asset filter (if portfolio switched and previously selected asset is invalid, treat as ALL)
  const effectiveSelectedAsset = useMemo(() => {
    if (selectedAsset === 'ALL') return 'ALL';
    return availableAssetFilters.includes(selectedAsset) ? selectedAsset : 'ALL';
  }, [availableAssetFilters, selectedAsset]);

  // Deterministic tick interval without side-effects in state updaters
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const elapsedSeconds = Math.max(0, Math.floor((now - lastSyncedTime) / 1000));
  const secondsRemaining = Math.max(0, REFRESH_INTERVAL_SECONDS - (elapsedSeconds % REFRESH_INTERVAL_SECONDS));
  const minutesRemaining = Math.floor(secondsRemaining / 60);
  const secondsFormatted = String(secondsRemaining % 60).padStart(2, '0');

  const handleManualRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      const timestamp = Date.now();
      setLastSyncedTime(timestamp);
      setNow(timestamp);
      setIsRefreshing(false);
    }, 450);
  };

  const filteredArticles = useMemo(() => {
    return activeArticles.filter((article) => {
      // Asset filter using effectiveSelectedAsset
      if (effectiveSelectedAsset !== 'ALL') {
        const matchesAsset = article.relatedAssets?.some(
          (asset) => asset.toLowerCase() === effectiveSelectedAsset.toLowerCase()
        );
        if (!matchesAsset) return false;
      }

      // Sentiment filter
      const resolvedSentiment = article.sentiment || analyzeSentiment(`${article.headline} ${article.summary}`);
      if (selectedSentiment !== 'ALL' && resolvedSentiment !== selectedSentiment) {
        return false;
      }

      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matches =
          article.headline.toLowerCase().includes(query) ||
          article.summary.toLowerCase().includes(query) ||
          article.source.toLowerCase().includes(query) ||
          article.category?.toLowerCase().includes(query) ||
          article.relatedAssets?.some((a) => a.toLowerCase().includes(query));
        if (!matches) return false;
      }

      return true;
    });
  }, [activeArticles, effectiveSelectedAsset, selectedSentiment, searchQuery]);

  // Derive selectedArticle cleanly from filteredArticles without setState cascading side-effects
  const selectedArticle = useMemo(() => {
    if (filteredArticles.length === 0) return null;
    if (userSelectedArticleId) {
      const found = filteredArticles.find((a) => a.id === userSelectedArticleId);
      if (found) return found;
    }
    // Default to a bearish risk article if available, otherwise the first story
    return filteredArticles.find((a) => a.sentiment === 'bearish') || filteredArticles[0] || null;
  }, [filteredArticles, userSelectedArticleId]);

  const handleSelectScenario = (article: NewsArticle) => {
    setUserSelectedArticleId(article.id);
  };

  const handleCardClick = (e: React.MouseEvent, article: NewsArticle) => {
    const target = e.target as HTMLElement;
    if (target.closest('a') || target.closest('button')) {
      return;
    }
    setUserSelectedArticleId(article.id);
  };

  const handleTriggerStressSimulation = () => {
    if (!selectedArticle) return;
    const primaryAsset = selectedArticle.relatedAssets?.[0];
    const scenarioId = selectedArticle.suggestedScenarioId ?? 'crash';
    if (onNavigateToStressLab) {
      onNavigateToStressLab(selectedArticle.headline, primaryAsset, scenarioId);
    } else {
      window.location.href = `index.html?page=stresslab&scenario=${scenarioId}`;
    }
  };

  // Holding weight helper for active portfolio
  const getHoldingWeight = (ticker?: string) => {
    if (!portfolio || !ticker) return null;
    const holding = portfolio.holdings.find(
      (h) => h.ticker.toLowerCase() === ticker.toLowerCase()
    );
    return holding ? `${holding.weight.toFixed(1)}%` : null;
  };

  // Quantitative portfolio impact breakdown calculation
  const impactBreakdown = useMemo(() => {
    if (!selectedArticle || !portfolio) return null;

    const matchingHoldings = portfolio.holdings.filter((h) =>
      selectedArticle.relatedAssets?.some(
        (asset) => asset.toLowerCase() === h.ticker.toLowerCase()
      )
    );

    const totalHoldingWeightPct = matchingHoldings.reduce((sum, h) => sum + h.weight, 0);
    const totalHoldingValInr = portfolio.marketValue * (totalHoldingWeightPct / 100);

    let shockPct = 0;
    const match = selectedArticle.impactEstimate?.match(/([+-]?\d+(?:\.\d+)?)%/);
    if (match) {
      shockPct = parseFloat(match[1]);
    } else if (selectedArticle.sentiment === 'bearish') {
      shockPct = -2.5;
    } else if (selectedArticle.sentiment === 'bullish') {
      shockPct = +2.5;
    }

    const estimatedPnlInr = totalHoldingValInr * (shockPct / 100);
    const portfolioReturnPct = (totalHoldingWeightPct * shockPct) / 100;

    const formatMoney = (valInr: number) => {
      const converted = currency === 'USD' ? valInr / illustrativeUsdInr : valInr;
      return new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
      }).format(converted);
    };

    return {
      matchingHoldings,
      hasDirectExposure: matchingHoldings.length > 0,
      totalHoldingWeightPct,
      formattedExposureVal: formatMoney(totalHoldingValInr),
      estimatedPnlInr,
      formattedPnl: `${estimatedPnlInr < 0 ? '−' : '+'}${formatMoney(Math.abs(estimatedPnlInr))}`,
      portfolioReturnPct,
      shockPct,
    };
  }, [selectedArticle, portfolio, currency]);

  return (
    <section className="news-widget" aria-labelledby="news-widget-title">
      {/* Header bar with title, live sync timer, and refresh action */}
      <header className="news-widget__header">
        <div className="news-widget__title-group">
          <p className="news-widget__eyebrow">Market Intelligence & News Stream</p>
          <h2 id="news-widget-title">Portfolio News & Catalyst Signals</h2>
          <p className="news-widget__intro">
            Curated coverage and macroeconomic catalysts tracked against{' '}
            <strong>{portfolio?.name ?? 'current portfolio'}</strong> holdings.
          </p>
        </div>

        <div className="news-widget__sync-bar">
          <div className="news-widget__live-pill">
            <span className="news-widget__live-dot" aria-hidden="true" />
            <span className="news-widget__live-text">
              {elapsedSeconds < 5 ? 'LIVE • Updated just now' : `LIVE • Updated ${elapsedSeconds}s ago`}
            </span>
            <span className="news-widget__sync-timer">
              Auto-sync: <strong>{String(minutesRemaining).padStart(2, '0')}:{secondsFormatted}</strong>
            </span>
          </div>

          <button
            type="button"
            onClick={handleManualRefresh}
            className="news-widget__refresh-btn"
            disabled={isRefreshing}
            aria-label="Refresh news feed"
            title="Refresh news feed"
          >
            <span className={`news-widget__refresh-icon ${isRefreshing ? 'is-spinning' : ''}`} aria-hidden="true">
              ↻
            </span>
            <span>{isRefreshing ? 'Syncing…' : 'Refresh'}</span>
          </button>
        </div>
      </header>

      {/* Filter and Search toolbar */}
      <div className="news-widget__toolbar">
        <div className="news-widget__search-box">
          <span className="news-widget__search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search news by headline, ticker, sector, or keyword…"
            className="news-widget__search-input"
            aria-label="Search news"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="news-widget__search-clear"
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        <div className="news-widget__filters">
          <div className="news-widget__filter-group" role="group" aria-label="Filter by asset">
            <span className="news-widget__filter-label">Asset:</span>
            <div className="news-widget__chips-scroll">
              {availableAssetFilters.map((asset) => (
                <button
                  key={asset}
                  type="button"
                  onClick={() => setSelectedAsset(asset)}
                  className={`news-widget__chip ${effectiveSelectedAsset === asset ? 'is-active' : ''}`}
                  aria-pressed={effectiveSelectedAsset === asset}
                >
                  {asset === 'ALL' ? 'All Coverage' : asset}
                </button>
              ))}
            </div>
          </div>

          <div className="news-widget__filter-group" role="group" aria-label="Filter by sentiment">
            <span className="news-widget__filter-label">Sentiment:</span>
            <div className="news-widget__chips-scroll">
              {(['ALL', 'bullish', 'bearish', 'neutral'] as const).map((sent) => (
                <button
                  key={sent}
                  type="button"
                  onClick={() => setSelectedSentiment(sent)}
                  className={`news-widget__chip news-widget__chip--${sent} ${selectedSentiment === sent ? 'is-active' : ''}`}
                  aria-pressed={selectedSentiment === sent}
                >
                  {sent === 'ALL' && 'All Sentiment'}
                  {sent === 'bullish' && 'Bullish / Upside'}
                  {sent === 'bearish' && 'Bearish / Risk'}
                  {sent === 'neutral' && 'Neutral'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main layout: 2 columns on desktop (Stories feed + Active Scenario Trigger sidebar) */}
      <div className="news-widget__layout">
        {/* Left Column: News Stories Feed */}
        <div className="news-widget__feed-column">
          <div className="news-widget__feed-header">
            <span className="news-widget__count">
              Showing <strong>{filteredArticles.length}</strong> of {activeArticles.length}{' '}
              {activeArticles.length === 1 ? 'story' : 'stories'}
            </span>
            {(effectiveSelectedAsset !== 'ALL' || selectedSentiment !== 'ALL' || searchQuery) && (
              <button
                type="button"
                onClick={() => {
                  setSelectedAsset('ALL');
                  setSelectedSentiment('ALL');
                  setSearchQuery('');
                }}
                className="news-widget__reset-filters"
              >
                Reset filters
              </button>
            )}
          </div>

          {filteredArticles.length > 0 ? (
            <ol className="news-widget__list">
              {filteredArticles.map((article) => {
                const url = safeArticleUrl(article.url);
                const sentiment = article.sentiment || analyzeSentiment(`${article.headline} ${article.summary}`);
                const isSelected = selectedArticle?.id === article.id;

                return (
                  <li
                    key={article.id}
                    className={`news-widget__story-card ${isSelected ? 'is-selected' : ''}`}
                    onClick={(e) => handleCardClick(e, article)}
                    tabIndex={0}
                    role="region"
                    aria-label={article.headline}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        handleSelectScenario(article);
                      }
                    }}
                  >
                    <div className="news-widget__story-top">
                      <div className="news-widget__badges">
                        <span className={`news-widget__sentiment-badge news-widget__sentiment-badge--${sentiment}`}>
                          {sentiment === 'bullish' && '▲ Bullish / Upside'}
                          {sentiment === 'bearish' && '▼ Bearish / Risk Alert'}
                          {sentiment === 'neutral' && '◆ Neutral Exposure'}
                        </span>
                        {article.category && (
                          <span className="news-widget__category-badge">{article.category}</span>
                        )}
                        {article.impactEstimate && (
                          <span className="news-widget__impact-pill">{article.impactEstimate}</span>
                        )}
                      </div>

                      <div className="news-widget__meta">
                        <span className="news-widget__source">{article.source}</span>
                        {url && (
                          <>
                            <span className="news-widget__meta-dot">•</span>
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="news-widget__source-link"
                              title={`Read original article on ${article.source} (opens external site)`}
                              onClick={(e) => e.stopPropagation()}
                            >
                              Source ↗
                            </a>
                          </>
                        )}
                        <span className="news-widget__meta-dot">•</span>
                        <time dateTime={article.publishedAt}>
                          {formatPublishedAt(article.publishedAt)}
                        </time>
                      </div>
                    </div>

                    <h3
                      className="news-widget__story-headline"
                      onClick={() => handleSelectScenario(article)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleSelectScenario(article);
                        }
                      }}
                      title="Click to select this narrative catalyst for stress testing"
                    >
                      {article.headline}
                    </h3>

                    <p className="news-widget__summary">{article.summary}</p>

                    <div className="news-widget__story-footer">
                      {article.relatedAssets && article.relatedAssets.length > 0 && (
                        <ul className="news-widget__assets" aria-label="Related portfolio assets">
                          {article.relatedAssets.map((asset) => {
                            const weight = getHoldingWeight(asset);
                            return (
                              <li key={asset} className="news-widget__asset-tag">
                                <strong>{asset}</strong>
                                {weight && <span className="news-widget__asset-weight"> ({weight})</span>}
                              </li>
                            );
                          })}
                        </ul>
                      )}

                      <button
                        type="button"
                        onClick={() => handleSelectScenario(article)}
                        className={`news-widget__test-scenario-btn ${isSelected ? 'is-active-trigger' : ''}`}
                        aria-pressed={isSelected}
                      >
                        ⚡ {isSelected ? 'Selected as Catalyst' : 'Test Stress Scenario'}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <div className="news-widget__empty" role="status">
              <p className="news-widget__empty-title">
                {activeArticles.length === 0
                  ? 'No news articles are loaded yet'
                  : 'No matching news articles found'}
              </p>
              <p className="news-widget__empty-desc">
                {activeArticles.length === 0
                  ? 'Connect a news provider to see coverage related to your holdings.'
                  : 'No headlines match your current filters. Try searching with different terms or reset your filters.'}
              </p>
              {activeArticles.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedAsset('ALL');
                    setSelectedSentiment('ALL');
                    setSearchQuery('');
                  }}
                  className="news-widget__empty-reset"
                >
                  Clear all filters
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Active Scenario Trigger / Stress Lab Connector */}
        <aside className="news-widget__scenario-column" aria-label="Stress scenario trigger">
          <div className="news-widget__scenario-card">
            <div className="news-widget__scenario-header">
              <span className="news-widget__scenario-eyebrow">Actionable Risk Catalyst</span>
              <h3 className="news-widget__scenario-title">⚡ Active Scenario Trigger</h3>
            </div>

            {selectedArticle ? (
              <div className="news-widget__scenario-body">
                <div className="news-widget__scenario-quote">
                  <p>"{selectedArticle.headline}"</p>
                  <small>Source: {selectedArticle.source}</small>
                </div>

                <div className="news-widget__scenario-details">
                  <div className="news-widget__scenario-row">
                    <span className="news-widget__scenario-label">Primary Asset:</span>
                    <strong className="news-widget__scenario-val">
                      {selectedArticle.relatedAssets?.[0] ?? 'Broad Market Index'}
                      {getHoldingWeight(selectedArticle.relatedAssets?.[0]) && (
                        <span className="news-widget__scenario-subval">
                          {' '}(Portfolio weight: {getHoldingWeight(selectedArticle.relatedAssets?.[0])})
                        </span>
                      )}
                    </strong>
                  </div>

                  <div className="news-widget__scenario-row">
                    <span className="news-widget__scenario-label">Sentiment Signal:</span>
                    <span className={`news-widget__scenario-sentiment-tag news-widget__scenario-sentiment-tag--${selectedArticle.sentiment ?? 'neutral'}`}>
                      {selectedArticle.sentiment === 'bearish' ? 'Downside Risk / Volatility' : selectedArticle.sentiment === 'bullish' ? 'Positive Upside Catalyst' : 'Macro Neutral Drift'}
                    </span>
                  </div>

                  {impactBreakdown && (
                    <>
                      <div className="news-widget__scenario-row">
                        <span className="news-widget__scenario-label">Direct Asset Exposure:</span>
                        <strong className="news-widget__scenario-exposure">
                          {impactBreakdown.hasDirectExposure ? (
                            <>
                              {impactBreakdown.formattedExposureVal}{' '}
                              <span className="news-widget__scenario-subval">
                                ({impactBreakdown.totalHoldingWeightPct.toFixed(1)}% of portfolio)
                              </span>
                            </>
                          ) : (
                            <span className="news-widget__scenario-neutral-note">
                              No direct asset holding in current portfolio
                            </span>
                          )}
                        </strong>
                      </div>

                      <div className="news-widget__scenario-row">
                        <span className="news-widget__scenario-label">Modeled Portfolio Impact ({currency}):</span>
                        <strong className={`news-widget__scenario-impact ${impactBreakdown.estimatedPnlInr < 0 ? 'is-downside' : impactBreakdown.estimatedPnlInr > 0 ? 'is-upside' : ''}`}>
                          {impactBreakdown.hasDirectExposure ? (
                            <>
                              {impactBreakdown.formattedPnl}{' '}
                              <small>({impactBreakdown.portfolioReturnPct >= 0 ? '+' : ''}{impactBreakdown.portfolioReturnPct.toFixed(2)}% return)</small>
                            </>
                          ) : (
                            <span className="news-widget__scenario-neutral-note">
                              Indirect systemic influence ({selectedArticle.impactEstimate ?? '±0.5% drift'})
                            </span>
                          )}
                        </strong>
                      </div>
                    </>
                  )}

                  <div className="news-widget__scenario-row">
                    <span className="news-widget__scenario-label">Mapped Stress Scenario:</span>
                    <strong className="news-widget__scenario-mapped">
                      {selectedArticle.suggestedScenarioId === 'technology' && 'Technology Reset (Tech -25%)'}
                      {selectedArticle.suggestedScenarioId === 'rates' && 'Rate Shock (+200 bps)'}
                      {selectedArticle.suggestedScenarioId === 'fx' && 'Adverse FX Move (INR +15%)'}
                      {(!selectedArticle.suggestedScenarioId || selectedArticle.suggestedScenarioId === 'crash') && '2008-Style Broad Crash (-30%)'}
                    </strong>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleTriggerStressSimulation}
                  className="news-widget__launch-stresslab-btn"
                >
                  <span>⚡ Model Catalyst in Stress Lab</span>
                  <span aria-hidden="true">→</span>
                </button>
                <p className="news-widget__scenario-hint">
                  Transfers this narrative catalyst into the quantitative stress simulation lab to model VaR, drawdown, and hedge trajectories.
                </p>
              </div>
            ) : (
              <div className="news-widget__scenario-empty">
                <p>Click <strong>"⚡ Test Stress Scenario"</strong> on any news headline to assess its potential portfolio downside.</p>
              </div>
            )}
          </div>
        </aside>
      </div>

      <footer className="news-widget__disclaimer">
        <p>
          <strong>Disclaimer:</strong> Financial news headlines and sentiment signals are aggregated for risk modeling and informational simulation purposes only. They do not constitute investment advice or buy/sell recommendations.
        </p>
      </footer>
    </section>
  );
};

export default NewsIntelligenceWidget;
