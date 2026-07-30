"""
Non-Blocking Async Orchestration Engine
Coordinates OpenCV fast motion detection, real-time YOLO headcount polling,
hardware state updates, and energy savings calculations without RTSP buffer lag.
FSD Reference: Section 7
"""

import time
import asyncio
import logging
from config import (
    SPATIAL_ZONES, SWITCH_MAPPINGS, OCCUPANCY_POLL_INTERVAL_SEC,
    LB_AUTO_OFF_SEC, LP_AUTO_OFF_SEC, AC_AUTO_OFF_SEC,
    BASE_KWH_RATE, FULL_LOAD_POWER_KW, IDLE_LOAD_POWER_KW,
    USE_SIMULATED_STREAM, HEADCOUNT_PANEL_ONLY_MAX
)
from hardware import TuyaRelayManager, BroadlinkIRManager
from vision import FastMotionEngine, OccupancyEngine, SyntheticStreamGenerator

logger = logging.getLogger("iris.orchestrator")

class IrisOrchestrator:
    def __init__(self):
        self.tuya = TuyaRelayManager()
        self.broadlink = BroadlinkIRManager()
        self.motion_engine = FastMotionEngine()
        self.occupancy_engine = OccupancyEngine()
        self.stream_gen = SyntheticStreamGenerator()

        # System State Variables
        self.is_running = False
        self.system_mode = "AUTO"  # AUTO, MANUAL, PRESENTATION, POWER_SAVING
        self.headcount = 0
        self.last_ai_check = time.time()
        self.zero_occupancy_counter = 0
        self.start_timestamp = time.time()

        # Device Auto-Off Vacancy Tracking
        self.vacancy_start_timestamp = time.time()
        self.lb_drop_timestamp = None
        self.lb_auto_off_done = True
        self.lp_auto_off_done = True
        self.ac_auto_off_done = True

        # Active Zone Motion State
        self.zone_states = {z_id: False for z_id in SPATIAL_ZONES}
        self.zone_motion_levels = {z_id: 0 for z_id in SPATIAL_ZONES}
        
        # Energy metrics
        self.total_kwh_saved = 0.42
        self.total_cost_saved = round(0.42 * BASE_KWH_RATE, 2)
        self.active_power_kw = IDLE_LOAD_POWER_KW

        # Motion bounding boxes & detection overlays
        self.latest_motion_boxes = []
        self.latest_person_boxes = []

        # Turn OFF all devices initially at startup
        self._turn_off_all_devices()

    def _turn_off_all_devices(self):
        """Initializes system with all devices (lights, TV, AC) OFF at startup."""
        for mod in ["A", "B"]:
            for ch in [1, 2, 3, 4]:
                self.tuya.set_relay_channel(mod, ch, False)
        self.broadlink.send_ac_command(24, power="OFF")
        self.broadlink.toggle_tv_power("OFF")
        for z_id in SPATIAL_ZONES:
            self.zone_states[z_id] = False
        self.active_power_kw = IDLE_LOAD_POWER_KW

    def _apply_zone_lighting(self, zone_id: str, turn_on: bool):
        """Applies relay commands for all physical lights assigned to a spatial zone."""
        if zone_id not in SPATIAL_ZONES:
            return
        zone = SPATIAL_ZONES[zone_id]
        self.zone_states[zone_id] = turn_on
        for mod, ch in zone["relays"]:
            self.tuya.set_relay_channel(mod, ch, turn_on)

    def trigger_manual_switch(self, switch_id: str, state: bool):
        """Manual override from switchboard UI."""
        self.system_mode = "MANUAL"
        if switch_id not in SWITCH_MAPPINGS:
            return False
        sw = SWITCH_MAPPINGS[switch_id]
        if sw["type"] == "Relay":
            res = self.tuya.set_relay_channel(sw["module"], sw["channel"], state)
            return res
        elif sw["type"] == "IR" and sw["target"] == "TV":
            res = self.broadlink.toggle_tv_power("ON" if state else "OFF")
            return res
        return False

    def activate_presentation_mode(self):
        """
        Section 8 Presentation Preset:
        Dims ambient lighting rows, sets AC to quiet mode (24°C), and turns TV ON.
        """
        logger.info("[IrisOrchestrator] Activating Presentation Mode Macro...")
        self.system_mode = "PRESENTATION"
        # Turn ON TV Area Bulbs & TV Power
        self.tuya.set_relay_channel("A", 3, True) # S7 TV Area Bulbs
        self.broadlink.toggle_tv_power("ON")
        # Dim/Turn OFF upper and far ambient panels
        self.tuya.set_relay_channel("A", 1, False) # S3
        self.tuya.set_relay_channel("A", 4, False) # S4
        self.tuya.set_relay_channel("B", 1, False) # S2
        self.broadlink.send_ac_command(24, power="ON", mode="COOL", fan="LOW")
        return self.get_telemetry()

    def process_telemetry_step(self, frame):
        """
        Core non-blocking execution loop step called at 5 FPS.
        FSD Section 7 Logic with device-specific auto-off timers:
        - Light Bulbs (LB): 3 seconds
        - LED Panels (LP): 5 seconds
        - Air Conditioner (AC): 10 Minutes (600s)
        """
        current_time = time.time()
        
        # OPTIMIZATION: If video stream is paused, suspend heavy motion & YOLO CPU calculation
        if getattr(self.stream_gen, "is_paused", False):
            return self.get_telemetry()

        # 1. Continuous Fast Motion Detection (5 FPS)
        motion_res = self.motion_engine.process_frame(frame)
        self.latest_motion_boxes = motion_res["contours"]
        self.zone_motion_levels = motion_res["zone_motion_levels"]

        # 2. Real-Time Occupancy Polling Loop
        if current_time - self.last_ai_check >= OCCUPANCY_POLL_INTERVAL_SEC:
            logger.info("[IrisOrchestrator] Running Real-Time YOLO Occupancy Polling...")
            occ_res = self.occupancy_engine.count_occupants(frame)
            self.headcount = occ_res["total_headcount"]
            self.latest_person_boxes = occ_res["boxes"]
            logger.info(f"[Project Iris] Current Headcount: {self.headcount}")

            # Detect hardware connection recovery to restart 3-strike vacancy countdown
            curr_connected = self.tuya.is_connected
            if not getattr(self, "was_hardware_connected", True) and curr_connected:
                logger.info("[IrisOrchestrator] Network reconnected. Restarting 3-strike vacancy timer...")
                self.vacancy_start_timestamp = current_time
                self.zero_occupancy_counter = 0
            self.was_hardware_connected = curr_connected

            if self.system_mode == "AUTO":
                if self.headcount > 0:
                    # Occupants present -> Reset zero vacancy tracking flags
                    self.vacancy_start_timestamp = None
                    self.zero_occupancy_counter = 0
                    self.lp_auto_off_done = False
                    self.ac_auto_off_done = False

                    # Turn ON TV Power
                    self.broadlink.toggle_tv_power("ON")

                    if self.headcount > HEADCOUNT_PANEL_ONLY_MAX:
                        # High occupancy (>3 occupants) -> Turn ON ALL lights & set AC to 22°C Cool High
                        logger.info(f"[Auto AI] Headcount > {HEADCOUNT_PANEL_ONLY_MAX} ({self.headcount} occupants detected) -> Turning ON ALL Light Bulbs (AZIOT Nodes 1-4). Setting AC to 22°C Cool High.")
                        # Actuate single AZIOT 4 Node Smart Switch channels 1-4 for Light Bulbs
                        self.tuya.set_relay_channel("A", 1, True) # S7 TV Area Bulbs
                        self.tuya.set_relay_channel("A", 2, True) # S4 Upper Bulbs
                        self.tuya.set_relay_channel("A", 3, True) # S2 Lower Bulbs
                        self.tuya.set_relay_channel("A", 4, True) # S12 Far Bulbs
                        self.broadlink.send_ac_command(22, power="ON", mode="COOL", fan="HIGH")

                        # Reset Light Bulb drop timer and auto-off flag
                        self.lb_drop_timestamp = None
                        self.lb_auto_off_done = False
                    else:
                        # Moderate occupancy (1-3 occupants) -> Actuate Light Bulbs (AZIOT 4 Node Switch)
                        logger.info(f"[Auto AI] Occupancy detected ({self.headcount} occupants) -> Actuating Light Bulbs on AZIOT 4 Node Switch (Nodes 1-4).")
                        self.tuya.set_relay_channel("A", 1, True) # S7 TV Area Bulbs
                        self.tuya.set_relay_channel("A", 2, True) # S4 Upper Bulbs
                        self.tuya.set_relay_channel("A", 3, True) # S2 Lower Bulbs
                        self.tuya.set_relay_channel("A", 4, True) # S12 Far Bulbs
                        self.broadlink.send_ac_command(24, power="ON", mode="COOL", fan="AUTO")

                        # Reset Light Bulb drop timer and auto-off flag
                        self.lb_drop_timestamp = None
                        self.lb_auto_off_done = False
                else:
                    # Headcount == 0 (Zero Occupancy)
                    self.zero_occupancy_counter += 1
                    if self.vacancy_start_timestamp is None:
                        self.vacancy_start_timestamp = current_time

                    vacancy_duration = current_time - self.vacancy_start_timestamp
                    logger.info(f"[Auto-Off AI] Zero Occupancy Duration: {vacancy_duration:.1f}s")

                    # RULE 1: Light Bulbs (LB) Auto-OFF after 3 seconds on AZIOT 4 Node Switch
                    any_bulbs_on = any(self.tuya.state_a[c] for c in [1, 2, 3, 4])
                    if vacancy_duration >= LB_AUTO_OFF_SEC and (not self.lb_auto_off_done or any_bulbs_on):
                        logger.info(f"[Auto-Off AI] {LB_AUTO_OFF_SEC}s Vacancy -> Auto Turning OFF Light Bulbs on AZIOT Switch (Nodes 1, 2, 3, 4)...")
                        r1 = self.tuya.set_relay_channel("A", 1, False) # S7 TV Area Bulbs
                        r2 = self.tuya.set_relay_channel("A", 2, False) # S4 Upper Bulbs
                        r3 = self.tuya.set_relay_channel("A", 3, False) # S2 Lower Bulbs
                        r4 = self.tuya.set_relay_channel("A", 4, False) # S12 Far Bulbs
                        if (r1 and r2 and r3 and r4) or self.tuya.mock_mode or not any(self.tuya.state_a[c] for c in [1, 2, 3, 4]):
                            self.lb_auto_off_done = True

                    # RULE 2: LED Panels (LP) Auto-OFF after 5 seconds
                    if vacancy_duration >= LP_AUTO_OFF_SEC and not self.lp_auto_off_done:
                        logger.info(f"[Auto-Off AI] {LP_AUTO_OFF_SEC}s Vacancy -> Auto Turning OFF LED Panels...")
                        self.lp_auto_off_done = True

                    # RULE 3: Air Conditioner (AC) Auto-OFF after 10 Minutes (600 seconds)
                    if vacancy_duration >= AC_AUTO_OFF_SEC and not self.ac_auto_off_done:
                        logger.info(f"[Auto-Off AI] {AC_AUTO_OFF_SEC}s (10 Minutes) Vacancy -> Auto Turning OFF Air Conditioner & TV...")
                        self.broadlink.send_ac_command(24, power="OFF")
                        self.broadlink.toggle_tv_power("OFF")
                        self.ac_auto_off_done = True

                # Synchronize spatial zone states dynamically based on active relay channels
                relays_state = self.tuya.get_state()
                for z_id, z_data in SPATIAL_ZONES.items():
                    self.zone_states[z_id] = any(
                        relays_state[f"Relay_{m}"][c] for m, c in z_data["relays"]
                    )

            self.last_ai_check = current_time

        # Update energy savings estimation dynamically
        all_lights_off = not any(self.zone_states.values())
        ac_off = self.broadlink.ac_state.get("power") == "OFF"
        if all_lights_off and ac_off:
            self.active_power_kw = IDLE_LOAD_POWER_KW
        else:
            self.active_power_kw = FULL_LOAD_POWER_KW

        # Saved = (Baseline Full Load - Actual Load) * Elapsed Hours
        saved_kw = (FULL_LOAD_POWER_KW - self.active_power_kw)
        self.total_kwh_saved += round(saved_kw * (5.0 / 3600.0), 5)
        self.total_cost_saved = round(self.total_kwh_saved * BASE_KWH_RATE, 2)

        return self.get_telemetry()

    def control_player(self, action: str, value=None):
        """Dispatches video player control commands to stream_gen."""
        if action == "play":
            self.stream_gen.play()
        elif action == "pause":
            self.stream_gen.pause()
        elif action == "toggle":
            self.stream_gen.toggle_play_pause()
        elif action == "seek":
            if value is not None:
                self.stream_gen.seek(float(value))
        elif action == "seek_relative":
            if value is not None:
                self.stream_gen.seek_relative(float(value))
        elif action == "step":
            if value is not None:
                self.stream_gen.step_frame(int(value))
        elif action == "set_speed":
            if value is not None:
                self.stream_gen.set_speed(float(value))
        elif action == "set_source":
            if value is not None:
                self.stream_gen.set_source(int(value))
        elif action == "live":
            self.stream_gen.jump_to_live()
        return self.stream_gen.get_player_status()

    def get_telemetry(self):
        """Returns snapshot payload for Frontend Dashboard (Section 8 requirements)."""
        relay_state = self.tuya.get_state()
        broadlink_state = self.broadlink.get_status()

        return {
            "timestamp": time.time(),
            "system_mode": self.system_mode,
            "headcount": self.headcount,
            "zero_occupancy_strikes": self.zero_occupancy_counter,
            "zone_states": self.zone_states,
            "zone_motion_levels": self.zone_motion_levels,
            "ac_state": broadlink_state["ac"],
            "tv_state": broadlink_state["tv"],
            "relays": relay_state,
            "player_state": self.stream_gen.get_player_status(),
            "energy_metrics": {
                "active_kw": round(self.active_power_kw, 2),
                "kwh_saved_today": round(self.total_kwh_saved, 3),
                "cost_saved_usd": round(self.total_cost_saved, 2)
            },
            "motion_boxes": self.latest_motion_boxes,
            "person_boxes": self.latest_person_boxes
        }
