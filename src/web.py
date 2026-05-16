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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    return jsonify({**system_state, "parking": parking_cache or None, "door": door_cache or None})

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
            # Yield gesture if changed
            current_gesture = system_state.get('last_gesture', 'None')
            if current_gesture != last_gesture:
                yield f"data: {current_gesture}\n\n"
                last_gesture = current_gesture
            
            # Yield MQTT events
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
    # Forzar host 0.0.0.0 para acceso desde fuera del contenedor y quitar threaded por seguridad
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)