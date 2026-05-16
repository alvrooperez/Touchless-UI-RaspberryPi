import time
import sys
import RPi.GPIO as GPIO

# Configuración de pines (BCM)
PINS = {
    "parking": {
        "servo": 17,
        "red": 22,
        "green": 23,
        "ir_entry": 18,
        "btn_exit": 13
    },
    "door": {
        "servo": 24,
        "red": 25,
        "green": 8,
        "white": 5,
        "ir": 7
    }
}

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False) # ESTO EVITA EL ERROR DE EDGE DETECTION

def test_led(name, pin):
    print(f"\n[LED] Probando: {name} (Pin BCM {pin})")
    try:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        input(f"  -> ¿Está encendido el LED {name}? (Presiona ENTER para continuar)")
        GPIO.output(pin, GPIO.LOW)
        print(f"  [OK] {name} apagado.")
    except Exception as e:
        print(f"  [ERROR] No se pudo probar {name}: {e}")

def test_servo(name, pin):
    print(f"\n[SERVO] Probando: {name} (Pin BCM {pin})")
    try:
        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, 50) # 50Hz
        pwm.start(0)
        
        print("  -> Moviendo a posición 0°...")
        pwm.ChangeDutyCycle(2.5) # 0 grados aprox
        time.sleep(1)
        
        print("  -> Moviendo a posición 90°...")
        pwm.ChangeDutyCycle(7.5) # 90 grados aprox
        time.sleep(1)
        
        input(f"  -> ¿Se ha movido el servo {name}? (Presiona ENTER)")
        pwm.stop()
    except Exception as e:
        print(f"  [ERROR] No se pudo probar {name}: {e}")

def test_input_manual(name, pin, is_button=False):
    print(f"\n[{'BOTÓN' if is_button else 'SENSOR'}] Probando: {name} (Pin BCM {pin})")
    try:
        # Configuramos con Resistencia Pull-Up para el pulsador NC y el IR
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        initial_state = GPIO.input(pin)
        print(f"  -> Estado inicial detectado: {initial_state} ({'HIGH' if initial_state else 'LOW'})")
        print(f"  -> {'PULSA el botón' if is_button else 'Pon tu MANO en el sensor'} para cambiar el estado (esperando 15s)...")

        start_time = time.time()
        changed = False

        while time.time() - start_time < 15:
            current_state = GPIO.input(pin)
            if current_state != initial_state:
                print(f"  [OK] ¡Cambio detectado! Nuevo estado: {current_state}")
                changed = True
                break
            time.sleep(0.1)

        if not changed:
            print(f"  [FAIL] No se detectó cambio en {name}. Revisa conexiones.")
            
    except Exception as e:
        print(f"  [ERROR] Error en {name}: {e}")

if __name__ == "__main__":
    print("================================================")
    print("   TEST DE HARDWARE INMUNE - RPi.GPIO DIRECTO   ")
    print("================================================")
    
    setup_gpio()

    try:
        # ZONA PARKING
        print("\n--- ZONA PARKING ---")
        test_led("Parking ROJO", PINS["parking"]["red"])
        test_led("Parking VERDE", PINS["parking"]["green"])
        test_servo("Barrera Parking", PINS["parking"]["servo"])
        test_input_manual("IR Entrada Parking", PINS["parking"]["ir_entry"])
        test_input_manual("Pulsador Salida Parking (NC)", PINS["parking"]["btn_exit"], is_button=True)

        # ZONA PUERTA
        print("\n--- ZONA PUERTA ---")
        test_led("Puerta ROJO", PINS["door"]["red"])
        test_led("Puerta VERDE", PINS["door"]["green"])
        test_led("Luz Blanca", PINS["door"]["white"])
        test_servo("Cerradura Puerta", PINS["door"]["servo"])
        test_input_manual("IR Interior Puerta", PINS["door"]["ir"])

    except KeyboardInterrupt:
        print("\n\n[!] Test cancelado.")
    finally:
        GPIO.cleanup()
        print("\n================================================")
        print("      PRUEBAS FINALIZADAS Y GPIO LIMPIO         ")
        print("================================================")
