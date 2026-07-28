# **Project Iris \- Detailed Technical Implementation Guide (FSD)**

## **1\. Executive Summary**

Traditional PIR motion sensors are inefficient for office environments—they fail to detect stationary employees at desks, cause lights to shut off unexpectedly, and cannot dynamically scale Air Conditioning based on room occupancy.  
**Project Iris** is a hybrid IoT and Computer Vision automation engine designed for commercial office spaces. It utilizes an existing overhead CCTV camera feed to apply lightweight Computer Vision (CV) logic, delivering:

> 1. **Instant-On Lighting (\<1 sec delay):** Triggered by fast, local pixel-difference detection.  
> 2. **Dynamic AC Load Balancing & Presence State (30-sec polling):** Governed by YOLOv8 object detection snapshots to count occupants and manage HVAC state cleanly without rapid cycling.

## **2\. Hardware Architecture & Bill of Materials (BOM)**

> * **Vision Source:** Existing Ceiling Dome CCTV Camera (accessible via local IP/RTSP stream).  
> * **Edge Compute:** Local Development Workstation (Intel i7, 32GB RAM, dedicated GPU) processing the RTSP stream in real-time.  
> * **Lighting Control:** 2x **AZIOT 4-Node Smart Switches** (Tuya-compatible).  
  * *Mounting Strategy:* Installed inside a standard plastic electrical junction box mounted in the false ceiling to bypass space constraints behind the 12-gang wall switchboard.  
> * **AC & Media Control:** 1x **Broadlink RM4 Mini** IR Blaster (placed on a desk divider with clear line-of-sight to the Cassette AC and TV).

## **3\. Physical Wiring & Circuit Mapping**

The system maps AI detection zones directly to the existing physical wall switches. The facility electrician wires the AZIOT relay channels in parallel with manual wall switches so physical manual overrides remain fully operational.

> * **Switch S1 (TV):** Hardwired / Always powered. On/Off state is handled via Broadlink IR signals.  
> * **AZIOT Relay Module A:**  
  * **Channel 1** \\rightarrow Wires in parallel to **S3** (Controls Upper LED Panels LP1, LP2)  
  * **Channel 2** \\rightarrow Wires in parallel to **S10** (Controls Lower LED Panels LP3, LP4)  
  * **Channel 3** \\rightarrow Wires in parallel to **S7** (Controls TV Area Bulbs LB1, LB2, LB3)  
  * **Channel 4** \\rightarrow Wires in parallel to **S4** (Controls Upper Bulbs LB4, LB5, LB6)  
> * **AZIOT Relay Module B:**  
  * **Channel 1** \\rightarrow Wires in parallel to **S2** (Controls Lower Bulbs LB7, LB8, LB9)  
  * **Channel 2** \\rightarrow Wires in parallel to **S12** (Controls Far Bulbs LB10, LB11, LB12)  
  * **Channels 3 & 4** \\rightarrow Unused / Spare.

## **4\. Environment & Dependencies Setup**

Run all commands within an isolated Python virtual environment (Python 3.8+ required).  
`# Create and activate virtual environment`  
`python -m venv iris_env`

`# Windows:`  
`iris_env\Scripts\activate`  
`# Linux/Mac:`  
`source iris_env/bin/activate`

`# Install required IoT, CV, and AI packages`  
`pip install tinytuya broadlink opencv-python ultralytics numpy`

## **5\. Phase 1: Hardware Interfacing (IoT Layer)**

### **5.1 Lighting Control (tinytuya)**

AZIOT devices use Tuya firmware. Local control bypasses external cloud APIs for lower latency.  
**Extracting Local Keys:**

> 1. Create a Tuya Developer account (iot.tuya.com) and link the Smart Life mobile app.  
> 2. Run python \-m tinytuya wizard in the terminal and provide your API credentials to fetch the Device ID and Local\_Key for each relay module.

**Control Snippet:**  
`import tinytuya`

`# Connect locally to AZIOT Relay Module A`  
`relay_a = tinytuya.OutletDevice(`  
    `dev_id='YOUR_DEVICE_ID',`  
    `address='192.168.1.50',  # Static IP assigned on local Wi-Fi`  
    `local_key='YOUR_LOCAL_KEY',`  
    `version=3.3`  
`)`

`# Control individual switches (1-indexed)`  
`relay_a.set_status(True, switch=1)   # Turn ON Switch 1 (LED Panels LP1, LP2)`  
`relay_a.set_status(False, switch=3)  # Turn OFF Switch 3 (TV Area Bulbs)`

### **5.2 AC & TV Control (broadlink)**

The RM4 Mini broadcasts Infrared (IR) pulses learned from physical remotes.  
**Learning IR Codes:**

> 1. Call device.enter\_learning() to place the puck into learning mode.  
> 2. Point the physical remote at the puck and press the desired command (e.g., 'Cool 24°C').  
> 3. Retrieve and save the hex payload string returned by device.check\_data().

**Execution Snippet:**  
`import broadlink`

`# Discover and authenticate device`  
`devices = broadlink.discover(timeout=5)`  
`rm4 = devices[0]`  
`rm4.auth()`

