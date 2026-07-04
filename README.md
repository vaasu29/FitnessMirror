# AI Fitness Mirror (MVP)

A webcam-based AI personal trainer: detects your pose, counts reps, checks
your form against simple biomechanical rules, gives live spoken + on-screen
feedback, and tracks your workout history over time.

**100% free and offline.** No API keys, no cloud services, no subscriptions.
Everything runs locally on your machine using open-source libraries.

## What it does (this version)

- Real-time pose detection via webcam (MediaPipe Pose - 33 body landmarks)
- Skeleton overlay drawn on the video feed
- Supports 3 exercises: **squat**, **push-up**, **bicep curl**
- Automatic rep counting (state machine on joint angles)
- Rule-based form scoring + feedback (e.g. "Go 5cm lower", "Keep your back straighter")
- Optional offline voice coaching (pyttsx3 - no internet required)
- Calorie estimate (rough, demo-level)
- Workout history saved to a local SQLite database
- Standalone charts dashboard (reps, form score, duration, exercise mix over time)

This matches "Version 1" through the early "Version 5" ideas from the project
plan: pose + angles + rep counting + real-time coaching + basic analytics.
Steps like exercise auto-recognition (ML classifier), 3D visualization, fatigue
detection, and an LLM-based coach are natural next additions once this base
is working (see "Next steps" below).

## 1. Requirements

- A computer with a webcam
- Python 3.9-3.11 (MediaPipe doesn't yet support the newest Python releases,
  so if you're on 3.12+, install 3.11 alongside it)
- macOS, Windows, or Linux

## 2. Setup (all free)

```bash
# 1. Create a virtual environment (recommended)
python3 -m venv venv

# 2. Activate it
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies (all free, open-source)
pip install -r requirements.txt
```

If `mediapipe` fails to install, it usually means your Python version is too
new. Install Python 3.11 from python.org (free) and recreate the venv with it.

## 3. Run it

```bash
python main.py --exercise squat
```

Other exercises:
```bash
python main.py --exercise pushup
python main.py --exercise curl
```

**While the window is open:**
- `1` / `2` / `3` — switch between squat / push-up / curl live
- `r` — reset the current session's rep counter
- `q` — quit and save the session to your workout history

If you don't want spoken feedback (e.g. on a shared computer), add `--no-voice`:
```bash
python main.py --exercise squat --no-voice
```

If you have multiple cameras and the wrong one opens, try:
```bash
python main.py --exercise squat --camera 1
```

## 4. View your progress

After you've logged at least one session:
```bash
python dashboard.py
```
This opens a chart window showing reps, form score, duration, and exercise
mix across your saved sessions (stored in `data/workouts.db`).

## Tips for good detection

- Stand 2-3 meters back so your full body is in frame
- Face the camera at a slight angle (side-on works well for squats/push-ups)
- Good, even lighting helps a lot
- Wear clothing that contrasts with the background

## Project structure

```
FitnessMirror/
  camera + pose detection   -> pose.py
  angle math                -> angle.py
  exercise logic & reps     -> exercise.py
  voice/text feedback       -> feedback.py
  workout history (SQLite)  -> storage.py
  progress charts           -> dashboard.py
  entry point                -> main.py
  data/workouts.db          -> created automatically on first save
```

## Next steps (from the roadmap, all still free to build)

- **Exercise auto-recognition**: train a small classifier (scikit-learn
  RandomForest or an LSTM) on landmark sequences instead of picking the
  exercise manually. Needs you to record a bit of labeled sample data.
- **Fatigue detection**: watch for slowing tempo / shrinking range of motion
  across reps.
- **Symmetry checks**: compare left vs right joint angles (e.g. curl ROM).
- **3D skeleton view**: MediaPipe already returns z-coordinates; plot them
  with matplotlib's 3D axes or a small OpenGL/Three.js viewer.
- **AI coach summaries**: after a session, send your stats to an LLM API to
  generate a written summary and next-session suggestions (this step does
  have a small API cost if you use a paid model — everything above it does not).

## Web App: upload videos or go live in the browser

There's now a full web app (`app.py`) with two modes, so anyone can use it
without installing Python:

- **Upload a video** — they upload an mp4/mov, the app analyzes it frame by
  frame and returns an annotated video (skeleton + live score overlay) plus a
  timestamped list of what went wrong ("12.4s — Go 5cm lower").
- **Live webcam** — runs entirely in their browser via WebRTC (`streamlit-webrtc`).
  Their video never leaves their machine except to be streamed to your server
  for processing and streamed straight back — nothing is saved.

### Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
Opens at `http://localhost:8501`.

### Deploy it for free so other people can use it

**Option A — Streamlit Community Cloud (easiest, free)**
1. Push this whole `FitnessMirror/` folder to a public GitHub repo.
2. Go to https://share.streamlit.io, sign in with GitHub.
3. Click "New app", pick your repo, set the main file to `app.py`.
4. Deploy. You'll get a public URL like `yourapp.streamlit.app`.

**Option B — Hugging Face Spaces (also free)**
1. Create a new Space at https://huggingface.co/spaces, choose the
   **Streamlit** SDK.
2. Upload the contents of `FitnessMirror/` (or push via git).
3. It builds automatically and gives you a public URL.

Both platforms are free for this kind of low-traffic app. Live webcam mode
needs a STUN server for the WebRTC connection to establish across networks —
`app.py` is already configured with Google's public STUN server, so this
works out of the box on both platforms.

**Note on live mode at scale:** the free tiers of both platforms have limited
CPU, and pose estimation is CPU-intensive. Fine for demoing to a handful of
people at once; if you get real traffic, you'd want a paid tier or a small
cloud VM (e.g. a $5-6/month box) instead of the free tier.

## Troubleshooting

- **Black window / no camera feed**: check OS camera permissions for your
  terminal/IDE, and try `--camera 1` if you have more than one camera.
- **No sound for voice coaching**: some systems don't have a default TTS
  voice installed; the app will silently continue with text-only feedback.
- **Low FPS**: close other apps using the camera/GPU, or reduce your camera
  resolution.
