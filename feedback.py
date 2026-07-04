"""
feedback.py
Turns form-check results into spoken/text coaching cues.
Voice is optional (pyttsx3, fully offline & free) - if it's not installed
or fails to init (e.g. no audio device), we silently fall back to text-only.
"""
import time

try:
    import pyttsx3
    _VOICE_AVAILABLE = True
except Exception:
    _VOICE_AVAILABLE = False


class Coach:
    def __init__(self, use_voice=True, cooldown_seconds=2.5):
        self.use_voice = use_voice and _VOICE_AVAILABLE
        self.cooldown = cooldown_seconds
        self._last_said = {}
        self.engine = None
        if self.use_voice:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 170)
            except Exception:
                self.use_voice = False

    def say(self, message):
        """Speak a message if voice is available, respecting a per-message cooldown
        so it doesn't repeat every single frame."""
        now = time.time()
        last = self._last_said.get(message, 0)
        if now - last < self.cooldown:
            return
        self._last_said[message] = now

        if self.use_voice and self.engine is not None:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception:
                pass  # fail silently, text feedback still shows on screen

    def process(self, issues, score):
        """Call once per frame with the current issue list; speaks the top issue,
        or praises good form if there are none."""
        if issues:
            self.say(issues[0])
        elif score is not None and score >= 95:
            self.say("Great rep!")
