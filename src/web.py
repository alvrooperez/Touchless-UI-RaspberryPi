from flask import Flask, jsonify
import threading

app = Flask(__name__)
system_state = {"last_gesture": "None", "uptime_seconds": 0}

@app.route('/')
def index():
    return f"<h1>Touchless UI Status</h1><p>Last Gesture: {system_state.get('last_gesture', 'None')}</p>"

@app.route('/status')
def status():
    return jsonify(system_state)

def run_web_server(state_dict):
    global system_state
    system_state = state_dict
    # disable debug & reloader to play nice with threads
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
