import React, { useState, useEffect, useRef } from 'react';
import LiveFeed from './components/LiveFeed';
import SpatialMap from './components/SpatialMap';
import Telemetry from './components/Telemetry';
import Switchboard from './components/Switchboard';
import SystemLog from './components/SystemLog';
import { Eye, TrendingDown, Zap } from 'lucide-react';

export default function App() {
  const [telemetry, setTelemetry] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);

  const metrics = telemetry?.energy_metrics ?? { active_kw: 1.8, kwh_saved_today: 0.42, cost_saved_usd: 0.06 };

  useEffect(() => {
    let isDisposed = false;
    let reconnectTimer = null;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

    function connect() {
      if (isDisposed) return;
      console.log("[Iris Frontend] Connecting to WebSocket telemetry at:", wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (isDisposed) {
          ws.close();
          return;
        }
        console.log("[Iris Frontend] WebSocket Telemetry connected.");
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setTelemetry(data);
        } catch (e) {
          console.error("Failed to parse telemetry payload:", e);
        }
      };

      ws.onerror = (err) => {
        if (!isDisposed) console.warn("WebSocket connection error:", err);
      };

      ws.onclose = () => {
        if (isDisposed) return;
        console.log("WebSocket connection closed. Reconnecting in 2s...");
        setWsConnected(false);
        reconnectTimer = setTimeout(connect, 2000);
      };

      wsRef.current = ws;
    }

    connect();

    return () => {
      isDisposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        const socket = wsRef.current;
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;

        if (socket.readyState === WebSocket.CONNECTING) {
          socket.onopen = () => {
            try { socket.close(); } catch (e) { }
          };
        } else {
          try { socket.close(); } catch (e) { }
        }
      }
    };
  }, []);

  const sendWsAction = (actionPayload) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(actionPayload));
    }
  };

  const handleToggleSwitch = async (switchId, state) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      sendWsAction({ action: 'override', switch_id: switchId, state });
    } else {
      try {
        await fetch('/api/override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ switch_id: switchId, state })
        });
      } catch (e) {
        console.error("Failed REST override:", e);
      }
    }
  };

  const handleAcChange = async (acParams, powerArg) => {
    let payload = {};
    if (typeof acParams === 'object' && acParams !== null) {
      payload = acParams;
    } else {
      payload = { temperature: acParams, power: powerArg };
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      sendWsAction({ action: 'ac_control', ...payload });
    }

    try {
      const res = await fetch('/api/ac', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data && data.ac_state) {
        setTelemetry(prev => prev ? { ...prev, ac_state: data.ac_state } : prev);
      }
    } catch (e) {
      console.error("Failed REST AC set:", e);
    }
  };

  const handleSimulateHeadcount = (count) => {
    sendWsAction({ action: 'headcount_simulate', count });
  };

  const handlePlayerControl = async (controlAction, value = null) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      sendWsAction({ action: 'player_control', control_action: controlAction, value });
    }
    try {
      const res = await fetch('/api/player/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: controlAction, value })
      });
      const data = await res.json();
      if (data && data.player_state) {
        setTelemetry(prev => prev ? { ...prev, player_state: data.player_state } : prev);
      }
    } catch (e) {
      console.error("Player control dispatch error:", e);
    }
  };

  const handleSetMode = async (mode) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      sendWsAction({ action: 'preset', preset: mode });
    }
    try {
      const res = await fetch('/api/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      const data = await res.json();
      if (data && data.telemetry) {
        setTelemetry(data.telemetry);
      }
    } catch (e) {
      console.error("Failed REST mode set:", e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-3 sm:p-5 lg:p-8 w-full space-y-4 sm:space-y-6">

      {/* Compact Top Header Bar */}
      <header className="iris-card flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-2.5 px-3.5 sm:px-5">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="p-2 rounded-xl bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20 shrink-0">
            <Eye className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div>
            <h1 className="text-sm sm:text-base md:text-lg font-black tracking-tight text-slate-100 flex items-center gap-2">
              PROJECT IRIS
            </h1>
            <p className="text-[10px] sm:text-[11px] text-slate-400 font-mono">Hybrid IoT & Computer Vision Office Automation System</p>
          </div>
        </div>

        {/* Daily Energy Savings Header Badge */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 bg-slate-900/90 border border-amber-500/30 px-3 sm:px-3.5 py-1.5 rounded-xl shadow-md max-w-full overflow-hidden">
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
            <TrendingDown className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </div>
          <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
            <div>
              <span className="text-[9px] sm:text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Daily Energy Savings</span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xs sm:text-sm font-extrabold font-mono text-amber-400">{metrics.kwh_saved_today} kWh</span>
                <span className="text-[9px] sm:text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30">
                  ${metrics.cost_saved_usd} Saved
                </span>
              </div>
            </div>
            <div className="hidden sm:block h-6 w-[1px] bg-slate-800" />
            <div className="text-[10px] sm:text-[11px] text-slate-400 font-mono flex items-center gap-1">
              <Zap className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-amber-400" />
              <span>Load: {metrics.active_kw} kW</span>
            </div>
          </div>
        </div>
      </header>

      {/* PRIMARY FEATURE SECTION (TOP FOCUS): Side-by-Side Grid (Left: Overhead CCTV Stream | Right: 2D Ceiling Topology) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 items-stretch">
        <LiveFeed
          telemetry={telemetry}
          onSimulateHeadcount={handleSimulateHeadcount}
          onPlayerControl={handlePlayerControl}
        />
        <SpatialMap
          zoneStates={telemetry?.zone_states}
          relays={telemetry?.relays}
          tvState={telemetry?.tv_state}
          acState={telemetry?.ac_state}
          systemMode={telemetry?.system_mode}
          onToggleSwitch={handleToggleSwitch}
          onSetMode={handleSetMode}
          onAcChange={handleAcChange}
        />
      </div>

      {/* SECONDARY SECTION: AC Remote, Event Console & Physical Switchboard Overrides */}
      <Telemetry
        telemetry={telemetry}
        onAcChange={handleAcChange}
        onToggleSwitch={handleToggleSwitch}
      />

      {/* Footer */}
      <footer className="text-center text-xs font-mono text-slate-500 pt-2 pb-4">
        Project Iris Technical FSD • Overhead CCTV Computer Vision & IoT Automation Engine
      </footer>

    </div>
  );
}
