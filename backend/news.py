"""
Backend Financial News Service for Indian Markets & Macro Catalysts.
Fetches, cleans, enriches, and caches live financial news from RSS feeds (Google News / Indian Markets).
Enriches articles with sentiment, portfolio ticker mapping, scenario triggers, and impact estimates.
Provides fallback to high-conviction curated catalysts if external feeds are unavailable.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import email.utils
import hashlib
import html
import logging
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Literal


logger = logging.getLogger("srujana_f06.news")

SentimentType = Literal["bullish", "bearish", "neutral"]
ScenarioIdType = Literal["crash", "rates", "technology", "fx", "custom"]

# Cache: query_key -> (expires_at_timestamp, articles_list)
_NEWS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

CURATED_CATALYSTS: list[dict[str, Any]] = [
    {
        "id": "curated-1",
        "headline": "RBI Maintains Repo Rate at 6.50% Amid Lingering Food Price Pressures and Global Inflation Risks",
        "summary": "The Reserve Bank of India Monetary Policy Committee voted to keep benchmark repo rates unchanged at 6.50%, reiterating its stance of withdrawal of accommodation. Governor highlighted persistent volatility in vegetable and food prices while pointing to steady domestic GDP growth.",
        "source": "Bloomberg / Mint",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=35)).isoformat(),
        "url": "https://www.livemint.com/economy",
        "relatedAssets": ["GSEC10Y_MOCK", "CORP_BOND_FUND_MOCK", "LIQUIDBEES.NS"],
        "sentiment": "neutral",
        "impactEstimate": "+0.12% Yield Stability",
        "category": "Macro & Policy",
        "suggestedScenarioId": "rates",
        "isLive": False,
    },
    {
        "id": "curated-2",
        "headline": "TCS Secures $1.2B Enterprise Cloud & AI Modernization Contract with European Telecom Leader",
        "summary": "Tata Consultancy Services announced a multi-year digital transformation mandate to overhaul IT core infrastructure, migrate workloads to hybrid cloud platforms, and implement generative AI governance workflows across customer service centers.",
        "source": "Economic Times",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=75)).isoformat(),
        "url": "https://economictimes.indiatimes.com/tech",
        "relatedAssets": ["TCS.NS", "USD_INR"],
        "sentiment": "bullish",
        "impactEstimate": "+2.4% Revenue Growth",
        "category": "Information Technology",
        "suggestedScenarioId": "technology",
        "isLive": False,
    },
    {
        "id": "curated-3",
        "headline": "US Enterprise Tech Budgets Tighten as CFOs Extend Approval Cycles for Discretionary Cloud Projects",
        "summary": "Industry survey indicates North American Fortune 500 corporations are delaying non-critical digital transformation renewals, creating near-term revenue visibility headwinds for tier-1 Indian software service exporters.",
        "source": "Reuters Financial",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=140)).isoformat(),
        "url": "https://www.reuters.com/technology",
        "relatedAssets": ["TCS.NS", "INFY.NS", "USD_INR"],
        "sentiment": "bearish",
        "impactEstimate": "-2.8% IT Margin Scrutiny",
        "category": "Information Technology",
        "suggestedScenarioId": "technology",
        "isLive": False,
    },
    {
        "id": "curated-4",
        "headline": "HDFC Bank Deposits Expand 18.2% YoY, Narrowing Credit-to-Deposit Gap Across Retail Branches",
        "summary": "Private banking heavyweight HDFC Bank reported strong sequential growth in low-cost CASA deposits, alleviating investor concerns regarding wholesale funding costs and stabilizing net interest margins.",
        "source": "Business Standard",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=210)).isoformat(),
        "url": "https://www.business-standard.com/finance",
        "relatedAssets": ["HDFCBANK.NS", "NIFTYBEES.NS"],
        "sentiment": "bullish",
        "impactEstimate": "+1.9% NIM Support",
        "category": "Banking & Financials",
        "suggestedScenarioId": "crash",
        "isLive": False,
    },
    {
        "id": "curated-5",
        "headline": "India 10-Year Benchmark G-Sec Yield Tests 7.18% Following US Treasury Sell-Off and Crude Oil Rebound",
        "summary": "Domestic sovereign debt yields edged higher tracking elevated US 10-year Treasury yields above 4.35%. Bond dealers noted institutional caution ahead of upcoming government bond auctions and weekly liquidity deficits.",
        "source": "Financial Express",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=320)).isoformat(),
        "url": "https://www.financialexpress.com/market",
        "relatedAssets": ["GSEC10Y_MOCK", "CORP_BOND_FUND_MOCK"],
        "sentiment": "bearish",
        "impactEstimate": "-0.7% Duration Mark-to-Market",
        "category": "Fixed Income",
        "suggestedScenarioId": "rates",
        "isLive": False,
    },
    {
        "id": "curated-6",
        "headline": "Domestic Gold Prices Surge Past ₹72,500/10g on Geopolitical Safe-Haven Bids and Central Bank Reserves",
        "summary": "Spot and futures gold contracts touched fresh highs in Mumbai and Delhi bullion markets as geopolitical frictions along key shipping lanes accelerated portfolio hedging demand from institutional and retail asset allocators.",
        "source": "Moneycontrol",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=430)).isoformat(),
        "url": "https://www.moneycontrol.com/commodity",
        "relatedAssets": ["GOLDBEES.NS"],
        "sentiment": "bullish",
        "impactEstimate": "+3.5% Hedge Outperformance",
        "category": "Commodities",
        "suggestedScenarioId": "crash",
        "isLive": False,
    },
    {
        "id": "curated-7",
        "headline": "Indian Rupee Stabilizes Near 83.42 Against USD as RBI Active Liquidity Operations Check Volatility",
        "summary": "The central bank maintained active interventions in non-deliverable forward markets and onshore spot desks, curbing speculative pressure on the rupee despite dollar strength and foreign institutional rebalancing outflows.",
        "source": "CNBC-TV18",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=560)).isoformat(),
        "url": "https://www.cnbctv18.com/market",
        "relatedAssets": ["USD_INR", "TCS.NS", "INFY.NS"],
        "sentiment": "neutral",
        "impactEstimate": "FX Volatility Dampened",
        "category": "Forex & Currencies",
        "suggestedScenarioId": "fx",
        "isLive": False,
    },
    {
        "id": "curated-8",
        "headline": "ITC Highlights Non-Cigarette FMCG Margin Expansion and Robust Rural Demand Signals",
        "summary": "Consumer goods bellwether ITC reported resilient rural volume traction across packaged foods and personal care divisions, supported by normalized agricultural commodity input costs and integrated supply chains.",
        "source": "The Hindu BusinessLine",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=690)).isoformat(),
        "url": "https://www.thehindubusinessline.com",
        "relatedAssets": ["ITC.NS", "NIFTYBEES.NS"],
        "sentiment": "bullish",
        "impactEstimate": "+1.6% Operating Resilience",
        "category": "Consumer Staples",
        "suggestedScenarioId": "crash",
        "isLive": False,
    },
    {
        "id": "curated-9",
        "headline": "SEBI Enforces Rigorous Valuation and Disclosure Frameworks for Locked Real Estate and Illiquid Debt",
        "summary": "Capital markets regulator SEBI introduced tightened periodic valuation guidelines for alternative investment funds holding illiquid commercial real estate and structured debt assets to ensure transparency in retail fund redemptions.",
        "source": "Livemint",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=840)).isoformat(),
        "url": "https://www.livemint.com/mutual-fund",
        "relatedAssets": ["CORP_BOND_FUND_MOCK", "LIQUIDBEES.NS"],
        "sentiment": "bearish",
        "impactEstimate": "-2.9% Liquidity Valuation Haircut",
        "category": "Credit & Compliance",
        "suggestedScenarioId": "crash",
        "isLive": False,
    },
    {
        "id": "curated-10",
        "headline": "Infosys Expands Enterprise Generative AI Platform ‘Topaz’ with Over 300 Global Engagements",
        "summary": "Infosys highlighted rapid scaling of its Topaz generative AI capabilities across global financial services and life sciences clients, unlocking productivity improvements and boosting higher-margin digital contract bookings.",
        "source": "TechCircle",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=980)).isoformat(),
        "url": "https://www.techcircle.in",
        "relatedAssets": ["INFY.NS", "TCS.NS"],
        "sentiment": "bullish",
        "impactEstimate": "+1.8% Digital Margin Expansion",
        "category": "Information Technology",
        "suggestedScenarioId": "technology",
        "isLive": False,
    },
    {
        "id": "curated-11",
        "headline": "Corporate Bond Spreads Compress to 3-Year Lows on Sustained Institutional Mutual Fund Liquidity",
        "summary": "Yield spreads on AAA-rated corporate debt contracted relative to government benchmarks as domestic mutual funds deployed strong debt SIP inflows into high-grade corporate bonds and short-duration liquid assets.",
        "source": "Crisil Research",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1140)).isoformat(),
        "url": "https://www.crisil.com",
        "relatedAssets": ["CORP_BOND_FUND_MOCK", "LIQUIDBEES.NS"],
        "sentiment": "bullish",
        "impactEstimate": "+0.5% Credit Spread Carry",
        "category": "Fixed Income",
        "suggestedScenarioId": "rates",
        "isLive": False,
    },
    {
        "id": "curated-12",
        "headline": "Nifty 50 Navigates Intraday Swings as FIIs Rotate Capital Toward Defensive and Large-Cap Counters",
        "summary": "The benchmark Nifty 50 consolidated in a tight range as institutional investors balanced broader global macroeconomic headwinds with robust domestic retail equity participation and sound corporate balance sheets.",
        "source": "NDTV Profit",
        "publishedAt": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1320)).isoformat(),
        "url": "https://www.ndtvprofit.com/markets",
        "relatedAssets": ["NIFTYBEES.NS", "HDFCBANK.NS", "ITC.NS"],
        "sentiment": "neutral",
        "impactEstimate": "Market Beta Neutral",
        "category": "Equities",
        "suggestedScenarioId": "crash",
        "isLive": False,
    },
]


def clean_html(raw_html: str) -> str:
    """Strip HTML markup and unescape XML/HTML character entities."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return " ".join(text.split())


