import React, { useState, useEffect, useRef } from 'react';
import { Trash2 } from 'lucide-react';

export default function SystemLog({ telemetry }) {
  const [logs, setLogs] = useState([]);
  
  const prevHeadcountRef = useRef(null);
  const prevAcRef = useRef(null);
  const prevRelaysRef = useRef(null);

  // Auto-generate logs ONLY from live incoming telemetry data
  useEffect(() => {
    if (!telemetry) return;

    const timeStr = new Date().toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });

    const newEntries = [];

    // 1. Live Headcount & Zone Detection log
    if (telemetry.headcount !== undefined && telemetry.headcount !== prevHeadcountRef.current) {
      prevHeadcountRef.current = telemetry.headcount;

      const activeZones = Object.entries(telemetry.zone_states || {})
        .filter(([_, isActive]) => isActive)
        .map(([zId, _]) => zId.replace(/_/g, ' '))
        .join(', ');

      newEntries.push({
        id: Date.now() + Math.random(),
        time: timeStr,
        icon: '🤖',
        tag: '[YOLOv8 DETECTED]',
        msg: `REAL HEADCOUNT: ${telemetry.headcount} PERSONS | Active: ${activeZones || 'None'}`
      });
    }

    // 2. Live AC State log
    if (telemetry.ac_state) {
      const acKey = `${telemetry.ac_state.power}-${telemetry.ac_state.temperature}-${telemetry.ac_state.mode}-${telemetry.ac_state.fan_speed}`;
      if (prevAcRef.current && prevAcRef.current !== acKey) {
        newEntries.push({
          id: Date.now() + Math.random(),
          time: timeStr,
          icon: '❄️',
          tag: '[AC CLIMATE IR]',
          msg: `Power: ${telemetry.ac_state.power} | Temp: ${telemetry.ac_state.temperature}°C | Mode: ${telemetry.ac_state.mode} | Fan: ${telemetry.ac_state.fan_speed}`
        });
      }
      prevAcRef.current = acKey;
    }

    // 3. Live Relays log
    if (telemetry.relays) {
      const relaysKey = JSON.stringify(telemetry.relays);
      if (prevRelaysRef.current && prevRelaysRef.current !== relaysKey) {
        newEntries.push({
          id: Date.now() + Math.random(),
          time: timeStr,
          icon: '⚡',
          tag: '[AZIOT RELAY BUS]',
          msg: `Relay A: ${JSON.stringify(telemetry.relays.Relay_A)} | Relay B: ${JSON.stringify(telemetry.relays.Relay_B)}`
        });
      }
      prevRelaysRef.current = relaysKey;
    }

    if (newEntries.length > 0) {
      // Prepend newest logs at the top so the latest log is immediately visible without scrolling the screen
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
          className="px-3.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700/80 cursor-pointer transition-all active:scale-95 flex items-center gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5 text-slate-400" />
          <span>Clear Log</span>
        </button>
      </div>

      {/* Terminal Console */}
      <div className="bg-slate-950 border-2 border-slate-800/90 rounded-2xl p-3 md:p-4 h-48 overflow-y-auto font-mono text-xs text-emerald-400 space-y-2 shadow-inner select-text scrollbar-thin scrollbar-thumb-slate-800">
        {logs.length === 0 ? (
          <div className="text-slate-600 italic py-4 text-center">No system events logged yet. Waiting for live telemetry stream...</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="leading-relaxed flex items-start gap-2">
              <span className="text-emerald-500 font-bold shrink-0">[{log.time}]</span>
              <span className="shrink-0">{log.icon}</span>
              <span className="text-emerald-300 font-black shrink-0">{log.tag}</span>
              <span className="text-emerald-400 break-words">{log.msg}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
