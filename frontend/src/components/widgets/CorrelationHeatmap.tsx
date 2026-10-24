// /frontend/src/components/widgets/CorrelationHeatmap.tsx
import React from 'react';

/** Contract: strictly greater than 0.75 is "high correlation" (red). */
export const HIGH_CORRELATION_THRESHOLD = 0.75;

export interface CorrelationHeatmapProps {
  matrixData: {
    tickers: string[];
    matrix: number[][];
    high_correlation_warning?: string | null;
  };
}

/** Returns a tailwind class string for the cell background. */
const getHeatmapColor = (val: number): string => {
  if (val > HIGH_CORRELATION_THRESHOLD) return 'bg-rose-600 text-white';
  if (val >= 0.5) return 'bg-amber-600/80 text-white';
  if (val >= 0.2) return 'bg-slate-700 text-slate-200';
  if (val >= 0.0) return 'bg-emerald-800/60 text-emerald-200';
  return 'bg-emerald-600 text-white';
};

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({ matrixData }) => {
  const { tickers, matrix, high_correlation_warning } = matrixData;

  const isEmpty = !tickers?.length || !matrix?.length;

  return (
    <div className="flex flex-col w-full bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
        <h3 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
          Asset Correlation Heatmap
        </h3>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-600 inline-block" /> Low / negative
            (&lt;0.2)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-slate-700 inline-block" /> Moderate
            (0.2–&lt;0.5)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-600/80 inline-block" /> Elevated
            (0.5–0.75)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-600 inline-block" /> High (&gt;{HIGH_CORRELATION_THRESHOLD})
          </span>
        </div>
      </div>

      {high_correlation_warning && (
        <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{high_correlation_warning}</span>
        </div>
      )}

      {isEmpty ? (
        <p className="text-xs text-slate-500 py-6 text-center">
          No correlation data available.
        </p>
      ) : (
        <div className="overflow-x-auto pb-2">
          <div className="inline-block min-w-full align-middle">
            <table className="border-collapse table-fixed mx-auto">
              <caption className="sr-only">
                Pairwise asset correlations. Values above {HIGH_CORRELATION_THRESHOLD} are highlighted.
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="w-16 p-1 text-[11px] text-slate-400 font-medium">
                    <span className="sr-only">Asset</span>
                  </th>
                  {tickers.map((t) => (
                    <th
                      key={t}
                      scope="col"
                      className="w-16 p-1 text-[11px] font-mono font-medium text-slate-300 text-center"
                    >
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tickers.map((rowTicker, rIdx) => (
                  <tr key={rowTicker}>
                    <th
                      scope="row"
                      className="p-1 text-[11px] font-mono font-medium text-slate-300 text-right pr-2"
                    >
                      {rowTicker}
                    </th>
                    {tickers.map((_, cIdx) => {
                      const val = matrix[rIdx]?.[cIdx];
                      const hasVal =
                        typeof val === 'number' &&
                        Number.isFinite(val) &&
                        val >= -1 &&
                        val <= 1;
                      return (
                        <td key={tickers[cIdx]} className="p-1">
                          <div
                            aria-label={
                              hasVal
                                ? `${rowTicker} and ${tickers[cIdx]} correlation ${val.toFixed(2)}`
                                : `${rowTicker} and ${tickers[cIdx]} correlation unavailable`
                            }
                            title={
                              hasVal
                                ? `${rowTicker} vs ${tickers[cIdx]}: ${val.toFixed(2)}`
                                : `${rowTicker} vs ${tickers[cIdx]}: no valid correlation data`
                            }
                            className={`w-14 h-10 flex items-center justify-center rounded text-xs font-mono font-medium transition-transform hover:scale-105 hover:ring-2 hover:ring-white/40 cursor-default ${
                              hasVal ? getHeatmapColor(val) : 'bg-slate-800 text-slate-600'
                            }`}
                          >
                            {hasVal ? val.toFixed(2) : '—'}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};