import React, { useState, useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';

export default function SystemLog({ telemetry }) {
  const [logs, setLogs] = useState([]);
  
  const prevHeadcountRef = useRef(null);
  const prevAcRef = useRef(null);
  const prevRelaysRef = useRef(null);
  const prevModeRef = useRef(null);

  // Auto-generate user-friendly logs from live incoming telemetry data
  useEffect(() => {
    if (!telemetry) return;

    const timeStr = new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });

    const newEntries = [];

    // 1. Live Headcount & Zone Detection log (Human Readable)
    if (telemetry.headcount !== undefined && telemetry.headcount !== prevHeadcountRef.current) {
      const currentCount = telemetry.headcount;
      prevHeadcountRef.current = currentCount;

      let msg = '';
      if (currentCount === 0) {
        msg = 'Room is empty — Vacancy timer initiated';
      } else if (currentCount === 1) {
        msg = '1 occupant detected in office';
      } else if (currentCount <= 3) {
        msg = `${currentCount} occupants detected — LED Panels active`;
      } else {
        msg = `${currentCount} occupants detected — Full lighting & AC active`;
      }

      newEntries.push({
        id: Date.now() + Math.random(),
        time: timeStr,
        icon: '👥',
        category: 'Camera AI',
        badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
        msg
      });
    }

    // 2. Live AC State log (Human Readable)
    if (telemetry.ac_state) {
      const acKey = `${telemetry.ac_state.power}-${telemetry.ac_state.temperature}-${telemetry.ac_state.mode}-${telemetry.ac_state.fan_speed}`;
      if (prevAcRef.current && prevAcRef.current !== acKey) {
        const power = telemetry.ac_state.power;
        const temp = telemetry.ac_state.temperature;
        const mode = telemetry.ac_state.mode;

        let msg = '';
        if (power === 'OFF') {
          msg = 'Air Conditioner turned OFF';
        } else {
          msg = `AC set to ${temp}°C (${mode.toLowerCase()} mode)`;
        }

        newEntries.push({
          id: Date.now() + Math.random(),
          time: timeStr,
          icon: '❄️',
          category: 'AC Unit',
          badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
          msg
        });
      }
      prevAcRef.current = acKey;
    }

    // 3. Live Relays / Lighting log (Human Readable)
    if (telemetry.relays) {
      const relaysKey = JSON.stringify(telemetry.relays);
      if (prevRelaysRef.current && prevRelaysRef.current !== relaysKey) {
        const rA = telemetry.relays.Relay_A || {};
        const rB = telemetry.relays.Relay_B || {};

        const activeLights = [];
        if (rA[1]) activeLights.push('Upper Panels (LP1, LP2)');
        if (rA[2]) activeLights.push('Lower Panels (LP3, LP4)');
        if (rA[3]) activeLights.push('TV Area Bulbs (LB1-LB3)');
        if (rA[4]) activeLights.push('Upper Bulbs (LB4-LB6)');
        if (rB[1]) activeLights.push('Lower Bulbs (LB7-LB9)');
        if (rB[2]) activeLights.push('Far Bulbs (LB10-LB12)');

        let msg = '';
        if (activeLights.length === 0) {
          msg = 'All lights turned OFF';
        } else if (activeLights.length === 6) {
          msg = 'All lights turned ON';
        } else {
          msg = `Active: ${activeLights.join(', ')}`;
        }

        newEntries.push({
          id: Date.now() + Math.random(),
          time: timeStr,
          icon: '💡',
          category: 'Lighting',
          badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          msg
        });
      }
      prevRelaysRef.current = relaysKey;
    }

    // 4. System Mode log
    if (telemetry.system_mode && prevModeRef.current && prevModeRef.current !== telemetry.system_mode) {
      newEntries.push({
        id: Date.now() + Math.random(),
        time: timeStr,
        icon: '🎛️',
        category: 'System Mode',
        badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
        msg: `Switched to ${telemetry.system_mode === 'AUTO' ? 'AI Auto Occupancy Mode' : 'Manual Override Mode'}`
      });
    }
    prevModeRef.current = telemetry.system_mode;

    if (newEntries.length > 0) {
      setLogs((prev) => [...newEntries.reverse(), ...prev.slice(0, 99)]);
    }
  }, [telemetry]);

  const handleClearLog = () => {
    setLogs([]);
  };

  return (
    <div className="iris-card space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-slate-100 font-bold text-sm md:text-base">
          <span className="text-lg">📜</span>
          <span>Live System Event Log</span>
        </div>
        
        <button
          onClick={handleClearLog}
          className="px-3 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700/80 cursor-pointer transition-all active:scale-95 flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5 text-slate-400" />
          <span>Clear Log</span>
        </button>
      </div>

      {/* User-Friendly Event Console */}
      <div className="bg-slate-950 border-2 border-slate-800/90 rounded-2xl p-3 md:p-3.5 h-48 overflow-y-auto font-sans text-xs space-y-2 shadow-inner select-text scrollbar-thin scrollbar-thumb-slate-800">
        {logs.length === 0 ? (
          <div className="text-slate-500 italic py-6 text-center font-mono text-xs">
            No system events logged yet. Waiting for live telemetry stream...
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex flex-wrap sm:flex-nowrap items-center gap-2 bg-slate-900/70 border border-slate-800/90 p-2 rounded-xl text-slate-200 transition-all hover:bg-slate-900">
              <span className="text-sm shrink-0">{log.icon}</span>
              
              <span className={`text-[9px] font-mono font-extrabold px-2 py-0.5 rounded-md border shrink-0 uppercase tracking-wider ${log.badgeColor}`}>
                {log.category}
              </span>

              <span className="font-semibold text-slate-100 flex-1 min-w-[150px]">
                {log.msg}
              </span>

              <span className="text-[10px] font-mono text-slate-400 shrink-0 ml-auto">
                {log.time}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
