"""
Tuya Relay Controller (AZIOT 4-Node Smart Switches)
Supports physical local TCP connection and Tuya Cloud API fallback for single AZIOT 4-Node Smart Switch
with seamless dry-run / mock hardware fallback.
"""

import logging
import time
import threading
from config import load_hardware_config, save_hardware_config

logger = logging.getLogger("iris.hardware.tuya")

try:
    import tinytuya
    TINYTUYA_AVAILABLE = True
except ImportError:
    TINYTUYA_AVAILABLE = False
    logger.warning("tinytuya module not installed. Running in mock hardware mode.")


class TuyaRelayManager:
    def __init__(self):
        hw_cfg = load_hardware_config()
        self.mock_mode = hw_cfg.get("hardware_mock_mode", False) if TINYTUYA_AVAILABLE else True
        self.relay_a_cfg = hw_cfg.get("relay_a", {})
        self.cloud_cfg = hw_cfg.get("tuya_cloud", {})
        
        self.relay_a = None
        self.cloud_device = None
        self.last_ping_ms = 0.0
        self.is_connected = False
        
        # State tracker for 4 output nodes on single AZIOT Relay A (Light Bulbs LB1-LB12)
        # Node 1: S7  (TV Area Bulbs)
        # Node 2: S4  (Upper Bulbs)
        # Node 3: S2  (Lower Bulbs)
        # Node 4: S12 (Far Bulbs)
        self.state_a = {1: False, 2: False, 3: False, 4: False}
        self.state_b = {1: False, 2: False, 3: False, 4: False}

        self._init_cloud()
        if not self.mock_mode:
            self._connect_device()

    def _init_cloud(self):
        """Initializes Tuya Cloud API client."""
        if not TINYTUYA_AVAILABLE:
            return
        api_key = self.cloud_cfg.get("api_key", "juugykgp344h8s4nvnk9")
        api_secret = self.cloud_cfg.get("api_secret", "c2e9f98826c0425a9916f8c5ce4d53fd")
        region = self.cloud_cfg.get("api_region", "in")
        try:
            self.cloud_device = tinytuya.Cloud(apiRegion=region, apiKey=api_key, apiSecret=api_secret)
            logger.info("[Tuya Cloud API] Initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Tuya Cloud API: {e}")
            self.cloud_device = None

    def _connect_device(self):
        """Attempts local socket connection; updates connectivity status."""
        if not TINYTUYA_AVAILABLE:
            self.is_connected = False
            return False

        ip = self.relay_a_cfg.get("address")
        dev_id = self.relay_a_cfg.get("dev_id", "d7dfa72170929e9eefvfx3")
        local_key = self.relay_a_cfg.get("local_key", "vYNWVn3aP=EIvy)'")
        ver = float(self.relay_a_cfg.get("version", 3.3))

        try:
            start_t = time.time()
            device = tinytuya.OutletDevice(dev_id=dev_id, address=ip, local_key=local_key, version=ver)
            device.set_socketPersistent(True)
            device.set_socketTimeout(1.0)
            status_data = device.status()
            elapsed_ms = round((time.time() - start_t) * 1000, 1)

            if status_data and "dps" in status_data:
                self.relay_a = device
                self.is_connected = True
                self.last_ping_ms = elapsed_ms
                self._sync_state_from_dps(status_data["dps"])
                logger.info(f"[AZIOT Local TCP] Connected at {ip} in {elapsed_ms} ms.")
                return True
        except Exception:
            pass

        # If local connection fails, check status via Tuya Cloud API
        if self.cloud_device:
            try:
                start_t = time.time()
                cloud_st = self.cloud_device.getstatus(dev_id)
                elapsed_ms = round((time.time() - start_t) * 1000, 1)
                if cloud_st and cloud_st.get("success"):
                    self.is_connected = True
                    self.last_ping_ms = elapsed_ms
                    self._sync_state_from_cloud(cloud_st.get("result", []))
                    logger.info(f"[AZIOT Cloud API] Connected via Tuya Cloud in {elapsed_ms} ms.")
                    return True
            except Exception as e:
                logger.error(f"Tuya Cloud status query error: {e}")

        self.is_connected = False
        return False

    def _sync_state_from_dps(self, dps_dict: dict):
        for ch in [1, 2, 3, 4]:
            str_key = str(ch)
            if str_key in dps_dict:
                self.state_a[ch] = bool(dps_dict[str_key])
            elif ch in dps_dict:
                self.state_a[ch] = bool(dps_dict[ch])

    def _sync_state_from_cloud(self, cloud_result_list: list):
        for item in cloud_result_list:
            code = item.get("code")
            val = item.get("value")
            if code in ["switch_1", "switch_2", "switch_3", "switch_4"]:
                ch_idx = int(code.split("_")[1])
                self.state_a[ch_idx] = bool(val)

    def set_relay_channel(self, module: str, channel: int, state: bool) -> bool:
        """
        Sets a specific relay node channel ON (True) or OFF (False).
        module: 'A' (AZIOT 4 Node switch)
        channel: 1 to 4
        """
        module = module.upper()
        if channel not in [1, 2, 3, 4]:
            logger.error(f"Invalid channel spec: Channel {channel}")
            return False

        target_state = self.state_a if module == 'A' else self.state_b
        target_state[channel] = state

        logger.info(f"[AZIOT Actuation] Module {module} Node {channel} -> {'ON' if state else 'OFF'} (Mock: {self.mock_mode})")

        if self.mock_mode or module == 'B':
            return True

        dev_id = self.relay_a_cfg.get("dev_id", "d7dfa72170929e9eefvfx3")
        
        # 1. Try local TCP socket first if connected
        if self.relay_a and self.is_connected:
            try:
                start_t = time.time()
                res = self.relay_a.set_status(state, switch=channel)
                self.last_ping_ms = round((time.time() - start_t) * 1000, 1)
                if res and "error" not in str(res).lower():
                    logger.info(f"[AZIOT Local Response] Node {channel} set to {state}: {res}")
                    return True
            except Exception as e:
                logger.warning(f"Local TCP command failed: {e}. Falling back to Cloud API...")

        # 2. Seamless Fallback to Tuya Cloud API
        if self.cloud_device:
            try:
                start_t = time.time()
                cmd_code = f"switch_{channel}"
                res = self.cloud_device.sendcommand(dev_id, {"commands": [{"code": cmd_code, "value": state}]})
                self.last_ping_ms = round((time.time() - start_t) * 1000, 1)
                if res and res.get("success"):
                    self.is_connected = True
                    logger.info(f"[AZIOT Cloud Response] Physical Node {channel} set to {state} via Cloud API!")
                    return True
                else:
                    logger.error(f"Tuya Cloud command error: {res}")
            except Exception as e:
                logger.error(f"Tuya Cloud command exception: {e}")

        return False

    def poll_physical_status(self):
        if self.mock_mode:
            return self.get_state()

        dev_id = self.relay_a_cfg.get("dev_id", "d7dfa72170929e9eefvfx3")
        if self.cloud_device:
            try:
                cloud_st = self.cloud_device.getstatus(dev_id)
                if cloud_st and cloud_st.get("success"):
                    self._sync_state_from_cloud(cloud_st.get("result", []))
                    self.is_connected = True
            except Exception:
                pass

        return self.get_state()

    def set_mock_mode(self, enable_mock: bool):
        self.mock_mode = enable_mock
        hw_cfg = load_hardware_config()
        hw_cfg["hardware_mock_mode"] = enable_mock
        save_hardware_config(hw_cfg)
        
        if not self.mock_mode:
            return self._connect_device()
        else:
            self.is_connected = False
            return True

    def update_credentials(self, address: str, dev_id: str, local_key: str, version: float = 3.3):
        hw_cfg = load_hardware_config()
        self.relay_a_cfg = {
            "dev_id": dev_id.strip(),
            "address": address.strip(),
            "local_key": local_key.strip(),
            "version": version,
            "description": "AZIOT 4 Node Smart Switch (Light Bulbs LB1-LB12)"
        }
        hw_cfg["relay_a"] = self.relay_a_cfg
        save_hardware_config(hw_cfg)

        if not self.mock_mode:
            return self._connect_device()
        return True

    def get_status_details(self):
        return {
            "mock_mode": self.mock_mode,
            "is_connected": self.is_connected,
            "ping_ms": self.last_ping_ms if self.is_connected else None,
            "device_info": {
                "ip": self.relay_a_cfg.get("address"),
                "dev_id": self.relay_a_cfg.get("dev_id"),
                "version": self.relay_a_cfg.get("version", 3.3),
                "model": "AZIOT 4 Node Smart Switch (Wi-Fi / Cloud Dual Mode)"
            },
            "nodes": {
                "node_1": {"name": "TV Area Bulbs (S7)", "channel": 1, "state": self.state_a[1]},
                "node_2": {"name": "Upper Bulbs (S4)", "channel": 2, "state": self.state_a[2]},
                "node_3": {"name": "Lower Bulbs (S2)", "channel": 3, "state": self.state_a[3]},
                "node_4": {"name": "Far Bulbs (S12)", "channel": 4, "state": self.state_a[4]},
            },
            "states": self.get_state()
        }

    def get_state(self):
        return {
            "Relay_A": self.state_a.copy(),
            "Relay_B": self.state_b.copy()
        }
