from flask import Flask, jsonify, render_template, Response, request
import time
import queue
import json

app = Flask(__name__)
system_state = {"last_gesture": "None"}
mqtt_queue = queue.Queue()
command_queue = queue.Queue()
parking_cache = {}
door_cache = {}

AVAILABLE_GESTURES = [
    "Open_Hand", "Closed_Fist", "Peace_Sign",
    "Pointing_Up", "Thumb_Up", "Thumb_Down", "Pinky_Up"
]

# Ordered list of (action_key, label) — order matters for the UI
GESTURE_ACTIONS = [
    ("parking_open",     "Barrera — Abrir"),
    ("parking_close",    "Barrera — Cerrar"),
    ("parking_red_on",   "LED Rojo — ON"),
    ("parking_red_off",  "LED Rojo — OFF"),
    ("parking_green_on", "LED Verde — ON"),
    ("parking_green_off","LED Verde — OFF"),
    ("door_unlock",      "Cerradura — Abrir"),
    ("door_lock",        "Cerradura — Cerrar"),
    ("buzzer_on",        "Buzzer — ON"),
    ("buzzer_off",       "Buzzer — OFF"),
    ("light_on",         "Luz Cortesía — ON"),
    ("light_off",        "Luz Cortesía — OFF"),
]
GESTURE_ACTION_KEYS = {k for k, _ in GESTURE_ACTIONS}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    gesture_map = {k: system_state.get(f"gesture_{k}", "") for k, _ in GESTURE_ACTIONS}
    return jsonify({
        **system_state,
        "available_gestures": AVAILABLE_GESTURES,
        "gesture_actions": {k: label for k, label in GESTURE_ACTIONS},
        "gesture_map": gesture_map,
    })

@app.route('/api/gesture', methods=['POST'])
def set_gesture():
    data = request.json
    if not data:
        return jsonify({"error": "invalid payload"}), 400
    for action_key in GESTURE_ACTION_KEYS:
        if action_key in data:
            system_state[f"gesture_{action_key}"] = data[action_key]
    gesture_map = {k: system_state.get(f"gesture_{k}", "") for k, _ in GESTURE_ACTIONS}
    return jsonify({"status": "ok", "gesture_map": gesture_map}), 200

@app.route('/api/command', methods=['POST'])
def command():
    data = request.json
    if data and 'zone' in data and 'command' in data:
        command_queue.put(data)
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "invalid payload"}), 400

@app.route('/stream')
def stream():
    def event_stream():
        last_gesture = None
        while True:
            current_gesture = system_state.get('last_gesture', 'None')
            if current_gesture != last_gesture:
                yield f"data: {current_gesture}\n\n"
                last_gesture = current_gesture
            try:
                while not mqtt_queue.empty():
                    mqtt_event = mqtt_queue.get_nowait()
                    if mqtt_event.get('topic') == 'home/parking/status':
                        parking_cache.update(mqtt_event['payload'])
                    elif mqtt_event.get('topic') == 'home/door/status':
                        door_cache.update(mqtt_event['payload'])
                    yield f"data: {json.dumps(mqtt_event)}\n\n"
            except queue.Empty:
                pass
            time.sleep(0.1)
    return Response(event_stream(), mimetype='text/event-stream')

def run_web_server(state_dict, mq_out=None, cmd_in=None):
    global system_state, mqtt_queue, command_queue
    system_state = state_dict
    if mq_out: mqtt_queue = mq_out
    if cmd_in: command_queue = cmd_in
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)
