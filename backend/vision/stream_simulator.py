"""
Synthetic CCTV Office Stream Generator
Generates realistic synthetic overhead CCTV camera frames for Project Iris testing & demo mode.
Includes moving occupants across 3 spatial zones, furniture layouts, and dynamic lighting state overlays.
"""

import time
import math
import numpy as np
import cv2

import os
import logging
import threading
from config import VIDEO_PATH, CCTV_SNAPSHOT_WIDTH, CCTV_SNAPSHOT_HEIGHT

# Without an explicit resolution the Hikvision ISAPI picture endpoint serves the
# 704x480 sub-stream. Upscaling that to 1280x720 for inference smears exactly the
# small overhead heads we need, so pull the full-resolution frame instead.
SNAPSHOT_QUERY = f"?videoResolutionWidth={CCTV_SNAPSHOT_WIDTH}&videoResolutionHeight={CCTV_SNAPSHOT_HEIGHT}"

logger = logging.getLogger("iris.vision.stream")

class SyntheticStreamGenerator:
    def __init__(self, width=1280, height=720, fps=15):
        self.width = width
        self.height = height
        self.fps = fps
        self.start_time = time.time()
        self.cap = None
        self.video_source_path = None
        self.lock = threading.Lock()
        
        # Player state
        self.is_paused = False
        self.playback_speed = 1.0  # 0.25, 0.5, 1.0, 1.5, 2.0
        self.current_frame_pos = 0
        self.total_frames = 0
        self.video_fps = float(fps)
        self.duration_sec = 0.0
        self.last_frame = None
        self.active_source_index = 0
        self.available_sources = []
        self.step_delay_counter = 0

        # Live CCTV snapshots are pulled by a background worker instead of inline,
        # so a slow or unreachable camera never stalls the 5 FPS telemetry loop.
        # cctv_lock guards only the frame handoff -- never held across network IO.
        self.cctv_session = None
        self.cctv_lock = threading.Lock()
        self.cctv_frame = None
        self.cctv_frame_ts = 0.0
        self.cctv_frame_seq = 0
        # Sequence number of the frame handed out by the last read_frame() call.
        # Lets the orchestrator tell a genuinely new frame from a re-served one.
        self.last_served_seq = 0
        self.cctv_thread = None
        self.cctv_stop = threading.Event()
        self.cctv_timeout = float(os.environ.get("IRIS_CCTV_TIMEOUT", 6.0))
        self.cctv_interval = float(os.environ.get("IRIS_CCTV_INTERVAL", 0.2))
        self.cctv_max_stale = float(os.environ.get("IRIS_CCTV_MAX_STALE", 5.0))
        self._cctv_last_error_log = 0.0

        # Virtual Occupants state for synthetic fallback
        self.occupants = [
            {"x": 200, "y": 200, "tx": 400, "ty": 250, "speed": 2.5, "hue": (50, 120, 250)},
            {"x": 250, "y": 550, "tx": 350, "ty": 600, "speed": 1.8, "hue": (200, 100, 50)},
            {"x": 900, "y": 450, "tx": 1000, "ty": 400, "speed": 2.0, "hue": (100, 200, 50)}
        ]

        self._discover_video_sources()
        self._load_active_source()

    def _discover_video_sources(self):
        """Registers live CCTV sources and scans backend/data for video files."""
        cctv_ip = os.environ.get("CCTV_IP", "192.168.0.21")
        found = []

        # 1. PRIMARY DEFAULT SOURCE (INDEX 0): Hikvision Camera 06
        found.append({
            "id": 0,
            "name": f"[Live Camera] Hikvision Camera 06 ({cctv_ip})",
            "path": f"http://{cctv_ip}/ISAPI/Streaming/channels/601/picture{SNAPSHOT_QUERY}",
            "type": "live_cctv"
        })

        # 2. Add remaining Hikvision channels (1, 2, 3, 4, 5, 7..16)
        for ch_num in range(1, 17):
            if ch_num == 6:
                continue
            ch_code = f"{ch_num}01"
            found.append({
                "id": len(found),
                "name": f"[Live Camera] Hikvision Camera {ch_num:02d} ({cctv_ip})",
                "path": f"http://{cctv_ip}/ISAPI/Streaming/channels/{ch_code}/picture{SNAPSHOT_QUERY}",
                "type": "live_cctv"
            })

        # 3. Discover local MP4 demo videos
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend dir
        root_dir = os.path.dirname(base_dir)  # project root

        search_roots = [
            os.path.join(base_dir, "data"),
            os.path.join(root_dir, "data"),
            os.path.join(os.getcwd(), "data"),
        ]

        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
        seen_paths = set()

        for s_root in search_roots:
            abs_root = os.path.abspath(s_root)
            if os.path.exists(abs_root):
                for root, _, files in sorted(os.walk(abs_root)):
                    for file in sorted(files):
                        if file.lower().endswith(valid_extensions):
                            abs_path = os.path.abspath(os.path.join(root, file))
                            if abs_path not in seen_paths:
                                seen_paths.add(abs_path)
                                folder_name = os.path.basename(root)
                                found.append({
                                    "id": len(found),
                                    "name": f"[{folder_name}] {file}",
                                    "path": abs_path,
                                    "type": "video"
                                })

        # Synthetic source fallback is always available
        found.append({
            "id": len(found),
            "name": "Synthetic CCTV Generator",
            "path": None,
            "type": "synthetic"
        })

        self.available_sources = found
        logger.info(f"StreamGenerator discovered {len(found)} video sources: {[s['name'] for s in found]}")

    def _load_active_source(self):
        """Initializes VideoCapture / Live Stream for the currently selected source."""
        if not self.available_sources:
            return

        idx = max(0, min(self.active_source_index, len(self.available_sources) - 1))
        src = self.available_sources[idx]

        if self.cap:
            self.cap.release()
            self.cap = None

        self.video_source_path = src["path"]
        if src["type"] == "live_cctv":
            self.total_frames = 999999
            self.video_fps = 15.0
            self.duration_sec = 99999.0
            self.current_frame_pos = 0
            logger.info(f"StreamGenerator connected to Live CCTV Camera [{src['name']}] -> {src['path']}")
            # Drop any previous source's frame so it can't be served as live footage.
            self.last_frame = None
            self._start_cctv_worker(src["path"])
            self._read_and_cache_frame(0)
            return

        self._stop_cctv_worker()

        if src["type"] == "video" and src["path"] and os.path.exists(src["path"]):
            self.cap = cv2.VideoCapture(src["path"])
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                v_fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.video_fps = v_fps if v_fps and v_fps > 0 else float(self.fps)
                self.duration_sec = self.total_frames / self.video_fps if self.video_fps > 0 else 0.0
                self.current_frame_pos = 0
                logger.info(f"StreamGenerator loaded source [{src['name']}] -> {self.total_frames} frames @ {self.video_fps:.1f} FPS ({self.duration_sec:.1f}s)")
                self._read_and_cache_frame(0)
                return

        # Synthetic fallback
        self.video_source_path = None
        self.total_frames = 1500
        self.video_fps = float(self.fps)
        self.duration_sec = 100.0
        self.current_frame_pos = 0
        self._read_and_cache_frame(0)

    # ------------------ Live CCTV Background Worker ------------------

    def _start_cctv_worker(self, url):
        """Spawns the snapshot polling thread for a live CCTV source."""
        self._stop_cctv_worker()
        self.cctv_stop = threading.Event()
        stop_event = self.cctv_stop
        self.cctv_thread = threading.Thread(
            target=self._cctv_worker_loop,
            args=(url, stop_event),
            name="iris-cctv-poller",
            daemon=True,
        )
        self.cctv_thread.start()
        logger.info(f"[CCTV Worker] Polling {url} every {self.cctv_interval:.2f}s (timeout {self.cctv_timeout:.1f}s).")

    def _stop_cctv_worker(self):
        """Signals the current worker to exit. Never joins -- a thread parked in a
        socket read would otherwise block the caller (which may hold self.lock)."""
        self.cctv_stop.set()
        self.cctv_thread = None
        with self.cctv_lock:
            self.cctv_frame = None
            self.cctv_frame_ts = 0.0

    def _cctv_worker_loop(self, url, stop_event):
        """Fetches snapshots off the telemetry loop's critical path until stopped."""
        while not stop_event.is_set():
            started = time.time()
            frame = self._fetch_cctv_snapshot(url)
            # A superseded worker must not clobber the new source's frames.
            if stop_event.is_set():
                return
            if frame is not None:
                with self.cctv_lock:
                    self.cctv_frame = frame
                    self.cctv_frame_ts = time.time()
                    self.cctv_frame_seq += 1
            elapsed = time.time() - started
            stop_event.wait(max(0.0, self.cctv_interval - elapsed))

    def _fetch_cctv_snapshot(self, url):
        """Blocking snapshot fetch. Only ever called from the worker thread."""
        try:
            if self.cctv_session is None:
                import requests
                from requests.auth import HTTPDigestAuth
                usr = os.environ.get("CCTV_USER", "admin")
                pwd = os.environ.get("CCTV_PASS", "admin123")
                self.cctv_session = requests.Session()
                self.cctv_session.auth = HTTPDigestAuth(usr, pwd)

            r = self.cctv_session.get(url, timeout=self.cctv_timeout)
            if r.status_code != 200:
                self._log_cctv_error(f"HTTP {r.status_code} from {url}")
                return None

            img_np = np.frombuffer(r.content, dtype=np.uint8)
            frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            if frame is None:
                self._log_cctv_error("snapshot decode failed")
                return None
            # Deliberately NOT resized: the detector needs the camera's
            # native pixels. /video_feed scales down for display only.
            return frame
        except Exception as e:
            self._log_cctv_error(str(e))
            return None

    def _log_cctv_error(self, msg):
        """Rate-limited so an offline camera doesn't flood the log every 200ms."""
        now = time.time()
        if now - self._cctv_last_error_log >= 10.0:
            self._cctv_last_error_log = now
            logger.error(f"Live CCTV capture error: {msg}")

    def _read_and_cache_frame(self, target_frame=None):
        """Reads frame from VideoCapture or Live CCTV stream and updates self.last_frame."""
        if target_frame is not None:
            self.current_frame_pos = max(0, min(int(target_frame), max(0, self.total_frames - 1)))

        idx = max(0, min(self.active_source_index, len(self.available_sources) - 1))
        src = self.available_sources[idx]

        if src.get("type") == "live_cctv":
            # Non-blocking: hand back whatever the worker last pulled.
            #
            # A live camera NEVER falls back to the synthetic generator. That
            # generator paints fake occupants, so substituting it puts fabricated
            # people (or an empty room) into a real headcount -- which resets the
            # high-occupancy streak and drives the vacancy auto-off while the room
            # is actually occupied. No frame is the honest answer; the caller
            # freezes state instead of acting on invented data.
            with self.cctv_lock:
                frame = self.cctv_frame
                seq = self.cctv_frame_seq
            if frame is not None:
                self.last_frame = frame.copy()
                self.last_served_seq = seq
                return frame.copy()
            return None

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.current_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))
                self.last_frame = frame.copy()
                return frame.copy()

        frame = self._generate_synthetic_frame(None, 3)
        self.last_frame = frame.copy()
        return frame.copy()

    # ------------------ Player Control Methods ------------------
    def play(self):
        with self.lock:
            self.is_paused = False
            logger.info("Player: PLAY")

    def pause(self):
        with self.lock:
            idx = max(0, min(self.active_source_index, len(self.available_sources) - 1))
            src = self.available_sources[idx] if self.available_sources else {}
            if src.get("type") == "live_cctv":
                self.is_paused = False
                return
            self.is_paused = True
            self._read_and_cache_frame()
            logger.info("Player: PAUSE")

    def toggle_play_pause(self):
        with self.lock:
            idx = max(0, min(self.active_source_index, len(self.available_sources) - 1))
            src = self.available_sources[idx] if self.available_sources else {}
            if src.get("type") == "live_cctv":
                self.is_paused = False
                return False
            self.is_paused = not self.is_paused
            if self.is_paused:
                self._read_and_cache_frame()
            logger.info(f"Player: TOGGLE -> is_paused={self.is_paused}")
            return self.is_paused

    def seek(self, target_seconds: float):
        with self.lock:
            target_seconds = max(0.0, min(target_seconds, self.duration_sec))
            target_frame = int(target_seconds * self.video_fps)
            self._read_and_cache_frame(target_frame)
            logger.info(f"Player: SEEK -> {target_seconds:.1f}s (Frame {self.current_frame_pos})")

    def seek_relative(self, delta_seconds: float):
        with self.lock:
            current_sec = self.current_frame_pos / self.video_fps if self.video_fps > 0 else 0
            target_sec = max(0.0, min(current_sec + delta_seconds, self.duration_sec))
            target_frame = int(target_sec * self.video_fps)
            self._read_and_cache_frame(target_frame)
            logger.info(f"Player: SEEK RELATIVE ({delta_seconds:+.1f}s) -> {target_sec:.1f}s (Frame {self.current_frame_pos})")

    def step_frame(self, delta_frames: int):
        with self.lock:
            self.is_paused = True
            target_frame = max(0, min(self.current_frame_pos + delta_frames, max(0, self.total_frames - 1)))
            self._read_and_cache_frame(target_frame)
            logger.info(f"Player: STEP FRAME ({delta_frames:+d}) -> Frame {self.current_frame_pos}")

    def set_speed(self, speed: float):
        with self.lock:
            valid_speeds = [0.25, 0.5, 1.0, 1.5, 2.0]
            closest_speed = min(valid_speeds, key=lambda x: abs(x - float(speed)))
            self.playback_speed = closest_speed
            logger.info(f"Player: SET SPEED -> {closest_speed}x")

    def set_source(self, source_id: int):
        with self.lock:
            if 0 <= source_id < len(self.available_sources):
                self.active_source_index = source_id
                self._load_active_source()

    def jump_to_live(self):
        with self.lock:
            self.is_paused = False
            self.playback_speed = 1.0
            target_frame = max(0, self.total_frames - int(self.video_fps * 2))
            self._read_and_cache_frame(target_frame)
            logger.info("Player: JUMP TO LIVE")

    def get_player_status(self):
        with self.lock:
            current_sec = round(self.current_frame_pos / self.video_fps, 1) if self.video_fps > 0 else 0.0
            src = self.available_sources[self.active_source_index] if self.available_sources else {}
            src_name = src.get("name", "Unknown")
            is_cctv = src.get("type") == "live_cctv"
            return {
                "is_paused": False if is_cctv else self.is_paused,
                "current_time": current_sec,
                "duration": round(self.duration_sec, 1),
                "current_frame": self.current_frame_pos,
                "total_frames": self.total_frames,
                "fps": round(self.video_fps, 1),
                "playback_speed": self.playback_speed,
                "active_source_id": self.active_source_index,
                "source_name": src_name,
                "source_type": src.get("type", "video"),
                "available_sources": [
                    {"id": s["id"], "name": s["name"], "type": s["type"]} for s in self.available_sources
                ],
                "is_live": is_cctv or (not self.is_paused and self.playback_speed == 1.0)
            }

    # ------------------ Frame Generation & Streaming ------------------
    def read_frame(self, zone_states=None, active_headcount=3):
        """Reads frame from real MP4 video file, live CCTV camera, or synthetic stream."""
        with self.lock:
            idx = max(0, min(self.active_source_index, len(self.available_sources) - 1))
            src = self.available_sources[idx] if self.available_sources else {}
            is_cctv = src.get("type") == "live_cctv"

            # 0. Live CCTV Camera feed fetch. Returns early either way: a live
            # source must never be silently replaced by synthetic footage.
            if is_cctv:
                return self._read_and_cache_frame()

            # 1. If paused AND NOT live CCTV, return cached frame
            if self.is_paused and not is_cctv and self.last_frame is not None:
                return self.last_frame.copy()

            # Handle fractional playback speed slow down (e.g. 0.5x, 0.25x)
            if not self.is_paused and self.playback_speed < 1.0:
                skip_factor = int(round(1.0 / self.playback_speed))
                self.step_delay_counter += 1
                if self.step_delay_counter % skip_factor != 0:
                    if self.last_frame is not None:
                        return self.last_frame.copy()

            # Fast forward (> 1.0x) speed frame skipping
            if not self.is_paused and self.playback_speed > 1.0:
                skip_frames = int(round(self.playback_speed)) - 1
                if self.cap and self.cap.isOpened():
                    self.current_frame_pos = (self.current_frame_pos + skip_frames) % max(1, self.total_frames)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)

            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    # Seamless continuous video loop on EOF
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_frame_pos = 0
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        self.cap.release()
                        self._load_active_source()
                        if self.cap:
                            ret, frame = self.cap.read()

                if ret and frame is not None:
                    self.current_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    if frame.shape[1] != self.width or frame.shape[0] != self.height:
                        frame = cv2.resize(frame, (self.width, self.height))
                    self.last_frame = frame.copy()
                    return frame.copy()

            # Synthetic Generator Fallback
            if not self.is_paused:
                self.current_frame_pos = (self.current_frame_pos + 1) % max(1, self.total_frames)

            frame = self._generate_synthetic_frame(zone_states, active_headcount)
            self.last_frame = frame.copy()
            return frame.copy()

    def _generate_synthetic_frame(self, zone_states=None, active_headcount=3):
        # Create base CCTV background (overhead view of office floor)
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 30  # Dark floor slate

        # Draw grid tile lines
        for x in range(0, self.width, 80):
            cv2.line(frame, (x, 0), (x, self.height), (45, 45, 50), 1)
        for y in range(0, self.height, 80):
            cv2.line(frame, (0, y), (self.width, y), (45, 45, 50), 1)

        # Draw Zone Bounding Rectangles (Normalized -> Pixels)
        z1_pt1 = (int(0.05 * self.width), int(0.05 * self.height))
        z1_pt2 = (int(0.45 * self.width), int(0.45 * self.height))
        cv2.rectangle(frame, z1_pt1, z1_pt2, (70, 70, 80), 2)
        cv2.putText(frame, "ZONE 1: UPPER DESKS", (z1_pt1[0] + 10, z1_pt1[1] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 190), 1)

        z2_pt1 = (int(0.05 * self.width), int(0.55 * self.height))
        z2_pt2 = (int(0.45 * self.width), int(0.95 * self.height))
        cv2.rectangle(frame, z2_pt1, z2_pt2, (70, 70, 80), 2)
        cv2.putText(frame, "ZONE 2: LOWER DESKS", (z2_pt1[0] + 10, z2_pt1[1] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 190), 1)

        z3_pt1 = (int(0.55 * self.width), int(0.20 * self.height))
        z3_pt2 = (int(0.95 * self.width), int(0.85 * self.height))
        cv2.rectangle(frame, z3_pt1, z3_pt2, (70, 70, 80), 2)
        cv2.putText(frame, "ZONE 3: TV & LOUNGE", (z3_pt1[0] + 10, z3_pt1[1] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 190), 1)

        # Draw Furniture Desks
        cv2.rectangle(frame, (120, 120), (500, 260), (55, 60, 65), -1) # Desk 1
        cv2.rectangle(frame, (120, 480), (500, 620), (55, 60, 65), -1) # Desk 2
        cv2.rectangle(frame, (750, 250), (1150, 450), (60, 50, 65), -1) # TV Lounge Sofa

        # Highlight Zone Lighting Status
        if zone_states:
            if zone_states.get("Zone_1_Upper"):
                cv2.circle(frame, (310, 100), 20, (0, 220, 255), -1)
                cv2.putText(frame, "LIGHTS ON", (340, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 255), 1)
            if zone_states.get("Zone_2_Lower"):
                cv2.circle(frame, (310, 460), 20, (0, 220, 255), -1)
                cv2.putText(frame, "LIGHTS ON", (340, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 255), 1)
            if zone_states.get("Zone_3_TV_Far"):
                cv2.circle(frame, (950, 210), 20, (0, 220, 255), -1)
                cv2.putText(frame, "LIGHTS ON", (980, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 255), 1)

        # Move and Draw Occupants if not paused
        current_num = min(len(self.occupants), active_headcount)
        for i in range(current_num):
            p = self.occupants[i]
            if not self.is_paused:
                dx = p["tx"] - p["x"]
                dy = p["ty"] - p["y"]
                dist = math.hypot(dx, dy)
                if dist < 10:
                    if i == 0:
                        p["tx"] = np.random.randint(int(0.08 * self.width), int(0.42 * self.width))
                        p["ty"] = np.random.randint(int(0.08 * self.height), int(0.42 * self.height))
                    elif i == 1:
                        p["tx"] = np.random.randint(int(0.08 * self.width), int(0.42 * self.width))
                        p["ty"] = np.random.randint(int(0.58 * self.height), int(0.92 * self.height))
                    else:
                        p["tx"] = np.random.randint(int(0.58 * self.width), int(0.92 * self.width))
                        p["ty"] = np.random.randint(int(0.25 * self.height), int(0.80 * self.height))
                else:
                    p["x"] += (dx / dist) * p["speed"] * self.playback_speed
                    p["y"] += (dy / dist) * p["speed"] * self.playback_speed

            cx, cy = int(p["x"]), int(p["y"])
            cv2.circle(frame, (cx, cy), 24, p["hue"], -1) # Shoulders
            cv2.circle(frame, (cx, cy), 12, (220, 200, 180), -1) # Head
            cv2.putText(frame, f"Person {i+1}", (cx - 25, cy - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Timestamp & CCTV camera overlay watermark
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        status_text = "PAUSED" if self.is_paused else f"PLAYING ({self.playback_speed}x)"
        cv2.putText(frame, f"IRIS CCTV OVERHEAD CAM #1 - {timestamp_str} [{status_text}]", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 120), 2)

        return frame

