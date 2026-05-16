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
    def __init__(self, mqtt_broker=None, mqtt_queue=None, command_queue=None):
        self.mqtt_broker = mqtt_broker
        self.mqtt_queue = mqtt_queue
        self.command_queue = command_queue
        
        # Mapeo de Pines (BCM)
        self.PINS = {
            "parking_servo": 17,
            "parking_red": 22,
            "parking_green": 23,
            "parking_ir": 18,
            "parking_btn": 13,
            "door_servo": 24,
            "door_red": 25,
            "door_green": 8,
            "door_ir": 7,
            "door_light": 5
        }
        
        # Configuración Inicial GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Salidas (LEDs y Servos)
        for pin in [self.PINS["parking_red"], self.PINS["parking_green"], 
                    self.PINS["door_red"], self.PINS["door_green"], self.PINS["door_light"]]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            
        GPIO.setup(self.PINS["parking_servo"], GPIO.OUT)
        GPIO.setup(self.PINS["door_servo"], GPIO.OUT)
        
        self.pwm_parking = GPIO.PWM(self.PINS["parking_servo"], 50)
        self.pwm_door = GPIO.PWM(self.PINS["door_servo"], 50)
        self.pwm_parking.start(0)
        self.pwm_door.start(0)
        
        # Entradas (Sensores y Botón) con Pull-Up
        for pin in [self.PINS["parking_ir"], self.PINS["parking_btn"], self.PINS["door_ir"]]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Lógica de Estado
        self.last_action_time = 0
        self.cooldown_ms = 2000
        self.car_waiting = False
        self.barrier_open = False
        self.door_unlocked = False
        self.light_on = False
        self.light_timer = None
        
        # Estados y Contadores para Debouncing (Antirrebote)
        self.prev_parking_ir = GPIO.input(self.PINS["parking_ir"])
        self.prev_parking_btn = GPIO.input(self.PINS["parking_btn"])
        self.prev_door_ir = GPIO.input(self.PINS["door_ir"])
        
        self.debounce_counts = {
            "parking_ir": 0,
            "parking_btn": 0,
            "door_ir": 0
        }
        self.STABLE_THRESHOLD = 3 # Ciclos necesarios para confirmar cambio (aprox 150ms)

    def loop(self):
        # 1. Procesar Comandos Web
        if self.command_queue and not self.command_queue.empty():
            cmd = self.command_queue.get()
            if cmd.get('zone') == 'parking' and cmd.get('command') == 'OPEN':
                self.open_parking()
            elif cmd.get('zone') == 'door' and cmd.get('command') == 'UNLOCK':
                self.unlock_door()

        # 2. Polling de Sensores con Filtro de Estabilidad
        
        # Sensor IR Parking (Entrada)
        curr_parking_ir = GPIO.input(self.PINS["parking_ir"])
        if curr_parking_ir != self.prev_parking_ir:
            self.debounce_counts["parking_ir"] += 1
            if self.debounce_counts["parking_ir"] >= self.STABLE_THRESHOLD:
                if curr_parking_ir == 0: # Detección real
                    logging.info("Hardware: Car arrived at entry sensor (Stable)")
                    self.car_waiting = True
                    self.publish_state("home/parking/status", {"barrier": "open" if self.barrier_open else "closed", "car_waiting": True})
                self.prev_parking_ir = curr_parking_ir
                self.debounce_counts["parking_ir"] = 0
        else:
            self.debounce_counts["parking_ir"] = 0

        # Botón Parking (Salida)
        curr_parking_btn = GPIO.input(self.PINS["parking_btn"])
        if curr_parking_btn != self.prev_parking_btn:
            self.debounce_counts["parking_btn"] += 1
            if self.debounce_counts["parking_btn"] >= self.STABLE_THRESHOLD:
                # Solo disparamos cuando se PULSA (circuito se abre: 0 -> 1)
                if curr_parking_btn == 1:
                    logging.info("Hardware: Exit button pressed (Stable) - Closing barrier")
                    self.car_waiting = False
                    self.close_parking()
                self.prev_parking_btn = curr_parking_btn
                self.debounce_counts["parking_btn"] = 0
        else:
            self.debounce_counts["parking_btn"] = 0

        # Sensor IR Puerta (Interior)
        curr_door_ir = GPIO.input(self.PINS["door_ir"])
        if curr_door_ir != self.prev_door_ir:
            self.debounce_counts["door_ir"] += 1
            if self.debounce_counts["door_ir"] >= self.STABLE_THRESHOLD:
                if curr_door_ir == 0: # Persona detectada real
                    logging.info("Hardware: Person detected inside (Stable)")
                    self.door_light_on()
                self.prev_door_ir = curr_door_ir
                self.debounce_counts["door_ir"] = 0
        else:
            self.debounce_counts["door_ir"] = 0

        time.sleep(0.05)

    def __del__(self):
        GPIO.cleanup()
