import React from 'react';
import { Sparkles, Play, ShieldAlert, Cpu } from 'lucide-react';

export default function Presets({ currentMode, onSelectPreset }) {
  return (
    <div className="iris-card">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-slate-100">Smart Automation Presets</h2>
          <p className="text-xs text-slate-400 font-mono">One-Tap System Preset Macros</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Presentation Preset */}
        <button
          onClick={() => onSelectPreset('PRESENTATION')}
          className={`p-4 rounded-xl border text-left transition flex flex-col justify-between cursor-pointer ${
            currentMode === 'PRESENTATION'
              ? 'bg-purple-950/40 border-purple-500 text-slate-100 shadow-lg shadow-purple-500/10'
              : 'bg-slate-900/60 hover:bg-slate-800/80 border-slate-800 text-slate-300'
          }`}
        >
          <div className="flex justify-between items-start">
            <div className="p-2 rounded-lg bg-purple-500/20 text-purple-300">
              <Play className="w-5 h-5" />
            </div>
            {currentMode === 'PRESENTATION' && (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
                ACTIVE
              </span>
            )}
          </div>
          <div className="mt-3">
            <h3 className="font-bold text-sm text-slate-100">Presentation Preset</h3>
            <p className="text-xs text-slate-400 mt-1">Dims ambient lights, sets AC to 24°C Quiet, and turns TV ON.</p>
          </div>
        </button>

        {/* Full Auto AI Mode */}
        <button
          onClick={() => onSelectPreset('AUTO')}
          className={`p-4 rounded-xl border text-left transition flex flex-col justify-between cursor-pointer ${
            currentMode === 'AUTO'
              ? 'bg-cyan-950/40 border-cyan-500 text-slate-100 shadow-lg shadow-cyan-500/10'
              : 'bg-slate-900/60 hover:bg-slate-800/80 border-slate-800 text-slate-300'
          }`}
        >
          <div className="flex justify-between items-start">
            <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-300">
              <Cpu className="w-5 h-5" />
            </div>
            {currentMode === 'AUTO' && (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                ACTIVE
              </span>
            )}
          </div>
          <div className="mt-3">
            <h3 className="font-bold text-sm text-slate-100">Full Auto AI Mode</h3>
            <p className="text-xs text-slate-400 mt-1">Instant light turn-on + 1s real-time YOLO headcount occupancy polling.</p>
          </div>
        </button>

        {/* Power Saving Vacate */}
        <button
          onClick={() => onSelectPreset('POWER_SAVING')}
          className={`p-4 rounded-xl border text-left transition flex flex-col justify-between cursor-pointer ${
            currentMode === 'POWER_SAVING'
              ? 'bg-amber-950/40 border-amber-500 text-slate-100 shadow-lg shadow-amber-500/10'
              : 'bg-slate-900/60 hover:bg-slate-800/80 border-slate-800 text-slate-300'
          }`}
        >
          <div className="flex justify-between items-start">
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-300">
              <ShieldAlert className="w-5 h-5" />
            </div>
            {currentMode === 'POWER_SAVING' && (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                ACTIVE
              </span>
            )}
          </div>
          <div className="mt-3">
            <h3 className="font-bold text-sm text-slate-100">Power Saving Vacate</h3>
            <p className="text-xs text-slate-400 mt-1">Immediate zero-occupancy energy shutdown across all relays and AC.</p>
          </div>
        </button>

      </div>
    </div>
  );
}
