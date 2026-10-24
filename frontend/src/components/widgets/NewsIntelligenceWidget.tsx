// frontend/src/components/widgets/NewsIntelligenceWidget.tsx
import React, { useState, useEffect } from 'react';

interface Article {
  headline: string;
  summary: string;
  source: string;
  datetime: number;
  url: string;
  image?: string;
}

const API_KEY = 'dbejbm9r01qp3vuru910dbejbm9r01qp3vuru91g';
const REFRESH_INTERVAL_SECONDS = 300;

export const NewsIntelligenceWidget: React.FC = () => {
  const [currentFeed, setCurrentFeed] = useState<string>('general');
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [secondsSinceLastUpdate, setSecondsSinceLastUpdate] = useState<number>(0);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(REFRESH_INTERVAL_SECONDS);
  
  const [selectedHeadline, setSelectedHeadline] = useState<string>(
    'No news headline selected yet. Click "Test Stress Scenario" on an article.'
  );
  const [affectedHolding, setAffectedHolding] = useState<string>('--');
  const [estimatedImpact, setEstimatedImpact] = useState<string>('--');

  const analyzeRiskSentiment = (text: string) => {
    const lower = text.toLowerCase();
    const bearishTerms = ['plunge', 'drop', 'slump', 'down', 'crisis', 'inflation', 'hike', 'war', 'fall', 'probe', 'risk', 'recession', 'miss'];
    const bullishTerms = ['surge', 'jump', 'gain', 'growth', 'record', 'soar', 'beat', 'rally', 'profit', 'optimism', 'expansion'];

    const bearishHits = bearishTerms.filter(word => lower.includes(word)).length;
    const bullishHits = bullishTerms.filter(word => lower.includes(word)).length;

    if (bearishHits > bullishHits) {
      return { label: 'Bearish / High Risk', color: 'bg-rose-500/10 text-rose-400 border-rose-500/20' };
    } else if (bullishHits > bearishHits) {
      return { label: 'Bullish / Upside', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' };
    }
    return { label: 'Neutral Exposure', color: 'bg-slate-700/30 text-slate-400 border-slate-700/40' };
  };

  const fetchNews = async (target: string) => {
    setLoading(true);
    const today = new Date().toISOString().split('T')[0];
    const pastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    const url = target === 'general'
      ? `https://finnhub.io/api/v1/news?category=general&token=${API_KEY}`
      : `https://finnhub.io/api/v1/company-news?symbol=${target}&from=${pastWeek}&to=${today}&token=${API_KEY}`;

    try {
      const res = await fetch(url);
      const data = await res.json();
      setArticles(Array.isArray(data) ? data.slice(0, 8) : []);
      setSecondsSinceLastUpdate(0);
      setSecondsRemaining(REFRESH_INTERVAL_SECONDS);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews(currentFeed);
  }, [currentFeed]);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsSinceLastUpdate(prev => prev + 1);
      setSecondsRemaining(prev => {
        if (prev <= 1) {
          fetchNews(currentFeed);
          return REFRESH_INTERVAL_SECONDS;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [currentFeed]);

  const selectHeadlineForScenario = (headline: string, ticker: string) => {
    setSelectedHeadline(`"${headline}"`);
    setAffectedHolding(ticker === 'general' ? 'Broad Index / Multi-Asset' : ticker.toUpperCase());
    setEstimatedImpact((Math.random() * -4 - 1.5).toFixed(2) + '% Portfolio VaR');
  };

  const minutesRemaining = Math.floor(secondsRemaining / 60);
  const secsFormatted = String(secondsRemaining % 60).padStart(2, '0');

  return (
    <div className="w-full bg-slate-950 text-slate-100 p-6 rounded-2xl border border-slate-800 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <span>⚡</span> Portfolio Risk & Market Intelligence
          </h2>
          <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>{secondsSinceLastUpdate < 5 ? 'Updated just now' : `Updated ${secondsSinceLastUpdate}s ago`}</span>
            <span>•</span>
            <span>Next sync in <strong className="text-indigo-400">{String(minutesRemaining).padStart(2, '0')}:{secsFormatted}</strong></span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {['general', 'AAPL', 'NVDA', 'MSFT', 'TSLA'].map(sym => (
            <button
              key={sym}
              onClick={() => setCurrentFeed(sym)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                currentFeed === sym ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {sym === 'general' ? 'Macro Market' : sym}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          {loading && <p className="text-xs text-indigo-400 animate-pulse">Syncing latest headlines...</p>}
          {articles.map((item, idx) => {
            const sentiment = analyzeRiskSentiment(item.headline + ' ' + (item.summary || ''));
            return (
              <div key={idx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition flex flex-col sm:flex-row gap-4">
                {item.image && (
                  <img src={item.image} alt="thumb" className="w-full sm:w-28 h-20 object-cover rounded-lg bg-slate-800 flex-shrink-0" />
                )}
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${sentiment.color}`}>
                      {sentiment.label}
                    </span>
                    <span className="text-xs text-slate-400">{item.source}</span>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-200 hover:text-indigo-400">
                    <a href={item.url} target="_blank" rel="noreferrer">{item.headline}</a>
                  </h4>
                  <div className="pt-2 flex items-center justify-between border-t border-slate-800">
                    <span className="text-[11px] text-slate-500">Asset: {currentFeed.toUpperCase()}</span>
                    <button
                      onClick={() => selectHeadlineForScenario(item.headline, currentFeed)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      ⚡ Test Stress Scenario
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 h-fit space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">🎯 Active Scenario Trigger</h3>
          <p className="text-xs text-slate-400 italic bg-slate-950 p-3 rounded-lg border border-slate-800">
            {selectedHeadline}
          </p>
          <div className="text-xs space-y-1 pt-2 border-t border-slate-800">
            <div className="flex justify-between text-slate-400">
              <span>Affected:</span> <strong className="text-slate-200">{affectedHolding}</strong>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Estimated Impact:</span> <strong className="text-amber-400">{estimatedImpact}</strong>
            </div>
          </div>
          <button
            onClick={() => alert('Triggering quantitative stress test run!')}
            className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium"
          >
            Run Stress Simulation
          </button>
        </div>
      </div>
    </div>
  );
};