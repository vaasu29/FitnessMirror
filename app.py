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
import base64

import av
import cv2
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase, RTCConfiguration

from pose import PoseDetector
from exercise import EXERCISES
from video_processor import ExerciseSession

st.set_page_config(page_title="AI Fitness Mirror", page_icon="🏋️", layout="wide")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Manrope:wght@600;700;800&display=swap');

:root {
    --primary: #4be277;
    --primary-container: #22c55e;
    --on-primary: #003915;
    --background: #0b1326;
    --surface: #0b1326;
    --surface-container: #171f33;
    --surface-container-high: #222a3d;
    --surface-variant: #2d3449;
    --on-surface: #dae2fd;
    --on-surface-variant: #bccbb9;
    --error: #ffb4ab;
    --outline-variant: #3d4a3d;
}

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: var(--background);
    color: var(--on-surface);
}

section[data-testid="stSidebar"] {
    background: rgba(23, 31, 51, 0.6);
    border-right: 1px solid var(--outline-variant);
}

section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] .stMarkdown p {
    color: var(--on-surface);
}

/* Card-style containers */
.fm-card {
    background: rgba(23, 31, 51, 0.6);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}

.fm-card-accent {
    border: 1px solid rgba(74,225,118,0.3);
    box-shadow: 0 0 30px rgba(74,225,118,0.05);
}

.fm-label {
    font-family: 'Manrope', sans-serif;
    font-size: 12px;
    letter-spacing: 0.1em;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--on-surface-variant);
    margin-bottom: 8px;
}

.fm-big-number {
    font-family: 'Manrope', sans-serif;
    font-size: 56px;
    font-weight: 800;
    color: var(--on-surface);
    text-align: center;
    line-height: 1;
    text-shadow: 0 0 15px rgba(255,255,255,0.15);
}

.fm-status-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    font-size: 14px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

.fm-status-row span:last-child {
    font-family: 'Manrope', monospace;
    color: var(--on-surface);
}

.fm-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(23,31,51,0.8);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    padding: 6px 12px;
    font-family: 'Manrope', monospace;
    font-size: 13px;
    color: var(--on-surface);
}

.fm-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--primary);
    box-shadow: 0 0 8px var(--primary);
    display: inline-block;
    animation: fm-pulse 1.5s infinite;
}

@keyframes fm-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.fm-mistake-thumb {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(255,180,171,0.5);
    position: relative;
}

.fm-mistake-thumb.ok {
    border: 1px solid rgba(74,225,118,0.4);
}

.fm-mistake-label {
    position: absolute;
    bottom: 4px;
    right: 4px;
    background: var(--error);
    color: #690005;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
}

.fm-mistake-label.ok {
    background: var(--primary);
    color: var(--on-primary);
}

/* Buttons */
div.stButton > button, div.stDownloadButton > button {
    background: var(--primary);
    color: var(--on-primary);
    border: none;
    border-radius: 6px;
    font-weight: 600;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background: #6bff8f;
    color: var(--on-primary);
}

/* Sidebar nav: secondary (inactive) buttons look like plain nav rows */
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: transparent !important;
    color: var(--on-surface-variant) !important;
    border: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.06) !important;
    color: var(--on-surface) !important;
}
section[data-testid="stSidebar"] button[kind="primary"] {
    background: var(--primary) !important;
    color: var(--on-primary) !important;
    border: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 700 !important;
    box-shadow: 0 0 12px rgba(74,225,118,0.3);
}

/* Header action buttons (Download / Upload New Video style) */
.fm-header-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    border-radius: 6px;
    font-family: 'Manrope', sans-serif;
    font-weight: 700;
    font-size: 13px;
    text-decoration: none;
}
.fm-header-btn.dark {
    background: rgba(11,19,38,0.5);
    border: 1px solid rgba(255,255,255,0.1);
    color: var(--on-surface);
}
.fm-header-btn.green {
    background: var(--primary);
    color: var(--on-primary);
}

/* Hero background behind the video panel */
.fm-hero-bg {
    position: relative;
    border-radius: 12px;
    overflow: hidden;
    background-size: cover;
    background-position: center;
    min-height: 380px;
}
.fm-hero-bg::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(11,19,38,0.95), rgba(11,19,38,0.2));
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

EXERCISE_LABELS = {"auto": "🔍 Auto-detect", "squat": "Squat", "pushup": "Push-up", "curl": "Bicep Curl"}


