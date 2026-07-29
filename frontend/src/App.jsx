import React, { useState, useEffect, useRef } from 'react';
import LiveFeed from './components/LiveFeed';
import SpatialMap from './components/SpatialMap';
import Telemetry from './components/Telemetry';
import Switchboard from './components/Switchboard';
import Presets from './components/Presets';
import { Eye, Activity } from 'lucide-react';

export default function App() {
  const [telemetry, setTelemetry] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);

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
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, []);

  const sendWsAction = (actionPayload) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(actionPayload));
    }
  };

  const handleToggleSwitch = async (switchId, state) => {
    sendWsAction({ action: 'override', switch_id: switchId, state });
    try {
      await fetch('/api/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ switch_id: switchId, state })
      });
    } catch (e) {
      console.error("Failed REST override:", e);
    }
  };

  const handleSelectPreset = async (preset) => {
    sendWsAction({ action: 'preset', preset });
    try {
      await fetch('/api/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: preset })
      });
    } catch (e) {
      console.error("Failed REST mode set:", e);
    }
  };

  const handleAcChange = async (temperature, power) => {
    try {
      await fetch('/api/ac', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temperature, power, mode: 'COOL', fan_speed: 'AUTO' })
      });
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
    } else {
      try {
        await fetch('/api/player/control', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: controlAction, value })
        });
      } catch (e) {
        console.error("Failed REST player control:", e);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      
      {/* Header Bar */}
      <header className="iris-card flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20">
            <Eye className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-black tracking-tight text-slate-100 flex items-center gap-2">
              PROJECT IRIS
              <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                v1.0 FSD Engine
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-mono">Hybrid IoT & Computer Vision Office Automation System</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={`px-3.5 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-2 ${
            wsConnected 
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40' 
              : 'bg-amber-950/40 text-amber-300 border-amber-500/40'
          }`}>
            <Activity className="w-4 h-4" />
            <span>{wsConnected ? 'WebSocket Telemetry Live' : 'Connecting to Engine...'}</span>
          </div>
        </div>
      </header>

      {/* Telemetry Metrics Row */}
      <Telemetry telemetry={telemetry} onAcChange={handleAcChange} />

      {/* Grid: CCTV Stream & 2D Spatial Map */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
          onToggleSwitch={handleToggleSwitch}
        />
      </div>

      {/* Presets Macro Actions */}
      <Presets
        currentMode={telemetry?.system_mode}
        onSelectPreset={handleSelectPreset}
      />

      {/* Physical 12-Gang Switchboard Overrides */}
      <Switchboard
        relays={telemetry?.relays}
        tvState={telemetry?.tv_state}
        onToggleSwitch={handleToggleSwitch}
      />

      {/* Footer */}
      <footer className="text-center text-xs font-mono text-slate-500 pt-2 pb-4">
        Project Iris Technical FSD • Overhead CCTV Computer Vision & IoT Automation Engine
      </footer>

    </div>
  );
}
