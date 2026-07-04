"""
main.py
AI Fitness Mirror - MVP

Run:
    python main.py --exercise squat
    python main.py --exercise pushup
    python main.py --exercise curl

Controls (while the window is focused):
    q       - quit and save workout to history
    r       - reset rep counter / form stats for current session
    1/2/3   - switch exercise live (squat / pushup / curl)

Press 'q' to exit. Requires a webcam.
"""
import argparse
import time
import cv2

from pose import PoseDetector
from exercise import EXERCISES
from feedback import Coach
import storage

WINDOW_NAME = "AI FITNESS MIRROR"

KEY_TO_EXERCISE = {ord("1"): "squat", ord("2"): "pushup", ord("3"): "curl"}

# Very rough calories-per-rep estimates, just for demo purposes (Version 1 MVP,
# not medically accurate - could be replaced with a proper MET-based formula later).
CALORIES_PER_REP = {"squat": 0.32, "pushup": 0.29, "curl": 0.15}


def draw_dashboard(frame, exercise_name, result, calories, elapsed_seconds):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    panel_w = 300
    cv2.rectangle(overlay, (0, 0), (panel_w, h), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    y = 40
    cv2.putText(frame, "AI FITNESS MIRROR", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
    y += 40
    cv2.putText(frame, f"{exercise_name}", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    y += 45

    reps = result.get("reps", 0)
    cv2.putText(frame, f"Reps: {reps}", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    y += 40

    score = result.get("score")
    score_txt = f"Form Score: {score}%" if score is not None else "Form Score: --"
    color = (0, 255, 0) if (score or 0) >= 80 else (0, 165, 255) if (score or 0) >= 50 else (0, 0, 255)
    cv2.putText(frame, score_txt, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    y += 35

    cv2.putText(frame, f"Calories: {calories:.1f}", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y += 30
    cv2.putText(frame, f"Time: {int(elapsed_seconds)}s", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    y += 40

    issues = result.get("issues", [])
    if issues:
        for issue in issues[:3]:
            cv2.putText(frame, f"! {issue}", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2)
            y += 25
    elif score is not None:
        cv2.putText(frame, "Good form!", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        y += 25

    y += 15
    cv2.putText(frame, "[1] Squat  [2] Push-up  [3] Curl", (15, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    cv2.putText(frame, "[r] Reset   [q] Quit + Save", (15, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    return frame


def run(exercise_key, use_voice, camera_index):
    detector = PoseDetector()
    coach = Coach(use_voice=use_voice)
    analyzer = EXERCISES[exercise_key]()

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Could not open webcam. Check camera_index / permissions.")
        return

    start_time = time.time()
    score_samples = []

    print("AI Fitness Mirror running. Press 'q' in the video window to quit and save.")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Failed to read frame from webcam.")
            break

        frame = cv2.flip(frame, 1)  # mirror view feels natural
        h, w = frame.shape[:2]

        results = detector.process(frame)
        frame = detector.draw(frame, results)

        result = analyzer.compute(detector, results, w, h)
        if result.get("score") is not None:
            score_samples.append(result["score"])
            coach.process(result.get("issues", []), result.get("score"))

        elapsed = time.time() - start_time
        calories = analyzer.counter * CALORIES_PER_REP.get(exercise_key, 0.2)

        frame = draw_dashboard(frame, analyzer.name, result, calories, elapsed)
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            analyzer.reset()
            score_samples = []
            start_time = time.time()
        elif key in KEY_TO_EXERCISE:
            exercise_key = KEY_TO_EXERCISE[key]
            analyzer = EXERCISES[exercise_key]()
            score_samples = []
            start_time = time.time()

    duration = time.time() - start_time
    avg_score = sum(score_samples) / len(score_samples) if score_samples else 0
    storage.save_workout(analyzer.name, analyzer.counter, avg_score, duration)
    print(f"Saved workout: {analyzer.name}, reps={analyzer.counter}, "
          f"avg_form={avg_score:.1f}%, duration={duration:.1f}s")

    cap.release()
    cv2.destroyAllWindows()
    detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Fitness Mirror")
    parser.add_argument("--exercise", choices=list(EXERCISES.keys()), default="squat")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice coaching")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0)")
    args = parser.parse_args()

    run(args.exercise, use_voice=not args.no_voice, camera_index=args.camera)
