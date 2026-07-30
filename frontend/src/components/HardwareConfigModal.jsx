import React, { useState, useEffect } from 'react';
import { Wifi, Cpu, Settings, Activity, CheckCircle2, AlertCircle, RefreshCw, X, Play } from 'lucide-react';

export default function HardwareConfigModal({ isOpen, onClose }) {
  const [hwStatus, setHwStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testingChannel, setTestingChannel] = useState(null);
  const [msg, setMsg] = useState(null);

  // Form State
  const [address, setAddress] = useState('192.168.1.50');
  const [devId, setDevId] = useState('');
  const [localKey, setLocalKey] = useState('');
  const [version, setVersion] = useState(3.3);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/hardware/status');
      const data = await res.json();
      setHwStatus(data);
      if (data && data.device_info) {
        setAddress(data.device_info.ip || '192.168.1.50');
        setDevId(data.device_info.dev_id || '');
        setVersion(data.device_info.version || 3.3);
      }
    } catch (e) {
      console.error("Failed to fetch hardware status:", e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleToggleMock = async () => {
    setLoading(true);
    setMsg(null);
    try {
      const newMockMode = !(hwStatus?.mock_mode);
      const res = await fetch('/api/hardware/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mock_mode: newMockMode })
      });
      const data = await res.json();
      setHwStatus(data.hardware);
      setMsg({ type: 'success', text: `Switched to ${newMockMode ? 'MOCK' : 'REAL WI-FI'} mode.` });
    } catch (e) {
      setMsg({ type: 'error', text: "Failed to toggle hardware mode." });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetch('/api/hardware/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, dev_id: devId, local_key: localKey, version: parseFloat(version) })
      });
      const data = await res.json();
      setHwStatus(data.hardware);
      if (data.status === 'success' || data.hardware?.is_connected) {
        setMsg({ type: 'success', text: "AZIOT 4 Node credentials updated & connected successfully!" });
      } else {
        setMsg({ type: 'amber', text: "Credentials saved. Device in MOCK mode (verify IP & Local Key on Wi-Fi)." });
      }
    } catch (e) {
      setMsg({ type: 'error', text: "Error saving hardware configuration." });
    } finally {
      setLoading(false);
    }
  };

  const handleTestChannel = async (ch) => {
    setTestingChannel(ch);
    try {
      await fetch('/api/hardware/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: ch })
      });
      await fetchStatus();
    } catch (e) {
      console.error(`Channel ${ch} test failed:`, e);
    } finally {
      setTestingChannel(null);
    }
  };

  const isRealConnected = hwStatus && !hwStatus.mock_mode && hwStatus.is_connected;
  const isMock = hwStatus && hwStatus.mock_mode;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                AZIOT 4 Node Smart Switch Setup
              </h2>
              <p className="text-xs text-slate-400 font-mono">Wi-Fi Local Control (Light Bulbs LB1-LB12)</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto">

          {/* Connection Status Banner */}
          <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
            isRealConnected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : isMock
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}>
            <div className="flex items-center gap-3">
              <Wifi className="w-5 h-5 shrink-0" />
              <div>
                <div className="flex items-center gap-2 text-sm font-bold">
                  {isRealConnected ? "AZIOT Physical Switch CONNECTED (Wi-Fi)" : isMock ? "MOCK HARDWARE MODE (Dry Run)" : "DISCONNECTED"}
                  {hwStatus?.ping_ms && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      {hwStatus.ping_ms} ms
                    </span>
                  )}
                </div>
                <p className="text-xs opacity-80 font-mono mt-0.5">
                  {isRealConnected ? `IP: ${address} | Single AZIOT 4 Node Switch` : "Simulated software switches for testing."}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleToggleMock}
              disabled={loading}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-mono border transition-all shrink-0 ${
                isMock
                  ? 'bg-emerald-500 text-slate-950 border-emerald-400 hover:bg-emerald-400'
                  : 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
              }`}
            >
              {isMock ? "Enable Real Hardware" : "Switch to Mock"}
            </button>
          </div>

          {msg && (
            <div className={`p-3 rounded-lg text-xs font-mono border ${
              msg.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' :
              msg.type === 'amber' ? 'bg-amber-500/10 border-amber-500/30 text-amber-300' :
              'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}>
              {msg.text}
            </div>
          )}

          {/* Node Output Test Panel */}
          <div className="space-y-2">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>AZIOT 4 Output Relay Nodes</span>
              <span className="text-[10px] text-slate-500">Light Bulbs LB1-LB12</span>
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {[
                { ch: 1, label: "Node 1: TV Bulbs", sub: "S7 (LB1-3)" },
                { ch: 2, label: "Node 2: Upper Bulbs", sub: "S4 (LB4-6)" },
                { ch: 3, label: "Node 3: Lower Bulbs", sub: "S2 (LB7-9)" },
                { ch: 4, label: "Node 4: Far Bulbs", sub: "S12 (LB10-12)" },
              ].map((item) => {
                const isNodeOn = hwStatus?.nodes?.[`node_${item.ch}`]?.state;
                return (
                  <div
                    key={item.ch}
                    className={`p-3 rounded-xl border flex flex-col justify-between gap-2 ${
                      isNodeOn
                        ? 'bg-amber-500/15 border-amber-500/40 text-amber-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400'
                    }`}
                  >
                    <div>
                      <div className="text-xs font-bold font-mono text-slate-200">{item.label}</div>
                      <div className="text-[10px] text-slate-400">{item.sub}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleTestChannel(item.ch)}
                      disabled={testingChannel === item.ch}
                      className="w-full mt-1 py-1 px-2 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-cyan-300 border border-cyan-500/30 flex items-center justify-center gap-1 transition-colors"
                    >
                      {testingChannel === item.ch ? (
                        <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
                      ) : (
                        <Play className="w-3 h-3 text-cyan-400" />
                      )}
                      <span>Pulse Test</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Hardware Credentials Form */}
          <form onSubmit={handleSaveConfig} className="space-y-4 pt-2 border-t border-slate-800">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
              Wi-Fi Connection Credentials
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-slate-300 mb-1">AZIOT Switch IP Address</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="192.168.1.50"
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:border-cyan-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 mb-1">Protocol Version</label>
                <select
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:border-cyan-500 focus:outline-none"
                >
                  <option value={3.3}>3.3 (Standard AZIOT 4 Node)</option>
                  <option value={3.4}>3.4 (Tuya Updated)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 mb-1">Device ID (20 characters)</label>
                <input
                  type="text"
                  value={devId}
                  onChange={(e) => setDevId(e.target.value)}
                  placeholder="AZIOT_RELAY_A_ID_12345"
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:border-cyan-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-300 mb-1">Local Key (16 characters)</label>
                <input
                  type="password"
                  value={localKey}
                  onChange={(e) => setLocalKey(e.target.value)}
                  placeholder="16-character local secret"
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:border-cyan-500 focus:outline-none"
                  required
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[10px] text-slate-500 font-mono">
                Run `python3 backend/hardware/discover_relays.py` to find device IP.
              </span>

              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 shadow-md shadow-cyan-500/20"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Save Hardware Config
              </button>
            </div>
          </form>

        </div>

      </div>
    </div>
  );
}
