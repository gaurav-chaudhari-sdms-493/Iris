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

  // The four bulb lines currently wired to the AZIOT relay. LED panels (S3, S10)
  // are excluded until Relay B is installed -- the backend rejects them today.
  const WIRED_SWITCHES = ['S2', 'S4', 'S7', 'S12'];

  const handleAllLightsOn = () => {
    setActivePreset('ALL_ON');
    onSetMode && onSetMode('MANUAL');
    WIRED_SWITCHES.forEach((swId) => {
      onToggleSwitch && onToggleSwitch(swId, true);
    });
  };

  const handleAllLightsOff = () => {
    setActivePreset('ALL_OFF');
    onSetMode && onSetMode('MANUAL');
    WIRED_SWITCHES.forEach((swId) => {
      onToggleSwitch && onToggleSwitch(swId, false);
    });
  };

  // Switch circuit states
  const isS1On = tvState === 'ON';
  const isS7On = Boolean(relayA[1]);  // Node 1: LB1, LB2, LB3 (S7)
  const isS4On = Boolean(relayA[2]);  // Node 2: LB4, LB5, LB6 (S4)
  const isS2On = Boolean(relayA[3]);  // Node 3: LB7, LB8, LB9 (S2)
  const isS12On = Boolean(relayA[4]); // Node 4: LB10, LB11, LB12 (S12)
  const isS3On = false;               // LP1, LP2 (Software Mock)
  const isS10On = false;              // LP3, LP4 (Software Mock)

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
  // `pending` marks hardware that is specced but not yet installed (Relay B).
  const renderSquarePanel = (id, isOn, switchId, pending = false) => (
    <div
      key={id}
      onClick={() => !pending && onToggleSwitch && onToggleSwitch(switchId, !isOn)}
      title={pending ? 'LED panels activate once Relay B is installed' : undefined}
      className={`select-none group flex justify-center relative z-10 ${pending ? 'cursor-not-allowed' : 'cursor-pointer'
        }`}
    >
      <div className={`relative w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 rounded-xl border-2 transition-all duration-300 flex flex-col items-center justify-center p-1 ${pending
        ? 'bg-slate-900/40 border-dashed border-slate-700/60 opacity-50'
        : isOn
          ? 'bg-gradient-to-br from-cyan-100 via-white to-cyan-300 border-cyan-300 shadow-[0_0_25px_6px_rgba(6,182,212,0.55)]'
          : 'bg-slate-900/90 border-slate-800 shadow-inner group-hover:border-slate-700'
        }`}>
        {!pending && <div className="absolute inset-1 border border-dashed border-slate-400/20 rounded-lg pointer-events-none" />}
        <span className={`text-xs sm:text-sm font-mono font-black tracking-wider ${pending ? 'text-slate-500' : isOn ? 'text-slate-950' : 'text-slate-200'
          }`}>
          {id}
        </span>
        <span className={`text-[8px] sm:text-[9px] font-mono font-bold leading-tight text-center ${pending ? 'text-slate-600' : isOn ? 'text-slate-900 font-extrabold' : 'text-slate-500'
          }`}>
          {pending ? 'RELAY B' : isOn ? 'LIT' : 'OFF'}
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

          {/* 4. Panels Only -- disabled until Relay B drives the LED panels */}
          <button
            disabled
            className="px-2.5 sm:px-3 py-1.5 rounded-xl font-extrabold text-xs flex items-center gap-1.5 border border-dashed border-slate-800 bg-slate-900/30 text-slate-600 cursor-not-allowed opacity-60"
            title="LED panels activate once Relay B is installed"
          >
            <Lightbulb className="w-3.5 h-3.5" />
            <span>Panels Only</span>
            <span className="text-[8px] font-mono tracking-wider">SOON</span>
          </button>

        </div>
      </div>

      {/* BLUEPRINT CEILING SURFACE WITH CONDUIT WIRING LINES FOR BULBS */}
      <div className="relative flex-1 flex flex-col justify-between bg-slate-950 border-2 border-slate-800 rounded-3xl p-2.5 sm:p-3.5 space-y-2 shadow-2xl bg-[linear-gradient(to_right,#1e293b20_1px,transparent_1px),linear-gradient(to_bottom,#1e293b20_1px,transparent_1px)] bg-[size:24px_24px]">

        {/* 1. TOP: TV TOP VIEW -- awaiting Broadlink IR blaster */}
        <div className="flex justify-center w-full relative z-10">
          <div
            title="TV control activates once the Broadlink IR blaster is installed"
            className="w-3/5 py-1 rounded-lg border-2 border-dashed border-slate-800 bg-slate-900/40 text-slate-600 text-center font-mono cursor-not-allowed opacity-60 transition-all flex items-center justify-center gap-1.5"
          >
            <Tv className="w-3.5 h-3.5 text-slate-700" />
            <span className="text-[10px] sm:text-[11px] font-black tracking-widest uppercase">
              TV DISPLAY (PENDING IR)
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
          {renderSquarePanel('LP1', isS3On, 'S3', true)}
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
            {renderSquarePanel('LP2', isS3On, 'S3', true)}
          </div>

          {/* CASSETTE AC UNIT -- awaiting Broadlink IR blaster */}
          <div
            title="AC control activates once the Broadlink IR blaster is installed"
            className="justify-self-center w-28 h-18 sm:w-34 sm:h-20 md:w-44 md:h-24 rounded-2xl border-2 border-dashed border-slate-800 bg-slate-900/40 text-slate-600 opacity-60 transition-all flex flex-col items-center justify-center gap-1 p-1.5 sm:p-2 relative z-10 cursor-not-allowed select-none"
          >
            {/* Louvers */}
            <div className="absolute top-1 left-2 right-2 h-0.5 bg-slate-800 rounded" />
            <div className="absolute bottom-1 left-2 right-2 h-0.5 bg-slate-800 rounded" />

            <div className="flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs font-black tracking-wider">
              <Wind className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-700" />
              <span>CASSETTE AC</span>
            </div>

            <span className="text-[8px] sm:text-[9px] font-mono font-bold tracking-wider text-slate-600 text-center leading-tight">
              PENDING IR
            </span>
          </div>

          <div className="justify-self-start">
            {renderSquarePanel('LP3', isS10On, 'S10', true)}
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
          {renderSquarePanel('LP4', isS10On, 'S10', true)}
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
