"""
GestHome - tests/calibrar_servo.py
Herramienta interactiva para calibrar el servo ES08A.

El ES08A usa un rango PWM diferente al SG90 estandar.
Este script permite encontrar los valores exactos para tu servo.

Uso:
    python3 tests/calibrar_servo.py

Resultado: te dira los valores exactos de ANGULO_ABIERTO
y ANGULO_CERRADO para poner en hardware.py
"""

import RPi.GPIO as GPIO
import time
import sys

PIN_SERVO = 18

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_SERVO, GPIO.OUT)

# ── El ES08A funciona mejor con estos rangos de ciclo ──
# Estandar SG90:  min=2.5   max=12.5  (rango 10%)
# ES08A tipico:   min=1.0   max=11.0  o min=0.5 max=11.5
# Vamos a buscar el tuyo especifico

PWM_MIN = 0.5    # ciclo minimo (0 grados)
PWM_MAX = 11.5   # ciclo maximo (180 grados)

pwm = GPIO.PWM(PIN_SERVO, 50)
pwm.start(0)

def ciclo_directo(valor):
    """Mueve el servo a un ciclo de trabajo directo (0.5 - 11.5)"""
    pwm.ChangeDutyCycle(valor)
    time.sleep(0.6)
    pwm.ChangeDutyCycle(0)

def angulo_a_ciclo(angulo, pwm_min, pwm_max):
    """Convierte angulo a ciclo con los limites dados"""
    return pwm_min + (angulo / 180.0) * (pwm_max - pwm_min)

def mover_a_angulo(angulo, pwm_min, pwm_max):
    ciclo = angulo_a_ciclo(angulo, pwm_min, pwm_max)
    pwm.ChangeDutyCycle(ciclo)
    time.sleep(0.7)
    pwm.ChangeDutyCycle(0)

def separador(titulo=""):
    print("\n" + "─" * 50)
    if titulo:
        print(f"  {titulo}")
        print("─" * 50)

def pedir_float(mensaje, default):
    try:
        val = input(f"  {mensaje} [{default}]: ").strip()
        return float(val) if val else default
    except ValueError:
        return default

def pedir_int(mensaje, default):
    try:
        val = input(f"  {mensaje} [{default}]: ").strip()
        return int(val) if val else default
    except ValueError:
        return default

# ════════════════════════════════════════════════════
print("=" * 50)
print("  Calibrador de Servo ES08A — GestHome")
print("=" * 50)
print("\nEste script mueve el servo a distintas posiciones")
print("para que encuentres los valores correctos.")
print("Ctrl+C en cualquier momento para salir.\n")

try:
    # ── PASO 1: Buscar el limite minimo (0 grados) ──
    separador("PASO 1: Encontrar posicion CERRADO (0 grados)")
    print("  Vamos a probar ciclos bajos hasta que el servo")
    print("  llegue al tope sin trabarse.\n")

    ciclos_prueba = [0.5, 1.0, 1.5, 2.0, 2.5]
    mejor_min = 1.0

    for c in ciclos_prueba:
        print(f"  -> Probando ciclo {c}%...")
        ciclo_directo(c)
        time.sleep(0.3)
        resp = input(f"     ¿Llego bien al tope SIN trabarse? (s/n): ").strip().lower()
        if resp == 's':
            mejor_min = c
            print(f"     Guardado: ciclo minimo = {c}%")
            break
        elif resp == 'n':
            print(f"     OK, probando siguiente...")

    print(f"\n  Ciclo minimo encontrado: {mejor_min}%")

    # ── PASO 2: Buscar el limite maximo (180 grados) ──
    separador("PASO 2: Encontrar posicion ABIERTO (90-180 grados)")
    print("  Ahora buscamos el tope del otro lado.\n")

    ciclos_prueba_max = [11.5, 11.0, 10.5, 10.0, 9.5, 9.0]
    mejor_max = 11.0

    for c in ciclos_prueba_max:
        print(f"  -> Probando ciclo {c}%...")
        ciclo_directo(c)
        time.sleep(0.3)
        resp = input(f"     ¿Llego bien al tope SIN trabarse? (s/n): ").strip().lower()
        if resp == 's':
            mejor_max = c
            print(f"     Guardado: ciclo maximo = {c}%")
            break

    print(f"\n  Ciclo maximo encontrado: {mejor_max}%")

    # ── PASO 3: Definir angulos utiles para la maqueta ──
    separador("PASO 3: Definir angulos para la maqueta")
    print("  Ahora movemos el servo a angulos concretos")
    print("  para que elijas los que mejor encajan con tu maqueta.\n")

    angulos = [0, 30, 45, 60, 90, 120, 150, 180]
    angulo_cerrado = 0
    angulo_abierto = 90

    for ang in angulos:
        print(f"  -> Moviendo a {ang} grados...")
        mover_a_angulo(ang, mejor_min, mejor_max)
        resp = input(f"     Este angulo, ¿es util para la barrera? (c=cerrado / a=abierto / n=no): ").strip().lower()
        if resp == 'c':
            angulo_cerrado = ang
            print(f"     Guardado como CERRADO = {ang}°")
        elif resp == 'a':
            angulo_abierto = ang
            print(f"     Guardado como ABIERTO = {ang}°")

    # ── PASO 4: Verificacion final ──
    separador("PASO 4: Verificacion final")
    print(f"  Ciclo minimo:    {mejor_min}%")
    print(f"  Ciclo maximo:    {mejor_max}%")
    print(f"  Angulo CERRADO:  {angulo_cerrado} grados")
    print(f"  Angulo ABIERTO:  {angulo_abierto} grados\n")

    print("  Probando secuencia CERRADO -> ABIERTO -> CERRADO...")
    mover_a_angulo(angulo_cerrado, mejor_min, mejor_max)
    time.sleep(0.5)
    mover_a_angulo(angulo_abierto, mejor_min, mejor_max)
    time.sleep(0.5)
    mover_a_angulo(angulo_cerrado, mejor_min, mejor_max)

    resp = input("\n  ¿La secuencia funciono correctamente? (s/n): ").strip().lower()

    if resp == 's':
        separador("RESULTADO — copia estos valores en hardware.py")
        print(f"""
  # ── Calibracion ES08A ──────────────────────────────
  PWM_MIN = {mejor_min}   # ciclo minimo
  PWM_MAX = {mejor_max}  # ciclo maximo

  BARRERA_CERRADA = {angulo_cerrado}
  BARRERA_ABIERTA = {angulo_abierto}
  PUERTA_CERRADA  = {angulo_cerrado}
  PUERTA_ABIERTA  = {angulo_abierto}

  # Sustituye tambien la funcion _angulo_a_ciclo en hardware.py:
  def _angulo_a_ciclo(self, angulo):
      PWM_MIN = {mejor_min}
      PWM_MAX = {mejor_max}
      return PWM_MIN + (angulo / 180.0) * (PWM_MAX - PWM_MIN)
        """)
    else:
        print("\n  Vuelve a ejecutar el script y ajusta los valores.")

except KeyboardInterrupt:
    print("\n\nCalibración interrumpida.")

finally:
    pwm.stop()
    GPIO.cleanup()
    print("GPIO liberado.")