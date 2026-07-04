"""
video_processor.py
Shared logic for drawing the skeleton + form dashboard onto a single frame.
Used by both:
  - app.py's "upload a video" mode (loops over a file with cv2.VideoCapture)
  - app.py's "live webcam" mode (streamlit-webrtc calls this per browser frame)

Keeping this in one place means the upload and live modes always give
identical scoring/feedback logic.
"""
import cv2
import time


def draw_overlay(frame, exercise_name, result, calories, elapsed_seconds):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    panel_w = min(300, w // 2)
    cv2.rectangle(overlay, (0, 0), (panel_w, h), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    y = 35
    cv2.putText(frame, "AI FITNESS MIRROR", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    y += 32
    cv2.putText(frame, exercise_name, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y += 35

    reps = result.get("reps", 0)
    cv2.putText(frame, f"Reps: {reps}", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
    y += 32

    score = result.get("score")
    score_txt = f"Form Score: {score}%" if score is not None else "Form Score: --"
    color = (0, 255, 0) if (score or 0) >= 80 else (0, 165, 255) if (score or 0) >= 50 else (0, 0, 255)
    cv2.putText(frame, score_txt, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    y += 28

    cv2.putText(frame, f"Calories: {calories:.1f}", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    y += 24
    cv2.putText(frame, f"Time: {int(elapsed_seconds)}s", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    y += 32

    issues = result.get("issues", [])
    if issues:
        for issue in issues[:3]:
            cv2.putText(frame, f"! {issue}", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
            y += 22
    elif score is not None:
        cv2.putText(frame, "Good form!", (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame


class ExerciseSession:
    """
    Wraps a PoseDetector + ExerciseAnalyzer and keeps running state
    (start time, calorie estimate, timestamped mistake log) across frames.
    Used identically for a live webcam stream and for looping over an
    uploaded video's frames.
    """

    CALORIES_PER_REP = {"squat": 0.32, "pushup": 0.29, "curl": 0.15}

    def __init__(self, detector, analyzer, exercise_key):
        self.detector = detector
        self.analyzer = analyzer
        self.exercise_key = exercise_key
        self.start_time = time.time()
        self.score_samples = []
        self.mistake_log = []  # list of (timestamp_seconds, issue_text)

    def process_frame(self, frame, video_time_seconds=None):
        """
        video_time_seconds: pass the video's own playback timestamp when
        processing an uploaded file (so the mistake log matches the video's
        clock, not wall-clock time). Leave None for live webcam (uses wall clock).
        """
        h, w = frame.shape[:2]
        results = self.detector.process(frame)
        frame = self.detector.draw(frame, results)

        result = self.analyzer.compute(self.detector, results, w, h)

        t = video_time_seconds if video_time_seconds is not None else (time.time() - self.start_time)

        if result.get("score") is not None:
            self.score_samples.append(result["score"])
            for issue in result.get("issues", []):
                self.mistake_log.append((round(t, 1), issue))

        elapsed = video_time_seconds if video_time_seconds is not None else (time.time() - self.start_time)
        calories = self.analyzer.counter * self.CALORIES_PER_REP.get(self.exercise_key, 0.2)

        frame = draw_overlay(frame, self.analyzer.name, result, calories, elapsed)
        return frame, result

    def summary(self):
        avg_score = sum(self.score_samples) / len(self.score_samples) if self.score_samples else 0
        # De-duplicate mistakes that repeat back-to-back within 1.5s (same issue lingering)
        deduped = []
        for t, issue in self.mistake_log:
            if deduped and deduped[-1][1] == issue and t - deduped[-1][0] < 1.5:
                continue
            deduped.append((t, issue))
        return {
            "exercise": self.analyzer.name,
            "reps": self.analyzer.counter,
            "avg_form_score": round(avg_score, 1),
            "duration_seconds": round(time.time() - self.start_time, 1),
            "mistakes": deduped,
        }
