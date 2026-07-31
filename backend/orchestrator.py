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
    USE_SIMULATED_STREAM, HEADCOUNT_PANEL_ONLY_MAX, FAST_MOTION_FPS,
    HIGH_TIER_CONFIRM_POLLS, HIGH_TIER_RELEASE_SEC, DEBUG_DUMP_DIR,
    ZERO_OCCUPANCY_CONFIRM_POLLS, VACANCY_MOTION_VETO_SEC
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
        # Consecutive polls reading above the high-occupancy threshold.
        self.high_tier_streak = 0

        # Device Auto-Off Vacancy Tracking
        self.vacancy_start_timestamp = time.time()
        self.lb_drop_timestamp = None
        self.lb_auto_off_done = True
        self.lp_auto_off_done = True
        self.ac_auto_off_done = True

        # Active Zone Motion State
        self.zone_states = {z_id: False for z_id in SPATIAL_ZONES}
        self.zone_motion_levels = {z_id: 0 for z_id in SPATIAL_ZONES}
        # Wall-clock of the last frame that produced motion above the area gate.
        # Seeded to startup so a cold start does not read as "no motion ever".
        self.last_motion_timestamp = time.time()
        
        # Energy metrics
        self.total_kwh_saved = 0.42
        self.total_cost_saved = round(0.42 * BASE_KWH_RATE, 2)
        self.active_power_kw = IDLE_LOAD_POWER_KW

        # Motion bounding boxes & detection overlays
        self.latest_motion_boxes = []
        self.latest_person_boxes = []

        # Most recent frame handed to the vision engines. The MJPEG endpoint serves
        # this exact frame instead of pulling its own, so the drawn boxes always
        # belong to the image they are drawn on (and the camera is polled once).
        self.latest_frame = None

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

        # Motion is the vacancy veto's evidence, so record when it last fired.
        # Contours here are already area-gated by the engine, and a stale repeated
        # camera frame diffs to nothing -- so this only advances on real movement.
        if self.latest_motion_boxes:
            self.last_motion_timestamp = current_time

        # 2. Real-Time Occupancy Polling Loop
        #
        # The camera delivers roughly 0.5 FPS at 1080p while this polls at 1 Hz, so
        # the same frame is served to consecutive polls. Re-counting it is not an
        # independent observation -- the escalation logic below treats agreeing
        # polls as corroboration, and one frame counted twice corroborates nothing.
        # Skip until genuinely new pixels arrive.
        frame_seq = getattr(self.stream_gen, "last_served_seq", 0)
        stale_repeat = frame_seq and frame_seq == getattr(self, "last_polled_seq", 0)

        if current_time - self.last_ai_check >= OCCUPANCY_POLL_INTERVAL_SEC and not stale_repeat:
            self.last_polled_seq = frame_seq
            logger.info("[IrisOrchestrator] Running Real-Time YOLO Occupancy Polling...")
            occ_res = self.occupancy_engine.count_occupants(frame)
            self.headcount = occ_res["total_headcount"]
            self.latest_person_boxes = occ_res["boxes"]
            logger.info(f"[Project Iris] Current Headcount: {self.headcount}")

            # Evidence capture: dump any frame that reads above the high-occupancy
            # threshold, with boxes drawn, so a spurious extra occupant can be
            # identified rather than merely damped. Rate-limited, off by default.
            if DEBUG_DUMP_DIR and self.headcount > HEADCOUNT_PANEL_ONLY_MAX:
                self._dump_debug_frame(frame, occ_res, current_time)

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

                    # Escalation confidence scales with how far past the threshold we
                    # are, because detection error is about +/-1 person.
                    #
                    #   count 4 (margin 1): a -1 error means the truth is 3, i.e. the
                    #       wrong tier. Ambiguous, so wait for corroborating polls.
                    #   count 5+ (margin 2+): even a -1 error still leaves us above
                    #       the threshold, so the tier is right either way. Act now.
                    #
                    # Measured on this camera with 3 people present, a spurious 4th
                    # appeared in 0.27% of polls and a spurious 5th never did, so two
                    # agreeing polls at margin 1 puts a false escalation somewhere
                    # around once every 37 hours.
                    margin = self.headcount - HEADCOUNT_PANEL_ONLY_MAX
                    if margin > 0:
                        self.high_tier_streak += 1
                    else:
                        self.high_tier_streak = 0

                    required_polls = 1 if margin >= 2 else HIGH_TIER_CONFIRM_POLLS

                    if margin > 0 and self.high_tier_streak >= required_polls:
                        # High occupancy (>3 occupants) -> Turn ON ALL light bulbs (S7, S4, S2, S12) & set AC to 22°C Cool High
                        basis = ("margin 2+, acted immediately" if margin >= 2
                                 else f"margin 1, confirmed over {self.high_tier_streak} polls")
                        logger.info(f"[Auto AI] Headcount {self.headcount} > {HEADCOUNT_PANEL_ONLY_MAX} "
                                    f"({basis}) -> Turning ON ALL Light Bulbs (S7, S4, S2, S12). "
                                    "Setting AC to 22°C Cool High.")
                        self.tuya.set_relay_channel("A", 1, True)  # S7 TV Area Bulbs
                        self.tuya.set_relay_channel("A", 2, True)  # S4 Upper Bulbs
                        self.tuya.set_relay_channel("A", 3, True)  # S2 Lower Bulbs
                        self.tuya.set_relay_channel("A", 4, True)  # S12 Far Bulbs
                        self.broadlink.send_ac_command(22, power="ON", mode="COOL", fan="HIGH")

                        # Reset drop timer and auto-off flag
                        self.lb_drop_timestamp = None
                        self.lb_auto_off_done = False
                    else:
                        # Moderate occupancy (1-3 occupants) -> S4 & S12 stay ON
                        self.tuya.set_relay_channel("A", 2, True)  # S4 Upper Bulbs ON
                        self.tuya.set_relay_channel("A", 4, True)  # S12 Far Bulbs ON
                        self.broadlink.send_ac_command(24, power="ON", mode="COOL", fan="AUTO")

                        # Asymmetric hysteresis on the extra bulbs (S7 & S2).
                        #
                        # People do not notice a light arriving a second late, but they
                        # very much notice one switching off and straight back on -- that
                        # reads as a broken product. Detection wobbles around the 3/4
                        # boundary, so releasing after a few seconds means a count of
                        # 4-3-4 cycles the room visibly.
                        #
                        # So: escalate quickly (HIGH_TIER_CONFIRM_POLLS), release slowly.
                        # Holding light that is no longer needed costs a little energy;
                        # strobing the room costs the customer's confidence.
                        s7_s2_on = self.tuya.state_a[1] or self.tuya.state_a[3]
                        if s7_s2_on:
                            if self.lb_drop_timestamp is None:
                                self.lb_drop_timestamp = current_time
                            drop_duration = current_time - self.lb_drop_timestamp
                            if drop_duration >= HIGH_TIER_RELEASE_SEC:
                                logger.info(f"[Hysteresis] Moderate occupancy held for {drop_duration:.0f}s "
                                            "-> releasing extra bulbs (S7 & S2).")
                                self.tuya.set_relay_channel("A", 1, False) # S7 OFF
                                self.tuya.set_relay_channel("A", 3, False) # S2 OFF
                                self.lb_drop_timestamp = None
                            else:
                                logger.info(f"[Hysteresis] Headcount {self.headcount}. Holding extra bulbs "
                                            f"({HIGH_TIER_RELEASE_SEC - drop_duration:.0f}s before release)...")
                        else:
                            self.lb_drop_timestamp = None

                        self.lb_auto_off_done = False
                else:
                    # Headcount == 0 (Zero Occupancy)
                    #
                    # Two independent conditions must BOTH hold before the vacancy
                    # clock is allowed to run. Turning the room dark on people who
                    # are still in it is the worst failure this system has, and a
                    # single zero-reading frame is weak evidence of an empty room:
                    # the head model is face-biased, and the body model loses anyone
                    # the sofa or a desk occludes.
                    #
                    #   1. Agreement across polls. One bad frame is noise; three
                    #      consecutive are a pattern.
                    #   2. No recent motion. Frame differencing shares no failure
                    #      mode with the detectors -- it does not know what a person
                    #      is, only that pixels moved -- so it still sees the person
                    #      turned away that both models just lost.
                    #
                    # An empty room satisfies both within seconds, so genuine
                    # auto-off is delayed by the confirmation window, not prevented.
                    self.zero_occupancy_counter += 1

                    motion_age = current_time - self.last_motion_timestamp
                    motion_veto = (VACANCY_MOTION_VETO_SEC > 0
                                   and motion_age < VACANCY_MOTION_VETO_SEC)
                    strikes_met = self.zero_occupancy_counter >= ZERO_OCCUPANCY_CONFIRM_POLLS

                    if motion_veto or not strikes_met:
                        # Hold the clock at zero. Not merely paused -- reset, so a
                        # person who steps out of frame and back in does not
                        # accumulate credit toward switching the room off.
                        self.vacancy_start_timestamp = None
                        if motion_veto:
                            logger.info(f"[Auto-Off AI] Headcount 0 but motion {motion_age:.1f}s ago "
                                        f"(< {VACANCY_MOTION_VETO_SEC:.0f}s) -> vacancy vetoed, room in use.")
                        else:
                            logger.info(f"[Auto-Off AI] Zero-occupancy strike "
                                        f"{self.zero_occupancy_counter}/{ZERO_OCCUPANCY_CONFIRM_POLLS} "
                                        "-> awaiting confirmation before vacancy timer starts.")
                    else:
                        if self.vacancy_start_timestamp is None:
                            self.vacancy_start_timestamp = current_time

                        vacancy_duration = current_time - self.vacancy_start_timestamp
                        logger.info(f"[Auto-Off AI] Zero Occupancy Duration: {vacancy_duration:.1f}s")

                        # RULE 1: Light Bulbs (LB) Auto-OFF on AZIOT 4 Node Switch
                        any_bulbs_on = any(self.tuya.state_a[c] for c in [1, 2, 3, 4])
                        if vacancy_duration >= LB_AUTO_OFF_SEC and (not self.lb_auto_off_done or any_bulbs_on):
                            logger.info(f"[Auto-Off AI] {LB_AUTO_OFF_SEC}s Vacancy -> Auto Turning OFF Light Bulbs on AZIOT Switch (Nodes 1, 2, 3, 4)...")
                            r1 = self.tuya.set_relay_channel("A", 1, False) # S7 TV Area Bulbs
                            r2 = self.tuya.set_relay_channel("A", 2, False) # S4 Upper Bulbs
                            r3 = self.tuya.set_relay_channel("A", 3, False) # S2 Lower Bulbs
                            r4 = self.tuya.set_relay_channel("A", 4, False) # S12 Far Bulbs
                            if (r1 and r2 and r3 and r4) or self.tuya.mock_mode or not any(self.tuya.state_a[c] for c in [1, 2, 3, 4]):
                                self.lb_auto_off_done = True

                        # RULE 2: LED Panels (LP) Auto-OFF
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

        # Saved = (Baseline Full Load - Actual Load) * Elapsed Hours.
        # This runs once per telemetry tick, so the elapsed term is the tick period
        # (1/FAST_MOTION_FPS seconds), not 5 seconds.
        saved_kw = (FULL_LOAD_POWER_KW - self.active_power_kw)
        tick_hours = (1.0 / FAST_MOTION_FPS) / 3600.0
        self.total_kwh_saved += saved_kw * tick_hours
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

    def _dump_debug_frame(self, frame, occ_res, current_time):
        """Writes an annotated copy of a frame that read above the high tier."""
        if current_time - getattr(self, "_last_dump_ts", 0) < 2.0:
            return
        self._last_dump_ts = current_time
        try:
            import os
            import cv2
            os.makedirs(DEBUG_DUMP_DIR, exist_ok=True)
            img = frame.copy()
            for b in occ_res.get("boxes", []):
                x, y, bw, bh = b["bbox"]
                is_body = b.get("source") == "body"
                colour = (0, 220, 90) if is_body else (0, 170, 255)
                label = "BODY" if is_body else f"HEAD {b.get('head_h')}"
                cv2.rectangle(img, (x, y), (x + bw, y + bh), colour, 3)
                cv2.putText(img, f"{label} {b.get('confidence')}", (x, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2)
            cv2.putText(img, f"COUNT={occ_res.get('total_headcount')}", (40, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 4)
            path = os.path.join(DEBUG_DUMP_DIR, f"high_{int(current_time)}.jpg")
            cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
            logger.info(f"[Debug] Wrote high-count frame to {path}")
        except Exception as e:
            logger.warning(f"Debug frame dump failed: {e}")

    def get_telemetry(self):
        """Returns snapshot payload for Frontend Dashboard (Section 8 requirements)."""
        relay_state = self.tuya.get_state()
        broadlink_state = self.broadlink.get_status()

        return {
            "timestamp": time.time(),
            "system_mode": self.system_mode,
            "headcount": self.headcount,
            "zero_occupancy_strikes": self.zero_occupancy_counter,
            "zero_occupancy_strikes_required": ZERO_OCCUPANCY_CONFIRM_POLLS,
            # Seconds since motion was last seen. The dashboard can show why the
            # lights are still on at headcount 0 instead of looking stuck.
            "seconds_since_motion": round(time.time() - self.last_motion_timestamp, 1),
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
