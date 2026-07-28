import React, { useState } from 'react';
import { Camera, Eye, Zap, AlertCircle } from 'lucide-react';

export default function LiveFeed({ telemetry, onSimulateHeadcount }) {
  const [streamError, setStreamError] = useState(false);

  const headcount = telemetry?.headcount ?? 0;
  const systemMode = telemetry?.system_mode ?? 'AUTO';
  const zeroStrikes = telemetry?.zero_occupancy_strikes ?? 0;

  return (
    <div className="iris-card flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                CCTV Camera Feed #1
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-mono">RTSP://192.168.1.100:554/stream1 • 5 FPS Pipeline</p>
            </div>
          </div>

          <span className="text-xs font-mono bg-slate-800 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700">
            Mode: <strong className="text-cyan-400">{systemMode}</strong>
          </span>
        </div>

        {/* Video Canvas Stream */}
        <div className="relative rounded-xl overflow-hidden border border-slate-800 bg-black aspect-video flex items-center justify-center">
          {!streamError ? (
            <img
              src="/video_feed"
              alt="Iris Live CCTV Stream"
              className="w-full h-full object-cover"
              onError={() => setStreamError(true)}
            />
          ) : (
            <div className="text-center p-6 text-slate-400">
              <AlertCircle className="w-10 h-10 mx-auto mb-2 text-amber-400" />
              <p className="text-sm font-semibold text-slate-200">Video Stream Standby</p>
              <button
                onClick={() => setStreamError(false)}
                className="mt-3 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-medium text-cyan-400 border border-slate-700 transition"
              >
                Retry Connection
              </button>
            </div>
          )}

          {/* CV Live Badges Overlay */}
          <div className="absolute top-3 left-3 flex gap-2">
            <div className="bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700 text-xs font-mono text-slate-200 flex items-center gap-2">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>YOLO Headcount: <strong className="text-cyan-400">{headcount}</strong></span>
            </div>

            {zeroStrikes > 0 && (
              <div className="bg-amber-950/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-amber-500/50 text-xs font-mono text-amber-300 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Vacancy Strike: {zeroStrikes}/3</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Headcount Simulation Test Controls */}
      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-400 font-mono">Simulate Headcount:</span>
        <div className="flex items-center gap-2">
          {[0, 1, 2, 4, 6].map((count) => (
            <button
              key={count}
              onClick={() => onSimulateHeadcount(count)}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition border ${
                headcount === count
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/60 font-bold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              }`}
            >
              {count} {count === 1 ? 'Person' : 'People'}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
