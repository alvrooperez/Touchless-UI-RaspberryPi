import threading
import queue
import cv2
import time
import os
import logging
from vision import GestureRecognizer
from hardware import HardwareController
from web import run_web_server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(threadName)s] %(message)s')

frame_queue = queue.Queue(maxsize=1)
gesture_queue = queue.Queue(maxsize=10)
mqtt_queue = queue.Queue()
command_queue = queue.Queue()
shared_state = {"last_gesture": "None"}

def capture_thread():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: continue
        if frame_queue.full():
            try: frame_queue.get_nowait()
            except queue.Empty: pass
        frame_queue.put(frame)

def inference_thread():
    recognizer = GestureRecognizer()
    current_gesture, count = None, 0
    while True:
        try:
            frame = frame_queue.get(timeout=1.0)
            gesture = recognizer.process_frame(frame)
            if gesture:
                if gesture == current_gesture: 
                    count += 1
                else: 
                    current_gesture, count = gesture, 1
                
                if count == 5: # Debouncing threshold
                    try: gesture_queue.put_nowait(gesture)
                    except queue.Full: pass
                    shared_state["last_gesture"] = gesture
                    count = 0 # Reset after triggering
            else:
                current_gesture, count = None, 0
        except queue.Empty: pass

def hardware_thread():
    hw = HardwareController(os.environ.get("MQTT_BROKER"), mqtt_queue, command_queue)
    while True:
        try:
            gesture = gesture_queue.get(timeout=0.1)
            hw.trigger_action(gesture)
        except queue.Empty: pass
        hw.loop()

if __name__ == "__main__":
    t1 = threading.Thread(target=capture_thread, name="Capture")
    t2 = threading.Thread(target=inference_thread, name="Inference")
    t3 = threading.Thread(target=hardware_thread, name="Hardware")
    t4 = threading.Thread(target=run_web_server, args=(shared_state, mqtt_queue, command_queue), name="Web")
    
    for t in [t1, t2, t3, t4]:
        t.daemon = True
        t.start()
        
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
