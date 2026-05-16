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
    "gesture_vip": os.environ.get("GESTURE_VIP", "Pointing_Up"),
    "gesture_pwd": os.environ.get("GESTURE_PWD", "Peace_Sign"),
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
            # Read mappings dynamically so web UI changes take effect immediately
            vip = shared_state.get("gesture_vip", "Pointing_Up")
            pwd = shared_state.get("gesture_pwd", "Peace_Sign")
            if gesture == vip:
                hw.trigger_action('VIP_PASS')
            elif gesture == pwd:
                hw.trigger_action('PASSWORD')
        except queue.Empty: pass
        hw.loop()

if __name__ == "__main__":
    logging.info(f"System starting. VIP Gesture: {shared_state['gesture_vip']}, Door Gesture: {shared_state['gesture_pwd']}")
    
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