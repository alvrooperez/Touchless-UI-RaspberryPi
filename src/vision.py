import cv2
import mediapipe as mp

class GestureRecognizer:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False, max_num_hands=1,
            model_complexity=0, min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def process_frame(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        if not results.multi_hand_landmarks:
            return None
        return self._classify_gesture(results.multi_hand_landmarks[0])

    def _classify_gesture(self, landmarks):
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        
        # Check which fingers are extended
        fingers_up = [landmarks.landmark[tip].y < landmarks.landmark[pip].y for tip, pip in zip(tips, pips)]
        # Check if thumb is open (distance on x-axis)
        thumb_is_open = abs(landmarks.landmark[4].x - landmarks.landmark[5].x) > 0.05
        
        up_count = sum(fingers_up)
        
        # Logic for 7 distinct gestures
        if up_count == 4 and thumb_is_open: return "Open_Hand"
        if up_count == 0 and not thumb_is_open: return "Closed_Fist"
        if fingers_up == [True, True, False, False]: return "Peace_Sign"
        if fingers_up == [True, False, False, False]: return "Pointing_Up"
        if up_count == 0 and thumb_is_open and landmarks.landmark[4].y < landmarks.landmark[3].y: return "Thumb_Up"
        if up_count == 0 and thumb_is_open and landmarks.landmark[4].y > landmarks.landmark[3].y: return "Thumb_Down"
        if fingers_up == [False, False, False, True]: return "Pinky_Up"
        
        return None
