import React, { useState } from 'react';

export type SectorType =
  | 'IT'
  | 'Banking'
  | 'Energy'
  | 'Healthcare'
  | 'Consumer'
  | 'Real Estate'
  | 'Gold';

export interface ScenarioState {
  preset_name?: string;
  market_decline_pct: number;
  interest_rate_change_bps: number;
  currency_inr_usd_shift_pct: number;
  sector_shocks?: Partial<Record<SectorType, number>>;
  custom_ai_prompt?: string;
}

export interface ScenarioControlPanelProps {
  scenario: ScenarioState;
  onChange: (updated: ScenarioState) => void;
  onRun: () => void;
  isLoading?: boolean;
}

const AVAILABLE_SECTORS: SectorType[] = [
  'IT',
  'Banking',
  'Energy',
  'Healthcare',
  'Consumer',
  'Real Estate',
  'Gold',
];

const PRESETS: Array<{
  name: string;
  label: string;
  decline: number;
  bps: number;
  inr: number;
  sector: SectorType;
  sectorShock: number;
  prompt: string;
}> = [
  {
    name: 'Tech Selloff',
    label: 'Tech Selloff',
    decline: -10,
    bps: 50,
    inr: 3,
    sector: 'IT',
    sectorShock: -15,
    prompt: 'Technology valuation drawdown under rate pressure',
  },
  {
    name: 'Yield Steepening',
    label: 'Yield Steepening',
    decline: -15,
    bps: 125,
    inr: -5,
    sector: 'Banking',
    sectorShock: 10,
    prompt: 'Banking sector response to yield steepening',
  },
  {
    name: 'Stagflation Crisis',
    label: 'Stagflation Crisis',
    decline: -30,
    bps: 200,
    inr: 12,
    sector: 'Energy',
    sectorShock: 25,
    prompt: 'Energy supply shock under a stagflation scenario',
  },
];

