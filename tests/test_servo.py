"""
GestHome - tests/test_servo.py
Test interactivo para verificar servo y LEDs por separado.

Uso:
    python3 tests/test_servo.py

Conexiones esperadas:
    Servo  -> GPIO 18 (señal), 5V (rojo), GND (negro)
    LED verde -> GPIO 24 -> resistencia 330Ω -> GND
    LED rojo  -> GPIO 25 -> resistencia 330Ω -> GND
"""

import RPi.GPIO as GPIO
import time
import sys

# ── Pines ────────────────────────────────────────────────────────
PIN_SERVO     = 18
PIN_LED_VERDE = 24
PIN_LED_ROJO  = 25

# Ajusta estos valores si tu servo no llega bien a los extremos
ANGULO_ABIERTO  = 90
ANGULO_CERRADO  = 0

# ── Setup ────────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(PIN_SERVO,     GPIO.OUT)
GPIO.setup(PIN_LED_VERDE, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_LED_ROJO,  GPIO.OUT, initial=GPIO.LOW)

pwm = GPIO.PWM(PIN_SERVO, 50)
pwm.start(0)

# ── Helpers ──────────────────────────────────────────────────────
def mover_servo(angulo):
    ciclo = 2.5 + (angulo / 180.0) * 10.0
    pwm.ChangeDutyCycle(ciclo)
    time.sleep(0.6)
    pwm.ChangeDutyCycle(0)  # evita vibración

def led(verde=False, rojo=False):
    GPIO.output(PIN_LED_VERDE, GPIO.HIGH if verde else GPIO.LOW)
    GPIO.output(PIN_LED_ROJO,  GPIO.HIGH if rojo  else GPIO.LOW)

def ok():
    print("  ✓ OK")

def separador():
    print("\n" + "─" * 40)

# ── Tests ────────────────────────────────────────────────────────
def test_led_verde():
    separador()
    print("TEST 1/5: LED verde")
    print("  -> Encendiendo LED verde 2 seg...")
    led(verde=True)
    time.sleep(2)
    led()
    respuesta = input("  ¿El LED verde se encendió? (s/n): ").strip().lower()
    assert respuesta == 's', "FALLO: LED verde no detectado"
    ok()

def test_led_rojo():
    separador()
    print("TEST 2/5: LED rojo")
    print("  -> Encendiendo LED rojo 2 seg...")
    led(rojo=True)
    time.sleep(2)
    led()
    respuesta = input("  ¿El LED rojo se encendió? (s/n): ").strip().lower()
    assert respuesta == 's', "FALLO: LED rojo no detectado"
    ok()

def test_leds_alternos():
    separador()
    print("TEST 3/5: LEDs alternos (5 veces)")
    for i in range(5):
        led(verde=True)
        time.sleep(0.3)
        led(rojo=True)
        time.sleep(0.3)
    led()
    respuesta = input("  ¿Alternaron verde y rojo correctamente? (s/n): ").strip().lower()
    assert respuesta == 's', "FALLO: LEDs alternos no funcionaron"
    ok()

def test_servo_basico():
    separador()
    print("TEST 4/5: Servo posiciones básicas")
    print(f"  -> Posición CERRADO ({ANGULO_CERRADO}°)...")
    led(rojo=True)
    mover_servo(ANGULO_CERRADO)
    time.sleep(2)

    print(f"  -> Posición ABIERTO ({ANGULO_ABIERTO}°)...")
    led(verde=True)
    mover_servo(ANGULO_ABIERTO)
    time.sleep(2)

    print(f"  -> Volviendo a CERRADO ({ANGULO_CERRADO}°)...")
    led(rojo=True)
    mover_servo(ANGULO_CERRADO)
    led()

    respuesta = input("  ¿El servo se movió a las dos posiciones? (s/n): ").strip().lower()
    assert respuesta == 's', "FALLO: Servo no se movió correctamente"
    ok()

def test_servo_suave():
    separador()
    print("TEST 5/5: Servo barrido suave 0° -> 90° -> 0°")
    print("  -> Subiendo...")
    for angulo in range(0, 91, 5):
        mover_servo(angulo)
        time.sleep(0.2)

    print("  -> Bajando...")
    for angulo in range(90, -1, -5):
        mover_servo(angulo)
        time.sleep(0.2)

    respuesta = input("  ¿El servo hizo el barrido suave? (s/n): ").strip().lower()
    assert respuesta == 's', "FALLO: Barrido suave no funcionó"
    ok()

# ── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 40)
    print("  GestHome - Test Servo + LEDs")
    print("=" * 40)
    print(f"  Servo  -> GPIO {PIN_SERVO}")
    print(f"  LED verde -> GPIO {PIN_LED_VERDE}")
    print(f"  LED rojo  -> GPIO {PIN_LED_ROJO}")
    print("\nPresiona Ctrl+C en cualquier momento para salir.")

    tests = [
        test_led_verde,
        test_led_rojo,
        test_leds_alternos,
        test_servo_basico,
        test_servo_suave,
    ]

    fallidos = []

    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"  ✗ {e}")
            fallidos.append(test.__name__)
        except KeyboardInterrupt:
            print("\n\nInterrumpido por el usuario.")
            break

    separador()
    total  = len(tests)
    passed = total - len(fallidos)
    print(f"\nResultado: {passed}/{total} tests pasados")

    if fallidos:
        print("Tests fallidos:")
        for f in fallidos:
            print(f"  - {f}")
        print("\nSi el servo vibra pero no gira, ajusta ANGULO_ABIERTO/ANGULO_CERRADO")
        print("en este archivo (prueba con 80 y 10 en vez de 90 y 0).")
    else:
        print("Todo OK. Hardware listo para el siguiente paso.")

    # Limpieza
    pwm.stop()
    GPIO.cleanup()
