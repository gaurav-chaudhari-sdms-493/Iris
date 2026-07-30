import React, { useState, useEffect } from 'react';
import { Map, Tv, Wind, Zap, Moon, Lightbulb, Info, Bot } from 'lucide-react';

export default function SpatialMap({ zoneStates, relays, tvState, acState, systemMode, onToggleSwitch, onSetMode, onAcChange }) {
  const relayA = relays?.Relay_A ?? { 1: false, 2: false, 3: false, 4: false };
  const relayB = relays?.Relay_B ?? { 1: false, 2: false, 3: false, 4: false };

  // Mutually Exclusive Radio Toggle State ('AI_MODE' | 'ALL_ON' | 'ALL_OFF' | 'PANELS_ONLY')
  const [activePreset, setActivePreset] = useState('AI_MODE');

  useEffect(() => {
    if (systemMode === 'AUTO') {
      setActivePreset('AI_MODE');
    }
  }, [systemMode]);

  // Preset Handlers
  const handleAiAutoMode = () => {
    setActivePreset('AI_MODE');
    onSetMode && onSetMode('AUTO');
  };

  const handleAllLightsOn = () => {
    setActivePreset('ALL_ON');
    onSetMode && onSetMode('MANUAL');
    ['S2', 'S3', 'S4', 'S7', 'S10', 'S12'].forEach((swId) => {
      onToggleSwitch && onToggleSwitch(swId, true);
    });
  };

  const handleAllLightsOff = () => {
    setActivePreset('ALL_OFF');
    onSetMode && onSetMode('MANUAL');
    ['S2', 'S3', 'S4', 'S7', 'S10', 'S12'].forEach((swId) => {
      onToggleSwitch && onToggleSwitch(swId, false);
    });
  };

  const handlePanelsOnly = () => {
    setActivePreset('PANELS_ONLY');
    onSetMode && onSetMode('MANUAL');
    ['S3', 'S10'].forEach((swId) => onToggleSwitch && onToggleSwitch(swId, true));
    ['S2', 'S4', 'S7', 'S12'].forEach((swId) => onToggleSwitch && onToggleSwitch(swId, false));
  };

  // Switch circuit states
  const isS1On = tvState === 'ON';
  const isS2On = Boolean(relayB[1]);  // LB7, LB8, LB9
  const isS3On = Boolean(relayA[1]);  // LP1, LP2
  const isS4On = Boolean(relayA[4]);  // LB4, LB5, LB6
  const isS7On = Boolean(relayA[3]);  // LB1, LB2, LB3
  const isS10On = Boolean(relayA[2]); // LP3, LP4
  const isS12On = Boolean(relayB[2]); // LB10, LB11, LB12

  const isAcOn = (acState?.power ?? 'ON') === 'ON';
  const acTemp = acState?.temperature ?? 24;

  // CIRCULAR CEILING DOWNLIGHT BULB (Compact dimensions)
  const renderCircleBulb = (id, isOn, switchId) => (
    <div
      key={id}
      onClick={() => onToggleSwitch && onToggleSwitch(switchId, !isOn)}
      className="flex flex-col items-center gap-0.5 cursor-pointer select-none group relative z-10"
    >
      <div className={`relative w-8 h-8 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${isOn
        ? 'bg-slate-950 border-amber-400 shadow-[0_0_20px_4px_rgba(245,158,11,0.5)] scale-105'
        : 'bg-slate-950 border-slate-700/80 shadow-inner group-hover:border-slate-500'
        }`}>
        <div className={`rounded-full transition-all duration-300 ${isOn
          ? 'w-4 h-4 bg-gradient-to-tr from-amber-300 via-white to-amber-400 shadow-[0_0_8px_#f59e0b]'
          : 'w-3 h-3 bg-slate-800 border border-slate-700'
          }`} />
      </div>

      <span className={`text-[10px] font-mono font-bold transition-colors ${isOn ? 'text-amber-300' : 'text-slate-500'
        }`}>
        {id}
      </span>
    </div>
  );

  // ALL LED PANELS ARE COMPACT SQUARE TILES
  const renderSquarePanel = (id, isOn, switchId) => (
    <div
      key={id}
      onClick={() => onToggleSwitch && onToggleSwitch(switchId, !isOn)}
      className="cursor-pointer select-none group flex justify-center relative z-10"
    >
      <div className={`relative w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 rounded-xl border-2 transition-all duration-300 flex flex-col items-center justify-center p-1 ${isOn
        ? 'bg-gradient-to-br from-cyan-100 via-white to-cyan-300 border-cyan-300 shadow-[0_0_25px_6px_rgba(6,182,212,0.55)]'
        : 'bg-slate-900/90 border-slate-800 shadow-inner group-hover:border-slate-700'
        }`}>
        <div className="absolute inset-1 border border-dashed border-slate-400/20 rounded-lg pointer-events-none" />
        <span className={`text-xs sm:text-sm font-mono font-black tracking-wider ${isOn ? 'text-slate-950' : 'text-slate-200'}`}>
          {id}
        </span>
        <span className={`text-[8px] sm:text-[9px] font-mono font-bold ${isOn ? 'text-slate-900 font-extrabold' : 'text-slate-500'}`}>
          {isOn ? 'LIT' : 'OFF'}
        </span>
      </div>
    </div>
  );

  // HORIZONTAL ELECTRICAL WIRING BUS CONDUIT LINE (Connecting simultaneous bulbs only)
  const renderHorizontalWireBus = (isCircuitOn, circuitLabel) => (
    <div className="absolute left-6 right-6 top-4 h-1 flex items-center justify-between pointer-events-none z-0">
      <div className={`w-full h-0.5 transition-all duration-300 ${isCircuitOn
        ? 'bg-amber-400 shadow-[0_0_12px_#f59e0b]'
        : 'border-t border-dashed border-slate-800/80'
        }`} />

      {/* Circuit Badge Label on Wire */}
      <span className={`absolute right-0 -top-3 text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border transition-colors ${isCircuitOn
        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
        : 'bg-slate-900/80 text-slate-600 border-slate-800'
        }`}>
        {circuitLabel}
      </span>
    </div>
  );

  return (
    <div className="iris-card flex flex-col justify-between h-full space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Map className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Ceiling Topology
            </h2>
            <p className="text-xs text-slate-400 font-mono">Click any device to toggle power</p>
          </div>
        </div>

        {/* MUTUALLY EXCLUSIVE RADIO TOGGLE BUTTON GROUP (EXACTLY 1 IS ON AT ALL TIMES) */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 bg-slate-950 p-1.5 rounded-2xl border border-slate-800">

          {/* 1. AI Auto Mode */}
          <button
            onClick={handleAiAutoMode}
            className={`px-2.5 sm:px-3 py-1.5 rounded-xl font-extrabold text-xs flex items-center gap-1.5 border transition-all cursor-pointer active:scale-95 ${activePreset === 'AI_MODE'
              ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 border-emerald-400 shadow-md shadow-emerald-500/30'
              : 'bg-slate-900/60 hover:bg-slate-800 text-slate-400 border-transparent hover:text-slate-200'
              }`}
            title="Shift to AI AUTO Occupancy Mode"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>AI Mode</span>
          </button>

          {/* 2. All Lights ON */}
          <button
            onClick={handleAllLightsOn}
            className={`px-2.5 sm:px-3 py-1.5 rounded-xl font-extrabold text-xs flex items-center gap-1.5 border transition-all cursor-pointer active:scale-95 ${activePreset === 'ALL_ON'
              ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-slate-950 border-cyan-400 shadow-md shadow-cyan-500/30'
              : 'bg-slate-900/60 hover:bg-slate-800 text-slate-400 border-transparent hover:text-slate-200'
              }`}
            title="Turns all lights ON"
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>All Lights ON</span>
          </button>

          {/* 3. All Lights OFF */}
          <button
            onClick={handleAllLightsOff}
            className={`px-2.5 sm:px-3 py-1.5 rounded-xl font-extrabold text-xs flex items-center gap-1.5 border transition-all cursor-pointer active:scale-95 ${activePreset === 'ALL_OFF'
              ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white border-indigo-400 shadow-md shadow-indigo-500/30'
              : 'bg-slate-900/60 hover:bg-slate-800 text-slate-400 border-transparent hover:text-slate-200'
              }`}
            title="Turns all lights OFF"
          >
            <Moon className="w-3.5 h-3.5" />
            <span>All Lights OFF</span>
          </button>

          {/* 4. Panels Only */}
          <button
            onClick={handlePanelsOnly}
            className={`px-2.5 sm:px-3 py-1.5 rounded-xl font-extrabold text-xs flex items-center gap-1.5 border transition-all cursor-pointer active:scale-95 ${activePreset === 'PANELS_ONLY'
              ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white border-purple-400 shadow-md shadow-purple-500/30'
              : 'bg-slate-900/60 hover:bg-slate-800 text-slate-400 border-transparent hover:text-slate-200'
              }`}
            title="Turns LED Panels ON only"
          >
            <Lightbulb className="w-3.5 h-3.5" />
            <span>Panels Only</span>
          </button>

        </div>
      </div>

      {/* BLUEPRINT CEILING SURFACE WITH CONDUIT WIRING LINES FOR BULBS */}
      <div className="relative flex-1 flex flex-col justify-between bg-slate-950 border-2 border-slate-800 rounded-3xl p-2.5 sm:p-3.5 space-y-2 shadow-2xl bg-[linear-gradient(to_right,#1e293b20_1px,transparent_1px),linear-gradient(to_bottom,#1e293b20_1px,transparent_1px)] bg-[size:24px_24px]">

        {/* 1. TOP: TV TOP VIEW */}
        <div className="flex justify-center w-full relative z-10">
          <div
            onClick={() => onToggleSwitch && onToggleSwitch('S1', !isS1On)}
            className={`w-3/5 py-1 rounded-lg border-2 text-center font-mono cursor-pointer transition-all flex items-center justify-center gap-1.5 shadow-md ${isS1On
              ? 'bg-gradient-to-r from-purple-950 via-purple-900 to-purple-950 border-purple-400 text-purple-200 shadow-[0_0_15px_rgba(168,85,247,0.4)]'
              : 'bg-slate-900/90 border-slate-800 text-slate-500 hover:border-slate-700'
              }`}
          >
            <Tv className={`w-3.5 h-3.5 ${isS1On ? 'text-purple-400' : 'text-slate-600'}`} />
            <span className="text-[10px] sm:text-[11px] font-black tracking-widest uppercase">
              TV DISPLAY {isS1On ? '(S1 ON)' : '(OFF)'}
            </span>
          </div>
        </div>

        {/* 2. ROW 1: LB1 | LB2 | LB3 CONNECTED BY S7 WIRE CONDUIT */}
        <div className="relative">
          {renderHorizontalWireBus(isS7On, 'S7')}
          <div className="grid grid-cols-3 gap-2 items-center justify-items-center relative z-10">
            {renderCircleBulb('LB1', isS7On, 'S7')}
            {renderCircleBulb('LB2', isS7On, 'S7')}
            {renderCircleBulb('LB3', isS7On, 'S7')}
          </div>
        </div>

        {/* 3. ROW 2: SQUARE 2x2 PANEL LP1 (S3 CIRCUIT) */}
        <div className="flex justify-center w-full relative">
          {renderSquarePanel('LP1', isS3On, 'S3')}
        </div>

        {/* 4. ROW 3: LB4 | LB5 | LB6 CONNECTED BY S4 WIRE CONDUIT */}
        <div className="relative">
          {renderHorizontalWireBus(isS4On, 'S4')}
          <div className="grid grid-cols-3 gap-2 items-center justify-items-center relative z-10">
            {renderCircleBulb('LB4', isS4On, 'S4')}
            {renderCircleBulb('LB5', isS4On, 'S4')}
            {renderCircleBulb('LB6', isS4On, 'S4')}
          </div>
        </div>

        {/* 5. ROW 4: SQUARE LP2 (S3) | SQUARE AC | SQUARE LP3 (S10) */}
        <div className="grid grid-cols-3 gap-1 sm:gap-2 items-center relative">
          <div className="justify-self-end">
            {renderSquarePanel('LP2', isS3On, 'S3')}
          </div>

          {/* INTERACTIVE CASSETTE AC UNIT */}
          <div
            onClick={() => onAcChange && onAcChange({ power: isAcOn ? 'OFF' : 'ON' })}
            className={`justify-self-center w-28 h-18 sm:w-34 sm:h-20 md:w-44 md:h-24 rounded-2xl border-2 transition-all flex flex-col items-center justify-between p-1.5 sm:p-2 relative shadow-xl z-10 cursor-pointer select-none group ${isAcOn
              ? 'bg-slate-950 border-emerald-500 text-emerald-300 shadow-[0_0_25px_rgba(16,185,129,0.45)] hover:border-emerald-400 hover:scale-[1.02]'
              : 'bg-slate-900/90 border-slate-800 text-slate-500 hover:border-slate-700 hover:scale-[1.02]'
              }`}
            title="Click AC cassette to toggle Power ON / OFF"
          >
            {/* Louvers */}
            <div className="absolute top-1 left-2 right-2 h-0.5 bg-slate-700/80 rounded" />
            <div className="absolute bottom-1 left-2 right-2 h-0.5 bg-slate-700/80 rounded" />

            <div className="flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs font-black tracking-wider mt-0.5">
              <Wind className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${isAcOn ? 'text-emerald-400 animate-spin' : 'text-slate-600'}`} />
              <span>AC {isAcOn ? '(ON)' : '(OFF)'}</span>
            </div>

            {/* Interactive Temp Control Badge with - and + buttons */}
            <div className="flex items-center gap-1 sm:gap-1.5 z-20 my-0.5">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAcChange && onAcChange({ temperature: Math.max(16, acTemp - 1) });
                }}
                disabled={!isAcOn}
                className="w-5 h-5 sm:w-6 sm:h-6 rounded-md bg-slate-900 hover:bg-emerald-600/40 text-emerald-300 font-black text-xs flex items-center justify-center border border-emerald-500/40 cursor-pointer active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed transition shadow"
                title="Decrease Temperature (-1°C)"
              >
                -
              </button>

              <span className={`text-[9px] sm:text-[11px] font-extrabold px-1.5 sm:px-2 py-0.5 rounded-full border ${isAcOn
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm'
                : 'bg-slate-800 text-slate-500 border-slate-700'
                }`}>
                {isAcOn ? `${acTemp}°C` : 'OFF'}
              </span>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAcChange && onAcChange({ temperature: Math.min(30, acTemp + 1) });
                }}
                disabled={!isAcOn}
                className="w-5 h-5 sm:w-6 sm:h-6 rounded-md bg-slate-900 hover:bg-emerald-600/40 text-emerald-300 font-black text-xs flex items-center justify-center border border-emerald-500/40 cursor-pointer active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed transition shadow"
                title="Increase Temperature (+1°C)"
              >
                +
              </button>
            </div>
          </div>

          <div className="justify-self-start">
            {renderSquarePanel('LP3', isS10On, 'S10')}
          </div>
        </div>

        {/* 6. ROW 5: LB7 | LB8 | LB9 CONNECTED BY S2 WIRE CONDUIT */}
        <div className="relative">
          {renderHorizontalWireBus(isS2On, 'S2')}
          <div className="grid grid-cols-3 gap-4 items-center justify-items-center relative z-10">
            {renderCircleBulb('LB7', isS2On, 'S2')}
            {renderCircleBulb('LB8', isS2On, 'S2')}
            {renderCircleBulb('LB9', isS2On, 'S2')}
          </div>
        </div>

        {/* 7. ROW 6: SQUARE 2x2 PANEL LP4 (S10 CIRCUIT) */}
        <div className="flex justify-center w-full relative">
          {renderSquarePanel('LP4', isS10On, 'S10')}
        </div>

        {/* 8. ROW 7: LB10 | LB11 | LB12 CONNECTED BY S12 WIRE CONDUIT */}
        <div className="relative">
          {renderHorizontalWireBus(isS12On, 'S12')}
          <div className="grid grid-cols-3 gap-4 items-center justify-items-center relative z-10">
            {renderCircleBulb('LB10', isS12On, 'S12')}
            {renderCircleBulb('LB11', isS12On, 'S12')}
            {renderCircleBulb('LB12', isS12On, 'S12')}
          </div>
        </div>

      </div>
    </div>
  );
}
