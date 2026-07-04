"""
app.py
AI Fitness Mirror - Web App

Two modes:
  1. Upload a video -> get back an annotated video + a mistakes report
  2. Live webcam (runs in the visitor's browser via WebRTC) -> real-time overlay

Run locally:
    streamlit run app.py

Deploy for free:
    - Streamlit Community Cloud (share.streamlit.io) - push this folder to a
      public GitHub repo, connect it, done.
    - Hugging Face Spaces (choose "Streamlit" SDK) - also free.
"""
import os
import tempfile
import time

import av
import cv2
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase, RTCConfiguration

from pose import PoseDetector
from exercise import EXERCISES
from video_processor import ExerciseSession

st.set_page_config(page_title="AI Fitness Mirror", page_icon="🏋️", layout="wide")

EXERCISE_LABELS = {"squat": "Squat", "pushup": "Push-up", "curl": "Bicep Curl"}


def sidebar_controls():
    st.sidebar.title("🏋️ AI Fitness Mirror")
    mode = st.sidebar.radio("Mode", ["Upload a video", "Live webcam"])
    exercise_key = st.sidebar.selectbox(
        "Exercise", list(EXERCISE_LABELS.keys()), format_func=lambda k: EXERCISE_LABELS[k]
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Tip: stand far enough back that your full body is in frame, "
        "side-on works best for squats and push-ups."
    )
    return mode, exercise_key


# ---------------------------------------------------------------------------
# Mode 1: Upload a video
# ---------------------------------------------------------------------------
def run_upload_mode(exercise_key):
    st.header("📤 Upload a video for analysis")
    uploaded = st.file_uploader("Upload a video (mp4, mov, avi)", type=["mp4", "mov", "avi", "mkv"])

    if uploaded is None:
        st.info("Upload a workout video to get rep count, form score, and a mistake timeline.")
        return

    # Persist the upload to a temp file so OpenCV can read it
    in_path = os.path.join(tempfile.gettempdir(), f"fm_in_{int(time.time())}_{uploaded.name}")
    with open(in_path, "wb") as f:
        f.write(uploaded.read())

    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        st.error("Could not read this video file. Try a different format (mp4 works best).")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = os.path.join(tempfile.gettempdir(), f"fm_out_{int(time.time())}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    detector = PoseDetector()
    analyzer = EXERCISES[exercise_key]()
    session = ExerciseSession(detector, analyzer, exercise_key)

    progress = st.progress(0, text="Analyzing video...")
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        video_time = frame_idx / fps
        annotated, _ = session.process_frame(frame, video_time_seconds=video_time)
        writer.write(annotated)

        frame_idx += 1
        if total_frames > 0 and frame_idx % 5 == 0:
            progress.progress(min(frame_idx / total_frames, 1.0), text="Analyzing video...")

    cap.release()
    writer.release()
    detector.close()
    progress.progress(1.0, text="Done!")

    summary = session.summary()

    st.success("Analysis complete!")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Annotated video")
        st.video(out_path)
        with open(out_path, "rb") as f:
            st.download_button("⬇️ Download annotated video", f, file_name="fitness_mirror_annotated.mp4")

    with col2:
        st.subheader("Session summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Reps", summary["reps"])
        m2.metric("Avg Form Score", f'{summary["avg_form_score"]}%')
        m3.metric("Duration", f'{summary["duration_seconds"]}s')

        st.subheader("What was wrong (and when)")
        if summary["mistakes"]:
            for t, issue in summary["mistakes"]:
                st.write(f"⏱️ **{t}s** — {issue}")
        else:
            st.write("No form issues detected — nice work! 🎉")


# ---------------------------------------------------------------------------
# Mode 2: Live webcam via WebRTC (runs in the visitor's browser)
# ---------------------------------------------------------------------------
class LiveProcessor(VideoProcessorBase):
    def __init__(self):
        self.detector = PoseDetector()
        self.exercise_key = "squat"
        self.analyzer = EXERCISES[self.exercise_key]()
        self.session = ExerciseSession(self.detector, self.analyzer, self.exercise_key)
        self.latest_result = {}

    def set_exercise(self, exercise_key):
        if exercise_key != self.exercise_key:
            self.exercise_key = exercise_key
            self.analyzer = EXERCISES[exercise_key]()
            self.session = ExerciseSession(self.detector, self.analyzer, exercise_key)

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        annotated, result = self.session.process_frame(img)
        self.latest_result = result
        return av.VideoFrame.from_ndarray(annotated, format="bgr24")


def run_live_mode(exercise_key):
    st.header("🎥 Live webcam")
    st.caption(
        "This runs the analysis on video streamed directly from your browser's webcam. "
        "Nothing is uploaded or stored — it's processed live and discarded."
    )

    ctx = webrtc_streamer(
        key="fitness-mirror-live",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=LiveProcessor,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
    )

    if ctx.video_processor:
        ctx.video_processor.set_exercise(exercise_key)

    st.markdown("---")
    if ctx.video_processor and st.button("Show session summary"):
        summary = ctx.video_processor.session.summary()
        c1, c2, c3 = st.columns(3)
        c1.metric("Reps", summary["reps"])
        c2.metric("Avg Form Score", f'{summary["avg_form_score"]}%')
        c3.metric("Duration", f'{summary["duration_seconds"]}s')
        st.subheader("What was wrong (and when)")
        if summary["mistakes"]:
            for t, issue in summary["mistakes"]:
                st.write(f"⏱️ **{t}s** — {issue}")
        else:
            st.write("No form issues logged yet.")


# ---------------------------------------------------------------------------
def main():
    mode, exercise_key = sidebar_controls()
    if mode == "Upload a video":
        run_upload_mode(exercise_key)
    else:
        run_live_mode(exercise_key)


if __name__ == "__main__":
    main()
