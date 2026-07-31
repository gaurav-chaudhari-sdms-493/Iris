#!/usr/bin/env python3
"""
Dual-model gate calibration.

Captures a burst of frames with people in BOTH the lounge and the developer row,
runs the head model and the COCO person model over each, and dumps every
geometric feature of every detection so a separating threshold can be chosen
from data rather than guessed.

Body-box HEIGHT is deliberately not assumed to be the answer: a seated person is
occluded by a desk and measures short, so height confuses "far away" with
"hidden behind furniture". This tool measures several candidate features and
reports which one actually splits the two groups.

Usage:
    cd backend
    ./iris_env/bin/python -m hardware.calibrate_gates --shots 10
"""

import os
import sys
import json
import time
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
import numpy as np
import requests
from requests.auth import HTTPDigestAuth

from config import (
    load_dotenv_file, CCTV_SNAPSHOT_WIDTH, CCTV_SNAPSHOT_HEIGHT,
    YOLO_MODEL_PATH, DETECTION_IMGSZ, DETECTION_IOU,
)

load_dotenv_file()

PERSON_WEIGHTS = os.environ.get("IRIS_PERSON_MODEL") or "models/yolo11s.pt"


def grab(url, auth):
    r = requests.get(url, auth=auth, timeout=8)
    r.raise_for_status()
    return cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)


def features(x1, y1, x2, y2, W, H):
    """Candidate depth cues, all normalized so they are resolution independent."""
    return {
        "h": round((y2 - y1) / H, 4),        # box height
        "w": round((x2 - x1) / W, 4),        # box width
        "area": round(((x2 - x1) * (y2 - y1)) / (W * H), 5),
        "top": round(y1 / H, 4),             # top edge  (higher in frame = farther)
        "bottom": round(y2 / H, 4),          # bottom edge (lower in frame = nearer)
        "cx": round(((x1 + x2) / 2) / W, 4),
        "cy": round(((y1 + y2) / 2) / H, 4),
    }


def separation(vals_a, vals_b, key, higher_is_near=True):
    """Score how cleanly `key` splits group A (near) from group B (far)."""
    a = [v[key] for v in vals_a]
    b = [v[key] for v in vals_b]
    if not a or not b:
        return None
    if higher_is_near:
        lo_near, hi_far = min(a), max(b)
    else:
        lo_near, hi_far = -max(a), -min(b)
    gap = lo_near - hi_far
    spread = max(abs(lo_near), abs(hi_far), 1e-6)
    return {
        "key": key,
        "near_min": min(a), "near_max": max(a),
        "far_min": min(b), "far_max": max(b),
        "gap": round(gap, 4),
        "margin_pct": round(100.0 * gap / spread, 1),
        "threshold": round((lo_near + hi_far) / 2.0, 4) if gap > 0 else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=10)
    ap.add_argument("--interval", type=float, default=2.5)
    ap.add_argument("--channel", default="601")
    ap.add_argument("--person-conf", type=float, default=0.35)
    ap.add_argument("--head-conf", type=float, default=0.30)
    ap.add_argument("--outdir", default="/tmp/iris_calib")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    from ultralytics import YOLO

    ip = os.environ.get("CCTV_IP", "192.168.0.21")
    auth = HTTPDigestAuth(os.environ.get("CCTV_USER", "admin"),
                          os.environ.get("CCTV_PASS", ""))
    url = (f"http://{ip}/ISAPI/Streaming/channels/{args.channel}/picture"
           f"?videoResolutionWidth={CCTV_SNAPSHOT_WIDTH}"
           f"&videoResolutionHeight={CCTV_SNAPSHOT_HEIGHT}")

    head = YOLO(YOLO_MODEL_PATH); head.to("cpu")
    person = YOLO(PERSON_WEIGHTS); person.to("cpu")
    print(f"head model : {YOLO_MODEL_PATH}")
    print(f"person model: {PERSON_WEIGHTS}\n")

    records = []
    for i in range(args.shots):
        try:
            frame = grab(url, auth)
        except Exception as e:
            print(f"shot {i+1}: capture failed ({type(e).__name__})")
            time.sleep(args.interval)
            continue

        H, W = frame.shape[:2]
        annotated = frame.copy()

        pr = person(frame, device="cpu", verbose=False, classes=[0],
                    conf=args.person_conf, imgsz=DETECTION_IMGSZ, iou=DETECTION_IOU)[0]
        hr = head(frame, device="cpu", verbose=False,
                  conf=args.head_conf, imgsz=DETECTION_IMGSZ, iou=DETECTION_IOU)[0]

        shot = {"shot": i + 1, "persons": [], "heads": []}

        for b in pr.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            f = features(x1, y1, x2, y2, W, H)
            f["conf"] = round(float(b.conf[0]), 2)
            shot["persons"].append(f)
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (90, 220, 0), 3)
            cv2.putText(annotated, f"P h={f['h']:.3f} bot={f['bottom']:.3f}",
                        (int(x1), int(y1) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (90, 220, 0), 2)

        for b in hr.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            f = features(x1, y1, x2, y2, W, H)
            f["conf"] = round(float(b.conf[0]), 2)
            shot["heads"].append(f)
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (0, 170, 255), 2)
            cv2.putText(annotated, f"{f['h']:.3f}", (int(x1), int(y2) + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 170, 255), 2)

        records.append(shot)
        cv2.imwrite(f"{args.outdir}/shot{i+1:02d}.jpg", annotated,
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"shot {i+1:>2}: {len(shot['persons'])} persons, {len(shot['heads'])} heads")
        time.sleep(args.interval)

    with open(f"{args.outdir}/records.json", "w") as fh:
        json.dump(records, fh, indent=1)

    all_p = [p for s in records for p in s["persons"]]
    all_h = [h for s in records for h in s["heads"]]

    print(f"\n{len(all_p)} person boxes, {len(all_h)} head boxes over {len(records)} shots")
    print(f"Annotated frames + records.json in {args.outdir}")
    print("\nPerson boxes, sorted by bottom edge (lower value = higher in frame = farther):")
    print(f"{'bottom':>8} {'top':>8} {'h':>8} {'area':>8} {'cx':>7} {'conf':>6}")
    for p in sorted(all_p, key=lambda z: z["bottom"]):
        print(f"{p['bottom']:>8.3f} {p['top']:>8.3f} {p['h']:>8.3f} "
              f"{p['area']:>8.4f} {p['cx']:>7.3f} {p['conf']:>6.2f}")

    print("\nNext: identify which rows are the developer row, then run")
    print("      hardware.calibrate_gates --split BOTTOM_VALUE")
    print("to score every candidate feature against that grouping.")


if __name__ == "__main__":
    main()
