import pytest
import json
import time
import queue
from unittest.mock import MagicMock
from src.hardware import HardwareController
from src.web import app, mqtt_queue as web_mqtt_queue, command_queue as web_command_queue

@pytest.fixture
def integration_setup(mocker):
    # Mock physical hardware
    mocker.patch('src.hardware.Servo')
    mocker.patch('src.hardware.LED')
    mocker.patch('src.hardware.LineSensor')
    mocker.patch('src.hardware.mqtt.Client')
    
    # Use the same queues that the web server uses
    mqtt_queue = web_mqtt_queue
    command_queue = web_command_queue
    
    # Clear queues before each test
    while not mqtt_queue.empty(): mqtt_queue.get()
    while not command_queue.empty(): command_queue.get()
    
    shared_state = {"last_gesture": "None"}
    
    # Initialize hardware controller with the shared queues
    hw = HardwareController(mqtt_broker="127.0.0.1", mqtt_queue=mqtt_queue, command_queue=command_queue)
    
    app.config['TESTING'] = True
    client = app.test_client()
    
    return {
        "hw": hw,
        "client": client,
        "mqtt_queue": mqtt_queue,
        "command_queue": command_queue,
        "shared_state": shared_state
    }

def test_integration_parking_logic(integration_setup):
    hw = integration_setup["hw"]
    mqtt_queue = integration_setup["mqtt_queue"]
    
    hw.trigger_action("VIP_PASS")
    
    assert not mqtt_queue.empty()
    event = mqtt_queue.get(timeout=1)
    
    assert event["topic"] == "home/parking/status"
    assert event["payload"]["barrier"] == "open"
    
def test_integration_door_gesture_logic(integration_setup):
    hw = integration_setup["hw"]
    mqtt_queue = integration_setup["mqtt_queue"]
    
    hw.trigger_action("PASSWORD")
    
    event = mqtt_queue.get(timeout=1)
    assert event["topic"] == "home/door/status"
    assert event["payload"]["lock"] == "unlocked"

def test_integration_web_to_hardware_command(integration_setup):
    client = integration_setup["client"]
    hw = integration_setup["hw"]
    mqtt_queue = integration_setup["mqtt_queue"]
    
    response = client.post('/api/command', json={'zone': 'door', 'command': 'UNLOCK'})
    assert response.status_code == 200
    
    hw.loop()
    
    event = mqtt_queue.get(timeout=1)
    assert event["topic"] == "home/door/status"
    assert event["payload"]["lock"] == "unlocked"

def test_integration_sensor_trigger_flow(integration_setup):
    hw = integration_setup["hw"]
    mqtt_queue = integration_setup["mqtt_queue"]
    
    hw.on_car_arrival()
    
    event = mqtt_queue.get(timeout=1)
    assert event["topic"] == "home/parking/status"
    assert event["payload"]["car_waiting"] is True
    
    hw.on_car_departure()
    event = mqtt_queue.get(timeout=1)
    assert event["payload"]["car_waiting"] is False
    assert event["payload"]["barrier"] == "closed"
