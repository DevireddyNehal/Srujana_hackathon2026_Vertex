import React from 'react';
import './NewsIntelligenceWidget.css';

export interface NewsArticle {
  id: string;
  headline: string;
  summary: string;
  source: string;
  publishedAt: string;
  url?: string;
  relatedAssets?: string[];
}

export interface NewsIntelligenceWidgetProps {
  articles?: NewsArticle[];
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

export const NewsIntelligenceWidget: React.FC<NewsIntelligenceWidgetProps> = ({
  articles = [],
}) => (
  <section className="news-widget" aria-labelledby="news-widget-title">
    <header className="news-widget__header">
      <div>
        <p className="news-widget__eyebrow">Market intelligence</p>
        <h2 id="news-widget-title">Portfolio news</h2>
        <p className="news-widget__intro">
          Recent coverage related to your portfolio holdings.
        </p>
      </div>
      <span className="news-widget__count">
        {articles.length} {articles.length === 1 ? 'story' : 'stories'}
      </span>
    </header>

    {articles.length ? (
      <ol className="news-widget__list">
        {articles.map((article) => {
          const url = safeArticleUrl(article.url);
          return (
            <li className="news-widget__story" key={article.id}>
              <div className="news-widget__meta">
                <span>{article.source}</span>
                <time dateTime={article.publishedAt}>
                  {formatPublishedAt(article.publishedAt)}
                </time>
              </div>
              <h3>
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    {article.headline}
                    <span className="news-widget__sr-only"> (opens in a new tab)</span>
                  </a>
                ) : (
                  article.headline
                )}
              </h3>
              <p className="news-widget__summary">{article.summary}</p>
              {article.relatedAssets && article.relatedAssets.length > 0 && (
                <ul className="news-widget__assets" aria-label="Related assets">
                  {article.relatedAssets.map((asset) => (
                    <li key={asset}>{asset}</li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    ) : (
      <p className="news-widget__empty" role="status">
        No news articles are loaded yet. Connect a news provider to see coverage related to your
        holdings.
      </p>
    )}

    <p className="news-widget__disclaimer">
      News is for informational purposes only and is not investment advice.
    </p>
  </section>
);

export default NewsIntelligenceWidget;
