import time
import logging
import json
import threading
import paho.mqtt.client as mqtt
from gpiozero import Servo, LED, LineSensor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(threadName)s] %(message)s')

class HardwareController:
    def __init__(self, mqtt_broker=None, mqtt_queue=None, command_queue=None):
        self.mqtt_broker = mqtt_broker
        self.mqtt_queue = mqtt_queue
        self.command_queue = command_queue
        
        # Parking components
        self.parking_servo = Servo(17)
        self.parking_red = LED(22)
        self.parking_green = LED(23)
        self.parking_ir_entry = LineSensor(18)
        self.parking_ir_exit = LineSensor(27)
        
        # Door components
        self.door_servo = Servo(24)
        self.door_red = LED(25)
        self.door_green = LED(8)
        self.door_ir = LineSensor(7)
        self.door_light = LED(5)
        
        # MQTT Setup
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        if self.mqtt_broker:
            try:
                self.client.connect(self.mqtt_broker, 1883, 60)
                self.client.loop_start()
            except Exception as e:
                logging.error(f"MQTT connection failed: {e}")

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Connected to MQTT Broker")
        client.subscribe("home/parking/cmd")
        client.subscribe("home/door/cmd")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        if msg.topic == "home/parking/cmd" and payload == "OPEN":
            self.open_parking()
        elif msg.topic == "home/door/cmd" and payload == "UNLOCK":
            self.unlock_door()

    def publish_state(self, topic, payload):
        if self.mqtt_queue:
            self.mqtt_queue.put({"topic": topic, "payload": payload})
        if self.mqtt_broker:
            self.client.publish(topic, json.dumps(payload))

    def trigger_action(self, gesture_name):
        logging.info(f"Gesture received: {gesture_name}")
        if gesture_name == 'VIP_PASS':
            self.open_parking()
        elif gesture_name == 'PASSWORD':
            self.unlock_door()

    def open_parking(self):
        self.parking_servo.max()
        self.parking_green.on()
        self.parking_red.off()
        self.publish_state("home/parking/status", {"barrier": "open", "car_waiting": False})

    def unlock_door(self):
        self.door_servo.max()
        self.door_green.on()
        self.door_red.off()
        self.publish_state("home/door/status", {"lock": "unlocked"})
        
    def loop(self):
        # Handle manual commands from Web UI
        if self.command_queue and not self.command_queue.empty():
            cmd = self.command_queue.get()
            if cmd.get('zone') == 'parking' and cmd.get('command') == 'OPEN':
                self.open_parking()
            elif cmd.get('zone') == 'door' and cmd.get('command') == 'UNLOCK':
                self.unlock_door()
        time.sleep(0.1)
