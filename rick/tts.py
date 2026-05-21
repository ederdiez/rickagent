import threading
import sys

from .logging_setup import log
from .system_utils import run_cmd, _has

try:
    import pyttsx3
    _TTS_OK = True
except ImportError:
    _TTS_OK = False
    print("⚠️  pyttsx3 no instalado. pip install pyttsx3 — TTS desactivado.")


class TTS:
    def __init__(self, cfg: dict):
        self.cfg     = cfg
        self.engine  = None
        self._lock   = threading.Lock()
        if _TTS_OK and not cfg["no_voice"]:
            self._init_engine()

    def _init_engine(self):
        try:
            e = pyttsx3.init()
            e.setProperty("rate", self.cfg["voice_rate"])
            e.setProperty("volume", self.cfg["voice_volume"])
            voices = e.getProperty("voices")
            lang   = self.cfg["language"]
            for v in voices:
                if lang in v.id.lower() or "spanish" in v.name.lower():
                    e.setProperty("voice", v.id)
                    break
            self.engine = e
        except Exception as ex:
            log.warning(f"pyttsx3 init failed: {ex}. TTS desactivado.")

    def say(self, text: str):
        print(f"\033[0;32m🔊 RICK: {text}\033[0m")
        if self.cfg["no_voice"]:
            return
        if self.engine:
            with self._lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                    return
                except Exception as e:
                    log.debug(f"pyttsx3 say error: {e}")
        # Fallback espeak
        if _has("espeak-ng"):
            run_cmd(["espeak-ng", "-v", f"{self.cfg['language']}+f3", "-s", "150", text])
        elif _has("espeak"):
            run_cmd(["espeak", "-v", self.cfg["language"], text])