def analyze_article_sentiment(text: str) -> SentimentType:
    """Analyze sentiment using a specialized Indian market financial lexicon."""
    lower = text.lower()
    bearish_terms = [
        "plunge", "drop", "slump", "down", "crisis", "inflation", "hike", "war",
        "fall", "probe", "risk", "recession", "miss", "headwind", "deficit",
        "scrutiny", "freeze", "slows", "tighten", "volatility", "weakness",
        "haircut", "selloff", "sell-off", "decline", "tumble", "cautions",
        "losses", "npa", "penalty", "default", "bearish", "downgrade"
    ]
    bullish_terms = [
        "surge", "jump", "gain", "growth", "record", "soar", "beat", "rally",
        "profit", "optimism", "expansion", "accelerate", "resilient", "win",
        "upgrade", "contract", "deal", "momentum", "inflow", "stability",
        "rebound", "bullish", "dividend", "order", "acquisition", "robust"
    ]

    bearish_hits = sum(1 for w in bearish_terms if w in lower)
    bullish_hits = sum(1 for w in bullish_terms if w in lower)

    if bearish_hits > bullish_hits:
        return "bearish"
    if bullish_hits > bearish_hits:
        return "bullish"
    return "neutral"


def map_related_assets(text: str) -> list[str]:
    """Identify which portfolio holdings or proxies are affected by the article."""
    lower = text.lower()
    assets: list[str] = []

    if any(k in lower for k in ["tcs", "tata consultancy"]):
        assets.append("TCS.NS")
    if any(k in lower for k in ["infosys", "infy"]):
        assets.append("INFY.NS")
    if any(k in lower for k in ["hdfc", "banking", "bank", "icici", "sbi", "credit", "lending", "casa", "npa"]):
        assets.append("HDFCBANK.NS")
    if any(k in lower for k in ["itc", "fmcg", "cigarette", "rural consumption"]):
        assets.append("ITC.NS")
    if any(k in lower for k in ["gold", "bullion", "precious metal", "mcx gold"]):
        assets.append("GOLDBEES.NS")
    if any(k in lower for k in ["g-sec", "gsec", "government bond", "10-year yield", "sovereign yield", "treasury"]):
        assets.append("GSEC10Y_MOCK")
    if any(k in lower for k in ["corporate bond", "credit spread", "debt fund", "aaa bond"]):
        assets.append("CORP_BOND_FUND_MOCK")
    if any(k in lower for k in ["liquid", "money market", "repo rate", "liquidity deficit", "overnight"]):
        assets.append("LIQUIDBEES.NS")
    if any(k in lower for k in ["rupee", "usd", "dollar", "forex", "fx", "currency"]):
        assets.append("USD_INR")
    if any(k in lower for k in ["nifty", "sensex", "market", "dalal street", "fii", "dii", "sebi"]):
        assets.append("NIFTYBEES.NS")

    if not assets:
        assets.append("NIFTYBEES.NS")

    # Return deduplicated asset list
    return list(dict.fromkeys(assets))


