"""
Non-Blocking Async Orchestration Engine
Coordinates OpenCV fast motion detection, 30-second YOLO headcount polling,
hardware state updates, and energy savings calculations without RTSP buffer lag.
FSD Reference: Section 7
"""

import time
import asyncio
import logging
from config import (
    SPATIAL_ZONES, SWITCH_MAPPINGS, OCCUPANCY_POLL_INTERVAL_SEC,
    VACANCY_SHUTOFF_STRIKES, BASE_KWH_RATE, FULL_LOAD_POWER_KW, IDLE_LOAD_POWER_KW,
    USE_SIMULATED_STREAM
)
from hardware import TuyaRelayManager, BroadlinkIRManager
from vision import FastMotionEngine, OccupancyEngine, SyntheticStreamGenerator

logger = logging.getLogger("iris.orchestrator")

class IrisOrchestrator:
    def __init__ (self):
        self.tuya = TuyaRelayManager()
        self.broadlink = BroadlinkIRManager()
        self.motion_engine = FastMotionEngine()
        self.occupancy_engine = OccupancyEngine()
        self.stream_gen = SyntheticStreamGenerator()

        # System State Variables
        self.is_running = False
        self.system_mode = "AUTO"  # AUTO, MANUAL, PRESENTATION, POWER_SAVING
        self.headcount = 2
        self.last_ai_check = time.time()
        self.zero_occupancy_counter = 0
        self.start_timestamp = time.time()

        # Active Zone Motion State
        self.zone_states = {z_id: True for z_id in SPATIAL_ZONES}
        self.zone_motion_levels = {z_id: 0 for z_id in SPATIAL_ZONES}
        
        # Energy metrics
        self.total_kwh_saved = 0.42
        self.total_cost_saved = round(0.42 * BASE_KWH_RATE, 2)
        self.active_power_kw = FULL_LOAD_POWER_KW

        # Motion bounding boxes & detection overlays
        self.latest_motion_boxes = []
        self.latest_person_boxes = []

        # Turn ON initial lighting default
        self._apply_zone_lighting("Zone_1_Upper", True)
        self._apply_zone_lighting("Zone_2_Lower", True)

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
        FSD Section 7 Logic.
        """
        current_time = time.time()
        
        # 1. Continuous Fast Motion Detection (5 FPS)
        motion_res = self.motion_engine.process_frame(frame)
        self.latest_motion_boxes = motion_res["contours"]
        self.zone_motion_levels = motion_res["zone_motion_levels"]

        # Motion detection updated for overlay telemetry tracking (No automatic device switching on motion)

        # 2. Real-Time 1-Second YOLO Occupancy Polling Loop
        if current_time - self.last_ai_check >= OCCUPANCY_POLL_INTERVAL_SEC:
            logger.info("[IrisOrchestrator] Running 1-Second Real-Time YOLO Occupancy Polling...")
            occ_res = self.occupancy_engine.count_occupants(frame)
            self.headcount = occ_res["total_headcount"]
            self.latest_person_boxes = occ_res["boxes"]
            logger.info(f"[Project Iris] Current Headcount: {self.headcount}")

            if self.system_mode == "AUTO":
                if self.headcount > 0:
                    self.zero_occupancy_counter = 0
                    
                    # Auto re-energize spatial zone lights where people are detected
                    for z_id, count in occ_res.get("zone_counts", {}).items():
                        if count > 0 and not self.zone_states.get(z_id, False):
                            logger.info(f"[Auto AI] Person detected in {z_id}. Turning ON zone lights.")
                            self._apply_zone_lighting(z_id, True)

                    # If all lights were OFF, turn on default active zone lights
                    if not any(self.zone_states.values()):
                        for z_id in SPATIAL_ZONES:
                            self._apply_zone_lighting(z_id, True)

                    if self.headcount >= 4:
                        # High occupancy -> Lower AC Temp to 22°C (High Fan)
                        logger.info("High Occupancy (>=4). Setting AC to 22°C Cool High.")
                        self.broadlink.send_ac_command(22, power="ON", mode="COOL", fan="HIGH")
                    else:
                        # Standard occupancy -> 24°C Cool Auto
                        logger.info("Standard Occupancy (<4). Setting AC to 24°C Cool Auto.")
                        self.broadlink.send_ac_command(24, power="ON", mode="COOL", fan="AUTO")
                else:
                    self.zero_occupancy_counter += 1
                    logger.warning(f"Zero Occupancy check strike {self.zero_occupancy_counter}/{VACANCY_SHUTOFF_STRIKES}")
                    
                    # 3 consecutive zero occupancy checks (3 seconds) -> Vacancy Shutoff
                    if self.zero_occupancy_counter >= VACANCY_SHUTOFF_STRIKES:
                        logger.info("[Project Iris] Vacancy confirmed (0 occupants). Office energy shutoff engaged.")
                        # Turn off all zone lighting relays
                        for z_id in SPATIAL_ZONES:
                            self._apply_zone_lighting(z_id, False)
                        # Turn off AC and TV
                        self.broadlink.send_ac_command(24, power="OFF")
                        self.broadlink.toggle_tv_power("OFF")

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