`# Pre-recorded Hex payloads from learning phase`  
`AC_COOL_24 = bytes.fromhex("2600500000012...")`   
`AC_POWER_OFF = bytes.fromhex("2600480000011...")`

`# Send command to AC`  
`rm4.send_data(AC_COOL_24)`

## **6\. Phase 2: Computer Vision Layer**

### **6.1 Fast Motion Engine (OpenCV at 5 FPS)**

Runs continuously to detect pixel differences across designated spatial zones for instant lighting response.  
`import cv2`

`# Stream capture from overhead CCTV`  
`cap = cv2.VideoCapture("rtsp://admin:password@192.168.1.100:554/stream1")`

`ret, frame1 = cap.read()`  
`ret, frame2 = cap.read()`

`while cap.isOpened():`  
    `diff = cv2.absdiff(frame1, frame2)`  
    `gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)`  
    `blur = cv2.GaussianBlur(gray, (5, 5), 0)`  
    `_, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)`  
    `dilated = cv2.dilate(thresh, None, iterations=3)`  
    `contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)`

    `for contour in contours:`  
        `if cv2.contourArea(contour) < 5000:  # Threshold to ignore minor noise/shadows`  
            `continue`  
          
        `# Trigger local lighting relays instantly when spatial motion is detected`  
        `# relay_a.set_status(True, switch=1)`  
          
    `frame1 = frame2`  
    `ret, frame2 = cap.read()`

### **6.2 Presence & Occupancy Engine (YOLOv8 at 30-sec Interval)**

Takes a high-resolution snapshot every 30 seconds to count human presence and adjust AC output or initiate a delayed shut-off.  
`from ultralytics import YOLO`

`# Load lightweight object detection model`  
`model = YOLO('yolov8n.pt')`

`def get_occupancy_count(frame):`  
    `results = model(frame, verbose=False)`  
    `person_count = 0`  
    `for r in results:`  
        `for box in r.boxes:`  
            `if int(box.cls[0]) == 0:  # Class ID 0 corresponds to 'person'`  
                `person_count += 1`  
    `return person_count`

## **7\. Non-Blocking Async Orchestration**

**Developer Rule:** Do NOT use time.sleep(30) inside the main frame reading loop. Pausing the loop blocks the RTSP buffer, leading to frame lag and eventual pipeline failure.  
Use non-blocking timestamp comparisons to manage the polling intervals:  
`import time`  
`import cv2`

`cap = cv2.VideoCapture("rtsp://admin:password@192.168.1.100:554/stream1")`

`last_ai_check = time.time()`  
`zero_occupancy_counter = 0`

`while cap.isOpened():`  
    `ret, frame = cap.read()`  
    `if not ret:`  
        `continue`

    `# 1. Continuous motion detection runs here on every frame...`

    `# 2. Asynchronous 30-Second AI Polling Loop`  
    `current_time = time.time()`  
    `if current_time - last_ai_check >= 30:`  
        `count = get_occupancy_count(frame)`  
        `print(f"[Project Iris] Current Headcount: {count}")`  
          
        `if count > 0:`  
            `zero_occupancy_counter = 0`  
            `if count >= 4:`  
                `# High occupancy -> Lower AC Temp`  
                `# rm4.send_data(AC_COOL_22)`  
                `pass`  
            `else:`  
                `# Moderate occupancy -> Standard Temp`  
                `# rm4.send_data(AC_COOL_24)`  
                `pass`  
        `else:`  
            `zero_occupancy_counter += 1`  
            `# If room is empty for 3 consecutive checks (90 seconds / 3 min window)`  
            `if zero_occupancy_counter >= 3:`  
                `print("[Project Iris] Vacancy confirmed. Powersaving mode engaged.")`  
                `# Turn OFF AC & Lights via relays and Broadlink`  
                  
        `last_ai_check = current_time`

## **8\. Frontend Dashboard Requirements**

The frontend team will build a single-page monitoring dashboard (React / React Native Web) with the following specifications:

> 1. **2D Spatial Zone Map:** Interactive layout showing the 3 physical seating areas. Zones glow active/inactive based on real-time state payloads from the backend WebSocket/API.  
> 2. **Live System Telemetry:**  
   * Active Headcount metrics.  
   * Target AC Setpoint & Fan Speed status.  
   * Estimated daily kWh energy savings indicator.  
> 3. **Control Overrides:** Manual toggle switches to force specific lighting rows ON/OFF during maintenance, bypassing AI logic.  
> 4. **Presentation Mode Preset:** One-tap macro that dims ambient lighting rows, sets AC to quiet/low fan mode, and sends the Broadlink IR power-on payload to the TV.

## **9\. Troubleshooting & Edge Cases**

> * **RTSP Stream Latency:** If the camera feed lags behind real time, ensure the OpenCV buffer size is set to 1: cap.set(cv2.CAP\_PROP\_BUFFERSIZE, 1).  
> * **tinytuya Connection Errors:** Tuya devices accept only one active local TCP connection at a time. Ensure the Smart Life mobile app is closed on all mobile devices during testing.  
> * **Broadlink Discovery Failure:** The Broadlink RM4 Mini must reside on the same 2.4GHz Wi-Fi network subnet as the edge compute machine; cross-subnet discovery pings will be dropped by standard router configurations.