import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(threadName)s] %(message)s')

class HardwareController:
    def __init__(self, mqtt_broker=None):
        self.mqtt_broker = mqtt_broker
        self.last_action_time = 0
        self.cooldown_ms = 2000
        logging.info("Initializing Dummy GPIO Pins...")

    def trigger_action(self, gesture_name):
        current_time = time.time() * 1000
        if current_time - self.last_action_time < self.cooldown_ms:
            return

        self.last_action_time = current_time
        logging.info(f"ACTION TRIGGERED: {gesture_name}")
        # Add your dummy actions here (e.g. print statements for now)
