# Touchless UI — Raspberry Pi

Sistema de domótica sin contacto basado en reconocimiento de gestos para Raspberry Pi. Controla una barrera de parking y una puerta principal mediante visión por computadora, con un dashboard web en tiempo real.

---

## ¿Qué hace?

- Detecta gestos de la mano con la cámara usando **MediaPipe**
- Cada gesto puede asignarse libremente a cualquier acción desde el dashboard web
- Por defecto: **`Pointing_Up`** → abre la barrera del parking | **`Peace_Sign`** → desbloquea la puerta
- El buzzer suena cuando la puerta se abre y se silencia al cerrarse
- La luz de cortesía se enciende al abrir la puerta y permanece encendida indefinidamente
- Dashboard web accesible desde cualquier dispositivo de la red

---

## Hardware

### Pines GPIO (BCM)

| Componente | Pin | Tipo |
|---|---|---|
| Servo barrera parking | 17 | PWM OUT |
| LED rojo parking | 22 | OUT |
| LED verde parking | 23 | OUT |
| Sensor IR entrada parking | 18 | IN |
| Botón salida parking | 13 | IN (Pull-Up, NC) |
| Servo cerradura puerta | 24 | PWM OUT |
| Buzzer pasivo puerta | 7 | PWM OUT |
| Luz cortesía puerta | 5 | OUT |

### Servos

| Parámetro | Valor |
|---|---|
| Frecuencia PWM | 50 Hz |
| Ángulo abierto | 30° |
| Ángulo cerrado | 100° |

### Buzzer

El buzzer es de tipo **pasivo**. Se activa con una señal PWM a 1 kHz y 20 % de duty cycle. Un `GPIO.output(HIGH)` solo produce un click; es necesario el PWM para sonido continuo.

### Botón de salida parking

Configurado como **normalmente cerrado (NC)** con pull-up interno. El estado lógico en reposo es HIGH (1); al pulsarlo baja a LOW (0). La detección de pulsación se hace en flanco de bajada (`raw_btn == 0`).

---

## Instalación y ejecución

### Con Docker (recomendado)

```bash
# Construir imágenes
make build

# Sistema completo con hardware real
make run-ui

# Solo cámara, GPIO simulado
make run-camera-test

# Todo simulado (sin hardware)
make run-simulation

# Test interactivo de hardware
make test-hw

# Detener servicios
make down
```

### Sin Docker (directamente en la Raspberry Pi)

```bash
pip install -r requirements.txt
python src/main.py
```

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `GESTURE_VIP` | `Pointing_Up` | Gesto inicial para abrir parking |
| `GESTURE_PWD` | `Peace_Sign` | Gesto inicial para desbloquear puerta |
| `MQTT_BROKER` | — | IP del broker MQTT |
| `MOCK_HARDWARE` | `0` | `1` para simular GPIO (útil en desarrollo) |

Los gestos pueden cambiarse en caliente desde el dashboard web sin reiniciar el sistema.

---

## Arquitectura

```
Cámara → capture_thread → frame_queue
                               ↓
                      inference_thread (MediaPipe)
                               ↓
                        gesture_queue
                               ↓
                      hardware_thread → GPIO (servos, buzzer, LEDs)
                          ↑       ↓
                   command_queue  mqtt_queue → Mosquitto broker
                          ↑           ↓
                        web.py (Flask) → SSE → Dashboard :8080
```

### Threads

| Thread | Función |
|---|---|
| `Capture` | Lee frames de `/dev/video0` a 320×240 |
| `Inference` | Procesa frames con MediaPipe, debounce 5 frames |
| `Hardware` | Controla GPIO, lee sensores, publica MQTT |
| `Web` | Servidor Flask en puerto 8080 |

---

## Dashboard web

Accesible en `http://<ip-raspberry>:8080`

El dashboard tiene tres columnas:

### Columna izquierda — Modo Manual

Controles individuales para activar cada componente directamente desde la web sin necesidad de gestos:

