import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json
import time

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

# Mock jsonify and render_template
mock_flask.jsonify = lambda x: json.dumps(x)
mock_flask.render_template = lambda template, **kwargs: f"Rendered {template}"
# Mock Response to just return the generator for testing
mock_flask.Response = lambda response, mimetype: response

sys.modules['flask'] = mock_flask

# Import web after mocking
import web

class TestWebModule(unittest.TestCase):
    def test_index_endpoint(self):
        web.system_state['last_gesture'] = 'Swipe Left'
        result = web.index()
        self.assertEqual(result, "Rendered index.html")

    def test_status_endpoint(self):
        web.system_state['last_gesture'] = 'Swipe Right'
        web.system_state['uptime_seconds'] = 120
        result = web.status()
        data = json.loads(result)
        self.assertEqual(data['last_gesture'], 'Swipe Right')

    @patch('time.sleep', return_value=None)
    def test_stream_endpoint(self, mock_sleep):
        web.system_state['last_gesture'] = 'Peace_Sign'
        gen = web.stream()
        
        # First iteration should yield Peace_Sign
        event1 = next(gen)
        self.assertEqual(event1, "data: Peace_Sign\n\n")
        
        # Change state and get next yield
        web.system_state['last_gesture'] = 'Closed_Fist'
        event2 = next(gen)
        self.assertEqual(event2, "data: Closed_Fist\n\n")

    def test_run_web_server_sets_state(self):
        new_state = {"last_gesture": "Circle", "uptime_seconds": 50}
        with unittest.mock.patch.object(web.app, 'run') as mock_run:
            web.run_web_server(new_state)
            self.assertEqual(web.system_state, new_state)
            mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
