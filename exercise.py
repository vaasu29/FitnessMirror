"""
exercise.py
Defines exercise-specific logic: which joints to track, rep-counting state
machines, and simple rule-based form checks.

This is intentionally rule-based (no ML) for the Version 1-3 MVP - easy to
understand, easy to extend, zero training data or cost required.
"""
import mediapipe as mp
from angle import calculate_angle

PL = mp.solutions.pose.PoseLandmark


class ExerciseAnalyzer:
    """
    Base class for a single exercise's rep-counting + form-checking logic.
    Subclasses implement `compute()` which:
      - reads landmarks
      - computes relevant joint angles
      - updates rep count (using a simple 'stage' state machine: up/down)
      - returns a dict with feedback messages + form score
    """

    def __init__(self):
        self.counter = 0
        self.stage = None  # e.g. "up" / "down"
        self.form_issues = []
        self.form_score = 100

    def reset(self):
        self.counter = 0
        self.stage = None
        self.form_issues = []
        self.form_score = 100

    def get_xy(self, detector, results, landmark, w, h):
        return detector.get_landmark_xy(results, landmark, w, h)


class SquatAnalyzer(ExerciseAnalyzer):
    name = "Squat"

    def compute(self, detector, results, w, h):
        issues = []
        score = 100

        hip = self.get_xy(detector, results, PL.LEFT_HIP, w, h)
        knee = self.get_xy(detector, results, PL.LEFT_KNEE, w, h)
        ankle = self.get_xy(detector, results, PL.LEFT_ANKLE, w, h)
        shoulder = self.get_xy(detector, results, PL.LEFT_SHOULDER, w, h)

        if not all([hip, knee, ankle, shoulder]):
            return {"angles": {}, "issues": ["Body not fully visible"], "score": None}

        knee_angle = calculate_angle(hip, knee, ankle)
        back_angle = calculate_angle(shoulder, hip, knee)

        # Rep counting: knee_angle small = "down" (squatting), large = "up" (standing)
        if knee_angle > 160:
            self.stage = "up"
        if knee_angle < 100 and self.stage == "up":
            self.stage = "down"
            self.counter += 1

        # Form checks
        if knee_angle < 100 and knee_angle > 70:
            pass  # decent depth
        elif self.stage == "down" and knee_angle >= 100:
            issues.append("Go 5cm lower")
            score -= 15

        if back_angle < 45:
            issues.append("Keep your back straighter")
            score -= 20

        return {
            "angles": {"knee_angle": round(knee_angle, 1), "back_angle": round(back_angle, 1)},
            "issues": issues,
            "score": max(score, 0),
            "reps": self.counter,
            "stage": self.stage,
        }


class PushupAnalyzer(ExerciseAnalyzer):
    name = "Push-up"

    def compute(self, detector, results, w, h):
        issues = []
        score = 100

        shoulder = self.get_xy(detector, results, PL.LEFT_SHOULDER, w, h)
        elbow = self.get_xy(detector, results, PL.LEFT_ELBOW, w, h)
        wrist = self.get_xy(detector, results, PL.LEFT_WRIST, w, h)
        hip = self.get_xy(detector, results, PL.LEFT_HIP, w, h)
        ankle = self.get_xy(detector, results, PL.LEFT_ANKLE, w, h)

        if not all([shoulder, elbow, wrist, hip]):
            return {"angles": {}, "issues": ["Body not fully visible"], "score": None}

        elbow_angle = calculate_angle(shoulder, elbow, wrist)
        body_angle = calculate_angle(shoulder, hip, ankle) if ankle else 180

        if elbow_angle > 160:
            self.stage = "up"
        if elbow_angle < 90 and self.stage == "up":
            self.stage = "down"
            self.counter += 1

        if body_angle < 160:
            issues.append("Keep your body in a straight line")
            score -= 20

        return {
            "angles": {"elbow_angle": round(elbow_angle, 1), "body_angle": round(body_angle, 1)},
            "issues": issues,
            "score": max(score, 0),
            "reps": self.counter,
            "stage": self.stage,
        }


class BicepCurlAnalyzer(ExerciseAnalyzer):
    name = "Bicep Curl"

    def compute(self, detector, results, w, h):
        issues = []
        score = 100

        shoulder = self.get_xy(detector, results, PL.LEFT_SHOULDER, w, h)
        elbow = self.get_xy(detector, results, PL.LEFT_ELBOW, w, h)
        wrist = self.get_xy(detector, results, PL.LEFT_WRIST, w, h)
        hip = self.get_xy(detector, results, PL.LEFT_HIP, w, h)

        if not all([shoulder, elbow, wrist, hip]):
            return {"angles": {}, "issues": ["Body not fully visible"], "score": None}

        elbow_angle = calculate_angle(shoulder, elbow, wrist)
        # Elbow should stay near the torso: check shoulder movement (rough proxy)
        torso_angle = calculate_angle(hip, shoulder, elbow)

        if elbow_angle > 150:
            self.stage = "down"
        if elbow_angle < 50 and self.stage == "down":
            self.stage = "up"
            self.counter += 1

        if torso_angle > 40:
            issues.append("Keep elbow close to your body")
            score -= 15

        return {
            "angles": {"elbow_angle": round(elbow_angle, 1), "torso_angle": round(torso_angle, 1)},
            "issues": issues,
            "score": max(score, 0),
            "reps": self.counter,
            "stage": self.stage,
        }


EXERCISES = {
    "squat": SquatAnalyzer,
    "pushup": PushupAnalyzer,
    "curl": BicepCurlAnalyzer,
}
