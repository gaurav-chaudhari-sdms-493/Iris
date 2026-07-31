#!/usr/bin/env python3
"""
Head-size calibration utility for the occupant depth gate.

The developer row sits directly behind the lounge and lands in the same band of
the frame, so no rectangular region can separate the two. Apparent head size can:
a head at twice the distance renders at half the height.

Run this with people sitting in BOTH areas. It prints every detected head sorted
by size, so the gap between the near group and the far group is obvious, and
suggests a threshold that sits in the middle of that gap.

Usage:
    cd backend
    ./iris_env/bin/python -m hardware.measure_heads
    ./iris_env/bin/python -m hardware.measure_heads --save annotated.jpg
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
import numpy as np
import requests
from requests.auth import HTTPDigestAuth

from config import (
    load_dotenv_file, CCTV_SNAPSHOT_WIDTH, CCTV_SNAPSHOT_HEIGHT,
    YOLO_MODEL_PATH, DETECTION_CONFIDENCE, DETECTION_IMGSZ, DETECTION_IOU,
    DETECTION_MIN_HEAD_H,
)

load_dotenv_file()


def grab_frame(channel="601"):
    ip = os.environ.get("CCTV_IP", "192.168.0.21")
    auth = HTTPDigestAuth(os.environ.get("CCTV_USER", "admin"),
                          os.environ.get("CCTV_PASS", ""))
    url = (f"http://{ip}/ISAPI/Streaming/channels/{channel}/picture"
           f"?videoResolutionWidth={CCTV_SNAPSHOT_WIDTH}"
           f"&videoResolutionHeight={CCTV_SNAPSHOT_HEIGHT}")
    r = requests.get(url, auth=auth, timeout=8)
    r.raise_for_status()
    frame = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError("Camera returned data that could not be decoded as an image")
    return frame


def suggest_threshold(heights):
    """Find the widest gap between consecutive head sizes and split it."""
    if len(heights) < 2:
        return None
    gaps = [(heights[i] - heights[i + 1], i) for i in range(len(heights) - 1)]
    gap, idx = max(gaps)
    near, far = heights[idx], heights[idx + 1]
    # Only meaningful if the groups are clearly separated
    if far <= 0 or near / far < 1.35:
        return None
    return round((near + far) / 2.0, 4), gap


def run_check(args):
    """
    Read-only health check on the occupant depth gate.

    Deliberately never writes configuration. The suggested threshold is only
    meaningful when people are sitting in BOTH the lounge and the developer row;
    with everyone in one area the "widest gap" is just the spread within a single
    group, and adopting it automatically could gate out real occupants. So this
    reports, and a human decides.

    Exit codes: 0 = gate looks right or no verdict possible, 1 = drifted.
    """
    import time
    from ultralytics import YOLO
    from config import DETECTION_MIN_HEAD_H

    shots = max(args.shots, 5)
    try:
        model = YOLO(YOLO_MODEL_PATH)
        model.to("cpu")
    except Exception as e:
        print(f"[gate check] SKIPPED - could not load model ({e})")
        return 0

    heights = []
    for _ in range(shots):
        try:
            frame = grab_frame(args.channel)
        except Exception as e:
            print(f"[gate check] SKIPPED - camera unreachable ({type(e).__name__})")
            return 0
        h = frame.shape[0]
        res = model(frame, device="cpu", verbose=False,
                    conf=args.conf, imgsz=DETECTION_IMGSZ, iou=DETECTION_IOU)[0]
        heights += [(b.xyxy[0][3].item() - b.xyxy[0][1].item()) / h for b in res.boxes]
        time.sleep(0.4)

    heights.sort(reverse=True)
    current = DETECTION_MIN_HEAD_H

    if len(heights) < 2:
        print(f"[gate check] NO VERDICT - only {len(heights)} head(s) visible. "
              f"Keeping IRIS_MIN_HEAD_H={current}.")
        return 0

    sug = suggest_threshold(heights)
    if not sug:
        print(f"[gate check] NO VERDICT - all {len(heights)} heads are a similar size, "
              "so the near and far groups cannot be told apart.")
        print(f"             Keeping IRIS_MIN_HEAD_H={current}. Re-check when the "
              "developer row and the lounge are both occupied.")
        return 0

    thresh, _ = sug
    drift = abs(thresh - current) / current if current else 1.0
    kept = sum(1 for x in heights if x >= current)

    if drift <= args.tolerance:
        print(f"[gate check] OK - measured split {thresh:.4f} vs configured {current} "
              f"({drift*100:.0f}% drift). Counting {kept}/{len(heights)} heads.")
        return 0

    print("=" * 68)
    print(f"[gate check] WARNING - the near/far split has moved.")
    print(f"    configured : IRIS_MIN_HEAD_H={current}")
    print(f"    measured   : {thresh:.4f}   ({drift*100:.0f}% drift)")
    print(f"    right now  : counting {kept} of {len(heights)} detected heads")
    print("    Not changed automatically. To apply, edit backend/.env and restart:")
    print(f"        IRIS_MIN_HEAD_H={thresh:.4f}")
    print("=" * 68)
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="601", help="Hikvision channel code (default 601 = camera 6)")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="Detection floor for measuring (lower than runtime, to reveal far heads)")
    ap.add_argument("--save", metavar="PATH", help="Write an annotated JPEG here")
    ap.add_argument("--check", action="store_true",
                    help="Health check: compare the live scene against the configured "
                         "gate and report. Never edits configuration.")
    ap.add_argument("--shots", type=int, default=1,
                    help="Frames to sample (--check uses 5 by default)")
    ap.add_argument("--tolerance", type=float, default=0.15,
                    help="Fractional drift from the configured gate before warning")
    args = ap.parse_args()

    if args.check:
        sys.exit(run_check(args))

    from ultralytics import YOLO

    frame = grab_frame(args.channel)
    h, w = frame.shape[:2]
    print(f"Frame: {w}x{h}   runtime gate: IRIS_MIN_HEAD_H={DETECTION_MIN_HEAD_H or 'off'}\n")

    model = YOLO(YOLO_MODEL_PATH)
    model.to("cpu")
    res = model(frame, device="cpu", verbose=False,
                conf=args.conf, imgsz=DETECTION_IMGSZ, iou=DETECTION_IOU)[0]

    rows = []
    for b in res.boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        rows.append({
            "conf": float(b.conf[0]),
            "px": y2 - y1,
            "frac": (y2 - y1) / h,
            "box": (int(x1), int(y1), int(x2), int(y2)),
        })
    rows.sort(key=lambda d: -d["frac"])

    if not rows:
        print("No heads detected. Make sure people are seated in both areas.")
        return

    print(f"{'#':>3}  {'height_px':>9}  {'frac':>7}  {'conf':>5}   position")
    print("-" * 58)
    for i, d in enumerate(rows, 1):
        x1, y1, x2, y2 = d["box"]
        passes = "" if not DETECTION_MIN_HEAD_H else (
            "  keep" if d["frac"] >= DETECTION_MIN_HEAD_H else "  DROP")
        print(f"{i:>3}  {d['px']:>9.0f}  {d['frac']:>7.4f}  {d['conf']:>5.2f}   "
              f"x={x1:<5} y={y1:<5}{passes}")

    heights = [d["frac"] for d in rows]
    sug = suggest_threshold(heights)
    print()
    if sug:
        thresh, gap = sug
        print(f"Clear size gap found ({gap:.4f} wide).")
        print(f"Suggested:  IRIS_MIN_HEAD_H={thresh}")
        near = sum(1 for x in heights if x >= thresh)
        print(f"That keeps {near} head(s) and drops {len(heights) - near}.")
    else:
        print("No clean gap between near and far heads.")
        print("Either everyone is at a similar distance, or the far group is")
        print("not being detected at all. Re-run with people in both areas.")

    if args.save:
        for d in rows:
            x1, y1, x2, y2 = d["box"]
            keep = (not DETECTION_MIN_HEAD_H) or d["frac"] >= DETECTION_MIN_HEAD_H
            col = (0, 220, 90) if keep else (70, 70, 240)
            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
            cv2.putText(frame, f"{d['px']:.0f}px {d['frac']:.3f}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
        cv2.imwrite(args.save, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"\nAnnotated frame written to {args.save}")


if __name__ == "__main__":
    main()
