import time
import logging
import json
import threading
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(threadName)s] %(message)s')

# Configuración de Servos (Basado en la observación física: 100 es abajo/cerrado, 30 es arriba/abierto)
PWM_MIN = 0.5   
PWM_MAX = 11.0  
ANGULO_ABIERTO = 30
ANGULO_CERRADO = 100

class HardwareController:
    def __init__(self, mqtt_broker=None, mqtt_queue=None, command_queue=None,shared_state=None):
        self.mqtt_broker = mqtt_broker
        self.mqtt_queue = mqtt_queue
        self.command_queue = command_queue
        self.shared_state = shared_state if shared_state is not None else {}

        # Mapeo de Pines (BCM)
        self.PINS = {
            "parking_servo": 17,
            "parking_red": 22,
            "parking_green": 23,
            "parking_ir": 18,
            "parking_btn": 13,
            "door_servo": 24,
            "door_buzzer": 7,
            "door_light": 5
        }
        
        # Configuración Inicial GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Salidas (LEDs, Buzzer y Servos)
        for pin in [self.PINS["parking_red"], self.PINS["parking_green"],
                    self.PINS["door_buzzer"], self.PINS["door_light"]]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            
        GPIO.setup(self.PINS["parking_servo"], GPIO.OUT)
        GPIO.setup(self.PINS["door_servo"], GPIO.OUT)
        
        self.pwm_parking = GPIO.PWM(self.PINS["parking_servo"], 50)
        self.pwm_door = GPIO.PWM(self.PINS["door_servo"], 50)
        self.pwm_buzzer = GPIO.PWM(self.PINS["door_buzzer"], 1000)
        self.pwm_parking.start(0)
        self.pwm_door.start(0)
        self.pwm_buzzer.start(0)
        
        # Entradas (Sensores y Botón) con Pull-Up
        for pin in [self.PINS["parking_ir"], self.PINS["parking_btn"]]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Estabilizadores para el loop de debouncing
        self.stable_parking_ir = GPIO.input(self.PINS["parking_ir"])
        self.stable_parking_btn = GPIO.input(self.PINS["parking_btn"])
        self.counts = {"parking_ir": 0, "parking_btn": 0}
        self.THRESHOLD = 5
        self.last_btn_trigger = 0

        # Lógica de Estado
        self.last_action_time = 0
        self.cooldown_ms = 2000
        self.car_waiting = False
        self.barrier_open = False
        self.door_unlocked = False
        self.light_on = False
        
        # Estados y Contadores para Debouncing (Antirrebote)
        self.prev_parking_ir = GPIO.input(self.PINS["parking_ir"])
        self.prev_parking_btn = GPIO.input(self.PINS["parking_btn"])

        self.debounce_counts = {
            "parking_ir": 0,
            "parking_btn": 0,
        }
        self.STABLE_THRESHOLD = 3 # Ciclos necesarios para confirmar cambio (aprox 150ms)
        
        # Estado Inicial Físico
        GPIO.output(self.PINS["parking_red"], GPIO.HIGH) # Rojo por defecto
        self.mover_servo_instantaneo(self.pwm_parking, ANGULO_CERRADO)
        self.mover_servo_instantaneo(self.pwm_door, ANGULO_ABIERTO)

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

    def calcular_duty(self, angulo):
        return PWM_MIN + (angulo / 180.0) * (PWM_MAX - PWM_MIN)

    def mover_servo_suave(self, pwm, inicio, fin):
        paso = 1 if fin > inicio else -1
        for angulo in range(inicio, fin + paso, paso):
            pwm.ChangeDutyCycle(self.calcular_duty(angulo))
            time.sleep(0.02)
        pwm.ChangeDutyCycle(0)

    def mover_servo_instantaneo(self, pwm, angulo):
        pwm.ChangeDutyCycle(self.calcular_duty(angulo))
        time.sleep(0.5)
        pwm.ChangeDutyCycle(0)

    def publish_state(self, topic, payload):
        if topic == "home/parking/status":                                                                                                                            
            self.shared_state["parking"] = payload                                                                                                                    
        elif topic == "home/door/status":                                                                                                                             
            self.shared_state["door"] = payload
        if self.mqtt_queue:
            self.mqtt_queue.put({"topic": topic, "payload": payload})
        if self.mqtt_broker:
            self.client.publish(topic, json.dumps(payload))

    def trigger_action(self, gesture_name):
        current_time = time.time() * 1000
        if current_time - self.last_action_time < self.cooldown_ms:
            return
            
        if gesture_name == 'VIP_PASS':
            logging.info("ACTION: Gesture VIP_PASS recognized.")
            self.open_parking()
            self.last_action_time = current_time
        elif gesture_name == 'PASSWORD':
            logging.info("ACTION: Gesture PASSWORD recognized.")
            self.unlock_door()
            self.last_action_time = current_time

    def open_parking(self):
        if not self.barrier_open:
            logging.info("Hardware: Opening barrier...")
            GPIO.output(self.PINS["parking_green"], GPIO.HIGH)
            GPIO.output(self.PINS["parking_red"], GPIO.LOW)
            self.mover_servo_suave(self.pwm_parking, ANGULO_CERRADO, ANGULO_ABIERTO)
            self.barrier_open = True
            self.publish_state("home/parking/status", {"barrier": "open", "car_waiting": self.car_waiting})

    def close_parking(self):
        if self.barrier_open:
            logging.info("Hardware: Closing barrier...")
            GPIO.output(self.PINS["parking_green"], GPIO.LOW)
            GPIO.output(self.PINS["parking_red"], GPIO.HIGH)
            self.mover_servo_suave(self.pwm_parking, ANGULO_ABIERTO, ANGULO_CERRADO)
            self.barrier_open = False
            self.publish_state("home/parking/status", {"barrier": "closed", "car_waiting": False})

    def unlock_door(self):
        if not self.door_unlocked:
            logging.info("Hardware: Unlocking door...")
            self.pwm_buzzer.ChangeDutyCycle(50)
            GPIO.output(self.PINS["door_light"], GPIO.HIGH)
            self.light_on = True
            self.mover_servo_suave(self.pwm_door, ANGULO_ABIERTO, ANGULO_CERRADO)
            self.door_unlocked = True
            self.publish_state("home/door/status", {"lock": "unlocked", "courtesy_light": "on"})
            threading.Timer(10.0, self.lock_door).start()

    def lock_door(self):
        if self.door_unlocked:
            logging.info("Hardware: Locking door...")
            self.pwm_buzzer.ChangeDutyCycle(0)
            GPIO.output(self.PINS["door_light"], GPIO.LOW)
            self.light_on = False
            self.mover_servo_suave(self.pwm_door, ANGULO_CERRADO, ANGULO_ABIERTO)
            self.door_unlocked = False
            self.publish_state("home/door/status", {"lock": "locked", "courtesy_light": "off"})

    def loop(self):
        # 1. Procesar Comandos Web
        if self.command_queue and not self.command_queue.empty():
            cmd = self.command_queue.get()
            if cmd.get('zone') == 'parking' and cmd.get('command') == 'OPEN':
                self.open_parking()
            elif cmd.get('zone') == 'parking' and cmd.get('command') == 'CLOSE':
                self.close_parking()
            elif cmd.get('zone') == 'door' and cmd.get('command') == 'UNLOCK':
                self.unlock_door()
            elif cmd.get('zone') == 'door' and cmd.get('command') == 'LOCK':
                self.lock_door()

        # 2. Detección con Integrador de Estabilidad
        now = time.time()
        
        # --- Sensor IR Parking ---
        raw_ir = GPIO.input(self.PINS["parking_ir"])
        if raw_ir != self.stable_parking_ir:
            self.counts["parking_ir"] += 1
            if self.counts["parking_ir"] >= self.THRESHOLD:
                self.stable_parking_ir = raw_ir
                if raw_ir == 1:
                    logging.info("Hardware: Car detected (Stable)")
                    self.car_waiting = True
                    self.publish_state("home/parking/status", {"barrier": "open" if self.barrier_open else "closed", "car_waiting": True})
                else:
                    logging.info("Hardware: Entry sensor cleared (Stable)")
        else:
            self.counts["parking_ir"] = 0

        # --- Botón Parking (Salida) ---
        raw_btn = GPIO.input(self.PINS["parking_btn"])
        if raw_btn != self.stable_parking_btn:
            self.counts["parking_btn"] += 1
            if self.counts["parking_btn"] >= self.THRESHOLD:
                self.stable_parking_btn = raw_btn
                # Solo disparamos en flanco de subida (pulsado) y con cooldown de 2s
                if raw_btn == 0 and (now - self.last_btn_trigger > 2):
                    logging.info("Hardware: Exit button pressed (Stable)")
                    self.car_waiting = False
                    self.close_parking()
                    self.last_btn_trigger = now
        else:
            self.counts["parking_btn"] = 0

        time.sleep(0.05)

    def __del__(self):
        GPIO.cleanup()