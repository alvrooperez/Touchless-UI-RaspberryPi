import pytest
import sys
import os
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