def determine_scenario_and_category(text: str, related_assets: list[str]) -> tuple[ScenarioIdType, str, str]:
    """
    Returns (suggestedScenarioId, category, impactEstimate).
    """
    lower = text.lower()

    if any(k in lower for k in ["rbi", "repo", "interest rate", "inflation", "g-sec", "yield", "bond", "monetary policy"]):
        scenario: ScenarioIdType = "rates"
        category = "Macro & Policy" if "rbi" in lower or "inflation" in lower else "Fixed Income"
        impact = "-0.7% Duration MTM" if "hike" in lower or "surge" in lower else "+0.2% Yield Carry"
        return scenario, category, impact

    if any(k in lower for k in ["tcs", "infosys", "tech", "cloud", "ai", "software", "it ", "digital"]):
        scenario = "technology"
        category = "Information Technology"
        impact = "+2.2% Tech Momentum" if any(w in lower for w in ["deal", "win", "cloud", "ai", "surge", "gain"]) else "-2.5% IT Budget Scrutiny"
        return scenario, category, impact

    if any(k in lower for k in ["rupee", "forex", "fx", "dollar", "usd/inr", "depreciation"]):
        scenario = "fx"
        category = "Forex & Currencies"
        impact = "FX Volatility Dampened" if "stabiliz" in lower else "+1.4% Exporter Tailwind"
        return scenario, category, impact

    if any(k in lower for k in ["gold", "bullion", "safe haven"]):
        scenario = "crash"
        category = "Commodities"
        impact = "+3.1% Hedge Outperformance"
        return scenario, category, impact

    if any(k in lower for k in ["hdfc", "bank", "credit", "lending", "npa"]):
        scenario = "crash"
        category = "Banking & Financials"
        impact = "+1.8% NIM Support" if "deposit" in lower or "growth" in lower else "-1.6% Credit Risk Review"
        return scenario, category, impact

    if any(k in lower for k in ["crash", "plunge", "bear", "crisis", "panic", "sell-off", "war", "recession", "risk"]):
        scenario = "crash"
        category = "Equities"
        impact = "-3.4% Beta Retracement"
        return scenario, category, impact

    return "crash", "Equities", "Market Beta Neutral"


