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
        "btn_exit": 27 # Pulsador NC
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

def test_sensor(name, pin, is_button=False):
    print(f"\n[{'BOTÓN' if is_button else 'SENSOR'}] Probando: {name} (Pin BCM {pin})")
    try:
        if is_button:
            # Para pulsador NC que está en ON (cerrado) y se abre al pulsar:
            device = Button(pin, pull_up=True)
            print(f"  -> El botón debería estar en ON ahora. Pulsa para detectar el cambio (esperando 10s)...")
            # En Button(pull_up=True), soltar el botón físico (abrir circuito) dispara 'released'
            device.wait_for_release(timeout=10)
            print(f"  [OK] ¡Pulsación detectada en {name}!")
        else:
            device = LineSensor(pin)
            print(f"  -> Esperando activación... (Pon tu mano frente al sensor {name}, esperando 10s)")
            device.wait_for_active(timeout=10)
            print(f"  [OK] ¡Detección confirmada en {name}!")
            print(f"  -> Ahora retira la mano del sensor...")
            device.wait_for_inactive(timeout=5)
            print(f"  [OK] Sensor {name} despejado.")
        
        device.close()
    except Exception as e:
        print(f"  [ERROR] No se pudo probar {name}: {e}")

if __name__ == "__main__":
    print("================================================")
    print("   TEST DE HARDWARE GUIADO - TOUCHLESS UI PI    ")
    print("================================================")
    print("Asegúrate de estar en la Raspberry Pi o tener")
    print("los dispositivos mapeados en Docker correctamente.")
    print("================================================\n")

    try:
        # ZONA PARKING
        print("--- PROBANDO ZONA PARKING ---")
        test_led("Parking ROJO", PINS["parking"]["red"])
        test_led("Parking VERDE", PINS["parking"]["green"])
        test_servo("Barrera Parking", PINS["parking"]["servo"])
        test_sensor("IR Entrada Parking", PINS["parking"]["ir_entry"])
        test_sensor("Pulsador Salida Parking (NC)", PINS["parking"]["btn_exit"], is_button=True)

        print("\n--- PROBANDO ZONA PUERTA ---")
        test_led("Puerta ROJO (Bloqueado)", PINS["door"]["red"])
        test_led("Puerta VERDE (Desbloqueado)", PINS["door"]["green"])
        test_led("Luz Blanca (Cortesía)", PINS["door"]["white"])
        test_servo("Cerradura Puerta", PINS["door"]["servo"])
        test_sensor("IR Interior Puerta", PINS["door"]["ir"])

    except KeyboardInterrupt:
        print("\n\n[!] Test cancelado por el usuario.")
        sys.exit(0)

    print("\n================================================")
    print("      TODAS LAS PRUEBAS HAN FINALIZADO          ")
    print("================================================")