def sidebar_controls():
    if "mode" not in st.session_state:
        st.session_state.mode = "Upload a video"
    if "exercise_key" not in st.session_state:
        st.session_state.exercise_key = "auto"

    st.sidebar.markdown(
        """
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;">
            <div style="width:40px;height:40px;border-radius:12px;background:var(--primary-container);
                        display:flex;align-items:center;justify-content:center;font-size:20px;">🏋️</div>
            <div>
                <div style="font-family:'Manrope',sans-serif;font-weight:800;font-size:18px;color:var(--primary);">
                    AI Fitness Mirror
                </div>
                <div class="fm-label" style="margin:0;">Elite Performance Tracking</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Mode nav (Video Upload / Live Webcam) ---
    nav_items = [("Upload a video", "☁️ Video Upload"), ("Live webcam", "🎥 Live Webcam")]
    for key, label in nav_items:
        active = st.session_state.mode == key
        if st.sidebar.button(label, key=f"nav_{key}", use_container_width=True,
                              type="primary" if active else "secondary"):
            st.session_state.mode = key
            st.rerun()

    st.sidebar.markdown('<div class="fm-label" style="margin-top:20px;">Exercises</div>', unsafe_allow_html=True)

    # --- Exercise nav ---
    exercise_items = [("auto", "🔍 Auto-detect"), ("squat", "🏋️ Squats"), ("pushup", "🏃 Push-ups"), ("curl", "🤸 Bicep Curls")]
    for key, label in exercise_items:
        active = st.session_state.exercise_key == key
        if st.sidebar.button(label, key=f"ex_{key}", use_container_width=True,
                              type="primary" if active else "secondary"):
            st.session_state.exercise_key = key
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Tip: stand far enough back that your full body is in frame, "
        "side-on works best for squats and push-ups."
    )
    st.sidebar.button("Start Session", use_container_width=True, type="primary")

    return st.session_state.mode, st.session_state.exercise_key


# ---------------------------------------------------------------------------
# Mode 1: Upload a video
# ---------------------------------------------------------------------------
def run_upload_mode(exercise_key):
    col_title, col_actions = st.columns([2, 1])
    with col_title:
        st.markdown(
            '<h1 style="font-family:\'Manrope\',sans-serif;font-weight:800;">📤 Upload a video for analysis</h1>',
            unsafe_allow_html=True,
        )
        st.caption("Upload a video (mp4, mov, avi)")
    with col_actions:
        st.markdown(
            """
            <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px;">
                <span class="fm-header-btn dark">⬇ Download Analysis Report</span>
                <span class="fm-header-btn green">+ Upload New Video</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    uploaded = st.file_uploader("Upload a video (mp4, mov, avi)", type=["mp4", "mov", "avi", "mkv"],
                                 label_visibility="collapsed")

    if uploaded is None:
        st.markdown(
            """
            <div class="fm-hero-bg" style="background-image:url('https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1200&q=80');">
                <div style="position:relative;z-index:1;height:380px;display:flex;align-items:flex-end;padding:24px;">
                    <span style="font-family:'Manrope',sans-serif;color:var(--on-surface-variant);">
                        Upload a workout video to get rep count, form score, and a mistake timeline.
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
    initial_key = exercise_key if exercise_key != "auto" else "squat"
    analyzer = EXERCISES[initial_key]()
    session = ExerciseSession(detector, analyzer, exercise_key)

    progress = st.progress(0, text="Analyzing video...")
    frame_idx = 0
    thumbnails = []  # list of (time_seconds, label, is_error, jpg_bytes)
    last_issue_seen = None
    last_thumb_time = -999

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        video_time = frame_idx / fps
        annotated, result = session.process_frame(frame, video_time_seconds=video_time)
        writer.write(annotated)

        issues = result.get("issues", [])
        current_issue = issues[0] if issues else None

        # Capture a thumbnail whenever a new mistake type appears, or
        # periodically (every ~4s) when form is good, to mirror the design's
        # mixed timeline of errors + "Optimal" snapshots.
        should_capture = False
        label, is_error = None, False
        if current_issue and current_issue != last_issue_seen:
            should_capture = True
            label, is_error = current_issue, True
        elif not current_issue and result.get("score") is not None and video_time - last_thumb_time > 4:
            should_capture = True
            label, is_error = "Optimal", False

        if should_capture and len(thumbnails) < 10:
            small = cv2.resize(annotated, (200, 120))
            ok_enc, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok_enc:
                thumbnails.append((round(video_time, 1), label, is_error, buf.tobytes()))
            last_thumb_time = video_time

        last_issue_seen = current_issue

        frame_idx += 1
        if total_frames > 0 and frame_idx % 5 == 0:
            progress.progress(min(frame_idx / total_frames, 1.0), text="Analyzing video...")

    cap.release()
    writer.release()
    detector.close()
    progress.progress(1.0, text="Done!")

    summary = session.summary()

    st.success("Analysis complete!")
    col1, col2 = st.columns([8, 4])

    with col1:
        st.markdown('<div class="fm-card">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="display:flex;gap:12px;margin-bottom:12px;">
                <span class="fm-pill"><span class="fm-dot"></span>ANALYZED</span>
                <span class="fm-pill">{uploaded.name.upper()}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.video(out_path)
        st.markdown('</div>', unsafe_allow_html=True)

        with open(out_path, "rb") as f:
            st.download_button("⬇️ Download annotated video", f, file_name="fitness_mirror_annotated.mp4")

        # Mistake / highlight timeline (real thumbnails pulled from the video)
        st.markdown('<div class="fm-card">', unsafe_allow_html=True)
        st.markdown('<div class="fm-label">Mistake Timeline</div>', unsafe_allow_html=True)
        if thumbnails:
            cols = st.columns(len(thumbnails))
            for c, (t, label, is_error, jpg_bytes) in zip(cols, thumbnails):
                with c:
                    b64 = base64.b64encode(jpg_bytes).decode()
                    css_class = "fm-mistake-thumb" if is_error else "fm-mistake-thumb ok"
                    label_class = "fm-mistake-label" if is_error else "fm-mistake-label ok"
                    st.markdown(
                        f"""
                        <div class="{css_class}">
                            <img src="data:image/jpeg;base64,{b64}" style="width:100%;display:block;">
                            <div class="{label_class}">{label}</div>
                        </div>
                        <div style="text-align:center;font-size:11px;color:var(--on-surface-variant);margin-top:4px;">{t}s</div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.caption("No timeline snapshots captured for this session.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # Rep count card
        st.markdown(
            f"""
            <div class="fm-card" style="text-align:center;">
                <div class="fm-label">Rep Count</div>
                <div class="fm-big-number">{summary['reps']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Form score circular gauge
        score = summary["avg_form_score"]
        circumference = 282.7
        offset = circumference * (1 - score / 100)
        gauge_color = "#4be277" if score >= 80 else "#ffb347" if score >= 50 else "#ffb4ab"
        st.markdown(
            f"""
            <div class="fm-card fm-card-accent" style="text-align:center;">
                <div class="fm-label">Form Score</div>
                <svg width="140" height="140" viewBox="0 0 100 100" style="transform:rotate(-90deg);">
                    <circle cx="50" cy="50" r="45" fill="transparent" stroke="#2d3449" stroke-width="6"></circle>
                    <circle cx="50" cy="50" r="45" fill="transparent" stroke="{gauge_color}"
                            stroke-width="6" stroke-dasharray="{circumference}"
                            stroke-dashoffset="{offset}" stroke-linecap="round"
                            style="filter:drop-shadow(0 0 8px {gauge_color});"></circle>
                </svg>
                <div style="margin-top:-90px;font-family:'Manrope',monospace;font-size:28px;font-weight:700;color:{gauge_color};">
                    {score:.0f}%
                </div>
                <div style="height:40px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Status / stats card
        mistakes_html = "".join(
            f'<div class="fm-status-row"><span>{t}s</span><span>{issue}</span></div>'
            for t, issue in summary["mistakes"][:6]
        ) or '<div class="fm-status-row"><span>No issues detected 🎉</span><span></span></div>'

        st.markdown(
            f"""
            <div class="fm-card">
                <div class="fm-label">Session Summary</div>
                <div class="fm-status-row"><span>Exercise</span><span>{summary['exercise']}</span></div>
                <div class="fm-status-row"><span>Duration</span><span>{summary['duration_seconds']}s</span></div>
                <div style="margin-top:16px;" class="fm-label">What Was Wrong</div>
                {mistakes_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


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
            initial_key = exercise_key if exercise_key != "auto" else "squat"
            self.analyzer = EXERCISES[initial_key]()
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