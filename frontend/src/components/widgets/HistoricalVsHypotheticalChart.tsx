import React, { useMemo } from 'react';

export type ChartDataPoint =
  | { date: string; value: number }
  | { month: string; actual_value: number };

export type ProjectionConePoint = {
  p10_worst_case: number;
  p50_median_case: number;
  p90_best_case: number;
  rebalanced_p50?: number;
} & ({ date: string } | { month: string });

export interface HistoricalVsHypotheticalChartProps {
  data: {
    historical_observations: ChartDataPoint[];
    hypothetical_projection_cone: ProjectionConePoint[];
    disclaimer: string;
  };
}

const chartWidth = 800;
const chartHeight = 360;
const padding = { top: 20, right: 30, bottom: 64, left: 88 };
const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const getHistoricalValue = (point: ChartDataPoint) =>
  'value' in point ? point.value : point.actual_value;

const getPointDate = (point: { date: string } | { month: string }) =>
  'date' in point ? point.date : point.month;

export const HistoricalVsHypotheticalChart: React.FC<HistoricalVsHypotheticalChartProps> = ({
  data,
}) => {
  const { historical_observations, hypothetical_projection_cone, disclaimer } = data;
  const chart = useMemo(() => {
    const history = historical_observations
      .filter((point) => Number.isFinite(getHistoricalValue(point)))
      .map((point) => ({
        date: getPointDate(point),
        value: getHistoricalValue(point),
      }));

    const projections = hypothetical_projection_cone
      .filter(
        (point) =>
          Number.isFinite(point.p10_worst_case) &&
          Number.isFinite(point.p50_median_case) &&
          Number.isFinite(point.p90_best_case) &&
          (point.rebalanced_p50 === undefined || Number.isFinite(point.rebalanced_p50))
      )
      .map((point) => ({
        ...point,
        date: getPointDate(point),
      }));

    const values = [
      ...history.map((point) => point.value),
      ...projections.flatMap((point) => [
        point.p10_worst_case,
        point.p50_median_case,
        point.p90_best_case,
        ...(point.rebalanced_p50 === undefined ? [] : [point.rebalanced_p50]),
      ]),
    ];
    const minVal = values.length ? Math.min(...values) : 0;
    const maxVal = values.length ? Math.max(...values) : 1;
    const valRange = maxVal - minVal || Math.max(Math.abs(maxVal) * 0.1, 1);
    const chartW = chartWidth - padding.left - padding.right;
    const chartH = chartHeight - padding.top - padding.bottom;
    const totalPoints = history.length + projections.length;
    const getX = (index: number) =>
      padding.left + (index / Math.max(totalPoints - 1, 1)) * chartW;
    const getY = (value: number) =>
      padding.top + chartH - ((value - minVal) / valRange) * chartH;

    const historicalCoords = history.map((point, index) => ({
      ...point,
      x: getX(index),
      y: getY(point.value),
    }));
    const projectionCoords = projections.map((point, index) => ({
      ...point,
      x: getX(history.length + index),
      yP10: getY(point.p10_worst_case),
      yP50: getY(point.p50_median_case),
      yP90: getY(point.p90_best_case),
      yRebalanced:
        point.rebalanced_p50 === undefined ? undefined : getY(point.rebalanced_p50),
    }));

    return { minVal, maxVal, historicalCoords, projectionCoords, totalPoints };
  }, [historical_observations, hypothetical_projection_cone]);

  const { minVal, maxVal, historicalCoords, projectionCoords, totalPoints } = chart;
  const lastHistorical = historicalCoords[historicalCoords.length - 1];
  const hasChartData = historicalCoords.length > 0 || projectionCoords.length > 0;
  const historicalPath = historicalCoords
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ');
  const conePath = projectionCoords.length
    ? [
        `M ${lastHistorical?.x ?? projectionCoords[0].x} ${
          lastHistorical?.y ?? projectionCoords[0].yP50
        }`,
        ...projectionCoords.map((point) => `L ${point.x} ${point.yP90}`),
        ...projectionCoords
          .slice()
          .reverse()
          .map((point) => `L ${point.x} ${point.yP10}`),
        'Z',
      ].join(' ')
    : '';
  const medianPath = projectionCoords
    .map((point, index) => {
      const start =
        index === 0 && lastHistorical
          ? `M ${lastHistorical.x} ${lastHistorical.y} L`
          : index === 0
            ? 'M'
            : 'L';
      return `${start} ${point.x} ${point.yP50}`;
    })
    .join(' ');

  const rebalancedSegments: string[] = [];
  let isDrawing = false;
  for (const point of projectionCoords) {
    if (point.yRebalanced === undefined) {
      isDrawing = false;
    } else {
      rebalancedSegments.push(`${isDrawing ? 'L' : 'M'} ${point.x} ${point.yRebalanced}`);
      isDrawing = true;
    }
  }
  const rebalancedPath = rebalancedSegments.join(' ');

  const dateTicks = [
    ...historicalCoords.map((point) => ({ x: point.x, date: point.date })),
    ...projectionCoords.map((point) => ({ x: point.x, date: point.date })),
  ];
  const dateTickStep = Math.max(1, Math.ceil(dateTicks.length / 6));

  return (
    <section
      aria-labelledby="historical-projection-heading"
      className="flex flex-col w-full bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-slate-800 mb-4">
        <h2
          id="historical-projection-heading"
          className="text-sm font-semibold tracking-wide text-slate-100 uppercase"
        >
          Historical observations vs hypothetical projection
        </h2>
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-blue-400 rounded-full inline-block" /> Historical
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-amber-500/20 border border-amber-500/40 rounded-sm inline-block" />{' '}
            Hypothetical range (P10–P90)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-amber-400 inline-block border-t border-dashed" /> P50
            scenario
          </span>
          {rebalancedPath && (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-400 inline-block border-t border-dashed" />{' '}
              Alternative allocation
            </span>
          )}
        </div>
      </div>

      {hasChartData ? (
        <div className="relative w-full overflow-x-auto">
          <svg
            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            className="w-full min-w-[600px] h-auto select-none"
            role="img"
            aria-label="Portfolio historical observations and hypothetical projection ranges"
          >
            {[0, 0.25, 0.5, 0.75, 1].map((percent) => {
              const y =
                padding.top +
                (chartHeight - padding.top - padding.bottom) * percent;
              const value = maxVal - percent * (maxVal - minVal);
              return (
                <g key={percent}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={chartWidth - padding.right}
                    y2={y}
                    stroke="#334155"
                    strokeDasharray="3 3"
                  />
                  <text
                    x={padding.left - 8}
                    y={y + 4}
                    textAnchor="end"
                    fill="#94a3b8"
                    fontSize="10"
                  >
                    {currencyFormatter.format(value)}
                  </text>
                </g>
              );
            })}

            {lastHistorical && (
              <line
                x1={lastHistorical.x}
                y1={padding.top}
                x2={lastHistorical.x}
                y2={chartHeight - padding.bottom}
                stroke="#64748b"
                strokeDasharray="4 4"
              />
            )}
            {conePath && <path d={conePath} fill="#f59e0b" fillOpacity="0.15" />}
            {historicalPath && (
              <path
                d={historicalPath}
                fill="none"
                stroke="#60a5fa"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            )}
            {medianPath && (
              <path
                d={medianPath}
                fill="none"
                stroke="#fbbf24"
                strokeWidth="2"
                strokeDasharray="5 3"
              />
            )}
            {rebalancedPath && (
              <path
                d={rebalancedPath}
                fill="none"
                stroke="#34d399"
                strokeWidth="2"
                strokeDasharray="3 3"
              />
            )}
            {dateTicks.map((tick, index) =>
              index % dateTickStep === 0 || index === totalPoints - 1 ? (
                <text
                  key={`${tick.date}-${index}`}
                  x={tick.x}
                  y={chartHeight - padding.bottom + 20}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10"
                >
                  {tick.date}
                </text>
              ) : null
            )}
            <text
              x={(padding.left + chartWidth - padding.right) / 2}
              y={chartHeight - 8}
              textAnchor="middle"
              fill="#64748b"
              fontSize="10"
            >
              Historical observations
              {projectionCoords.length > 0 ? ' | Hypothetical scenarios' : ''}
            </text>
          </svg>
        </div>
      ) : (
        <p className="py-8 text-center text-sm text-slate-400">
          No valid historical or scenario data is available to chart.
        </p>
      )}

      <p className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 leading-relaxed italic">
        {disclaimer}
      </p>
    </section>
  );
};
