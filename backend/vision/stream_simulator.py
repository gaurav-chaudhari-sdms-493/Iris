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
from config import VIDEO_PATH

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

        # Virtual Occupants state for synthetic fallback
        self.occupants = [
            {"x": 200, "y": 200, "tx": 400, "ty": 250, "speed": 2.5, "hue": (50, 120, 250)},
            {"x": 250, "y": 550, "tx": 350, "ty": 600, "speed": 1.8, "hue": (200, 100, 50)},
            {"x": 900, "y": 450, "tx": 1000, "ty": 400, "speed": 2.0, "hue": (100, 200, 50)}
        ]

        self._discover_video_sources()
        self._load_active_source()

    def _discover_video_sources(self):
        """Recursively scans backend/data (including subfolders) for video files."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend dir
        root_dir = os.path.dirname(base_dir)  # project root

        search_roots = [
            os.path.join(base_dir, "data"),
            os.path.join(root_dir, "data"),
            os.path.join(os.getcwd(), "data"),
        ]

        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
        found = []
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
        """Initializes OpenCV VideoCapture for the currently selected source."""
        if not self.available_sources:
            return

        idx = max(0, min(self.active_source_index, len(self.available_sources) - 1))
        src = self.available_sources[idx]

        if self.cap:
            self.cap.release()
            self.cap = None

        self.video_source_path = src["path"]
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

    def _read_and_cache_frame(self, target_frame=None):
        """Reads frame from VideoCapture at target_frame (or current pos) and updates self.last_frame."""
        if target_frame is not None:
            self.current_frame_pos = max(0, min(int(target_frame), max(0, self.total_frames - 1)))

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
            self.is_paused = True
            self._read_and_cache_frame()
            logger.info("Player: PAUSE")

    def toggle_play_pause(self):
        with self.lock:
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
            src_name = self.available_sources[self.active_source_index]["name"] if self.available_sources else "Unknown"
            return {
                "is_paused": self.is_paused,
                "current_time": current_sec,
                "duration": round(self.duration_sec, 1),
                "current_frame": self.current_frame_pos,
                "total_frames": self.total_frames,
                "fps": round(self.video_fps, 1),
                "playback_speed": self.playback_speed,
                "active_source_id": self.active_source_index,
                "source_name": src_name,
                "available_sources": [
                    {"id": s["id"], "name": s["name"], "type": s["type"]} for s in self.available_sources
                ],
                "is_live": not self.is_paused and self.playback_speed == 1.0
            }

    # ------------------ Frame Generation & Streaming ------------------
    def read_frame(self, zone_states=None, active_headcount=3):
        """Reads frame from real MP4 video file or synthetic stream, respecting pause and speed."""
        with self.lock:
            # 1. If paused and we already have a cached frame, return cached frame
            if self.is_paused and self.last_frame is not None:
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