def extract_headline_tokens(title: str) -> set[str]:
    """Extract significant lowercase word tokens ignoring common stopwords."""
    stopwords = {
        "the", "a", "an", "in", "on", "at", "of", "for", "to", "and", "or", "is", "are",
        "was", "were", "by", "with", "from", "as", "its", "how", "what", "why", "who",
        "when", "where", "after", "before", "into", "over", "than", "more", "about", "all",
        "today", "market", "indian", "india"
    }
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return {w for w in words if len(w) > 2 and w not in stopwords}


def is_narrative_duplicate(headline: str, seen_token_sets: list[set[str]]) -> bool:
    """Detect if this headline covers an event that has already been reported in this batch."""
    tokens = extract_headline_tokens(headline)
    if not tokens:
        return False
    for seen in seen_token_sets:
        intersection = tokens.intersection(seen)
        union = tokens.union(seen)
        if len(union) > 0 and (len(intersection) / len(union)) > 0.38:
            return True
        if len(intersection) >= 3 and len(intersection) / min(len(tokens), len(seen)) > 0.55:
            return True
    return False


def parse_rss_xml(
    xml_content: bytes,
    max_items: int = 25,
    override_category: str | None = None,
    seen_token_sets: list[set[str]] | None = None,
) -> list[dict[str, Any]]:
    """Parse RSS 2.0 XML bytes and construct structured NewsArticle objects with deduplication."""
    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except Exception:
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    items = channel.findall("item")
    articles: list[dict[str, Any]] = []

    for item in items:
        if len(articles) >= max_items:
            break

        raw_title = clean_html(item.findtext("title") or "")
        raw_desc = clean_html(item.findtext("description") or "")
        link = item.findtext("link") or ""
        pub_str = item.findtext("pubDate") or ""
        source = clean_html(item.findtext("source") or "")

        if not raw_title:
            continue

        # Split trailing source if title ends with ' - Source'
        if source and raw_title.endswith(f" - {source}"):
            headline = raw_title[:-len(f" - {source}")].strip()
        elif " - " in raw_title:
            parts = raw_title.rsplit(" - ", 1)
            headline = parts[0].strip()
            if not source:
                source = parts[1].strip()
        else:
            headline = raw_title

        if not source:
            source = "Financial Markets Wire"

        # Check narrative event duplication
        if seen_token_sets is not None:
            if is_narrative_duplicate(headline, seen_token_sets):
                continue
            seen_token_sets.append(extract_headline_tokens(headline))

        # Parse publication date to ISO 8601
        published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if pub_str:
            try:
                dt = email.utils.parsedate_to_datetime(pub_str)
                published_at = dt.isoformat()
            except Exception:
                pass

        # Text combination for NLP
        full_text = f"{headline} {raw_desc}"
        sentiment = analyze_article_sentiment(full_text)
        related_assets = map_related_assets(full_text)
        suggested_scenario, category, impact_estimate = determine_scenario_and_category(full_text, related_assets)

        if override_category:
            category = override_category

        # Unique reproducible ID
        article_id = "live-" + hashlib.md5(headline.encode("utf-8")).hexdigest()[:10]
        summary = raw_desc if len(raw_desc) > 30 else headline

        articles.append({
            "id": article_id,
            "headline": headline,
            "summary": summary,
            "source": source,
            "publishedAt": published_at,
            "url": link,
            "relatedAssets": related_assets,
            "sentiment": sentiment,
            "impactEstimate": impact_estimate,
            "category": category,
            "suggestedScenarioId": suggested_scenario,
            "isLive": True,
        })

    return articles


