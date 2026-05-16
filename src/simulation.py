import time
import threading
import queue
import os
import logging
import json
from unittest.mock import MagicMock
import src.hardware

# Mock gpiozero before it's used in HardwareController
src.hardware.Servo = MagicMock()
src.hardware.LED = MagicMock()
src.hardware.LineSensor = MagicMock()

from src.hardware import HardwareController
from src.web import run_web_server

# Configure logging to be very verbose for the simulation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] %(levelname)s - %(message)s'
)

# Shared structures
gesture_queue = queue.Queue()
mqtt_queue = queue.Queue()
command_queue = queue.Queue()
shared_state = {"last_gesture": "None"}

def mock_vision_thread():
    """Simulates a user performing gestures at specific intervals."""
    time.sleep(5) # Wait for system to start
    
    simulated_gestures = [
        ("VIP_PASS", "A car arrives at the parking..."),
        ("PASSWORD", "A person tries to open the main door..."),
        ("None", "Resting..."),
        ("VIP_PASS", "Another car at the parking...")
    ]
    
    for gesture, description in simulated_gestures:
        logging.info(f"SIMULATION: {description}")
        shared_state["last_gesture"] = gesture
        gesture_queue.put(gesture)
        time.sleep(8) # Wait between gestures

def mock_sensor_thread(hw):
    """Simulates physical IR sensors being triggered."""
    time.sleep(3)
    
    logging.info("SIMULATION: Triggering Parking IR Entry Sensor (Car arrived)")
    hw.on_car_arrival()
    
    time.sleep(15)
    
    logging.info("SIMULATION: Triggering Parking IR Exit Sensor (Car passed)")
    hw.on_car_departure()
    
    time.sleep(5)
    
    logging.info("SIMULATION: Triggering Main Door Interior IR Sensor (Person entered)")
    hw.on_door_approach()

def hardware_thread():
    # Note: HardwareController will use mocks for gpiozero internally 
    # if we are not on a Pi, but for the docker simulation we should ensure
    # it doesn't crash.
    hw = HardwareController(
        mqtt_broker=os.environ.get("MQTT_BROKER", "localhost"),
        mqtt_queue=mqtt_queue,
        command_queue=command_queue
    )
    
    # Start a side thread for sensor simulation
    threading.Thread(target=mock_sensor_thread, args=(hw,), name="SensorSim", daemon=True).start()
    
    while True:
        try:
            gesture = gesture_queue.get(timeout=0.1)
            hw.trigger_action(gesture)
        except queue.Empty:
            pass
        hw.loop()

if __name__ == "__main__":
    logging.info("=== STARTING FULL SYSTEM SIMULATION ===")
    
    # Start threads
    t_vision = threading.Thread(target=mock_vision_thread, name="MockVision", daemon=True)
    t_hw = threading.Thread(target=hardware_thread, name="HardwareLogic", daemon=True)
    t_web = threading.Thread(
        target=run_web_server, 
        args=(shared_state, mqtt_queue, command_queue), 
        name="WebDashboard", 
        daemon=True
    )
    
    t_vision.start()
    t_hw.start()
    t_web.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Simulation stopped by user.")