export const ScenarioControlPanel: React.FC<ScenarioControlPanelProps> = ({
  scenario,
  onChange,
  onRun,
  isLoading = false,
}) => {
  const [selectedSector, setSelectedSector] = useState<SectorType>(
    () => AVAILABLE_SECTORS.find((sector) => scenario.sector_shocks?.[sector] !== undefined) ?? 'IT'
  );
  const selectedSectorShock = scenario.sector_shocks?.[selectedSector] ?? 0;

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    setSelectedSector(preset.sector);
    onChange({
      preset_name: preset.name,
      market_decline_pct: preset.decline,
      interest_rate_change_bps: preset.bps,
      currency_inr_usd_shift_pct: preset.inr,
      sector_shocks: { [preset.sector]: preset.sectorShock },
      custom_ai_prompt: preset.prompt,
    });
  };

  const updateSectorShock = (sector: SectorType, shock: number) => {
    const sector_shocks = { ...scenario.sector_shocks };
    if (shock === 0) {
      delete sector_shocks[sector];
    } else {
      sector_shocks[sector] = shock;
    }
    onChange({ ...scenario, sector_shocks });
  };

  return (
    <section
      aria-labelledby="scenario-control-heading"
      className="flex flex-col w-full bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h2 id="scenario-control-heading" className="text-sm font-semibold tracking-wide text-slate-100 uppercase">
          Scenario Control Panel
        </h2>
        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
          Hypothetical stress test
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 font-medium mr-1">Presets:</span>
        {PRESETS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            onClick={() => applyPreset(preset)}
            className="px-2.5 py-1 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            {preset.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <label className="flex flex-col gap-2 text-xs">
          <span className="flex justify-between items-center text-slate-300 font-medium">
            Market decline
            <span className="font-mono text-rose-400">{scenario.market_decline_pct}%</span>
          </span>
          <input
            type="range"
            min="-40"
            max="0"
            step="1"
            value={scenario.market_decline_pct}
            onChange={(event) =>
              onChange({ ...scenario, market_decline_pct: Number(event.target.value), preset_name: undefined })
            }
            aria-label="Market decline percentage"
            className="w-full accent-rose-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <span className="flex justify-between text-[10px] text-slate-400">
            <span>-40%</span>
            <span>0%</span>
          </span>
        </label>

        <label className="flex flex-col gap-2 text-xs">
          <span className="flex justify-between items-center text-slate-300 font-medium">
            Interest-rate change
            <span className="font-mono text-amber-400">
              {scenario.interest_rate_change_bps > 0 ? '+' : ''}
              {scenario.interest_rate_change_bps} bps
            </span>
          </span>
          <input
            type="range"
            min="-100"
            max="200"
            step="25"
            value={scenario.interest_rate_change_bps}
            onChange={(event) =>
              onChange({
                ...scenario,
                interest_rate_change_bps: Number(event.target.value),
                preset_name: undefined,
              })
            }
            aria-label="Interest-rate change in basis points"
            className="w-full accent-amber-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <span className="flex justify-between text-[10px] text-slate-400">
            <span>-100 bps</span>
            <span>+200 bps</span>
          </span>
        </label>

        <label className="flex flex-col gap-2 text-xs">
          <span className="flex justify-between items-center text-slate-300 font-medium">
            INR/USD shift
            <span className="font-mono text-indigo-400">
              {scenario.currency_inr_usd_shift_pct > 0 ? '+' : ''}
              {scenario.currency_inr_usd_shift_pct}%
            </span>
          </span>
          <input
            type="range"
            min="-15"
            max="15"
            step="1"
            value={scenario.currency_inr_usd_shift_pct}
            onChange={(event) =>
              onChange({
                ...scenario,
                currency_inr_usd_shift_pct: Number(event.target.value),
                preset_name: undefined,
              })
            }
            aria-label="INR/USD shift percentage"
            className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <span className="flex justify-between text-[10px] text-slate-400">
            <span>-15%</span>
            <span>+15%</span>
          </span>
        </label>

        <div className="flex flex-col gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
          <label className="flex justify-between items-center gap-2 text-xs text-slate-300 font-medium">
            Sector shock
            <select
              value={selectedSector}
              onChange={(event) => {
                const sector = AVAILABLE_SECTORS.find((item) => item === event.target.value);
                if (sector) setSelectedSector(sector);
              }}
              className="bg-slate-800 text-slate-200 border border-slate-700 rounded px-1.5 py-1 text-xs"
            >
              {AVAILABLE_SECTORS.map((sector) => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </select>
          </label>
          <label className="flex justify-between items-center text-xs text-slate-300">
            Shock
            <span className="font-mono text-cyan-300">
              {selectedSectorShock > 0 ? '+' : ''}
              {selectedSectorShock}%
            </span>
          </label>
          <input
            type="range"
            min="-30"
            max="30"
            step="1"
            value={selectedSectorShock}
            onChange={(event) => updateSectorShock(selectedSector, Number(event.target.value))}
            aria-label={`${selectedSector} sector shock percentage`}
            className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <span className="flex justify-between text-[10px] text-slate-400">
            <span>-30%</span>
            <span>+30%</span>
          </span>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
        <label className="sr-only" htmlFor="custom-scenario-prompt">
          Custom scenario prompt
        </label>
        <input
          id="custom-scenario-prompt"
          type="text"
          value={scenario.custom_ai_prompt ?? ''}
          placeholder="Describe an additional scenario assumption..."
          onChange={(event) =>
            onChange({ ...scenario, custom_ai_prompt: event.target.value, preset_name: undefined })
          }
          className="flex-1 w-full text-xs px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={onRun}
          disabled={isLoading}
          className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold tracking-wide transition-colors whitespace-nowrap shadow-md shadow-blue-600/20"
        >
          {isLoading ? 'Running analysis...' : 'Run analysis'}
        </button>
      </div>
      <p className="text-[11px] text-slate-500">
        Scenario inputs are hypothetical assumptions, not forecasts or guaranteed outcomes.
      </p>
    </section>
  );
};
