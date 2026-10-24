// /frontend/src/components/widgets/HistoricalVsHypotheticalChart.tsx
import React, { useMemo } from 'react';

export interface ChartDataPoint {
  date: string;
  value: number;
}

export interface ProjectionConePoint {
  date: string;
  p10_worst_case: number;
  p50_median_case: number;
  p90_best_case: number;
  rebalanced_p50?: number;
}

export interface HistoricalVsHypotheticalChartProps {
  data: {
    historical_observations: ChartDataPoint[];
    hypothetical_projection_cone: ProjectionConePoint[];
    disclaimer: string;
  };
}

export const HistoricalVsHypotheticalChart: React.FC<HistoricalVsHypotheticalChartProps> = ({ data }) => {
  const { historical_observations, hypothetical_projection_cone, disclaimer } = data;

  const totalPoints = historical_observations.length + hypothetical_projection_cone.length;
  const width = 800;
  const height = 320;
  const padding = { top: 20, right: 30, bottom: 40, left: 60 };

  const { minVal, maxVal, histCoords, projCoords } = useMemo(() => {
    const histVals = historical_observations.map((d) => d.value);
    const projVals = hypothetical_projection_cone.flatMap((d) => [
      d.p10_worst_case,
      d.p50_median_case,
      d.p90_best_case,
      ...(d.rebalanced_p50 !== undefined ? [d.rebalanced_p50] : []),
    ]);
    const allVals = [...histVals, ...projVals];
    const min = Math.min(...(allVals.length ? allVals : [0]));
    const max = Math.max(...(allVals.length ? allVals : [100]));
    const valRange = max - min || 1;

    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const getX = (index: number) => padding.left + (index / (Math.max(totalPoints - 1, 1))) * chartW;
    const getY = (val: number) => padding.top + chartH - ((val - min) / valRange) * chartH;

    const hCoords = historical_observations.map((d, i) => ({ x: getX(i), y: getY(d.value), ...d }));
    
    // Connect the start of projection cone from the last historical point if available
    const offset = historical_observations.length;
    const pCoords = hypothetical_projection_cone.map((d, i) => ({
      x: getX(offset + i),
      yP10: getY(d.p10_worst_case),
      yP50: getY(d.p50_median_case),
      yP90: getY(d.p90_best_case),
      yRebal: d.rebalanced_p50 !== undefined ? getY(d.rebalanced_p50) : undefined,
      ...d,
    }));

    return { minVal: min, maxVal: max, histCoords: hCoords, projCoords: pCoords };
  }, [historical_observations, hypothetical_projection_cone, totalPoints]);

  const histPath = histCoords.reduce(
    (acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`,
    ''
  );

  // SVG Area path for shaded confidence cone (p90 forward, then p10 in reverse)
  const lastHist = histCoords[histCoords.length - 1];
  const conePath = useMemo(() => {
    if (!projCoords.length) return '';
    const startX = lastHist ? lastHist.x : projCoords[0].x;
    const startY = lastHist ? lastHist.y : projCoords[0].yP50;

    let path = `M ${startX} ${startY}`;
    projCoords.forEach((p) => {
      path += ` L ${p.x} ${p.yP90}`;
    });
    for (let i = projCoords.length - 1; i >= 0; i--) {
      path += ` L ${projCoords[i].x} ${projCoords[i].yP10}`;
    }
    path += ` Z`;
    return path;
  }, [projCoords, lastHist]);

  const p50Path = projCoords.reduce(
    (acc, pt, i) => `${acc} ${i === 0 ? (lastHist ? `M ${lastHist.x} ${lastHist.y} L` : 'M') : 'L'} ${pt.x} ${pt.yP50}`,
    ''
  );

  const rebalPath = projCoords.reduce(
    (acc, pt, i) =>
      pt.yRebal !== undefined
        ? `${acc} ${i === 0 ? (lastHist ? `M ${lastHist.x} ${lastHist.y} L` : 'M') : 'L'} ${pt.x} ${pt.yRebal}`
        : acc,
    ''
  );

  return (
    <div className="flex flex-col w-full bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <h3 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
          Historical Observations vs Hypothetical Projection
        </h3>
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-blue-400 rounded-full inline-block" /> Historical
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-amber-500/20 border border-amber-500/40 rounded-sm inline-block" /> Cone (P10–P90)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-amber-400 inline-block border-t border-dashed" /> P50 Median
          </span>
          {rebalPath && (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-400 inline-block border-t border-dashed" /> Rebalanced P50
            </span>
          )}
        </div>
      </div>

      <div className="relative w-full overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto text-xs select-none">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
            const y = padding.top + (height - padding.top - padding.bottom) * pct;
            const val = (maxVal - pct * (maxVal - minVal)).toFixed(0);
            return (
              <g key={idx} className="text-slate-700">
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="currentColor" strokeDasharray="3 3" />
                <text x={padding.left - 8} y={y + 4} textAnchor="end" fill="#64748b" className="text-[10px]">
                  {val}
                </text>
              </g>
            );
          })}

          {/* Historical line separator boundary */}
          {lastHist && (
            <line
              x1={lastHist.x}
              y1={padding.top}
              x2={lastHist.x}
              y2={height - padding.bottom}
              stroke="#475569"
              strokeDasharray="4 4"
            />
          )}

          {/* Projection Shaded Cone */}
          {conePath && <path d={conePath} fill="#f59e0b" fillOpacity="0.15" />}

          {/* Historical Solid Line */}
          {histPath && <path d={histPath} fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeLinecap="round" />}

          {/* P50 Line */}
          {p50Path && (
            <path d={p50Path} fill="none" stroke="#fbbf24" strokeWidth="2" strokeDasharray="5 3" />
          )}

          {/* Rebalanced P50 Line */}
          {rebalPath && (
            <path d={rebalPath} fill="none" stroke="#34d399" strokeWidth="2" strokeDasharray="3 3" />
          )}
        </svg>
      </div>

      <p className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 leading-relaxed italic">
        {disclaimer}
      </p>
    </div>
  );
};