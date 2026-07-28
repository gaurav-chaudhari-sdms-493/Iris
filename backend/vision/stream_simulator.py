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
        self._check_video_file()
        
        # Virtual Occupants state for synthetic fallback
        self.occupants = [
            {"x": 200, "y": 200, "tx": 400, "ty": 250, "speed": 2.5, "hue": (50, 120, 250)},
            {"x": 250, "y": 550, "tx": 350, "ty": 600, "speed": 1.8, "hue": (200, 100, 50)},
            {"x": 900, "y": 450, "tx": 1000, "ty": 400, "speed": 2.0, "hue": (100, 200, 50)}
        ]

    def _check_video_file(self):
        """Checks potential video file locations (backend/video.mp4, root/video.mp4, etc)."""
        candidates = [
            VIDEO_PATH,
            os.path.join(os.path.dirname(__file__), "../video.mp4"),
            os.path.join(os.path.dirname(__file__), "../../video.mp4"),
            "video.mp4"
        ]
        for path in candidates:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                self.video_source_path = abs_path
                self.cap = cv2.VideoCapture(abs_path)
                if self.cap.isOpened():
                    logger.info(f"StreamGenerator: Playing real video file -> {abs_path}")
                    return
                else:
                    self.cap = None

    def read_frame(self, zone_states=None, active_headcount=3):
        """Reads frame from real MP4 video file if present, otherwise uses synthetic generator."""
        with self.lock:
            if self.cap is None and self.video_source_path is None:
                self._check_video_file()

            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    # Seamless continuous video loop on EOF
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        # Re-open capture object if seek is not supported by codec
                        self.cap.release()
                        self.cap = cv2.VideoCapture(self.video_source_path)
                        ret, frame = self.cap.read()

                if ret and frame is not None:
                    if frame.shape[1] != self.width or frame.shape[0] != self.height:
                        frame = cv2.resize(frame, (self.width, self.height))
                    return frame.copy()

        # Fallback to synthetic office overhead generator
        return self._generate_synthetic_frame(zone_states, active_headcount)

    def _generate_synthetic_frame(self, zone_states=None, active_headcount=3):
        
        # Create base CCTV background (overhead view of office floor)
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 30  # Dark floor slate

        # Draw grid tile lines
        for x in range(0, self.width, 80):
            cv2.line(frame, (x, 0), (x, self.height), (45, 45, 50), 1)
        for y in range(0, self.height, 80):
            cv2.line(frame, (0, y), (self.width, y), (45, 45, 50), 1)

        # Draw Zone Bounding Rectangles (Normalized -> Pixels)
        # Zone 1: Upper Workstation [0.05, 0.05, 0.45, 0.45]
        z1_pt1 = (int(0.05 * self.width), int(0.05 * self.height))
        z1_pt2 = (int(0.45 * self.width), int(0.45 * self.height))
        cv2.rectangle(frame, z1_pt1, z1_pt2, (70, 70, 80), 2)
        cv2.putText(frame, "ZONE 1: UPPER DESKS", (z1_pt1[0] + 10, z1_pt1[1] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 190), 1)

        # Zone 2: Lower Workstation [0.05, 0.55, 0.45, 0.95]
        z2_pt1 = (int(0.05 * self.width), int(0.55 * self.height))
        z2_pt2 = (int(0.45 * self.width), int(0.95 * self.height))
        cv2.rectangle(frame, z2_pt1, z2_pt2, (70, 70, 80), 2)
        cv2.putText(frame, "ZONE 2: LOWER DESKS", (z2_pt1[0] + 10, z2_pt1[1] + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 190), 1)

        # Zone 3: Lounge & TV Area [0.55, 0.20, 0.95, 0.85]
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

        # Move and Draw Occupants
        current_num = min(len(self.occupants), active_headcount)
        for i in range(current_num):
            p = self.occupants[i]
            # Smooth movement towards target
            dx = p["tx"] - p["x"]
            dy = p["ty"] - p["y"]
            dist = math.hypot(dx, dy)
            if dist < 10:
                # Pick new random target within office zones
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
                p["x"] += (dx / dist) * p["speed"]
                p["y"] += (dy / dist) * p["speed"]

            cx, cy = int(p["x"]), int(p["y"])
            # Draw synthetic head + shoulders from overhead perspective
            cv2.circle(frame, (cx, cy), 24, p["hue"], -1) # Shoulders
            cv2.circle(frame, (cx, cy), 12, (220, 200, 180), -1) # Head
            # Label
            cv2.putText(frame, f"Person {i+1}", (cx - 25, cy - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Timestamp & CCTV camera overlay watermark
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"IRIS CCTV OVERHEAD CAM #1 - {timestamp_str}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 120), 2)

        return frame
