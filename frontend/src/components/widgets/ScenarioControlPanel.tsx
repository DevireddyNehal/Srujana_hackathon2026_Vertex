// /frontend/src/components/widgets/ScenarioControlPanel.tsx
import React from 'react';

export interface ScenarioState {
  market_decline_pct: number;
  interest_rate_change_bps: number;
  currency_inr_usd_shift_pct: number;
  custom_prompt?: string;
}

export interface ScenarioControlPanelProps {
  scenario: ScenarioState;
  onChange: (updated: ScenarioState) => void;
  onRun: () => void;
  isLoading?: boolean;
}

export const ScenarioControlPanel: React.FC<ScenarioControlPanelProps> = ({
  scenario,
  onChange,
  onRun,
  isLoading = false,
}) => {
  const updateField = <K extends keyof ScenarioState>(field: K, value: ScenarioState[K]) => {
    onChange({ ...scenario, [field]: value });
  };

  const applyPreset = (preset: { decline: number; bps: number; inr: number; prompt: string }) => {
    onChange({
      market_decline_pct: preset.decline,
      interest_rate_change_bps: preset.bps,
      currency_inr_usd_shift_pct: preset.inr,
      custom_prompt: preset.prompt,
    });
  };

  return (
    <div className="flex flex-col w-full bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
          Scenario Control Panel
        </h3>
        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
          Interactive Stress Test
        </span>
      </div>

      {/* Preset Quick Actions */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 font-medium mr-1">Presets:</span>
        <button
          type="button"
          onClick={() => applyPreset({ decline: -10, bps: 50, inr: 3, prompt: 'Mild rate hike correction' })}
          className="px-2.5 py-1 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          Mild Correction
        </button>
        <button
          type="button"
          onClick={() => applyPreset({ decline: -25, bps: 150, inr: -8, prompt: 'Aggressive Fed tightening & INR drop' })}
          className="px-2.5 py-1 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          Rate Shock
        </button>
        <button
          type="button"
          onClick={() => applyPreset({ decline: -35, bps: 200, inr: 15, prompt: 'Global liquidity contraction' })}
          className="px-2.5 py-1 text-xs rounded-md bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/50 transition-colors"
        >
          Max Stress
        </button>
      </div>

      {/* Sliders */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Market Decline */}
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center text-xs">
            <label className="text-slate-300 font-medium">Market Decline</label>
            <span className="font-mono text-rose-400 font-semibold">{scenario.market_decline_pct}%</span>
          </div>
          <input
            type="range"
            min="-40"
            max="0"
            step="1"
            value={scenario.market_decline_pct}
            onChange={(e) => updateField('market_decline_pct', Number(e.target.value))}
            className="w-full accent-rose-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-40%</span>
            <span>0%</span>
          </div>
        </div>

        {/* Interest Rate Change */}
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center text-xs">
            <label className="text-slate-300 font-medium">Interest Rate Shift</label>
            <span className="font-mono text-amber-400 font-semibold">
              {scenario.interest_rate_change_bps >= 0 ? `+${scenario.interest_rate_change_bps}` : scenario.interest_rate_change_bps} bps
            </span>
          </div>
          <input
            type="range"
            min="-100"
            max="200"
            step="25"
            value={scenario.interest_rate_change_bps}
            onChange={(e) => updateField('interest_rate_change_bps', Number(e.target.value))}
            className="w-full accent-amber-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-100 bps</span>
            <span>+200 bps</span>
          </div>
        </div>

        {/* INR/USD Shift */}
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center text-xs">
            <label className="text-slate-300 font-medium">INR/USD Shift</label>
            <span className="font-mono text-indigo-400 font-semibold">
              {scenario.currency_inr_usd_shift_pct >= 0 ? `+${scenario.currency_inr_usd_shift_pct}` : scenario.currency_inr_usd_shift_pct}%
            </span>
          </div>
          <input
            type="range"
            min="-15"
            max="15"
            step="1"
            value={scenario.currency_inr_usd_shift_pct}
            onChange={(e) => updateField('currency_inr_usd_shift_pct', Number(e.target.value))}
            className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-15%</span>
            <span>+15%</span>
          </div>
        </div>
      </div>

      {/* Custom AI Prompt Input & Run Button */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <input
          type="text"
          value={scenario.custom_prompt || ''}
          placeholder="Inject custom AI scenario constraint (e.g., crude oil spikes by 25%)..."
          onChange={(e) => updateField('custom_prompt', e.target.value)}
          className="flex-1 w-full text-xs px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={onRun}
          disabled={isLoading}
          className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold tracking-wide transition-colors whitespace-nowrap shadow-md shadow-blue-600/20"
        >
          {isLoading ? 'Running Analysis...' : 'Run Analysis'}
        </button>
      </div>
    </div>
  );
};