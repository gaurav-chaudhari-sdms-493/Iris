import React from 'react';
import { Snowflake, Plug, ChevronUp, ChevronDown } from 'lucide-react';

export default function AcRemote({ telemetry, onAcChange }) {
  const acState = telemetry?.ac_state;

  // AC Remote Controls
  const handleTempChange = (delta) => {
    if (!acState) return;
    const currentTemp = acState.temperature ?? 24;
    const newTemp = Math.max(16, Math.min(30, currentTemp + delta));
    onAcChange && onAcChange({ temperature: newTemp });
  };

  const cycleMode = () => {
    if (!acState) return;
    const modes = ['COOL', 'FAN', 'HEAT', 'AUTO'];
    const currIndex = modes.indexOf(acState.mode ?? 'COOL');
    const nextMode = modes[(currIndex + 1) % modes.length];
    onAcChange && onAcChange({ mode: nextMode });
  };

  const cycleFan = () => {
    if (!acState) return;
    const fans = ['AUTO', 'LOW', 'MED', 'HIGH'];
    const currIndex = fans.indexOf(acState.fan_speed ?? 'AUTO');
    const nextFan = fans[(currIndex + 1) % fans.length];
    onAcChange && onAcChange({ fan_speed: nextFan });
  };

  const togglePower = () => {
    if (!acState) return;
    const nextPower = acState.power === 'ON' ? 'OFF' : 'ON';
    onAcChange && onAcChange({ power: nextPower });
  };

  return (
    <div className="iris-card space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-100 font-bold text-base md:text-lg">
          <Snowflake className="w-5 h-5 text-cyan-400" />
          <span>AC Broadlink IR Controller</span>
        </div>
      </div>

      {/* Thermostat Digital Display Box */}
      <div className="bg-slate-950/90 border-2 border-cyan-500/40 rounded-2xl p-4 md:p-5 relative shadow-[0_0_25px_rgba(6,182,212,0.15)] flex flex-col justify-between space-y-4">
        {!acState ? (
          <div className="text-center py-6 text-slate-500 font-mono text-xs animate-pulse">
            Connecting to AC Engine Telemetry...
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono tracking-widest text-cyan-400 font-extrabold">CLIMATE IR</span>
              <div className={`w-3 h-3 rounded-full transition-all ${
                acState.power === 'ON' ? 'bg-emerald-400 shadow-[0_0_10px_#10b981]' : 'bg-red-500/50'
              }`} />
            </div>

            <div className="flex items-center justify-between px-2 md:px-6 py-2">
              <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300">
                <Snowflake className="w-10 h-10 md:w-12 md:h-12" />
              </div>
              <div className="text-4xl md:text-6xl font-black text-cyan-400 drop-shadow-[0_0_20px_rgba(6,182,212,0.6)] font-mono">
                {acState.power === 'ON' ? `${acState.temperature}°C` : 'OFF'}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-t border-slate-800/80 pt-3">
              <span>{acState.mode} MODE</span>
              <span>FAN: {acState.fan_speed}</span>
            </div>
          </>
        )}
      </div>

      {/* Control Buttons Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Power IR */}
        <button
          onClick={togglePower}
          disabled={!acState}
          className={`px-4 py-2.5 rounded-xl font-black text-xs md:text-sm flex items-center gap-2 transition-all cursor-pointer shadow-lg active:scale-95 ${
            acState?.power === 'ON' 
              ? 'bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600 text-white shadow-red-500/20' 
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
          }`}
        >
          <Plug className="w-4 h-4" />
          <span>POWER IR</span>
        </button>

        {/* Temp Up ▲ */}
        <button
          onClick={() => handleTempChange(1)}
          disabled={!acState}
          className="w-10 h-10 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-black flex items-center justify-center border border-slate-700 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
          title="Temperature Up"
        >
          <ChevronUp className="w-5 h-5" />
        </button>

        {/* Temp Down ▼ */}
        <button
          onClick={() => handleTempChange(-1)}
          disabled={!acState}
          className="w-10 h-10 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-black flex items-center justify-center border border-slate-700 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
          title="Temperature Down"
        >
          <ChevronDown className="w-5 h-5" />
        </button>

        {/* MODE */}
        <button
          onClick={cycleMode}
          disabled={!acState}
          className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-bold text-xs md:text-sm border border-slate-700 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
        >
          MODE
        </button>

        {/* FAN SPEED */}
        <button
          onClick={cycleFan}
          disabled={!acState}
          className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-bold text-xs md:text-sm border border-slate-700 cursor-pointer active:scale-95 transition-all disabled:opacity-50"
        >
          FAN SPEED
        </button>
      </div>
    </div>
  );
}
