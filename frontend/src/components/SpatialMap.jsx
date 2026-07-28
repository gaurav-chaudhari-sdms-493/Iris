import React from 'react';
import { Map, Tv, Wind, Zap, Info } from 'lucide-react';

export default function SpatialMap({ zoneStates, relays, tvState, acState, onToggleSwitch }) {
  const relayA = relays?.Relay_A ?? { 1: false, 2: false, 3: false, 4: false };
  const relayB = relays?.Relay_B ?? { 1: false, 2: false, 3: false, 4: false };

  // Switch circuit states from relays & IR
  const isS1On = tvState === 'ON';
  const isS2On = Boolean(relayB[1]);  // LB7, LB8, LB9
  const isS3On = Boolean(relayA[1]);  // LP1, LP2
  const isS4On = Boolean(relayA[4]);  // LB4, LB5, LB6
  const isS7On = Boolean(relayA[3]);  // LB1, LB2, LB3
  const isS10On = Boolean(relayA[2]); // LP3, LP4
  const isS12On = Boolean(relayB[2]); // LB10, LB11, LB12

  const isAcOn = (acState?.power ?? 'ON') === 'ON';
  const acTemp = acState?.temperature ?? 24;

  // 12-Gang Switchboard Quick Mapping Bar (S1-S12)
  const switchboardGangs = [
    { id: 'S1', label: 'TV', active: isS1On, target: 'S1' },
    { id: 'S2', label: 'LB7-9', active: isS2On, target: 'S2' },
    { id: 'S3', label: 'LP1,2', active: isS3On, target: 'S3' },
    { id: 'S4', label: 'LB4-6', active: isS4On, target: 'S4' },
    { id: 'S5', label: 'Spare', active: false, target: null },
    { id: 'S6', label: 'Spare', active: false, target: null },
    { id: 'S7', label: 'LB1-3', active: isS7On, target: 'S7' },
    { id: 'S8', label: 'Spare', active: false, target: null },
    { id: 'S9', label: 'Spare', active: false, target: null },
    { id: 'S10', label: 'LP3,4', active: isS10On, target: 'S10' },
    { id: 'S11', label: 'Spare', active: false, target: null },
    { id: 'S12', label: 'LB10-12', active: isS12On, target: 'S12' },
  ];

  // Helper for Circular Light Bulb Nodes
  const renderBulb = (id, isOn, switchId) => (
    <div
      onClick={() => onToggleSwitch && onToggleSwitch(switchId, !isOn)}
      className={`flex flex-col items-center justify-center p-1.5 rounded-lg border cursor-pointer select-none transition-all ${
        isOn
          ? 'bg-amber-950/40 border-amber-500/80 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.3)]'
          : 'bg-slate-900/60 border-slate-800 text-slate-500 hover:border-slate-700'
      }`}
    >
      <div className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
        isOn ? 'bg-amber-400 border-amber-300 shadow-[0_0_8px_#f59e0b]' : 'bg-slate-800 border-slate-700'
      }`} />
      <span className="text-[10px] font-mono mt-1 font-semibold">{id}</span>
    </div>
  );

  // Helper for Rectangular LED Panel Nodes
  const renderPanel = (id, isOn, switchId) => (
    <div
      onClick={() => onToggleSwitch && onToggleSwitch(switchId, !isOn)}
      className={`py-2.5 px-4 rounded-xl border text-center font-mono cursor-pointer select-none transition-all ${
        isOn
          ? 'bg-cyan-950/40 border-cyan-500/80 text-cyan-300 shadow-[0_0_16px_rgba(6,182,212,0.25)]'
          : 'bg-slate-900/60 border-slate-800 text-slate-500 hover:border-slate-700'
      }`}
    >
      <div className="text-xs font-bold">{id}</div>
      <div className="text-[10px] opacity-80">{isOn ? `LIT (${switchId})` : 'OFF'}</div>
    </div>
  );

  return (
    <div className="iris-card space-y-4">
      {/* Component Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/30">
            <Map className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">2D Spatial Floorplan Map</h2>
            <p className="text-xs text-slate-400 font-mono">Exact Room Top View (TV, AC, LP1-4, LB1-12)</p>
          </div>
        </div>

        <span className="text-[11px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-3 py-1 rounded-lg flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5" /> AC Remote Controlled
        </span>
      </div>

      {/* 12-Gang Switch Board Quick Reference Grid */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-2.5">
        <div className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex justify-between">
          <span>Switch Board (Physical 12-Gang)</span>
          <span className="text-slate-500">S1-S12 Wiring Schematic</span>
        </div>
        <div className="grid grid-cols-6 gap-1.5">
          {switchboardGangs.map((sw) => (
            <div
              key={sw.id}
              onClick={() => sw.target && onToggleSwitch && onToggleSwitch(sw.target, !sw.active)}
              className={`p-1.5 rounded border text-center font-mono transition-all text-[10px] ${
                sw.label === 'Spare'
                  ? 'bg-slate-950/30 border-slate-800 text-slate-600 opacity-40'
                  : sw.active
                  ? 'bg-cyan-950/50 border-cyan-500/80 text-cyan-300 font-bold cursor-pointer'
                  : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-400 cursor-pointer'
              }`}
            >
              <span>{sw.id}</span>
              <span className="block text-[9px] text-slate-400 truncate">{sw.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 2D ROOM TOP VIEW (EXACT MATCH TO HANDWRITTEN DIAGRAM IMAGE 2) */}
      <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3 relative">
        <div className="flex items-center justify-between text-xs font-mono border-b border-slate-800 pb-2">
          <span className="text-slate-200 font-bold">Room Layout (Top View)</span>
          <span className="text-slate-500">Exact Spatial Map</span>
        </div>

        {/* 1. TV TOP VIEW (Wall Mounted at top) */}
        <div
          onClick={() => onToggleSwitch && onToggleSwitch('S1', !isS1On)}
          className={`w-full py-2.5 rounded-lg border text-center font-mono cursor-pointer transition-all flex items-center justify-center gap-2 ${
            isS1On
              ? 'bg-purple-950/40 border-purple-500/80 text-purple-300 shadow-[0_0_16px_rgba(168,85,247,0.3)]'
              : 'bg-slate-900 border-slate-800 text-slate-500 hover:border-slate-700'
          }`}
        >
          <Tv className={`w-4 h-4 ${isS1On ? 'text-purple-400' : 'text-slate-600'}`} />
          <span className="text-xs font-bold tracking-wider">TV TOP VIEW {isS1On ? '(POWERED ON)' : '(OFF)'}</span>
        </div>

        {/* 2. ROW 1 BULBS: LB1, LB2, LB3 (S7 -> Relay A3) */}
        <div className="grid grid-cols-3 gap-4 px-4">
          {renderBulb('LB1', isS7On, 'S7')}
          {renderBulb('LB2', isS7On, 'S7')}
          {renderBulb('LB3', isS7On, 'S7')}
        </div>

        {/* 3. ROW 2 PANEL: LP1 (S3 -> Relay A1) */}
        <div className="max-w-md mx-auto">
          {renderPanel('LP1 (Panel 1)', isS3On, 'S3')}
        </div>

        {/* 4. ROW 3 BULBS: LB4, LB5, LB6 (S4 -> Relay A4) */}
        <div className="grid grid-cols-3 gap-4 px-4">
          {renderBulb('LB4', isS4On, 'S4')}
          {renderBulb('LB5', isS4On, 'S4')}
          {renderBulb('LB6', isS4On, 'S4')}
        </div>

        {/* 5. MIDDLE ROW: LP2 (Left) - AC (Center) - LP3 (Right) */}
        <div className="grid grid-cols-3 gap-3 items-center">
          {/* LP2 Panel (S3 -> Relay A1) */}
          {renderPanel('LP2', isS3On, 'S3')}

          {/* AC Unit (Center) */}
          <div className={`py-3 px-2 rounded-xl border text-center font-mono transition-all flex flex-col items-center justify-center ${
            isAcOn
              ? 'bg-emerald-950/40 border-emerald-500/70 text-emerald-300 shadow-[0_0_16px_rgba(16,185,129,0.2)]'
              : 'bg-slate-900 border-slate-800 text-slate-500'
          }`}>
            <div className="flex items-center gap-1.5 text-xs font-bold">
              <Wind className={`w-4 h-4 ${isAcOn ? 'text-emerald-400 animate-spin' : 'text-slate-600'}`} />
              <span>AC UNIT</span>
            </div>
            <span className="text-[10px] mt-1 font-semibold">{isAcOn ? `${acTemp}°C COOL` : 'OFF'}</span>
            <span className="text-[9px] text-slate-400">IR Remote Controlled</span>
          </div>

          {/* LP3 Panel (S10 -> Relay A2) */}
          {renderPanel('LP3', isS10On, 'S10')}
        </div>

        {/* 6. ROW 4 BULBS: LB7, LB8, LB9 (S2 -> Relay B1) */}
        <div className="grid grid-cols-3 gap-4 px-4">
          {renderBulb('LB7', isS2On, 'S2')}
          {renderBulb('LB8', isS2On, 'S2')}
          {renderBulb('LB9', isS2On, 'S2')}
        </div>

        {/* 7. ROW 5 PANEL: LP4 (S10 -> Relay A2) */}
        <div className="max-w-md mx-auto">
          {renderPanel('LP4 (Panel 4)', isS10On, 'S10')}
        </div>

        {/* 8. ROW 6 BULBS: LB10, LB11, LB12 (S12 -> Relay B2) */}
        <div className="grid grid-cols-3 gap-4 px-4">
          {renderBulb('LB10', isS12On, 'S12')}
          {renderBulb('LB11', isS12On, 'S12')}
          {renderBulb('LB12', isS12On, 'S12')}
        </div>

      </div>

      {/* Spec Footer */}
      <div className="text-[11px] font-mono text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 flex items-center gap-2">
        <Info className="w-4 h-4 text-cyan-400 shrink-0" />
        <span><strong>FSD Room Mapping:</strong> S1 (TV) | S3 (LP1, LP2) | S4 (LB4-6) | S7 (LB1-3) | S10 (LP3, LP4) | S2 (LB7-9) | S12 (LB10-12) | AC (Remote).</span>
      </div>
    </div>
  );
}
