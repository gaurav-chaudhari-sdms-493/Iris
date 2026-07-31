"""
Project Iris - Configuration Module
FSD Hardware & Spatial Mapping Settings
"""

import os
import json

def load_dotenv_file():
    """Loads environment variables from .env file into os.environ."""
    env_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            os.environ[k] = v
            except Exception:
                pass

def update_env_variable(key: str, value: str):
    """Updates or appends a key=value pair in the .env file."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    os.environ[key] = str(value)
    if not os.path.exists(env_path):
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    if os.path.exists(env_path):
        try:
            lines = []
            found = False
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#") and "=" in line:
                        k, _ = line.split("=", 1)
                        if k.strip() == key:
                            lines.append(f"{key}={value}\n")
                            found = True
                            continue
                    lines.append(line)
            if not found:
                lines.append(f"{key}={value}\n")
            with open(env_path, "w") as f:
                f.writelines(lines)
        except Exception:
            pass

load_dotenv_file()

# RTSP / Video Source
RTSP_URL = os.environ.get("IRIS_RTSP_URL", "rtsp://admin:password@192.168.1.100:554/stream1")
VIDEO_PATH = os.environ.get("IRIS_VIDEO_PATH", "data/office/VIDEO-2026-07-28-15-36-24.mp4")
USE_SIMULATED_STREAM = os.environ.get("IRIS_SIMULATED", "true").lower() == "true"
YOLO_MODEL_PATH = os.environ.get("IRIS_YOLO_MODEL", "models/best.pt")

# Minimum detection confidence for a head to count as an occupant.
# Lower this if overhead heads are being missed at the demo site.
DETECTION_CONFIDENCE = float(os.environ.get("IRIS_YOLO_CONF", 0.50))

# Inference letterbox size. Overhead heads are small; 960 resolves them far better
# than the 640 default and measured no slower on this CPU.
DETECTION_IMGSZ = int(os.environ.get("IRIS_YOLO_IMGSZ", 960))

# NMS IoU. The 0.7 default leaves two boxes on a single head, inflating headcount.
DETECTION_IOU = float(os.environ.get("IRIS_YOLO_IOU", 0.50))

# Hikvision ISAPI snapshots default to the 704x480 sub-stream. Requesting an
# explicit resolution pulls the full-resolution main stream instead, which is
# what makes distant heads detectable at all.
CCTV_SNAPSHOT_WIDTH = int(os.environ.get("CCTV_SNAPSHOT_WIDTH", 1920))
CCTV_SNAPSHOT_HEIGHT = int(os.environ.get("CCTV_SNAPSHOT_HEIGHT", 1080))

# --- Occupant depth / region gating -------------------------------------------
# The developer row sits directly behind the lounge and projects into the same
# band of the frame, so no rectangle can separate them. Apparent head size can:
# a head at twice the distance is half the height. Minimum head height, as a
# fraction of frame height. 0.0 disables the gate.
# Calibrate with: ./iris_env/bin/python -m hardware.measure_heads
DETECTION_MIN_HEAD_H = float(os.environ.get("IRIS_MIN_HEAD_H", 0.0))

# Optional rectangular region of interest, normalized "x_min,y_min,x_max,y_max".
# A head is counted only if its centre falls inside. Empty disables the gate.
# Safety-net body detector. The head model is face-biased and can miss someone
# turned fully away from the camera; a COCO person model sees the whole body and
# does not care which way they face. Empty path = disabled.
# Body-box height is NOT a reliable depth cue (a seated person is occluded by the
# desk and measures small), so this needs its own calibrated gate before use.
PERSON_MODEL_PATH = os.environ.get("IRIS_PERSON_MODEL", "").strip()
PERSON_CONFIDENCE = float(os.environ.get("IRIS_PERSON_CONF", 0.40))
PERSON_MIN_BODY_H = float(os.environ.get("IRIS_MIN_BODY_H", 0.0))
# Run the body model on every poll. Default ON: the tier-gated version had a
# self-reinforcing dead zone at 1-2 heads where the body model -- the only
# detector that sees someone face-down at a laptop -- was skipped, so the count
# could not climb out of the band that skipped it. Measured 2 correct polls in 20
# with five people in the room. Costs roughly double the inference time; set
# false only on hardware that cannot afford it.
PERSON_ALWAYS_ON = os.environ.get("IRIS_PERSON_ALWAYS", "true").lower() == "true"

# Two body boxes overlapping by more than this share of the smaller box are
# treated as one person. The detector often returns both a partial box (torso
# above a desk) and a full box for the same body, and plain NMS keeps both.
BODY_OVERLAP_MERGE = float(os.environ.get("IRIS_BODY_OVERLAP_MERGE", 0.5))

_roi_raw = os.environ.get("IRIS_DETECTION_ROI", "").strip()
try:
    DETECTION_ROI = [float(v) for v in _roi_raw.split(",")] if _roi_raw else None
    if DETECTION_ROI and len(DETECTION_ROI) != 4:
        DETECTION_ROI = None
except ValueError:
    DETECTION_ROI = None

# Hardware Direct Access Mode
HARDWARE_MOCK_MODE = os.environ.get("IRIS_HARDWARE_MOCK", "false").lower() == "true"

# Tuya Cloud API Credentials
TUYA_CLOUD_CONFIG = {
    "api_key": os.environ.get("TUYA_API_KEY", ""),
    "api_secret": os.environ.get("TUYA_API_SECRET", ""),
    "project_code": os.environ.get("TUYA_PROJECT_CODE", ""),
    "api_region": os.environ.get("TUYA_API_REGION", "in")
}

HARDWARE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "hardware_config.json")

def load_hardware_config():
    """Loads physical hardware config from .env and JSON file."""
    default_config = {
        "hardware_mock_mode": HARDWARE_MOCK_MODE,
        "tuya_cloud": TUYA_CLOUD_CONFIG,
        "relay_a": {
            "dev_id": os.environ.get("RELAY_A_ID", ""),
            "address": os.environ.get("RELAY_A_IP", "192.168.30.125"),
            "local_key": os.environ.get("RELAY_A_KEY", ""),
            "version": float(os.environ.get("RELAY_A_VERSION", 3.3)),
            "description": "AZIOT 4 Node Smart Switch (Light Bulbs LB1-LB12)"
        },
        "relay_b": {
            "dev_id": os.environ.get("RELAY_B_ID", ""),
            "address": os.environ.get("RELAY_B_IP", "192.168.1.51"),
            "local_key": os.environ.get("RELAY_B_KEY", ""),
            "version": float(os.environ.get("RELAY_B_VERSION", 3.3)),
            "description": "Reserved for future expansion"
        }
    }
    if os.path.exists(HARDWARE_CONFIG_PATH):
        try:
            with open(HARDWARE_CONFIG_PATH, "r") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception:
            pass
    return default_config

def save_hardware_config(config_dict):
    """Saves updated hardware config dictionary to JSON file."""
    os.makedirs(os.path.dirname(HARDWARE_CONFIG_PATH), exist_ok=True)
    with open(HARDWARE_CONFIG_PATH, "w") as f:
        json.dump(config_dict, f, indent=2)

hw_cfg = load_hardware_config()
RELAY_MODULE_A = hw_cfg["relay_a"]
RELAY_MODULE_B = hw_cfg["relay_b"]

# Physical Switch & Load Mapping
# AZIOT 4 Node Smart Switch (Module A):
# Ch 1 -> S7  (TV Area Bulbs LB1-LB3)
# Ch 2 -> S4  (Upper Bulbs LB4-LB6)
# Ch 3 -> S2  (Lower Bulbs LB7-LB9)
# Ch 4 -> S12 (Far Bulbs LB10-LB12)
# LED Panels LP1-LP4 stay on Software/Mock mode for now.

SWITCH_MAPPINGS = {
    "S1": {"name": "TV Power Switch", "type": "IR", "device": "Broadlink", "target": "TV"},
    "S7": {"name": "TV Area Bulbs LB1-LB3", "type": "Relay", "module": "A", "channel": 1},
    "S4": {"name": "Upper Bulbs LB4-LB6", "type": "Relay", "module": "A", "channel": 2},
    "S2": {"name": "Lower Bulbs LB7-LB9", "type": "Relay", "module": "A", "channel": 3},
    "S12": {"name": "Far Bulbs LB10-LB12", "type": "Relay", "module": "A", "channel": 4},
    "S3": {"name": "Upper LED Panels LP1-LP2", "type": "Mock", "module": "A", "channel": 1},
    "S10": {"name": "Lower LED Panels LP3-LP4", "type": "Mock", "module": "A", "channel": 2},
}

# Broadlink RM4 Mini Settings
BROADLINK_CONFIG = {
    "ip": os.environ.get("BROADLINK_IP", "192.168.1.60"),
    "mac": os.environ.get("BROADLINK_MAC", "A4:91:B1:00:00:00")
}

# Computer Vision Spatial Zone Definitions (Normalized 0.0 - 1.0 bounding boxes on CCTV frame)
SPATIAL_ZONES = {
    "Zone_1_Upper": {
        "name": "Upper Workstations & Lighting",
        "bbox": [0.05, 0.05, 0.45, 0.45], # [x_min, y_min, x_max, y_max] normalized
        "relays": [("A", 2)],              # S4 (Upper Bulbs LB4-LB6)
        "switches": ["S4"]
    },
    "Zone_2_Lower": {
        "name": "Lower Workstations & Lighting",
        "bbox": [0.05, 0.55, 0.45, 0.95],
        "relays": [("A", 3)],              # S2 (Lower Bulbs LB7-LB9)
        "switches": ["S2"]
    },
    "Zone_3_TV_Far": {
        "name": "Lounge & TV Area",
        "bbox": [0.55, 0.20, 0.95, 0.85],
        "relays": [("A", 1), ("A", 4)],     # S7 (TV Bulbs LB1-LB3), S12 (Far Bulbs LB10-LB12)
        "switches": ["S7", "S12"]
    }
}

# Polling & System Parameters
FAST_MOTION_FPS = 5
OCCUPANCY_POLL_INTERVAL_SEC = 1

# Headcount Lighting Thresholds
HEADCOUNT_PANEL_ONLY_MAX = 3  # Headcount 1-3 -> LED Panels Only; >3 -> All Lights ON

# Consecutive polls that must agree before escalating to the all-lines-on tier.
# Detection is noisy at the margin -- a single spurious box (a duplicate that
# survived NMS, or a distant head briefly crossing the size gate) is enough to
# read 4 people in a room of 3. Acting on one frame turns the lights on, the next
# frame reads 3 again, and the anti-flicker hold produces a visible on/off cycle.
# Requiring agreement across polls costs a second of latency and removes it.
HIGH_TIER_CONFIRM_POLLS = int(os.environ.get("IRIS_HIGH_TIER_CONFIRM", 2))

# How long the room must stay below the high-occupancy threshold before the extra
# bulbs are released. Deliberately far longer than the escalation delay: a light
# that arrives late goes unnoticed, a light that blinks off and on does not.
HIGH_TIER_RELEASE_SEC = float(os.environ.get("IRIS_HIGH_TIER_RELEASE", 30))

# Directory for annotated frames captured whenever the count reads above the
# high-occupancy threshold. Set to diagnose spurious occupants; empty disables.
DEBUG_DUMP_DIR = os.environ.get("IRIS_DEBUG_DUMP", "").strip()

# Consecutive zero-headcount polls required before the vacancy timer even starts.
# The mirror image of HIGH_TIER_CONFIRM_POLLS, and far more important: escalating
# on a bad frame turns a light on, but reading zero on a bad frame turns the room
# dark on people who are still in it. The head model is face-biased, so a single
# occupant who turns away can vanish from a poll while plainly present.
ZERO_OCCUPANCY_CONFIRM_POLLS = int(os.environ.get("IRIS_ZERO_CONFIRM_POLLS", 3))

# Vacancy is vetoed while frame-differencing motion was seen this recently.
# Motion is a genuinely independent sensor: it has no notion of class or pose, so
# it still fires on someone turned away, crouched, or half-occluded by the sofa --
# exactly the cases both the head and body detectors lose. An empty room produces
# no contours above the area gate, so this does not block real auto-off.
# 0 disables the veto.
VACANCY_MOTION_VETO_SEC = float(os.environ.get("IRIS_VACANCY_MOTION_VETO", 10))

# Device Auto-Off Vacancy Timers (FSD Section 7.2)
# Raising LB_AUTO_OFF_SEC is the cheapest insurance against a brief detection
# miss (someone turning away) switching the lights off while the room is in use.
# At a ~1s poll that a stale camera frame often halves, 3s was only two or three
# missed polls from darkness. A light lingering 20s after a real exit reads as
# normal; one that dies on an occupied room reads as broken.
LB_AUTO_OFF_SEC = float(os.environ.get("IRIS_LB_AUTO_OFF", 20))   # Light Bulbs (LB)
LP_AUTO_OFF_SEC = float(os.environ.get("IRIS_LP_AUTO_OFF", 5))    # LED Panels (LP)
AC_AUTO_OFF_SEC = float(os.environ.get("IRIS_AC_AUTO_OFF", 600))  # Air Conditioner (AC)

BASE_KWH_RATE = 0.15          # $0.15 / kWh
FULL_LOAD_POWER_KW = 1.8      # Lights + AC peak load in kW
IDLE_LOAD_POWER_KW = 0.15     # Standby power in kW