| Componente | Acciones |
|---|---|
| Barrera parking | Abrir / Cerrar |
| LED rojo | ON / OFF |
| LED verde | ON / OFF |
| Cerradura puerta | Abrir / Cerrar |
| Buzzer | ON / OFF |
| Luz cortesía | ON / OFF |

### Columna central — Estado del sistema

- Estado en tiempo real vía SSE
- Badges de color: verde = abierto/desbloqueado, rojo = cerrado/bloqueado, ámbar = coche / luz encendida
- Botones de control de zona (parking y puerta)
- Log de actividad con las últimas 8 acciones
- Indicador de último gesto detectado
- Reconexión automática si se pierde la conexión SSE (backoff exponencial 2 s → 30 s máx.)

### Columna derecha — Configuración de gestos

- Lista de los 7 gestos disponibles; los asignados se resaltan en azul con un badge indicando la acción
- **Selector por cada acción** (12 en total): cualquier gesto puede asociarse a cualquier acción
- Los cambios se aplican en caliente sin reiniciar el sistema

#### Gestos disponibles

| Gesto |
|---|
| `Open_Hand` |
| `Closed_Fist` |
| `Peace_Sign` |
| `Pointing_Up` |
| `Thumb_Up` |
| `Thumb_Down` |
| `Pinky_Up` |

#### Acciones configurables

| Acción | Clave interna |
|---|---|
| Barrera — Abrir | `parking_open` |
| Barrera — Cerrar | `parking_close` |
| LED Rojo — ON | `parking_red_on` |
| LED Rojo — OFF | `parking_red_off` |
| LED Verde — ON | `parking_green_on` |
| LED Verde — OFF | `parking_green_off` |
| Cerradura — Abrir | `door_unlock` |
| Cerradura — Cerrar | `door_lock` |
| Buzzer — ON | `buzzer_on` |
| Buzzer — OFF | `buzzer_off` |
| Luz Cortesía — ON | `light_on` |
| Luz Cortesía — OFF | `light_off` |

---

## MQTT

**Broker:** Eclipse Mosquitto (puerto 1883)

| Topic | Dirección | Payload ejemplo |
|---|---|---|
| `home/parking/status` | Hardware → Web | `{"barrier":"open","car_waiting":true}` |
| `home/door/status` | Hardware → Web | `{"lock":"unlocked","courtesy_light":"on"}` |
| `home/parking/cmd` | Web → Hardware | `"OPEN"` |
| `home/door/cmd` | Web → Hardware | `"UNLOCK"` |

---

## API REST

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Dashboard web |
| `GET` | `/status` | Estado completo del sistema (JSON) |
| `GET` | `/stream` | SSE de eventos en tiempo real |
| `POST` | `/api/command` | Enviar comando a hardware `{"zone":"parking","command":"OPEN"}` |
| `POST` | `/api/gesture` | Actualizar asignación de gestos `{"parking_open":"Pointing_Up", ...}` |

---

## Comportamientos automáticos

| Comportamiento | Valor |
|---|---|
| Debounce gesto | 5 frames (~250 ms) |
| Debounce sensor IR | 5 ciclos (~250 ms) |
| Cooldown entre acciones de zona | 2000 ms |
| Auto-lock puerta | 10 s tras desbloqueo |
| Luz cortesía | Se enciende al abrir la puerta, permanece encendida |
| Buzzer | Suena al abrir la puerta, se silencia al cerrarla |

---

## Estructura del proyecto

```
├── src/
│   ├── main.py          # Orquestador multi-thread y mapeo gesto → acción
│   ├── vision.py        # Reconocimiento de gestos (MediaPipe)
│   ├── hardware.py      # Control GPIO, sensores, buzzer PWM y MQTT
│   ├── web.py           # API Flask + SSE + configuración de gestos
│   ├── simulation.py    # Modo sin hardware
│   └── templates/
│       └── index.html   # Dashboard web (3 columnas)
├── tests/
│   └── hardware_guided_test.py  # Test interactivo paso a paso
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## Dependencias

```
opencv-python-headless==4.8.1.78
mediapipe==0.10.9
RPi.GPIO==0.7.1
paho-mqtt==1.6.1
flask==3.0.0
```
