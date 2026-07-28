"""
Tuya Relay Controller (AZIOT 4-Node Smart Switches)
Supports physical local TCP connection via tinytuya with seamless dry-run/mock fallback.
"""

import logging
from config import HARDWARE_MOCK_MODE, RELAY_MODULE_A, RELAY_MODULE_B

logger = logging.getLogger("iris.hardware.tuya")
logging.basicConfig(level=logging.INFO)

try:
    import tinytuya
    TINYTUYA_AVAILABLE = True
except ImportError:
    TINYTUYA_AVAILABLE = False
    logger.warning("tinytuya module not installed. Running in mock hardware mode.")


class TuyaRelayManager:
    def __init__(self):
        self.mock_mode = HARDWARE_MOCK_MODE or not TINYTUYA_AVAILABLE
        self.relay_a = None
        self.relay_b = None
        
        # State tracker for 4 channels on Relay A, 4 channels on Relay B
        self.state_a = {1: False, 2: False, 3: False, 4: False}
        self.state_b = {1: False, 2: False, 3: False, 4: False}

        if not self.mock_mode:
            self._connect_devices()
        else:
            logger.info("[TuyaRelayManager] Running in MOCK HARDWARE mode.")

    def _connect_devices(self):
        try:
            logger.info(f"Connecting to AZIOT Relay A at {RELAY_MODULE_A['address']}...")
            self.relay_a = tinytuya.OutletDevice(
                dev_id=RELAY_MODULE_A["dev_id"],
                address=RELAY_MODULE_A["address"],
                local_key=RELAY_MODULE_A["local_key"],
                version=RELAY_MODULE_A["version"]
            )
            logger.info(f"Connecting to AZIOT Relay B at {RELAY_MODULE_B['address']}...")
            self.relay_b = tinytuya.OutletDevice(
                dev_id=RELAY_MODULE_B["dev_id"],
                address=RELAY_MODULE_B["address"],
                local_key=RELAY_MODULE_B["local_key"],
                version=RELAY_MODULE_B["version"]
            )
        except Exception as e:
            logger.error(f"Failed to connect to Tuya physical hardware: {e}. Falling back to MOCK mode.")
            self.mock_mode = True

    def set_relay_channel(self, module: str, channel: int, state: bool) -> bool:
        """
        Sets a specific relay channel ON (True) or OFF (False).
        module: 'A' or 'B'
        channel: 1 to 4
        """
        module = module.upper()
        if module not in ['A', 'B'] or channel not in [1, 2, 3, 4]:
            logger.error(f"Invalid relay channel spec: Module {module}, Channel {channel}")
            return False

        target_state_dict = self.state_a if module == 'A' else self.state_b
        target_state_dict[channel] = state

        logger.info(f"[TuyaRelayManager] Module {module} Ch {channel} -> {'ON' if state else 'OFF'} (Mock: {self.mock_mode})")

        if self.mock_mode:
            return True

        device = self.relay_a if module == 'A' else self.relay_b
        if not device:
            return False

        try:
            device.set_status(state, switch=channel)
            return True
        except Exception as e:
            logger.error(f"Tuya TCP error on Module {module} Ch {channel}: {e}")
            return False

    def get_state(self):
        """Returns active states of Relay A and Relay B channels."""
        return {
            "Relay_A": self.state_a.copy(),
            "Relay_B": self.state_b.copy()
        }
