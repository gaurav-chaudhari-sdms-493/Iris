import React from 'react';
import { Sliders, ShieldAlert } from 'lucide-react';

const SWITCH_DESCRIPTIONS = {
  S1: { label: "TV Power (IR Blaster)", module: "Broadlink IR", type: "IR" },
  S2: { label: "Lower Bulbs LB7, LB8, LB9", module: "Relay B • Ch 1", type: "Relay" },
  S3: { label: "Upper LED Panels LP1, LP2", module: "Relay A • Ch 1", type: "Relay" },
  S4: { label: "Upper Bulbs LB4, LB5, LB6", module: "Relay A • Ch 4", type: "Relay" },
  S7: { label: "TV Area Bulbs LB1, LB2, LB3", module: "Relay A • Ch 3", type: "Relay" },
  S10: { label: "Lower LED Panels LP3, LP4", module: "Relay A • Ch 2", type: "Relay" },
  S12: { label: "Far Bulbs LB10, LB11, LB12", module: "Relay B • Ch 2", type: "Relay" },
};

export default function Switchboard({ relays, tvState, onToggleSwitch }) {
  const relayA = relays?.Relay_A ?? { 1: false, 2: false, 3: false, 4: false };
  const relayB = relays?.Relay_B ?? { 1: false, 2: false, 3: false, 4: false };

  const getSwitchState = (swId) => {
    if (swId === 'S1') return tvState === 'ON';
    if (swId === 'S3') return Boolean(relayA[1]);
    if (swId === 'S10') return Boolean(relayA[2]);
    if (swId === 'S7') return Boolean(relayA[3]);
    if (swId === 'S4') return Boolean(relayA[4]);
    if (swId === 'S2') return Boolean(relayB[1]);
    if (swId === 'S12') return Boolean(relayB[2]);
    return false;
  };

  return (
    <div className="iris-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">12-Gang Physical Switchboard</h2>
            <p className="text-xs text-slate-400 font-mono">AZIOT Parallel Relay Mapping & Manual Overrides</p>
          </div>
        </div>

        <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-lg flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5" /> Wall Override Active
        </span>
      </div>

      {/* Switchboard Grid Layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(SWITCH_DESCRIPTIONS).map(([swId, info]) => {
          const isActive = getSwitchState(swId);
          return (
            <div
              key={swId}
              onClick={() => onToggleSwitch(swId, !isActive)}
              className={`p-3.5 rounded-xl border cursor-pointer select-none transition-all flex items-center justify-between ${
                isActive
                  ? 'bg-cyan-950/30 border-cyan-500/60 text-slate-100 shadow-sm'
                  : 'bg-slate-900/60 hover:bg-slate-800/70 border-slate-800 text-slate-400'
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sm text-cyan-400">{swId}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    {info.module}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1 font-medium">{info.label}</p>
              </div>

              {/* Toggle Switch Pill */}
              <div
                className={`w-10 h-6 rounded-full transition-colors p-1 flex items-center shrink-0 ml-2 ${
                  isActive ? 'bg-cyan-500 justify-end' : 'bg-slate-700 justify-start'
                }`}
              >
                <div className="w-4 h-4 rounded-full bg-white shadow-md transform transition-transform" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
