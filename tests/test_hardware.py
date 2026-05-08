import unittest
import time
from unittest.mock import patch
import sys
import os

# Add src to path so we can import hardware
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hardware import HardwareController

class TestHardwareController(unittest.TestCase):
    def test_trigger_action_success(self):
        with patch('logging.info') as mock_logging:
            controller = HardwareController()
            controller.trigger_action("test_gesture")
            
            # 1: Init, 2: Trigger
            self.assertEqual(mock_logging.call_count, 2)
            mock_logging.assert_any_call("Initializing Dummy GPIO Pins...")
            mock_logging.assert_any_call("ACTION TRIGGERED: test_gesture")
            self.assertGreater(controller.last_action_time, 0)

    def test_cooldown_logic(self):
        with patch('logging.info') as mock_logging:
            controller = HardwareController()
            # Call 1: Init
            
            # Call 2: First trigger
            controller.trigger_action("action1")
            self.assertEqual(mock_logging.call_count, 2)
            
            # Call 3: Second trigger (should be ignored due to cooldown)
            controller.trigger_action("action2")
            self.assertEqual(mock_logging.call_count, 2)
            
            # Simulate cooldown passed
            controller.last_action_time = 0
            
            # Call 3: Third trigger
            controller.trigger_action("action3")
            self.assertEqual(mock_logging.call_count, 3)
            mock_logging.assert_any_call("ACTION TRIGGERED: action3")

if __name__ == '__main__':
    unittest.main()
