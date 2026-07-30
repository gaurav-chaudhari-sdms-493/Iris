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

# Device Auto-Off Vacancy Timers (FSD Section 7.2)
LB_AUTO_OFF_SEC = 3      # 3 seconds for Light Bulbs (LB)
LP_AUTO_OFF_SEC = 5      # 5 seconds for LED Panels (LP)
AC_AUTO_OFF_SEC = 600    # 10 Minutes (600 seconds) for Air Conditioner (AC)

BASE_KWH_RATE = 0.15          # $0.15 / kWh
FULL_LOAD_POWER_KW = 1.8      # Lights + AC peak load in kW
IDLE_LOAD_POWER_KW = 0.15     # Standby power in kW

