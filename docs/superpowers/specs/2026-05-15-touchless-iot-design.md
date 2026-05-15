# Touchless UI - IoT Ecosystem Design Specification

## 1. Overview
This document specifies the design for integrating an MQTT-based IoT ecosystem into the existing Touchless UI gesture recognition project on a Raspberry Pi 3. The system controls a parking barrier and a main door lock based on camera gestures and external manual commands, providing a modern web dashboard for real-time monitoring and control.

## 2. Architecture & Data Flow
The architecture relies on the existing multi-threaded Python backend.
- **Hardware Thread:** The `HardwareController` manages the physical GPIO devices. It maintains an active connection to the external MQTT Broker to publish component statuses and subscribe to override commands.
- **Web Thread (Flask):** Acts as a bridge between the frontend and the system state. It exposes Server-Sent Events (SSE) to stream live data (gestures, MQTT states) to the UI, and provides REST API endpoints to receive manual override clicks from the UI, which are then passed to the hardware controller to publish over MQTT.
- **Frontend UI:** A TailwindCSS dashboard that visualizes the state of the parking and door zones in real-time without needing a direct WebSockets connection to the external MQTT broker.

## 3. Hardware Components (gpiozero mapping)
The physical ecosystem is divided into two distinct zones. The GPIO configuration uses the `gpiozero` library and BCM numbering.

### 3.1 Parking Zone
- **Barrier Servo:** BCM 17
- **Traffic Light:** BCM 22 (Red), BCM 23 (Green)
- **IR Entry Sensor:** BCM 18
- **IR Exit Sensor:** BCM 27

*Logic Flow:*
1. IR Entry detects a car -> Red LED is ON, waiting for gesture.
2. Camera detects "VIP_PASS" gesture -> Barrier Servo opens, Green LED turns ON.
3. IR Exit detects the car passing -> Barrier Servo closes, Red LED turns ON.

### 3.2 Main Door Zone
- **Lock Servo:** BCM 24
- **State LEDs:** BCM 25 (Red/Locked), BCM 8 (Green/Unlocked)
- **Interior IR Sensor:** BCM 7
- **Courtesy Light (White LED):** BCM 5

*Logic Flow:*
1. Default state: Locked (Red LED ON, Servo in locked position).
2. Camera detects "PASSWORD" gesture -> Door Unlocks (Green LED ON, Servo opens).
3. Interior IR Sensor detects entry -> Courtesy Light (White LED) turns ON for 10 seconds.
4. Auto-lock after entry or timeout.

## 4. MQTT Protocol
Topics used by `paho-mqtt` in the backend:
- `home/parking/status`: Publishes JSON (e.g., `{"barrier": "open", "car_waiting": true}`).
- `home/door/status`: Publishes JSON (e.g., `{"lock": "locked", "courtesy_light": "off"}`).
- `home/parking/cmd`: Subscribes to commands (e.g., `OPEN`).
- `home/door/cmd`: Subscribes to commands (e.g., `UNLOCK`).

## 5. Implementation Modifications
- **src/hardware.py**: Will be completely rewritten to initialize `gpiozero` components, set up the `paho-mqtt` client, and implement the event loops for sensors. Placeholders will be explicitly marked for gesture insertion (e.g., `if gesture_name == 'VIP_PASS':`).
- **src/web.py**: Extended to yield MQTT statuses through the existing SSE `/stream` endpoint and handle POST requests at `/api/command` for manual overrides.
- **src/templates/index.html**: Upgraded with a dark-mode Tailwind CSS layout containing separate cards for the "Parking" and "Main Door" zones.

## 6. Docker & Environment
- Environment variable `MQTT_BROKER` inside `docker-compose.yml` remains the source of truth for the broker IP.
- The `Dockerfile` already has `gpiozero`, `paho-mqtt`, and `RPi.GPIO` mapped. No changes required.
