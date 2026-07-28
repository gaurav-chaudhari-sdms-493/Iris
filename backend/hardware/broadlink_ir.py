"""
Broadlink RM4 Mini IR Blaster Interface
Manages IR signal generation for Cassette AC temperature setpoints and TV power control.
Includes mock fallback for development without physical line-of-sight hardware.
"""

import logging
from config import HARDWARE_MOCK_MODE, BROADLINK_CONFIG

logger = logging.getLogger("iris.hardware.broadlink")

try:
    import broadlink
    BROADLINK_AVAILABLE = True
except ImportError:
    BROADLINK_AVAILABLE = False
    logger.warning("broadlink module not installed. Running in mock IR mode.")

# Sample pre-recorded Broadlink Hex payloads for AC and TV
IR_PAYLOADS = {
    "AC_POWER_OFF": "260048000001150001000100010001000100010001000100010001000100",
    "AC_COOL_22": "260050000001250001000100010001000100010001000100010001000100",
    "AC_COOL_24": "260050000001240001000100010001000100010001000100010001000100",
    "AC_COOL_26": "260050000001260001000100010001000100010001000100010001000100",
    "TV_POWER_TOGGLE": "26002400000120000100010001000100010001000100010001000100"
}

class BroadlinkIRManager:
    def __init__(self):
        self.mock_mode = HARDWARE_MOCK_MODE or not BROADLINK_AVAILABLE
        self.device = None
        self.ac_state = {
            "power": "OFF",
            "temperature": 24,
            "mode": "COOL",
            "fan_speed": "AUTO"
        }
        self.tv_state = "OFF"

        if not self.mock_mode:
            self._connect_device()
        else:
            logger.info("[BroadlinkIRManager] Running in MOCK IR mode.")

    def _connect_device(self):
        try:
            logger.info(f"Discovering Broadlink RM4 Mini at {BROADLINK_CONFIG['ip']}...")
            devices = broadlink.discover(timeout=3, ip_address=BROADLINK_CONFIG['ip'])
            if devices:
                self.device = devices[0]
                self.device.auth()
                logger.info(f"Broadlink RM4 Mini authenticated: {self.device.get_type()}")
            else:
                logger.warning("No Broadlink device discovered on local subnet. Switching to MOCK mode.")
                self.mock_mode = True
        except Exception as e:
            logger.error(f"Broadlink discovery failed: {e}. Falling back to MOCK mode.")
            self.mock_mode = True

    def send_ac_command(self, temp: int, power: str = "ON", mode: str = "COOL", fan: str = "AUTO") -> bool:
        """Sends IR signal to set AC temperature (e.g. 22, 24, 26) or turn OFF."""
        if power.upper() == "OFF":
            payload_key = "AC_POWER_OFF"
            self.ac_state["power"] = "OFF"
        else:
            payload_key = f"AC_COOL_{temp}" if f"AC_COOL_{temp}" in IR_PAYLOADS else "AC_COOL_24"
            self.ac_state.update({"power": "ON", "temperature": temp, "mode": mode, "fan_speed": fan})

        logger.info(f"[BroadlinkIRManager] Sending AC command: Power={power}, Temp={temp}°C, Fan={fan} (Mock: {self.mock_mode})")

        if self.mock_mode:
            return True

        if not self.device:
            return False

        try:
            hex_data = IR_PAYLOADS.get(payload_key, IR_PAYLOADS["AC_COOL_24"])
            self.device.send_data(bytes.fromhex(hex_data))
            return True
        except Exception as e:
            logger.error(f"Failed to send Broadlink IR data: {e}")
            return False

    def toggle_tv_power(self, force_state: str = None) -> bool:
        """Toggles TV power via Broadlink IR signal."""
        new_state = force_state if force_state else ("ON" if self.tv_state == "OFF" else "OFF")
        self.tv_state = new_state
        logger.info(f"[BroadlinkIRManager] TV Power set to {new_state} (Mock: {self.mock_mode})")

        if self.mock_mode:
            return True

        if not self.device:
            return False

        try:
            self.device.send_data(bytes.fromhex(IR_PAYLOADS["TV_POWER_TOGGLE"]))
            return True
        except Exception as e:
            logger.error(f"Failed to send TV IR payload: {e}")
            return False

    def get_status(self):
        return {
            "ac": self.ac_state.copy(),
            "tv": self.tv_state
        }
