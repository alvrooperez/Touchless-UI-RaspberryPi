import unittest
from unittest.mock import MagicMock
import sys
import os
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock flask BEFORE importing web
mock_flask = MagicMock()
mock_app = MagicMock()
mock_flask.Flask.return_value = mock_app

# Mock route decorator to return the function itself
def mock_route(path):
    def decorator(f):
        return f
    return decorator

mock_app.route = mock_route

# Mock jsonify to just return the dict as a JSON string for testing
mock_flask.jsonify = lambda x: json.dumps(x)
sys.modules['flask'] = mock_flask

# Import web after mocking
import web

class TestWebModule(unittest.TestCase):
    def test_index_endpoint(self):
        # Setup state
        web.system_state['last_gesture'] = 'Swipe Left'
        
        # Manually call the index function logic
        result = web.index()
        self.assertIn("Touchless UI Status", result)
        self.assertIn("Last Gesture: Swipe Left", result)

    def test_status_endpoint(self):
        # Setup state
        web.system_state['last_gesture'] = 'Swipe Right'
        web.system_state['uptime_seconds'] = 120
        
        # Manually call the status function logic
        result = web.status()
        data = json.loads(result)
        self.assertEqual(data['last_gesture'], 'Swipe Right')
        self.assertEqual(data['uptime_seconds'], 120)

    def test_run_web_server_sets_state(self):
        new_state = {"last_gesture": "Circle", "uptime_seconds": 50}
        
        # Mock app.run to not actually start the server
        with unittest.mock.patch.object(web.app, 'run') as mock_run:
            web.run_web_server(new_state)
            self.assertEqual(web.system_state, new_state)
            mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
