"""
GestHome - tests/test_servo_leds.py
Test servo ES08A + LED RGB BQ.

Valores calibrados ES08A:
    PWM_MIN = 0.5  ->  0 grados = ABIERTO
    PWM_MAX = 11.0 -> 150 grados = CERRADO

Pines:
    Servo    -> GPIO 18
    LED rojo -> GPIO 24
    LED azul -> GPIO 25
"""

import RPi.GPIO as GPIO
import time

PIN_SERVO    = 18
PIN_LED_ROJO = 24
PIN_LED_AZUL = 25

PWM_MIN = 0.5
PWM_MAX = 11.0

ANGULO_ABIERTO  = 0
ANGULO_CERRADO  = 90

# ── Setup ────────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_SERVO,    GPIO.OUT)
GPIO.setup(PIN_LED_ROJO, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_LED_AZUL, GPIO.OUT, initial=GPIO.LOW)

pwm = GPIO.PWM(PIN_SERVO, 50)
pwm.start(0)

# ── Helpers ──────────────────────────────────────────────────────
def mover_servo(angulo):
    ciclo = PWM_MIN + (angulo / 180.0) * (PWM_MAX - PWM_MIN)
    pwm.ChangeDutyCycle(ciclo)
    time.sleep(0.7)
    pwm.ChangeDutyCycle(0)

def led(rojo=False, azul=False):
    GPIO.output(PIN_LED_ROJO, GPIO.HIGH if rojo else GPIO.LOW)
    GPIO.output(PIN_LED_AZUL, GPIO.HIGH if azul else GPIO.LOW)

def ok():
    print("  ✓ OK")

def separador(titulo):
    print(f"\n{'─'*45}\n  {titulo}\n{'─'*45}")

# ── Tests ────────────────────────────────────────────────────────
def test_led_rojo():
    separador("TEST 1/5: LED rojo")
    led(rojo=True)
    time.sleep(2)
    led()
    assert input("  ¿LED rojo encendido? (s/n): ").strip().lower() == 's', "FALLO: LED rojo"
    ok()

def test_led_azul():
    separador("TEST 2/5: LED azul")
    led(azul=True)
    time.sleep(2)
    led()
    assert input("  ¿LED azul encendido? (s/n): ").strip().lower() == 's', "FALLO: LED azul"
    ok()

def test_leds_alternos():
    separador("TEST 3/5: LEDs alternos (5 veces)")
    for _ in range(5):
        led(rojo=True);  time.sleep(0.3)
        led(azul=True);  time.sleep(0.3)
    led()
    assert input("  ¿Alternaron rojo y azul? (s/n): ").strip().lower() == 's', "FALLO: alternos"
    ok()

def test_servo_posiciones():
    separador("TEST 4/5: Servo ABIERTO y CERRADO")
    print(f"  -> ABIERTO ({ANGULO_ABIERTO}deg)...")
    led(azul=True)
    mover_servo(ANGULO_ABIERTO)
    time.sleep(3)

    print(f"  -> CERRADO ({ANGULO_CERRADO}deg)...")
    led(rojo=True)
    mover_servo(ANGULO_CERRADO)
    led()
    time.sleep(3)

    assert input("  ¿Llego a las dos posiciones sin trabarse? (s/n): ").strip().lower() == 's', "FALLO: posiciones"
    ok()

def test_servo_suave():
    separador("TEST 5/5: Barrido suave 0 -> 150 -> 0")
    print("  -> Subiendo...")
    for ang in range(0, 91, 5):
        mover_servo(ang)
        time.sleep(0.2)
    print("  -> Bajando...")
    for ang in range(90, -1, -5):
        mover_servo(ang)
        time.sleep(0.2)
    assert input("  ¿Barrido suave sin traba? (s/n): ").strip().lower() == 's', "FALLO: barrido suave"
    ok()

# ── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 45)
    print("  GestHome -- Test Servo ES08A + LED RGB BQ")
    print("=" * 45)
    print(f"  PWM_MIN={PWM_MIN}  PWM_MAX={PWM_MAX}")
    print(f"  ABIERTO={ANGULO_ABIERTO} grados")
    print(f"  CERRADO={ANGULO_CERRADO} grados")
    print("  Ctrl+C para salir en cualquier momento.\n")

    tests = [
        #test_led_rojo,
        #test_led_azul,
        test_leds_alternos,
        test_servo_posiciones,
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
            print("\nInterrumpido.")
            break

    print(f"\n{'─'*45}")
    print(f"  Resultado: {len(tests) - len(fallidos)}/{len(tests)} pasados")
    if fallidos:
        for f in fallidos:
            print(f"  ✗ {f}")
    else:
        print("  Todo OK. Hardware listo para el siguiente paso.")

    pwm.stop()
    GPIO.cleanup()