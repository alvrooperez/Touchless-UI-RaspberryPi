# Touchless UI — Raspberry Pi

Sistema de domótica sin contacto basado en reconocimiento de gestos para Raspberry Pi. Controla una barrera de parking y una puerta principal mediante visión por computadora, con un dashboard web en tiempo real.

---

## ¿Qué hace?

- Detecta gestos de la mano con la cámara usando **MediaPipe**
- **Gesto `Pointing_Up`** → abre la barrera del parking
- **Gesto `Peace_Sign`** → desbloquea la puerta principal
- El buzzer suena cuando la puerta se abre y se silencia al cerrarse
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
| Botón salida parking | 13 | IN |
| Servo puerta | 24 | PWM OUT |
| Buzzer puerta | 7 | OUT |
| Luz cortesía puerta | 5 | OUT |

### Servos

| Parámetro | Valor |
|---|---|
| Frecuencia PWM | 50 Hz |
| Ángulo abierto | 30° |
| Ángulo cerrado | 100° |

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
| `GESTURE_VIP` | `Pointing_Up` | Gesto para abrir parking |
| `GESTURE_PWD` | `Peace_Sign` | Gesto para desbloquear puerta |
| `MQTT_BROKER` | — | IP del broker MQTT |
| `MOCK_HARDWARE` | `0` | `1` para simular GPIO |

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
                               ↓
                         mqtt_queue → Mosquitto broker
                               ↓
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

- Estado en tiempo real vía SSE
- Badges de color: verde = abierto, rojo = cerrado
- Botones de control manual (Abrir/Cerrar, Desbloquear/Bloquear)
- Log de actividad con las últimas 8 acciones
- Reconexión automática si se pierde la conexión

---

## MQTT

**Broker:** Eclipse Mosquitto (puerto 1883)

| Topic | Dirección | Payload ejemplo |
|---|---|---|
| `home/parking/status` | Hardware → Web | `{"barrier":"open","car_waiting":true}` |
| `home/door/status` | Hardware → Web | `{"lock":"unlocked","courtesy_light":"off"}` |
| `home/parking/cmd` | Web → Hardware | `"OPEN"` |
| `home/door/cmd` | Web → Hardware | `"UNLOCK"` |

---

## Comportamientos automáticos

| Comportamiento | Valor |
|---|---|
| Debounce gesto | 5 frames (~250 ms) |
| Debounce sensor IR | 5 ciclos (~250 ms) |
| Cooldown entre acciones | 2000 ms |
| Auto-lock puerta | 10 s tras desbloqueo |

---

## Estructura del proyecto

```
├── src/
│   ├── main.py          # Orquestador multi-thread
│   ├── vision.py        # Reconocimiento de gestos (MediaPipe)
│   ├── hardware.py      # Control GPIO y MQTT
│   ├── web.py           # API Flask + SSE
│   ├── simulation.py    # Modo sin hardware
│   └── templates/
│       └── index.html   # Dashboard web
├── tests/               # Tests unitarios e integración
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
