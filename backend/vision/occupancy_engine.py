"""
Presence & Occupancy Engine (YOLOv8 at 30-sec Polling)
Calculates human headcount and spatial presence using YOLOv8 object detection.
FSD Reference: Section 6.2
"""

import logging
import numpy as np
import cv2
from config import (
    SPATIAL_ZONES, YOLO_MODEL_PATH, DETECTION_CONFIDENCE,
    DETECTION_IMGSZ, DETECTION_IOU,
    DETECTION_MIN_HEAD_H, DETECTION_ROI,
    PERSON_MODEL_PATH, PERSON_CONFIDENCE, PERSON_MIN_BODY_H, PERSON_ALWAYS_ON,
    BODY_OVERLAP_MERGE,
    HEADCOUNT_PANEL_ONLY_MAX,
)

logger = logging.getLogger("iris.vision.occupancy")

class OccupancyEngine:
    def __init__(self, model_name=YOLO_MODEL_PATH):
        self.model_name = model_name
        self.model = None
        self.person_model = None
        self.device = "cpu"
        self.use_mock = False
        self._init_model()
        self._init_person_model()

    def _init_model(self):
        try:
            import os
            import torch
            from ultralytics import YOLO

            # Cap CPU processing threads to 50% available cores
            total_cores = os.cpu_count() or 4
            half_cores = max(1, total_cores // 2)
            try:
                torch.set_num_threads(half_cores)
            except Exception:
                pass

            # Device selection (explicit override -> CUDA -> MPS -> CPU fallback).
            # A CUDA GPU is only usable if the installed torch build actually ships
            # kernels for its compute capability. Selecting an unsupported GPU makes
            # every predict() raise "no kernel image is available for execution on the
            # device", which would silently demote us to the heuristic blob counter.
            forced = os.environ.get("IRIS_YOLO_DEVICE", "").strip().lower()
            if forced:
                self.device = forced
                logger.info(f"Device pinned by IRIS_YOLO_DEVICE -> [{self.device}].")
            elif torch.cuda.is_available() and self._cuda_is_supported(torch):
                self.device = "cuda:0"
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU Hardware Detected ({gpu_name}). Prioritizing GPU inference on device [{self.device}]...")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"
                logger.info("Apple MPS GPU Acceleration Detected. Initializing YOLO on MPS GPU...")
            else:
                self.device = "cpu"
                logger.info(f"Using CPU inference (Allocated {half_cores}/{total_cores} CPU threads).")

            logger.info(f"Loading YOLO model weights from: {self.model_name}...")
            self.model = YOLO(self.model_name)

            try:
                self.model.to(self.device)
                logger.info(f"YOLO model successfully assigned to device: {self.device}")
            except Exception as e_dev:
                logger.warning(f"Could not explicitly assign model device ({e_dev}). Will use device flag during predict calls.")

            # Warm up on a dummy frame so a broken device fails here, at startup,
            # rather than once per second inside the live telemetry loop.
            if not self._warmup(np.zeros((720, 1280, 3), dtype=np.uint8)):
                logger.warning(f"Warmup failed on [{self.device}]. Demoting to CPU inference.")
                self.device = "cpu"
                try:
                    self.model.to("cpu")
                except Exception:
                    pass
                if not self._warmup(np.zeros((720, 1280, 3), dtype=np.uint8)):
                    raise RuntimeError("YOLO warmup failed on both GPU and CPU")

            logger.info(f"YOLO Occupancy Engine initialized (Target Device: {self.device}, classes: {getattr(self.model, 'names', {})}).")
        except Exception as e:
            logger.error(
                f"Failed to load YOLO model ({e}). Falling back to the heuristic blob counter -- "
                "headcount will NOT be reliable."
            )
            self.use_mock = True

    def _init_person_model(self):
        """Optional COCO person detector used as a safety net for missed heads."""
        if not PERSON_MODEL_PATH:
            return
        try:
            from ultralytics import YOLO
            self.person_model = YOLO(PERSON_MODEL_PATH)
            self.person_model.to(self.device)
            self.person_model(np.zeros((720, 1280, 3), dtype=np.uint8),
                              device=self.device, classes=[0], verbose=False)
            logger.info(f"Person safety-net model loaded from {PERSON_MODEL_PATH} "
                        f"(min body height {PERSON_MIN_BODY_H}).")
        except Exception as e:
            logger.error(f"Failed to load person model ({e}). Safety net disabled.")
            self.person_model = None

    def _rescue_missed_people(self, frame, all_head_centres):
        """
        Recovers occupants the head model failed on (someone turned away from the
        camera renders no face, and this head model is face-biased).

        Body geometry cannot be used to judge distance here: measurements showed
        the developer row sitting between the near occupants on height, width,
        area and bottom edge, because a standing person is cropped by the table
        while a seated one is cropped by their desk.

        What does discriminate is whether the head model saw *anything* there:
          - head found inside the body, then size-gated away -> genuinely distant,
            already correctly rejected, so do not resurrect it.
          - no head found inside the body at all -> the head model failed on a
            pose, so trust the body detector and count the person.

        Returns (rescued_count, rescued_boxes).
        """
        if self.person_model is None:
            return 0, []
        try:
            h, w = frame.shape[:2]
            res = self.person_model(
                frame, device=self.device, verbose=False, classes=[0],
                conf=PERSON_CONFIDENCE, imgsz=DETECTION_IMGSZ, iou=DETECTION_IOU,
            )[0]

            rescued, boxes = 0, []
            candidates, kept = [], []
            for b in res.boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                body_h = (y2 - y1) / float(h)

                # Floor on body size keeps deep-background people out.
                if PERSON_MIN_BODY_H and body_h < PERSON_MIN_BODY_H:
                    continue

                if DETECTION_ROI:
                    rx1, ry1, rx2, ry2 = DETECTION_ROI
                    cx = ((x1 + x2) / 2.0) / float(w)
                    cy = ((y1 + y2) / 2.0) / float(h)
                    if not (rx1 <= cx <= rx2 and ry1 <= cy <= ry2):
                        continue

                # Already accounted for (counted or deliberately gated) by the head
                # model? Test against a padded box: a body box frequently starts just
                # below the crown of the head or clips it, and an exact containment
                # test then fails to pair a head with its own body -- counting that
                # person twice, once as a head and again as a "rescue".
                pad_x = (x2 - x1) * 0.25
                pad_y = (y2 - y1) * 0.25
                if any(x1 - pad_x <= hx <= x2 + pad_x and y1 - pad_y <= hy <= y2 + pad_y
                       for hx, hy in all_head_centres):
                    continue

                candidates.append((float(b.conf[0]), x1, y1, x2, y2, body_h))

            # Suppress duplicate bodies. The detector regularly emits both a partial
            # box (head and shoulders above a desk) and a full box for the same
            # person; their IoU stays under the NMS threshold, so both survive and
            # the person is counted twice. Compare intersection against the SMALLER
            # box, which catches the nested case that plain IoU misses.
            candidates.sort(key=lambda c: -c[0])
            for conf, x1, y1, x2, y2, body_h in candidates:
                duplicate = False
                for _, kx1, ky1, kx2, ky2, _ in kept:
                    ix = max(0.0, min(x2, kx2) - max(x1, kx1))
                    iy = max(0.0, min(y2, ky2) - max(y1, ky1))
                    inter = ix * iy
                    if inter <= 0:
                        continue
                    smaller = min((x2 - x1) * (y2 - y1), (kx2 - kx1) * (ky2 - ky1))
                    if smaller > 0 and inter / smaller > BODY_OVERLAP_MERGE:
                        duplicate = True
                        break
                if duplicate:
                    continue
                kept.append((conf, x1, y1, x2, y2, body_h))
                rescued += 1
                boxes.append({
                    "bbox": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                    "confidence": round(conf, 2),
                    "body_h": round(body_h, 4),
                    "source": "body"
                })

            if rescued:
                logger.info("[Occupancy] Rescued body heights: "
                            + ", ".join(f"{b['body_h']:.3f}" for b in boxes))
            return rescued, boxes
        except Exception as e:
            logger.error(f"Person safety-net inference failed: {e}")
            return 0, []

    def _cuda_is_supported(self, torch) -> bool:
        """True only if the installed torch build ships kernels for this GPU's arch."""
        try:
            major, minor = torch.cuda.get_device_capability(0)
            device_arch = f"sm_{major}{minor}"
            supported = torch.cuda.get_arch_list()
            if supported and device_arch not in supported:
                logger.warning(
                    f"GPU {torch.cuda.get_device_name(0)} is {device_arch}, but this torch build "
                    f"only supports {supported}. Skipping GPU and using CPU inference."
                )
                return False
            return True
        except Exception as e:
            logger.warning(f"Could not verify CUDA compute capability ({e}). Using CPU inference.")
            return False

    def _warmup(self, frame) -> bool:
        """Runs one throwaway inference to prove the selected device actually executes."""
        try:
            self.model(frame, device=self.device, verbose=False)
            return True
        except Exception as e:
            logger.warning(f"Warmup inference on [{self.device}] failed: {e}")
            return False

    def count_occupants(self, frame):
        """
        Runs YOLO object detection for human presence (class 0).
        Returns:
            dict: {
                "total_headcount": int,
                "zone_counts": dict of {zone_id: count},
                "boxes": list of [{"bbox": [x, y, w, h], "confidence": float}]
            }
        """
        if self.use_mock or self.model is None:
            return self._heuristic_occupancy(frame)

        try:
            results = self.model(
                frame,
                device=self.device,
                verbose=False,
                imgsz=DETECTION_IMGSZ,
                iou=DETECTION_IOU,
            )
            h, w = frame.shape[:2]
            headcount = 0
            rejected = 0
            zone_counts = {z_id: 0 for z_id in SPATIAL_ZONES}
            boxes = []
            # Every head the model saw, gated or not. A head that was rejected for
            # being distant still proves the head model was working there, which
            # stops the body detector from resurrecting that same person.
            all_head_centres = []

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    # best.pt is a single-class head detector, so class 0 is a head.
                    # One head == one occupant, so this still yields the headcount.
                    if cls_id == 0 and conf >= DETECTION_CONFIDENCE:
                        xyxy = box.xyxy[0].tolist()
                        bx1, by1, bx2, by2 = xyxy
                        bw, bh = bx2 - bx1, by2 - by1

                        # Normalize center point
                        cx_norm = (bx1 + bw / 2.0) / float(w)
                        cy_norm = (by1 + bh / 2.0) / float(h)
                        bh_norm = bh / float(h)
                        all_head_centres.append((bx1 + bw / 2.0, by1 + bh / 2.0))

                        # Depth gate: distant heads (the developer row behind the
                        # lounge) project smaller than anyone actually in the room.
                        if DETECTION_MIN_HEAD_H and bh_norm < DETECTION_MIN_HEAD_H:
                            rejected += 1
                            continue

                        # Region gate: ignore heads outside the controlled area.
                        if DETECTION_ROI:
                            rx1, ry1, rx2, ry2 = DETECTION_ROI
                            if not (rx1 <= cx_norm <= rx2 and ry1 <= cy_norm <= ry2):
                                rejected += 1
                                continue

                        headcount += 1
                        boxes.append({
                            "bbox": [int(bx1), int(by1), int(bw), int(bh)],
                            "confidence": round(conf, 2),
                            "head_h": round(bh_norm, 4)
                        })

                        for zone_id, zone_data in SPATIAL_ZONES.items():
                            x_min, y_min, x_max, y_max = zone_data["bbox"]
                            if x_min <= cx_norm <= x_max and y_min <= cy_norm <= y_max:
                                zone_counts[zone_id] += 1

            if rejected:
                logger.info(f"[Occupancy] {rejected} detection(s) gated out (too distant / outside region).")

            # The body model costs roughly as much again as the head model (~1s
            # combined on this CPU, against a 1s poll), so only spend it when it
            # can actually change the lighting decision:
            #   0 heads      -> a miss here wrongly reports an empty room and kills
            #                   the lights while people are still in it.
            #   >= threshold -> one more occupant crosses into the "all lines on"
            #                   tier, so an extra body matters.
            #   1..threshold-1 -> the tier is identical whether it is 1, 2 or 3
            #                   people, so a rescue would change nothing.
            worth_checking = (headcount == 0
                              or headcount >= HEADCOUNT_PANEL_ONLY_MAX
                              or PERSON_ALWAYS_ON)
            rescued, rescued_boxes = (
                self._rescue_missed_people(frame, all_head_centres)
                if worth_checking else (0, [])
            )
            if rescued:
                logger.info(f"[Occupancy] Body detector recovered {rescued} occupant(s) "
                            "the head model missed.")
                headcount += rescued
                boxes.extend(rescued_boxes)

            return {
                "total_headcount": headcount,
                "zone_counts": zone_counts,
                "boxes": boxes
            }

        except Exception as e:
            # A device-level failure repeats on every single poll, so demote to CPU
            # once and keep running real inference instead of quietly degrading to
            # the blob counter for the rest of the session.
            if self.device != "cpu":
                logger.error(f"YOLO inference failed on [{self.device}] ({e}). Demoting to CPU permanently.")
                self.device = "cpu"
                try:
                    self.model.to("cpu")
                except Exception:
                    pass
                try:
                    return self.count_occupants(frame)
                except Exception as e_cpu:
                    logger.error(f"YOLO CPU inference also failed: {e_cpu}")
            else:
                logger.error(f"YOLO inference error: {e}")
            return self._heuristic_occupancy(frame)

    def _heuristic_occupancy(self, frame):
        """Synthetic fallback when YOLO model weights are unavailable or in dry run."""
        h, w = frame.shape[:2]
        # Detect bright torso circles / skin tone approximations in synthetic stream
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Mask non-background elements
        mask = cv2.inRange(hsv, (0, 30, 60), (180, 255, 255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        zone_counts = {z_id: 0 for z_id in SPATIAL_ZONES}
        for c in contours:
            if 400 < cv2.contourArea(c) < 5000:
                x, y, bw, bh = cv2.boundingRect(c)
                boxes.append({"bbox": [x, y, bw, bh], "confidence": 0.85})
                cx_norm = (x + bw / 2.0) / float(w)
                cy_norm = (y + bh / 2.0) / float(h)
                for zone_id, zone_data in SPATIAL_ZONES.items():
                    x_min, y_min, x_max, y_max = zone_data["bbox"]
                    if x_min <= cx_norm <= x_max and y_min <= cy_norm <= y_max:
                        zone_counts[zone_id] += 1

        headcount = min(len(boxes), 6)
        return {
            "total_headcount": headcount,
            "zone_counts": zone_counts,
            "boxes": boxes[:headcount]
        }
