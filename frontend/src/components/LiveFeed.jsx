import React, { useState, useRef, useEffect } from 'react';
import {
  Camera, Eye, Zap, AlertCircle, Play, Pause, RotateCcw, RotateCw,
  ChevronLeft, ChevronRight, Maximize, Minimize, Radio, Download, HelpCircle, Sliders
} from 'lucide-react';

export default function LiveFeed({ telemetry, onSimulateHeadcount, onPlayerControl }) {
  const [streamError, setStreamError] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
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

  // Listen to browser fullscreen state changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Format seconds to MM:SS
  const formatTime = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Keyboard shortcuts listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;

      if (e.code === 'Space' || e.code === 'KeyK') {
        e.preventDefault();
        onPlayerControl(isPaused ? 'play' : 'pause');
      } else if (e.code === 'ArrowLeft' || e.code === 'KeyJ') {
        e.preventDefault();
        onPlayerControl('seek_relative', -10);
      } else if (e.code === 'ArrowRight' || e.code === 'KeyL') {
        e.preventDefault();
        onPlayerControl('seek_relative', 10);
      } else if (e.code === 'KeyF') {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.code === 'KeyS') {
        e.preventDefault();
        handleTakeSnapshot();
      } else if (e.code === 'Comma') {
        e.preventDefault();
        onPlayerControl('step', -1);
      } else if (e.code === 'Period') {
        e.preventDefault();
        onPlayerControl('step', 1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPaused, onPlayerControl]);

  // Fullscreen Handler
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => console.error("Fullscreen error:", err));
    } else {
      document.exitFullscreen().catch(err => console.error("Exit Fullscreen error:", err));
    }
  };

  // Snapshot Capture Handler
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

  const sourceType = playerState?.source_type ?? 'video';
  const isCctv = sourceType === 'live_cctv';
  const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (currentTime / duration) * 100)) : 0;

  return (
    <div 
      ref={containerRef}
      className={
        isFullscreen
          ? "fixed inset-0 z-50 bg-slate-950 flex flex-col justify-between p-4 w-screen h-screen overflow-hidden select-none"
          : "iris-card flex flex-col justify-between"
      }
    >
      <div className={isFullscreen ? "flex-1 flex flex-col justify-between overflow-hidden" : ""}>
        
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
                Overhead CCTV Stream
                <span className="flex h-2.5 w-2.5 relative">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isPaused && !isCctv ? 'bg-amber-400' : 'bg-emerald-400'} opacity-75`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isPaused && !isCctv ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
                </span>
              </h2>
              <p className="text-xs text-slate-400 font-mono truncate max-w-[220px] md:max-w-xs">
                {sourceName}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHelp(!showHelp)}
              title="Keyboard Shortcuts"
              className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition text-xs flex items-center gap-1 cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
              <span className="hidden sm:inline font-mono">Shortcuts</span>
            </button>

            <span className="text-xs font-mono bg-slate-800/80 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700/80">
              Mode: <strong className="text-cyan-400">{systemMode}</strong>
            </span>
          </div>
        </div>

        {/* Shortcuts Box */}
        {showHelp && (
          <div className="mb-3 p-3 bg-slate-900/95 border border-cyan-500/30 rounded-xl text-xs font-mono text-slate-300 space-y-1 relative z-30">
            <button 
              onClick={() => setShowHelp(false)}
              className="absolute top-2 right-2 text-slate-400 hover:text-slate-200 font-bold"
            >
              ✕
            </button>
            <div className="font-bold text-cyan-400 flex items-center gap-1 mb-1">
              <Sliders className="w-3.5 h-3.5" /> Keyboard Controls:
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
              <div><kbd className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">Space / K</kbd> Play / Pause</div>
              <div><kbd className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">J / L</kbd> Seek -10s / +10s</div>
              <div><kbd className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">, / .</kbd> Step Frame prev / next</div>
              <div><kbd className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">F</kbd> Fullscreen</div>
              <div><kbd className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">S</kbd> Snapshot</div>
            </div>
          </div>
        )}

        {/* UNIFIED VIDEO PLAYER CONTAINER */}
        <div className={`rounded-2xl border-2 border-slate-800/90 overflow-hidden bg-slate-950 shadow-2xl flex flex-col justify-between ${
          isFullscreen ? 'flex-1 h-full relative' : ''
        }`}>
          
          {/* Top: Video Stream Canvas */}
          <div 
            onClick={() => !isCctv && onPlayerControl(isPaused ? 'play' : 'pause')}
            className={`relative flex items-center justify-center bg-slate-950 select-none ${
              isCctv ? '' : 'cursor-pointer group'
            } ${
              isFullscreen ? 'flex-1 w-full h-full' : 'aspect-video'
            }`}
            title={isCctv ? "Live Hikvision Camera Stream" : (isPaused ? "Click to Resume Video" : "Click to Stop Video")}
          >
            {!streamError ? (
              <img
                ref={imgRef}
                src="/video_feed"
                alt="Iris CCTV Stream"
                className="w-full h-full object-contain select-none pointer-events-none"
                onError={() => setStreamError(true)}
              />
            ) : (
              <div className="text-center p-6 text-slate-400">
                <AlertCircle className="w-10 h-10 mx-auto mb-2 text-amber-400" />
                <p className="text-sm font-semibold text-slate-200">Video Stream Standby</p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setStreamError(false);
                  }}
                  className="mt-3 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-medium text-cyan-400 border border-slate-700 transition cursor-pointer"
                >
                  Retry Connection
                </button>
              </div>
            )}

            {/* YOLO Badges Overlay */}
            <div className="absolute top-3 left-3 flex gap-2 z-10 pointer-events-none">
              <div className="bg-slate-950/80 backdrop-blur-md px-3 py-1 rounded-lg border border-slate-800 text-xs font-mono text-slate-200 flex items-center gap-1.5 shadow-md">
                <Eye className="w-3.5 h-3.5 text-cyan-400" />
                <span>YOLO Headcount: <strong className="text-cyan-400">{headcount}</strong></span>
              </div>

              {zeroStrikes > 0 && (
                <div className="bg-amber-950/80 backdrop-blur-md px-3 py-1 rounded-lg border border-amber-500/40 text-xs font-mono text-amber-300 flex items-center gap-1.5 shadow-md">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>Strike: {zeroStrikes}/3</span>
                </div>
              )}
            </div>

            {/* Centered Play Button Overlay when Paused (Recorded Video Only) */}
            {isPaused && !isCctv && (
              <div 
                className="absolute inset-0 z-20 flex items-center justify-center bg-black/40 backdrop-blur-[2px] cursor-pointer transition"
              >
                <div className="p-4 rounded-full bg-cyan-500/90 text-slate-950 shadow-xl shadow-cyan-500/20 hover:scale-110 transition flex items-center justify-center">
                  <Play className="w-8 h-8 fill-current ml-0.5" />
                </div>
              </div>
            )}
          </div>

          {/* Bottom: Player Controls Bar (YouTube-Style overlay at bottom during Fullscreen) */}
          <div className={`bg-slate-900/95 border-t border-slate-800/90 p-3 md:p-3.5 space-y-2.5 ${
            isFullscreen ? 'absolute bottom-0 left-0 right-0 z-40 bg-slate-950/90 backdrop-blur-md' : ''
          }`}>
            
            <div className="flex items-center justify-end pb-1">
              <button
                onClick={() => onPlayerControl('live')}
                title="Sync Live Stream"
                className={`px-2 py-0.5 rounded-lg text-xs font-mono font-bold flex items-center gap-1 border transition cursor-pointer ${
                  isLive
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                <Radio className={`w-3 h-3 ${isLive ? 'text-emerald-400' : ''}`} />
                <span>LIVE</span>
              </button>
            </div>

            {/* 1. Progress Slider & Timestamp */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-cyan-400 font-bold">{formatTime(currentTime)}</span>
                <span className="text-slate-400">{formatTime(duration)}</span>
              </div>

              <div className="relative flex items-center h-3.5 cursor-pointer group">
                <div className="absolute inset-0 h-1.5 my-auto bg-slate-800 rounded-full overflow-hidden w-full">
                  <div 
                    className="h-full bg-cyan-500 transition-all duration-75"
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
            </div>

            {/* 2. Control Toolbar (Play/Pause, Rewind, Forward, Step, Source, Speed, Utilities) */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/60">
              
              {/* Left Actions */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => onPlayerControl(isPaused ? 'play' : 'pause')}
                  title={isPaused ? "Play" : "Pause"}
                  className={`p-1.5 rounded-lg border transition flex items-center justify-center cursor-pointer ${
                    isPaused
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                      : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/30'
                  }`}
                >
                  {isPaused ? <Play className="w-4 h-4 fill-current ml-0.5" /> : <Pause className="w-4 h-4 fill-current" />}
                </button>

                <button
                  onClick={() => onPlayerControl('seek_relative', -10)}
                  title="Rewind 10s"
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition text-xs font-mono flex items-center gap-1 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>-10s</span>
                </button>

                <button
                  onClick={() => onPlayerControl('seek_relative', 10)}
                  title="Forward 10s"
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition text-xs font-mono flex items-center gap-1 cursor-pointer"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>+10s</span>
                </button>

                <button
                  onClick={() => onPlayerControl('step', -1)}
                  title="Step 1 frame backward"
                  className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700/80 transition cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                <button
                  onClick={() => onPlayerControl('step', 1)}
                  title="Step 1 frame forward"
                  className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700/80 transition cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {/* Right Selectors & Actions */}
              <div className="flex items-center gap-2">
                {availableSources.length > 0 && (
                  <select
                    value={activeSourceId}
                    onChange={(e) => onPlayerControl('set_source', parseInt(e.target.value, 10))}
                    title="Select Video Source"
                    className="bg-slate-800 text-cyan-300 text-xs font-mono px-2 py-1 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500 max-w-[120px] truncate cursor-pointer"
                  >
                    {availableSources.map((src) => (
                      <option key={src.id} value={src.id}>{src.name}</option>
                    ))}
                  </select>
                )}

                <select
                  value={playbackSpeed}
                  onChange={(e) => onPlayerControl('set_speed', parseFloat(e.target.value))}
                  title="Playback Speed"
                  className="bg-slate-800 text-slate-200 text-xs font-mono px-1.5 py-1 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  {[0.25, 0.5, 1.0, 1.5, 2.0].map((s) => (
                    <option key={s} value={s}>{s}x</option>
                  ))}
                </select>

                <button
                  onClick={handleTakeSnapshot}
                  title="Take Snapshot"
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition cursor-pointer"
                >
                  <Camera className="w-3.5 h-3.5 text-cyan-400" />
                </button>

                <button
                  onClick={toggleFullscreen}
                  title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Mode"}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition cursor-pointer"
                >
                  {isFullscreen ? <Minimize className="w-3.5 h-3.5 text-amber-400" /> : <Maximize className="w-3.5 h-3.5" />}
                </button>
              </div>

            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
