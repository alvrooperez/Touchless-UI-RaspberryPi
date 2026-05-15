import pytest
import sys
import os
import time
import threading
from unittest.mock import MagicMock, patch

# Mock missing modules before importing from src.hardware
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()
sys.modules['gpiozero'] = MagicMock()

# Ensure src is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.hardware import HardwareController

def test_hardware_init(mocker):
    # Mock gpiozero to avoid needing real GPIO on test machine
    mocker.patch('src.hardware.Servo')
    mocker.patch('src.hardware.LED')
    mocker.patch('src.hardware.LineSensor')
    mocker.patch('src.hardware.mqtt.Client')
    
    hw = HardwareController(mqtt_broker="127.0.0.1")
    assert hw.mqtt_broker == "127.0.0.1"
    # Verify callbacks are assigned
    assert hw.parking_ir_entry.when_activated is not None
    assert hw.parking_ir_exit.when_activated is not None
    assert hw.door_ir.when_activated is not None

def test_parking_sensors(mocker):
    mocker.patch('src.hardware.Servo')
    mocker.patch('src.hardware.LED')
    mocker.patch('src.hardware.mqtt.Client')
    mocker.patch('src.hardware.LineSensor')
    
    hw = HardwareController()
    hw.publish_state = MagicMock()
    
    # Simulate car arrival
    hw.on_car_arrival()
    assert hw.parking_red.on.called
    hw.publish_state.assert_called_with("home/parking/status", {"barrier": "closed", "car_waiting": True})
    
    # Simulate car departure
    hw.on_car_departure()
    assert hw.parking_servo.min.called
    hw.publish_state.assert_called_with("home/parking/status", {"barrier": "closed", "car_waiting": False})

def test_door_light_logic(mocker):
    mocker.patch('src.hardware.Servo')
    mocker.patch('src.hardware.LED')
    mocker.patch('src.hardware.LineSensor')
    mocker.patch('src.hardware.mqtt.Client')
    mock_timer = mocker.patch('threading.Timer')
    
    hw = HardwareController()
    hw.publish_state = MagicMock()
    
    # Person approaches
    hw.on_door_approach()
    assert hw.door_light.on.called
    assert hw.light_on is True
    assert mock_timer.call_count == 1
    
    # Check MQTT message
    hw.publish_state.assert_called_with("home/door/status", {
        "lock": "locked",
        "courtesy_light": "on"
    })
    
    # Person approaches again (should reset timer)
    timer_instance = mock_timer.return_value
    hw.on_door_approach()
    assert timer_instance.cancel.called
    assert mock_timer.call_count == 2

def test_trigger_action_cooldown(mocker):
    mocker.patch('src.hardware.Servo')
    mocker.patch('src.hardware.LED')
    mocker.patch('src.hardware.LineSensor')
    mocker.patch('src.hardware.mqtt.Client')
    
    hw = HardwareController()
    hw.open_parking = MagicMock()
    
    # First call
    hw.trigger_action('VIP_PASS')
    assert hw.open_parking.call_count == 1
    
    # Immediate second call
    hw.trigger_action('VIP_PASS')
    assert hw.open_parking.call_count == 1
    
    # After cooldown (mocking time)
    mocker.patch('time.time', return_value=time.time() + 3)
    hw.trigger_action('VIP_PASS')
    assert hw.open_parking.call_count == 2
