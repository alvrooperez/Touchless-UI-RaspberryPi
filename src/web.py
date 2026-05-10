from flask import Flask, jsonify, render_template, Response
import time

app = Flask(__name__)
system_state = {"last_gesture": "None", "uptime_seconds": 0}

@app.route('/')
def index():
    return render_template('index.html', gesture=system_state.get('last_gesture', 'None'))

@app.route('/status')
def status():
    return jsonify(system_state)

@app.route('/stream')
def stream():
    def event_stream():
        last_sent = None
        while True:
            current = system_state.get('last_gesture', 'None')
            if current != last_sent:
                yield f"data: {current}\n\n"
                last_sent = current
            time.sleep(0.1)
    return Response(event_stream(), mimetype='text/event-stream')

def run_web_server(state_dict):
    global system_state
    system_state = state_dict
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
