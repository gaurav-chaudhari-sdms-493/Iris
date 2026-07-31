"""
Fast Motion Engine (OpenCV at 5 FPS)
Computes spatial pixel-differencing across defined office zones for instant lighting control (<1s delay).
FSD Reference: Section 6.1
"""

import cv2
import numpy as np
import logging
from config import SPATIAL_ZONES

logger = logging.getLogger("iris.vision.motion")

class FastMotionEngine:
    def __init__(self, min_contour_area=3500):
        self.min_contour_area = min_contour_area
        self.prev_gray = None

    def process_frame(self, frame):
        """
        Processes an incoming CCTV video frame and identifies spatial zones with motion.
        Returns:
            dict: {
                "active_zones": list of zone_ids,
                "zone_motion_levels": dict of {zone_id: area_count},
                "contours": list of bounding boxes [(x, y, w, h)]
            }
        """
        h, w = frame.shape[:2]

        # min_contour_area was tuned against 1280x720. Scale it with the frame so a
        # higher-resolution camera doesn't flood the overlay with noise boxes.
        area_threshold = self.min_contour_area * ((w * h) / (1280.0 * 720.0))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Frame size can change mid-stream: live CCTV serves native 1920x1080 while
        # the synthetic fallback is 1280x720, so any camera dropout swaps resolution
        # between consecutive frames. absdiff on mismatched shapes raises
        # "Sizes of input arguments do not match" -- reseed the baseline instead.
        if self.prev_gray is None or self.prev_gray.shape != gray.shape:
            self.prev_gray = gray
            return {"active_zones": [], "zone_motion_levels": {}, "contours": []}

        # Frame absolute difference
        diff = cv2.absdiff(self.prev_gray, gray)
        _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)

        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        self.prev_gray = gray

        active_zones = set()
        zone_motion_levels = {zone_id: 0 for zone_id in SPATIAL_ZONES}
        valid_motion_boxes = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < area_threshold:
                continue

            x, y, box_w, box_h = cv2.boundingRect(contour)
            valid_motion_boxes.append((x, y, box_w, box_h))

            # Normalize contour center coordinates (0.0 to 1.0)
            cx_norm = (x + box_w / 2.0) / float(w)
            cy_norm = (y + box_h / 2.0) / float(h)

            # Check which spatial zone contains the motion center
            for zone_id, zone_data in SPATIAL_ZONES.items():
                x_min, y_min, x_max, y_max = zone_data["bbox"]
                if x_min <= cx_norm <= x_max and y_min <= cy_norm <= y_max:
                    active_zones.add(zone_id)
                    zone_motion_levels[zone_id] += int(area)

        return {
            "active_zones": list(active_zones),
            "zone_motion_levels": zone_motion_levels,
            "contours": valid_motion_boxes
        }
