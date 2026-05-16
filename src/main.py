import threading
import queue
import cv2
import time
import os
import logging
from unittest.mock import MagicMock
import src.hardware

# FORCE MOCKING FOR SAFETY (to run with real camera but without real GPIO)
if os.environ.get("MOCK_HARDWARE", "0") == "1":
    logging.info("MOCK MODE: Mocking RPi.GPIO and gpiozero for safe logic testing")
    mock_gpio = MagicMock()
    mock_gpio.input.return_value = 0
    mock_gpio.BCM = 11
    mock_gpio.OUT = 0
    mock_gpio.IN = 1
    mock_gpio.HIGH = 1
    mock_gpio.LOW = 0
    mock_gpio.PUD_UP = 22
    src.hardware.GPIO = mock_gpio
    src.hardware.Servo = MagicMock()
    src.hardware.LED = MagicMock()
    src.hardware.LineSensor = MagicMock()
    src.hardware.Button = MagicMock()

from src.vision import GestureRecognizer
from src.hardware import HardwareController
from src.web import run_web_server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(threadName)s] %(message)s')

# Shared structures
frame_queue = queue.Queue(maxsize=1)
gesture_queue = queue.Queue(maxsize=10)
mqtt_queue = queue.Queue()
command_queue = queue.Queue()
shared_state = {
    "last_gesture": "None",
    # Gesture → action mapping (empty string = unassigned)
    "gesture_parking_open":     os.environ.get("GESTURE_VIP", "Pointing_Up"),
    "gesture_parking_close":    "",
    "gesture_parking_red_on":   "",
    "gesture_parking_red_off":  "",
    "gesture_parking_green_on": "",
    "gesture_parking_green_off":"",
    "gesture_door_unlock":      os.environ.get("GESTURE_PWD", "Peace_Sign"),
    "gesture_door_lock":        "",
    "gesture_buzzer_on":        "",
    "gesture_buzzer_off":       "",
    "gesture_light_on":         "",
    "gesture_light_off":        "",
}

# Maps each action key to the command dict sent to hardware loop()
ACTION_TO_COMMAND = {
    "parking_open":     {"zone": "parking",       "command": "OPEN"},
    "parking_close":    {"zone": "parking",       "command": "CLOSE"},
    "parking_red_on":   {"zone": "parking_red",   "command": "ON"},
    "parking_red_off":  {"zone": "parking_red",   "command": "OFF"},
    "parking_green_on": {"zone": "parking_green", "command": "ON"},
    "parking_green_off":{"zone": "parking_green", "command": "OFF"},
    "door_unlock":      {"zone": "door",          "command": "UNLOCK"},
    "door_lock":        {"zone": "door",          "command": "LOCK"},
    "buzzer_on":        {"zone": "buzzer",        "command": "ON"},
    "buzzer_off":       {"zone": "buzzer",        "command": "OFF"},
    "light_on":         {"zone": "door_light",    "command": "ON"},
    "light_off":        {"zone": "door_light",    "command": "OFF"},
}

def sensor_simulator(hw):
    """Simula eventos de sensores IR periódicamente para pruebas."""
    logging.info("SIMULATOR: Sensor simulation thread started.")
    while True:
        time.sleep(10)
        logging.info("SIMULATOR: Car arrived at entry sensor (Simulated)")
        hw.on_car_arrival()
        time.sleep(10)
        logging.info("SIMULATOR: Car cleared exit sensor (Simulated)")
        hw.on_car_departure()
        time.sleep(10)
        logging.info("SIMULATOR: Person detected at door (Simulated)")
        hw.on_door_approach()

def capture_thread():
    # Intentar con V4L2 explícitamente para mayor compatibilidad en Linux/Docker
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        logging.warning("Failed to open camera with V4L2, trying default backend...")
        cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logging.error("CRITICAL: Could not open camera. Please check /dev/video0 permissions.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: continue
        if frame_queue.full():
            try: frame_queue.get_nowait()
            except queue.Empty: pass
        frame_queue.put(frame)

def inference_thread():
    recognizer = GestureRecognizer()
    current_gesture, count = None, 0
    while True:
        try:
            frame = frame_queue.get(timeout=1.0)
            gesture = recognizer.process_frame(frame)
            if gesture:
                if gesture == current_gesture: 
                    count += 1
                else: 
                    current_gesture, count = gesture, 1
                
                if count == 5: # Debouncing threshold
                    try: gesture_queue.put_nowait(gesture)
                    except queue.Full: pass
                    shared_state["last_gesture"] = gesture
                    count = 0 # Reset after triggering
            else:
                current_gesture, count = None, 0
        except queue.Empty: pass

def hardware_thread():
    hw = HardwareController(
        mqtt_broker=os.environ.get("MQTT_BROKER"),
        mqtt_queue=mqtt_queue,
        command_queue=command_queue,
        shared_state=shared_state
    )
    
    # Iniciar simulador de sensores si estamos en modo mock
    if os.environ.get("MOCK_HARDWARE") == "1":
        threading.Thread(target=sensor_simulator, args=(hw,), name="SensorSim", daemon=True).start()
    
    while True:
        try:
            gesture = gesture_queue.get(timeout=0.1)
            for action_key, cmd in ACTION_TO_COMMAND.items():
                assigned = shared_state.get(f"gesture_{action_key}", "")
                if assigned and gesture == assigned:
                    command_queue.put(cmd)
                    break
        except queue.Empty: pass
        hw.loop()

if __name__ == "__main__":
    logging.info(f"System starting. Parking gesture: {shared_state['gesture_parking_open']}, Door gesture: {shared_state['gesture_door_unlock']}")
    
    t1 = threading.Thread(target=capture_thread, name="Capture")
    t2 = threading.Thread(target=inference_thread, name="Inference")
    t3 = threading.Thread(target=hardware_thread, name="Hardware")
    t4 = threading.Thread(target=run_web_server, args=(shared_state, mqtt_queue, command_queue), name="Web")
    
    for t in [t1, t2, t3, t4]:
        t.daemon = True
        t.start()
        
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")