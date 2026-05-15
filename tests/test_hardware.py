import pytest
import sys
import os
import time
from unittest.mock import MagicMock

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

def test_parking_sensors(mocker):
    mocker.patch('src.hardware.Servo')
    mocker.patch('src.hardware.LED')
    mocker.patch('src.hardware.mqtt.Client')
    mocker.patch('src.hardware.LineSensor')
    
    hw = HardwareController()
    hw.publish_state = MagicMock()
    
    # Mocking instances separately
    hw.parking_ir_entry = MagicMock()
    hw.parking_ir_entry.is_active = True
    hw.parking_ir_exit = MagicMock()
    hw.parking_ir_exit.is_active = False
    hw.door_ir = MagicMock()
    hw.door_ir.is_active = False
    
    hw.loop()
    
    assert hw.parking_red.on.called
    hw.publish_state.assert_called_with("home/parking/status", {"barrier": "closed", "car_waiting": True})

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
