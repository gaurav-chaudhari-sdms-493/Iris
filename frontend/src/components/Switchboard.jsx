import React from 'react';
import { Sliders, ShieldAlert } from 'lucide-react';

const SWITCH_PAIRS = [
  // Row 1 Pairs
  [
    { id: 'S1', label: 'TV Power', sub: 'Broadlink IR', isSpare: false },
    { id: 'S2', label: 'Lower Bulbs', sub: 'LB7, LB8, LB9', isSpare: false },
  ],
  [
    { id: 'S3', label: 'Upper LED', sub: 'LP1, LP2', isSpare: false },
    { id: 'S4', label: 'Upper Bulbs', sub: 'LB4, LB5, LB6', isSpare: false },
  ],
  [
    { id: 'S5', label: 'Aux Switch 5', sub: 'Spare Gang 5', isSpare: true },
    { id: 'S6', label: 'Aux Switch 6', sub: 'Spare Gang 6', isSpare: true },
  ],
  // Row 2 Pairs
  [
    { id: 'S7', label: 'TV Bulbs', sub: 'LB1, LB2, LB3', isSpare: false },
    { id: 'S8', label: 'Aux Switch 8', sub: 'Spare Gang 8', isSpare: true },
  ],
  [
    { id: 'S9', label: 'Aux Switch 9', sub: 'Spare Gang 9', isSpare: true },
    { id: 'S10', label: 'Lower LED', sub: 'LP3, LP4', isSpare: false },
  ],
  [
    { id: 'S11', label: 'Aux Switch 11', sub: 'Spare Gang 11', isSpare: true },
    { id: 'S12', label: 'Far Bulbs', sub: 'LB10, LB11, LB12', isSpare: false },
  ],
];

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
    <div className="iris-card space-y-4">
      {/* Switchboard Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Physical 12-Gang Switchboard
            </h2>
          </div>
        </div>
      </div>

      {/* SINGLE UNIFIED DARK TITANIUM WALL PLATE HOUSING */}
      <div className="relative bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 border-2 border-slate-800 rounded-2xl p-4 md:p-5 shadow-2xl">
        
        {/* Chamfered Inner Frame */}
        <div className="border border-slate-800/90 rounded-xl p-3 md:p-5 bg-slate-950/80 shadow-inner relative">
          
          {/* Metallic Corner Screws */}
          <div className="absolute top-2.5 left-3 w-3 h-3 rounded-full bg-slate-700 border border-slate-600 shadow-inner flex items-center justify-center">
            <div className="w-2 h-0.5 bg-slate-500 transform rotate-45" />
          </div>
          <div className="absolute top-2.5 right-3 w-3 h-3 rounded-full bg-slate-700 border border-slate-600 shadow-inner flex items-center justify-center">
            <div className="w-2 h-0.5 bg-slate-500 transform -rotate-45" />
          </div>
          <div className="absolute bottom-2.5 left-3 w-3 h-3 rounded-full bg-slate-700 border border-slate-600 shadow-inner flex items-center justify-center">
            <div className="w-2 h-0.5 bg-slate-500 transform rotate-12" />
          </div>
          <div className="absolute bottom-2.5 right-3 w-3 h-3 rounded-full bg-slate-700 border border-slate-600 shadow-inner flex items-center justify-center">
            <div className="w-2 h-0.5 bg-slate-500 transform -rotate-12" />
          </div>

          {/* 12 SWITCH GANGS IN 6 PAIRS (NO MARGIN BETWEEN S1-S2, S3-S4, S5-S6, S7-S8, S9-S10, S11-S12) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-5 my-1">
            {SWITCH_PAIRS.map((pair, pIdx) => (
              <div key={pIdx} className="grid grid-cols-2 gap-0 border border-slate-800/80 rounded-xl bg-slate-900/30 overflow-hidden">
                {pair.map((sw) => {
                  const isActive = getSwitchState(sw.id);
                  return (
                    <div
                      key={sw.id}
                      onClick={() => !sw.isSpare && onToggleSwitch && onToggleSwitch(sw.id, !isActive)}
                      className={`flex flex-col items-center justify-between select-none p-2 transition-all duration-200 ${
                        sw.isSpare 
                          ? 'bg-slate-900/10 opacity-40 cursor-not-allowed' 
                          : 'bg-slate-900/30 hover:bg-slate-800/60 cursor-pointer'
                      }`}
                    >
                      {/* Switch ID & Label Above Socket */}
                      <div className="text-center w-full mb-2">
                        <div className="flex items-center justify-center gap-1">
                          <span className={`text-xs font-mono font-black ${
                            isActive ? 'text-emerald-400' : sw.isSpare ? 'text-slate-600' : 'text-red-400'
                          }`}>
                            {sw.id}
                          </span>
                        </div>
                        <span className="text-xs font-bold text-slate-100 block mt-0.5 font-sans truncate" title={sw.label}>
                          {sw.label}
                        </span>
                      </div>

                      {/* RECESSED MODULAR SOCKET SLOT */}
                      <div className={`relative w-14 h-28 rounded-xl border-2 p-1 transition-all flex items-center justify-center ${
                        sw.isSpare
                          ? 'bg-slate-950 border-slate-800 shadow-inner'
                          : isActive
                          ? 'bg-slate-950 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.35)]'
                          : 'bg-slate-950 border-red-500/60 shadow-[0_0_12px_rgba(239,68,68,0.25)]'
                      }`}>
                        
                        {/* TACTILE VERTICAL WHITE ROCKER SWITCH */}
                        <div 
                          className={`w-full h-full rounded-lg transition-all duration-200 flex flex-col items-center justify-between p-1.5 border-2 select-none ${
                            isActive
                              ? 'bg-gradient-to-b from-slate-100 via-white to-slate-200 border-slate-300 shadow-[0_4px_8px_rgba(0,0,0,0.3)] -translate-y-0.5'
                              : 'bg-gradient-to-b from-slate-200 via-slate-300 to-slate-400 border-slate-400 shadow-[inset_0_4px_8px_rgba(0,0,0,0.3)] translate-y-0.5'
                          }`}
                        >
                          {/* TOP: OFF Indicator */}
                          <div className="flex flex-col items-center gap-0.5 w-full">
                            <div className={`w-2.5 h-2.5 rounded-full border transition-all ${
                              !isActive 
                                ? 'bg-red-500 border-red-200 shadow-[0_0_8px_#ef4444]' 
                                : 'bg-slate-400/20 border-slate-400/30'
                            }`} />
                            <span className={`text-[8px] font-mono font-black tracking-tighter transition-all px-1 rounded ${
                              !isActive 
                                ? 'bg-red-500/20 text-red-600 border border-red-500/40 font-black' 
                                : 'text-slate-400/50'
                            }`}>
                              OFF
                            </span>
                          </div>

                          {/* Center Tactile Ridge */}
                          <div className="w-5 h-0.5 bg-slate-400/60 rounded-full my-0.5" />

                          {/* BOTTOM: ON Indicator */}
                          <div className="flex flex-col items-center gap-0.5 w-full">
                            <span className={`text-[8px] font-mono font-black tracking-tighter transition-all px-1 rounded ${
                              isActive 
                                ? 'bg-emerald-500/20 text-emerald-600 border border-emerald-500/40 font-black' 
                                : 'text-slate-400/50'
                            }`}>
                              ON
                            </span>
                            <div className={`w-2.5 h-2.5 rounded-full border transition-all ${
                              isActive 
                                ? 'bg-emerald-500 border-emerald-200 shadow-[0_0_8px_#10b981]' 
                                : 'bg-slate-400/20 border-slate-400/30'
                            }`} />
                          </div>

                        </div>

                      </div>

                      {/* Subtitle Below Socket */}
                      <div className="text-center w-full mt-2">
                        <span className="text-[10px] font-mono text-slate-400 font-semibold block truncate" title={sw.sub}>
                          {sw.sub}
                        </span>
                      </div>

                    </div>
                  );
                })}
              </div>
            ))}
          </div>

        </div>

      </div>
    </div>
  );
}
