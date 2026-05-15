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
        
        # Cooldown logic
        self.last_action_time = 0
        self.cooldown_ms = 2000
        
        # State tracking to prevent redundant MQTT messages
        self.car_waiting = False
        self.barrier_open = False
        self.door_unlocked = False
        self.light_on = False
        self.light_timer = None
        
        # Sensor callbacks (Event-driven design)
        self.parking_ir_entry.when_activated = self.on_car_arrival
        self.parking_ir_exit.when_activated = self.on_car_departure
        self.door_ir.when_activated = self.on_door_approach
        
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
        current_time = time.time() * 1000
        if current_time - self.last_action_time < self.cooldown_ms:
            logging.info(f"Gesture {gesture_name} ignored (cooldown)")
            return
            
        logging.info(f"Gesture received: {gesture_name}")
        if gesture_name == 'VIP_PASS':
            self.open_parking()
            self.last_action_time = current_time
        elif gesture_name == 'PASSWORD':
            self.unlock_door()
            self.last_action_time = current_time

    def open_parking(self):
        self.parking_servo.max()
        self.parking_green.on()
        self.parking_red.off()
        self.barrier_open = True
        self.publish_state("home/parking/status", {
            "barrier": "open", 
            "car_waiting": self.car_waiting
        })

    def unlock_door(self):
        self.door_servo.max()
        self.door_green.on()
        self.door_red.off()
        self.door_unlocked = True
        self.publish_state("home/door/status", {
            "lock": "unlocked",
            "courtesy_light": "on" if self.light_on else "off"
        })

    # Callback handlers
    def on_car_arrival(self):
        logging.info("Car arrived at entry sensor")
        if not self.car_waiting:
            self.car_waiting = True
            self.parking_red.on()
            self.publish_state("home/parking/status", {
                "barrier": "open" if self.barrier_open else "closed", 
                "car_waiting": True
            })

    def on_car_departure(self):
        logging.info("Car cleared exit sensor")
        self.car_waiting = False
        self.barrier_open = False
        self.parking_servo.min() # Close
        self.parking_green.off()
        self.parking_red.on()
        self.publish_state("home/parking/status", {
            "barrier": "closed", 
            "car_waiting": False
        })

    def on_door_approach(self):
        logging.info("Person detected at door")
        self.door_light_on()

    def door_light_on(self):
        self.door_light.on()
        if not self.light_on:
            self.light_on = True
            self.publish_state("home/door/status", {
                "lock": "unlocked" if self.door_unlocked else "locked",
                "courtesy_light": "on"
            })
        
        # Reset/Start timer (properly handling single thread)
        if self.light_timer:
            self.light_timer.cancel()
        
        self.light_timer = threading.Timer(10.0, self.door_light_off_callback)
        self.light_timer.start()

    def door_light_off_callback(self):
        logging.info("Courtesy light turning off")
        self.door_light.off()
        self.light_on = False
        self.publish_state("home/door/status", {
            "lock": "unlocked" if self.door_unlocked else "locked",
            "courtesy_light": "off"
        })
        
    def loop(self):
        # Handle commands from internal queue
        if self.command_queue and not self.command_queue.empty():
            cmd = self.command_queue.get()
            if cmd.get('zone') == 'parking' and cmd.get('command') == 'OPEN':
                self.open_parking()
            elif cmd.get('zone') == 'door' and cmd.get('command') == 'UNLOCK':
                self.unlock_door()
        
        # Sensor logic is now event-driven via callbacks
        # No polling needed for IR sensors here
        time.sleep(0.1)
