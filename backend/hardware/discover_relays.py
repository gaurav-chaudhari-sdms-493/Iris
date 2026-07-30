#!/usr/bin/env python3
"""
AZIOT 4 Node Smart Switch Wi-Fi & Tuya Cloud Discovery Utility
Scans the local 2.4 GHz network subnet and queries Tuya Cloud API for registered smart switches.
"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import load_hardware_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("iris.hardware.discover")

def fetch_tuya_cloud_devices():
    try:
        import tinytuya
    except ImportError:
        logger.error("tinytuya module is required. Install via `pip install tinytuya`.")
        return []

    hw_cfg = load_hardware_config()
    cloud_cfg = hw_cfg.get("tuya_cloud", {})
    api_key = cloud_cfg.get("api_key", "juugykgp344h8s4nvnk9")
    api_secret = cloud_cfg.get("api_secret", "c2e9f98826c0425a9916f8c5ce4d53fd")
    region = cloud_cfg.get("api_region", "in")

    logger.info(f"Querying Tuya Cloud API (Region: {region})...")
    try:
        cloud = tinytuya.Cloud(apiRegion=region, apiKey=api_key, apiSecret=api_secret)
        devices = cloud.getdevices()
        logger.info(f"Discovered {len(devices)} device(s) on Tuya Cloud:")
        for dev in devices:
            logger.info(f"  [+] Device: {dev.get('name')} | ID: {dev.get('id')} | Local Key: {dev.get('key')} | MAC: {dev.get('mac')}")
        return devices
    except Exception as e:
        logger.error(f"Error querying Tuya Cloud API: {e}")
        return []

def scan_local_network():
    try:
        import tinytuya
    except ImportError:
        logger.error("tinytuya module is required.")
        return []

    logger.info("Scanning local Wi-Fi subnet for AZIOT 4 Node Smart Switches...")
    try:
        devices = tinytuya.deviceScan(verbose=False)
        return devices
    except Exception as e:
        logger.error(f"Error during network discovery scan: {e}")
        return []

if __name__ == "__main__":
    print("\n--- 1. Tuya Cloud Registered Devices ---")
    cloud_devs = fetch_tuya_cloud_devices()
    print(json.dumps(cloud_devs, indent=2))

    print("\n--- 2. Local Wi-Fi Network Scan ---")
    local_devs = scan_local_network()
    print(json.dumps(local_devs, indent=2))
