import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock cv2 and mediapipe before importing GestureRecognizer
sys.modules['cv2'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['mediapipe.solutions'] = MagicMock()
sys.modules['mediapipe.solutions.hands'] = MagicMock()

# Import after mocking
try:
    from vision import GestureRecognizer
except ImportError:
    GestureRecognizer = None

class TestGestureRecognizer(unittest.TestCase):
    def setUp(self):
        if GestureRecognizer is None:
            self.skipTest("GestureRecognizer not implemented yet")
        self.recognizer = GestureRecognizer()

    def create_mock_landmark(self, x, y):
        landmark = MagicMock()
        landmark.x = x
        landmark.y = y
        return landmark

    def create_mock_landmarks(self, y_values, thumb_x=0.5, thumb_y=0.5):
        mock_results = MagicMock()
        landmarks = [self.create_mock_landmark(0, 0) for _ in range(21)]
        
        # Thumb tip and base for open/closed check
        # landmark 4 is tip, 5 is mcp, 3 is ip
        landmarks[4].x = thumb_x
        landmarks[5].x = 0.5 
        landmarks[4].y = thumb_y
        landmarks[3].y = 0.6 
        
        # Finger tip/pip pairs
        # tips = [8, 12, 16, 20], pips = [6, 10, 14, 18]
        finger_indices = [(8, 6), (12, 10), (16, 14), (20, 18)]
        for i, (tip, pip) in enumerate(finger_indices):
            if y_values[i]: # Finger up
                landmarks[tip].y = 0.4
                landmarks[pip].y = 0.5
            else: # Finger down
                landmarks[tip].y = 0.6
                landmarks[pip].y = 0.5
                
        mock_results.landmark = landmarks
        return mock_results

    def test_classify_open_hand(self):
        # All fingers up, thumb open
        landmarks = self.create_mock_landmarks([True, True, True, True], thumb_x=0.6)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Open_Hand")

    def test_classify_closed_fist(self):
        # All fingers down, thumb closed
        landmarks = self.create_mock_landmarks([False, False, False, False], thumb_x=0.52)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Closed_Fist")

    def test_classify_peace_sign(self):
        # Index and middle up, others down, thumb closed
        landmarks = self.create_mock_landmarks([True, True, False, False], thumb_x=0.52)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Peace_Sign")

    def test_classify_pointing_up(self):
        # Index up, others down, thumb closed
        landmarks = self.create_mock_landmarks([True, False, False, False], thumb_x=0.52)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Pointing_Up")

    def test_classify_thumb_up(self):
        # All fingers down, thumb open, thumb tip above thumb base
        landmarks = self.create_mock_landmarks([False, False, False, False], thumb_x=0.6, thumb_y=0.4)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Thumb_Up")

    def test_classify_thumb_down(self):
        # All fingers down, thumb open, thumb tip below thumb base
        landmarks = self.create_mock_landmarks([False, False, False, False], thumb_x=0.6, thumb_y=0.8)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Thumb_Down")

    def test_classify_pinky_up(self):
        # Only pinky up, thumb closed
        landmarks = self.create_mock_landmarks([False, False, False, True], thumb_x=0.52)
        self.assertEqual(self.recognizer._classify_gesture(landmarks), "Pinky_Up")

if __name__ == '__main__':
    unittest.main()