def _fetch_single_rss_bytes(feed_url: str, timeout: float = 3.5) -> bytes:
    """Fetch raw bytes from RSS URL with realistic browser headers."""
    req = urllib.request.Request(
        feed_url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


# Seven core institutional market pillars representing the full multi-asset portfolio landscape
MARKET_PILLARS: list[tuple[str, str]] = [
    ("Equities", "Indian stock market Nifty Sensex large cap"),
    ("Information Technology", "TCS OR Infosys OR Indian IT tech stocks AI cloud"),
    ("Banking & Financials", "HDFC Bank OR Indian banking credit deposits CASA"),
    ("Commodities", "Gold price India bullion MCX safe haven"),
    ("Forex & Currencies", "Rupee USD exchange rate India foreign exchange"),
    ("Fixed Income", "India 10 year government bond yield G-Sec corporate bond"),
    ("Macro & Policy", "RBI monetary policy repo rate India GDP inflation CPI"),
]


def fetch_live_market_news(
    query: str | None = None,
    asset: str | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """
    Fetch live financial market news.
    Uses in-memory cache (300s TTL).
    Employs multi-pillar concurrent RSS sourcing and token similarity deduplication to ensure
    broad, diverse market coverage (Equities, IT, Banking, Commodities, Forex, Bonds, Macro)
    instead of clustering on repetitive headlines.
    Falls back gracefully to curated catalysts if the network or external feed fails.
    """
    now = time.time()
    cache_key = f"{query or ''}:{asset or ''}:{limit}"

    # Return cached data if still fresh
    if cache_key in _NEWS_CACHE:
        expires_at, cached_data = _NEWS_CACHE[cache_key]
        if now < expires_at:
            logger.debug("Serving market news from in-memory cache (%d items)", len(cached_data))
            return cached_data

    seen_tokens: list[set[str]] = []
    live_articles: list[dict[str, Any]] = []

    # Case 1: User requested a specific targeted query or single asset
    if query or (asset and asset != "ALL"):
        search_terms: list[str] = []
        if query:
            search_terms.append(query)
        if asset and asset != "ALL":
            asset_map = {
                "TCS.NS": "TCS",
                "INFY.NS": "Infosys",
                "HDFCBANK.NS": "HDFC Bank",
                "ITC.NS": "ITC",
                "GOLDBEES.NS": "Gold bullion",
                "GSEC10Y_MOCK": "India 10 year bond yield",
                "CORP_BOND_FUND_MOCK": "Corporate bonds India",
                "LIQUIDBEES.NS": "RBI repo rate liquidity",
                "USD_INR": "Rupee USD exchange rate",
                "NIFTYBEES.NS": "Nifty 50 Sensex",
            }
            search_terms.append(asset_map.get(asset, asset))

        rss_query = f"{' '.join(search_terms)} Indian market"
        encoded_query = urllib.parse.quote(rss_query)
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            xml_bytes = _fetch_single_rss_bytes(feed_url, timeout=3.5)
            live_articles = parse_rss_xml(xml_bytes, max_items=limit, seen_token_sets=seen_tokens)
        except Exception as exc:
            logger.warning("Targeted news RSS fetch failed (%s); falling back to curated catalysts", exc)

    # Case 2: General portfolio market intelligence feed — Multi-pillar diverse sourcing
    else:
        def fetch_pillar(pillar: tuple[str, str]) -> tuple[str, bytes]:
            cat, q = pillar
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
            try:
                content = _fetch_single_rss_bytes(url, timeout=3.0)
                return cat, content
            except Exception as e:
                logger.debug("Pillar '%s' fetch failed: %s", cat, e)
                return cat, b""

        pillar_buckets: dict[str, list[dict[str, Any]]] = {p[0]: [] for p in MARKET_PILLARS}
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
                results = list(executor.map(fetch_pillar, MARKET_PILLARS))

            for category, xml_bytes in results:
                if not xml_bytes:
                    continue
                parsed = parse_rss_xml(
                    xml_bytes,
                    max_items=4,
                    override_category=category,
                    seen_token_sets=seen_tokens,
                )
                pillar_buckets[category].extend(parsed)

            # Interleave / round-robin across pillars for maximum thematic diversity
            max_depth = max(len(b) for b in pillar_buckets.values()) if pillar_buckets else 0
            for depth in range(max_depth):
                for cat in pillar_buckets:
                    if depth < len(pillar_buckets[cat]):
                        live_articles.append(pillar_buckets[cat][depth])
        except Exception as exc:
            logger.warning("Multi-pillar news RSS fetch failed (%s); falling back to curated catalysts", exc)

    # Combine with curated catalysts if live feed returned fewer than limit
    combined: list[dict[str, Any]] = []
    if live_articles:
        combined = live_articles
        if len(combined) < limit:
            for c in CURATED_CATALYSTS:
                if len(combined) >= limit:
                    break
                # Only add curated item if its narrative isn't already covered in live feed
                if not is_narrative_duplicate(c["headline"], seen_tokens):
                    seen_tokens.append(extract_headline_tokens(c["headline"]))
                    combined.append(c)
    else:
        combined = list(CURATED_CATALYSTS)

    # Optional post-filter by asset if specified
    if asset and asset != "ALL":
        filtered = [
            a for a in combined
            if any(a_asset.lower() == asset.lower() for a_asset in a.get("relatedAssets", []))
        ]
        if filtered:
            combined = filtered

    results = combined[:limit]

    # Store in cache
    _NEWS_CACHE[cache_key] = (now + CACHE_TTL_SECONDS, results)
    return results

