import React, { useState, useRef, useEffect } from 'react';
import {
  Camera, Eye, Zap, AlertCircle, Play, Pause, RotateCcw, RotateCw,
  ChevronLeft, ChevronRight, Maximize, Radio, HelpCircle, Download, Sliders
} from 'lucide-react';

export default function LiveFeed({ telemetry, onSimulateHeadcount, onPlayerControl }) {
  const [streamError, setStreamError] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const containerRef = useRef(null);
  const imgRef = useRef(null);

  const headcount = telemetry?.headcount ?? 0;
  const systemMode = telemetry?.system_mode ?? 'AUTO';
  const zeroStrikes = telemetry?.zero_occupancy_strikes ?? 0;
  
  const playerState = telemetry?.player_state ?? {};
  const isPaused = playerState?.is_paused ?? false;
  const currentTime = playerState?.current_time ?? 0;
  const duration = playerState?.duration ?? 0;
  const playbackSpeed = playerState?.playback_speed ?? 1.0;
  const activeSourceId = playerState?.active_source_id ?? 0;
  const availableSources = playerState?.available_sources ?? [];
  const isLive = playerState?.is_live ?? true;
  const sourceName = playerState?.source_name ?? 'CCTV Camera Stream';

  // Format seconds to MM:SS
  const formatTime = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Keyboard shortcuts event listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger shortcuts if focus is inside an input/select
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        onPlayerControl('toggle');
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        onPlayerControl('seek_relative', -10);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        onPlayerControl('seek_relative', 10);
      } else if (e.code === 'KeyF') {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.code === 'KeyS') {
        e.preventDefault();
        handleTakeSnapshot();
      } else if (e.code === 'KeyL') {
        e.preventDefault();
        onPlayerControl('live');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onPlayerControl]);

  // Fullscreen Handler
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => console.error("Fullscreen error:", err));
    } else {
      document.exitFullscreen().catch(err => console.error("Exit Fullscreen error:", err));
    }
  };

  // Capture & Download Frame Snapshot
  const handleTakeSnapshot = () => {
    if (!imgRef.current) return;
    try {
      const canvas = document.createElement('canvas');
      canvas.width = imgRef.current.naturalWidth || 1280;
      canvas.height = imgRef.current.naturalHeight || 720;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(imgRef.current, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg');
      
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = `iris_cctv_snapshot_${Date.now()}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) {
      console.error("Snapshot capture failed:", e);
    }
  };

  const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (currentTime / duration) * 100)) : 0;

  return (
    <div className="iris-card flex flex-col justify-between" ref={containerRef}>
      <div>
        {/* Card Header & Metadata */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                CCTV Camera Feed #1
                <span className="flex h-2 w-2 relative">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isPaused ? 'bg-amber-400' : 'bg-emerald-400'} opacity-75`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${isPaused ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-mono truncate max-w-[260px] md:max-w-xs">
                {sourceName}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHelp(!showHelp)}
              title="Keyboard Shortcuts Cheat Sheet"
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition text-xs flex items-center gap-1"
            >
              <HelpCircle className="w-4 h-4 text-cyan-400" />
              <span className="hidden sm:inline font-mono">Shortcuts</span>
            </button>

            <span className="text-xs font-mono bg-slate-800 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700">
              Mode: <strong className="text-cyan-400">{systemMode}</strong>
            </span>
          </div>
        </div>

        {/* Shortcuts Modal / Help Box */}
        {showHelp && (
          <div className="mb-3 p-3 bg-slate-900/90 border border-cyan-500/30 rounded-xl text-xs font-mono text-slate-300 space-y-1 relative">
            <button 
              onClick={() => setShowHelp(false)}
              className="absolute top-2 right-2 text-slate-400 hover:text-slate-200 font-bold"
            >
              ✕
            </button>
            <div className="font-bold text-cyan-400 flex items-center gap-1 mb-1">
              <Sliders className="w-3.5 h-3.5" /> Video Player Keyboard Controls:
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
              <div><kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">Space</kbd> Play / Pause</div>
              <div><kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">← / →</kbd> Rewind / Forward 10s</div>
              <div><kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">F</kbd> Toggle Fullscreen</div>
              <div><kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">S</kbd> Save Frame Snapshot</div>
              <div><kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">L</kbd> Sync Live Stream</div>
            </div>
          </div>
        )}

        {/* Video Canvas Container */}
        <div className="relative rounded-xl overflow-hidden border border-slate-800 bg-black aspect-video flex items-center justify-center group">
          {!streamError ? (
            <img
              ref={imgRef}
              src="/video_feed"
              alt="Iris Live CCTV Stream"
              className="w-full h-full object-cover select-none"
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
          <div className="absolute top-3 left-3 flex gap-2 z-10 pointer-events-none">
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

          {/* Status Overlay Badges (Paused / Speed) */}
          <div className="absolute top-3 right-3 flex gap-2 z-10">
            {isPaused && (
              <div className="bg-amber-500 text-slate-950 px-2.5 py-1 rounded-md font-mono text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-amber-500/20">
                <Pause className="w-3.5 h-3.5 fill-current" />
                PAUSED
              </div>
            )}
            {playbackSpeed !== 1.0 && !isPaused && (
              <div className="bg-cyan-500 text-slate-950 px-2.5 py-1 rounded-md font-mono text-xs font-bold flex items-center gap-1 shadow-lg shadow-cyan-500/20">
                SPEED: {playbackSpeed}x
              </div>
            )}
          </div>

          {/* Click Video to Play/Pause Overlay */}
          <div 
            onClick={() => onPlayerControl(isPaused ? 'play' : 'pause')}
            className="absolute inset-0 cursor-pointer flex items-center justify-center bg-black/0 hover:bg-black/10 transition"
          >
            {isPaused && (
              <div className="p-4 rounded-full bg-slate-950/70 border border-cyan-500/50 text-cyan-400 backdrop-blur-md shadow-2xl transition transform group-hover:scale-110">
                <Play className="w-8 h-8 fill-cyan-400 ml-1" />
              </div>
            )}
          </div>
        </div>

        {/* Video Player Timeline & Controls Bar */}
        <div className="mt-3 bg-slate-900/80 border border-slate-800 rounded-xl p-3 space-y-2.5">
          
          {/* Progress Timeline Slider */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-cyan-400 min-w-[42px]">
              {formatTime(currentTime)}
            </span>

            <div className="relative flex-1 flex items-center h-4 cursor-pointer group">
              <div className="absolute inset-0 h-1.5 my-auto bg-slate-800 rounded-full overflow-hidden w-full">
                <div 
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-75"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <input
                type="range"
                min="0"
                max={duration || 100}
                step="0.5"
                value={currentTime}
                onChange={(e) => onPlayerControl('seek', parseFloat(e.target.value))}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </div>

            <span className="text-xs font-mono text-slate-400 min-w-[42px] text-right">
              {formatTime(duration)}
            </span>
          </div>

          {/* Video Controls Action Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/80">
            
            {/* Left Controls: Play/Pause, Rewind, Step, Forward */}
            <div className="flex items-center gap-1.5">
              {/* Play / Pause */}
              <button
                onClick={() => onPlayerControl(isPaused ? 'play' : 'pause')}
                title={isPaused ? "Play (Space)" : "Pause (Space)"}
                className={`p-2 rounded-lg transition border flex items-center justify-center ${
                  isPaused
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                    : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/30'
                }`}
              >
                {isPaused ? <Play className="w-4 h-4 fill-current ml-0.5" /> : <Pause className="w-4 h-4 fill-current" />}
              </button>

              {/* Rewind -10s */}
              <button
                onClick={() => onPlayerControl('seek_relative', -10)}
                title="Rewind 10 seconds (←)"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-1 text-xs font-mono"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>-10s</span>
              </button>

              {/* Fast Forward +10s */}
              <button
                onClick={() => onPlayerControl('seek_relative', 10)}
                title="Forward 10 seconds (→)"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition flex items-center gap-1 text-xs font-mono"
              >
                <RotateCw className="w-3.5 h-3.5" />
                <span>+10s</span>
              </button>

              {/* Precision Step Prev Frame */}
              <button
                onClick={() => onPlayerControl('step', -1)}
                title="Step 1 frame backward"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {/* Precision Step Next Frame */}
              <button
                onClick={() => onPlayerControl('step', 1)}
                title="Step 1 frame forward"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>

              {/* Jump to Live Sync */}
              <button
                onClick={() => onPlayerControl('live')}
                title="Sync to real-time live stream (L)"
                className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5 border transition ${
                  isLive
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                <Radio className={`w-3.5 h-3.5 ${isLive ? 'text-emerald-400 animate-pulse' : ''}`} />
                <span>LIVE</span>
              </button>
            </div>

            {/* Right Controls: Playback Speed, Source Select, Snapshot, Fullscreen */}
            <div className="flex items-center gap-2">
              
              {/* Playback Speed Selector */}
              <select
                value={playbackSpeed}
                onChange={(e) => onPlayerControl('set_speed', parseFloat(e.target.value))}
                title="Playback Speed"
                className="bg-slate-800 text-slate-200 text-xs font-mono px-2 py-1.5 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                {[0.25, 0.5, 1.0, 1.5, 2.0].map((s) => (
                  <option key={s} value={s}>{s}x Speed</option>
                ))}
              </select>

              {/* Source Switcher */}
              {availableSources.length > 0 && (
                <select
                  value={activeSourceId}
                  onChange={(e) => onPlayerControl('set_source', parseInt(e.target.value, 10))}
                  title="Switch Video Source"
                  className="bg-slate-800 text-cyan-300 text-xs font-mono px-2 py-1.5 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500 max-w-[130px] md:max-w-[160px] truncate cursor-pointer"
                >
                  {availableSources.map((src) => (
                    <option key={src.id} value={src.id}>{src.name}</option>
                  ))}
                </select>
              )}

              {/* Snapshot Download Button */}
              <button
                onClick={handleTakeSnapshot}
                title="Capture & Download Snapshot Frame (S)"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                <Download className="w-4 h-4 text-cyan-400" />
              </button>

              {/* Fullscreen Button */}
              <button
                onClick={toggleFullscreen}
                title="Toggle Fullscreen (F)"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                <Maximize className="w-4 h-4" />
              </button>

            </div>
          </div>
        </div>
      </div>

      {/* Headcount Simulation Test Controls */}
      <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between">
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
