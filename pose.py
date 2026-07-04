"""
pose.py
Wraps MediaPipe Pose so the rest of the app can just ask for landmarks.
"""
import cv2
import mediapipe as mp


class PoseDetector:
    def __init__(self, min_detection_confidence=0.6, min_tracking_confidence=0.6):
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr):
        """
        Runs pose detection on a BGR frame (as read by OpenCV).
        Returns the mediapipe results object (has .pose_landmarks or None).
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.pose.process(rgb)
        return results

    def draw(self, frame_bgr, results):
        """Draws the skeleton onto the frame in place."""
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                frame_bgr,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2),
            )
        return frame_bgr

    def get_landmark_xy(self, results, landmark_enum, frame_width, frame_height):
        """
        Returns (x, y) pixel coordinates for a given mediapipe PoseLandmark enum,
        or None if not detected.
        """
        if not results.pose_landmarks:
            return None
        lm = results.pose_landmarks.landmark[landmark_enum]
        if lm.visibility < 0.4:
            return None
        return (lm.x * frame_width, lm.y * frame_height)

    def close(self):
        self.pose.close()
