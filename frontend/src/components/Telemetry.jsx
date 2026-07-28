import React from 'react';
import { Users, Thermometer, TrendingDown, Zap } from 'lucide-react';

export default function Telemetry({ telemetry, onAcChange }) {
  const headcount = telemetry?.headcount ?? 0;
  const acState = telemetry?.ac_state ?? { power: 'ON', temperature: 24, mode: 'COOL', fan_speed: 'AUTO' };
  const metrics = telemetry?.energy_metrics ?? { active_kw: 1.8, kwh_saved_today: 0.42, cost_saved_usd: 0.06 };

  const isAcOn = acState.power === 'ON';

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      
      {/* 1. Active Headcount */}
      <div className="iris-card flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Headcount</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-4xl font-extrabold text-cyan-400 font-mono">{headcount}</span>
            <span className="text-sm font-medium text-slate-300">Occupants</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-mono">Real-Time 1-sec YOLO Object Detection</p>
        </div>
        <div className="p-3.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
          <Users className="w-7 h-7" />
        </div>
      </div>

      {/* 2. AC HVAC Climate Status */}
      <div className="iris-card flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AC HVAC Status</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className={`text-3xl font-extrabold font-mono ${isAcOn ? 'text-emerald-400' : 'text-slate-500'}`}>
              {isAcOn ? `${acState.temperature}°C` : 'OFF'}
            </span>
            {isAcOn && <span className="text-xs font-mono text-slate-300">{acState.mode} • FAN {acState.fan_speed}</span>}
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => onAcChange(22, 'ON')}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition border ${
                acState.temperature === 22 && isAcOn
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 font-bold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              }`}
            >
              22°C Cool
            </button>
            <button
              onClick={() => onAcChange(24, 'ON')}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition border ${
                acState.temperature === 24 && isAcOn
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 font-bold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              }`}
            >
              24°C Cool
            </button>
          </div>
        </div>
        <div className={`p-3.5 rounded-xl border ${isAcOn ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-slate-800 text-slate-600 border-slate-700'}`}>
          <Thermometer className="w-7 h-7" />
        </div>
      </div>

      {/* 3. Daily Energy Savings */}
      <div className="iris-card flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Daily Energy Savings</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-3xl font-extrabold font-mono text-amber-400">{metrics.kwh_saved_today}</span>
            <span className="text-xs text-slate-300">kWh</span>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
              ${metrics.cost_saved_usd} Saved
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2 flex items-center gap-1 font-mono">
            <Zap className="w-3.5 h-3.5 text-amber-400" /> Active Load: {metrics.active_kw} kW
          </p>
        </div>
        <div className="p-3.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <TrendingDown className="w-7 h-7" />
        </div>
      </div>

    </div>
  );
}
