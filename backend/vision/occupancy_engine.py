"""
Presence & Occupancy Engine (YOLOv8 at 30-sec Polling)
Calculates human headcount and spatial presence using YOLOv8 object detection.
FSD Reference: Section 6.2
"""

import logging
import numpy as np
import cv2
from config import SPATIAL_ZONES, YOLO_MODEL_PATH

logger = logging.getLogger("iris.vision.occupancy")

class OccupancyEngine:
    def __init__(self, model_name=YOLO_MODEL_PATH):
        self.model_name = model_name
        self.model = None
        self.use_mock = False
        self._init_model()

    def _init_model(self):
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model: {self.model_name}...")
            self.model = YOLO(self.model_name)
            logger.info("YOLO model loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load YOLO model ({e}). Using synthetic detection fallback.")
            self.use_mock = True

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
            results = self.model(frame, verbose=False)
            h, w = frame.shape[:2]
            headcount = 0
            zone_counts = {z_id: 0 for z_id in SPATIAL_ZONES}
            boxes = []

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls_id == 0 and conf >= 0.40: # Class 0 = Person
                        headcount += 1
                        xyxy = box.xyxy[0].tolist()
                        bx1, by1, bx2, by2 = xyxy
                        bw, bh = bx2 - bx1, by2 - by1
                        boxes.append({
                            "bbox": [int(bx1), int(by1), int(bw), int(bh)],
                            "confidence": round(conf, 2)
                        })

                        # Normalize center point
                        cx_norm = (bx1 + bw / 2.0) / float(w)
                        cy_norm = (by1 + bh / 2.0) / float(h)

                        for zone_id, zone_data in SPATIAL_ZONES.items():
                            x_min, y_min, x_max, y_max = zone_data["bbox"]
                            if x_min <= cx_norm <= x_max and y_min <= cy_norm <= y_max:
                                zone_counts[zone_id] += 1

            return {
                "total_headcount": headcount,
                "zone_counts": zone_counts,
                "boxes": boxes
            }

        except Exception as e:
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
