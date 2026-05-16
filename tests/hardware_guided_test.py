import time
import sys
from gpiozero import Servo, LED, LineSensor, Button

# Pines configurados según la especificación de diseño (BCM)
PINS = {
    "parking": {
        "servo": 17,
        "red": 22,
        "green": 23,
        "ir_entry": 18,
        "btn_exit": 13 # Pulsador NC
    },
    "door": {
        "servo": 24,
        "red": 25,
        "green": 8,
        "white": 5,
        "ir": 7
    }
}

def test_led(name, pin):
    print(f"\n[LED] Probando: {name} (Pin BCM {pin})")
    try:
        led = LED(pin)
        led.on()
        input(f"  -> ¿Está encendido el LED {name}? (Presiona ENTER para continuar)")
        led.off()
        print(f"  [OK] {name} apagado.")
        led.close()
    except Exception as e:
        print(f"  [ERROR] No se pudo probar {name}: {e}")

def test_servo(name, pin):
    print(f"\n[SERVO] Probando: {name} (Pin BCM {pin})")
    try:
        servo = Servo(pin)
        print("  -> Moviendo a posición MÍNIMA (Cerrado)...")
        servo.min()
        time.sleep(1.5)
        print("  -> Moviendo a posición MÁXIMA (Abierto)...")
        servo.max()
        time.sleep(1.5)
        input(f"  -> ¿Se ha movido el servo {name} correctamente? (Presiona ENTER)")
        servo.close()
    except Exception as e:
        print(f"  [ERROR] No se pudo probar {name}: {e}")

def test_sensor_manual(name, pin, is_button=False):
    """Prueba de sensor leyendo estado bruto para evitar errores de edge detection."""
    print(f"\n[{'BOTÓN' if is_button else 'SENSOR'}] Probando: {name} (Pin BCM {pin})")
    try:
        if is_button:
            # Pulsador NC: Por defecto en ON (circuito cerrado). Al pulsar se vuelve OFF.
            device = Button(pin, pull_up=True)
            print(f"  -> Estado actual: {'CERRADO (ON)' if device.is_pressed else 'ABIERTO (OFF)'}")
            print(f"  -> PULSA el botón para abrir el circuito (esperando deteccion real)...")
        else:
            # Sensor IR: Por defecto suele estar en OFF. Al detectar algo se vuelve ON.
            device = LineSensor(pin)
            print(f"  -> Estado actual: {'DETECTANDO (ON)' if device.is_active else 'LIBRE (OFF)'}")
            print(f"  -> Pon tu mano frente al sensor {name} para cambiar el estado...")

        start_time = time.time()
        initial_state = device.is_active if not is_button else device.is_pressed
        changed = False

        while time.time() - start_time < 15:
            current_state = device.is_active if not is_button else device.is_pressed
            
            # Si el estado cambia respecto al inicial, confirmamos deteccion real
            if current_state != initial_state:
                print(f"  [OK] ¡Cambio de estado detectado! (Estado actual: {current_state})")
                changed = True
                break
            time.sleep(0.1)

        if not changed:
            print(f"  [FAIL] No se detectó ningún cambio en {name} (¿Está bien conectado?)")
        
        device.close()
    except Exception as e:
        print(f"  [ERROR] Error físico en {name}: {e}")

if __name__ == "__main__":
    print("================================================")
    print("   TEST DE HARDWARE ROBUSTO - TOUCHLESS UI PI   ")
    print("================================================")
    print("Este test lee el estado real de los pines en")
    print("bucle para evitar fallos de software (Edge Detect).")
    print("================================================\n")

    try:
        print("--- ZONA PARKING ---")
        test_led("Parking ROJO", PINS["parking"]["red"])
        test_led("Parking VERDE", PINS["parking"]["green"])
        test_servo("Barrera Parking", PINS["parking"]["servo"])
        test_sensor_manual("IR Entrada Parking", PINS["parking"]["ir_entry"])
        test_sensor_manual("Pulsador Salida Parking (NC)", PINS["parking"]["btn_exit"], is_button=True)

        print("\n--- ZONA PUERTA ---")
        test_led("Puerta ROJO (Bloqueado)", PINS["door"]["red"])
        test_led("Puerta VERDE (Desbloqueado)", PINS["door"]["green"])
        test_led("Luz Blanca (Cortesía)", PINS["door"]["white"])
        test_servo("Cerradura Puerta", PINS["door"]["servo"])
        test_sensor_manual("IR Interior Puerta", PINS["door"]["ir"])

    except KeyboardInterrupt:
        print("\n\n[!] Test cancelado.")
        sys.exit(0)

    print("\n================================================")
    print("      PRUEBAS DE HARDWARE COMPLETADAS           ")
    print("================================================")
