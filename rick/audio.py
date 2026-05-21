import numpy as np
import sounddevice as sd

from .logging_setup import log

try:
    import whisper
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False
    print("⚠️  openai-whisper no instalado. pip install openai-whisper")


def _rms_db(chunk: np.ndarray) -> float:
    rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
    return 20.0 * np.log10(rms + 1e-9)


class VADRecorder:
    """
    Graba voz con detección de actividad (VAD) basada en energía con histéresis.
    Incluye pre-buffer para no perder el inicio del habla.
    Chunks pequeños (30 ms) y `latency='low'` para cortar rápido al callar.
    """
    CHUNK_MS = 30
    THRESH_MIN = 22.0
    THRESH_MAX = 50.0
    NOISE_MARGIN_DB = 15.0

    def __init__(self, cfg: dict):
        self.sr       = cfg["sample_rate"]
        self.channels = cfg["channels"]
        self.device   = cfg["mic_device"]
        self.thresh   = float(cfg["silence_db"])
        self.hold_ms  = cfg["vad_hold_ms"]
        self.prebuf_ms= cfg["vad_prebuf_ms"]
        self.max_s    = cfg["max_record_s"]
        self.min_ms   = cfg["min_speech_ms"]
        self.chunk_n  = int(self.sr * self.CHUNK_MS / 1000)

    def calibrate(self, duration_s: float = 0.7) -> None:
        """Mide ruido ambiente y fija el umbral por encima de él."""
        n_chunks = max(8, int(duration_s * 1000 / self.CHUNK_MS))
        levels: list[float] = []
        try:
            with sd.InputStream(
                device=self.device,
                samplerate=self.sr,
                channels=self.channels,
                dtype="int16",
                blocksize=self.chunk_n,
                latency="low",
            ) as stream:
                # descarta primeros chunks (transitorio del arranque del stream)
                for _ in range(3):
                    stream.read(self.chunk_n)
                for _ in range(n_chunks):
                    chunk, _ = stream.read(self.chunk_n)
                    levels.append(_rms_db(chunk))
        except Exception as e:
            log.warning(f"VAD: calibración fallida ({e}); umbral={self.thresh:.1f}")
            return

        if not levels:
            return
        noise = sum(levels) / len(levels)
        new_thresh = noise + self.NOISE_MARGIN_DB
        new_thresh = min(max(new_thresh, self.THRESH_MIN), self.THRESH_MAX)
        self.thresh = max(self.thresh, new_thresh)
        log.info(f"VAD calibrado: ruido≈{noise:.1f} dB → umbral={self.thresh:.1f} dB")

    def record(self) -> np.ndarray | None:
        chunk_ms   = self.CHUNK_MS
        chunk_n    = self.chunk_n
        prebuf_n   = max(1, self.prebuf_ms // chunk_ms)
        hold_n     = max(2, self.hold_ms // chunk_ms)
        max_chunks = int(self.max_s * 1000 / chunk_ms)
        min_chunks = max(1, self.min_ms // chunk_ms)

        ring:    list[np.ndarray] = []   # pre-buffer circular
        speech:  list[np.ndarray] = []
        silence_count = 0
        speaking = False

        try:
            with sd.InputStream(
                device=self.device,
                samplerate=self.sr,
                channels=self.channels,
                dtype="int16",
                blocksize=chunk_n,
                latency="low",
            ) as stream:
                for _ in range(max_chunks):
                    chunk, _ = stream.read(chunk_n)
                    db = _rms_db(chunk)

                    if db > self.thresh:
                        if not speaking:
                            speech.extend(ring[-prebuf_n:])
                            speaking = True
                        silence_count = 0
                        speech.append(chunk.copy())
                    else:
                        if speaking:
                            speech.append(chunk.copy())
                            silence_count += 1
                            if silence_count >= hold_n:
                                break
                        else:
                            ring.append(chunk.copy())
                            if len(ring) > prebuf_n * 2:
                                ring.pop(0)
        except sd.PortAudioError as e:
            log.error(f"Error de audio: {e}")
            return None

        if not speaking or len(speech) < min_chunks:
            return None

        # recorta cola de silencio (deja un chunk como margen natural)
        if silence_count > 1:
            speech = speech[:-(silence_count - 1)]

        audio = np.concatenate(speech).flatten()
        return audio.astype(np.float32) / 32768.0


def load_whisper(model_name: str, device: str = "cpu"):
    if not _WHISPER_OK:
        log.error("whisper no disponible")
        return None
    log.info(f"Cargando Whisper '{model_name}' en {device}...")
    return whisper.load_model(model_name, device=device)


def transcribir(model, audio: np.ndarray, language: str) -> str:
    if not _WHISPER_OK or model is None:
        return ""
    try:
        result = model.transcribe(
            audio,
            language=language,
            fp16=False,
            condition_on_previous_text=False,
            temperature=0,
        )
        return result["text"].strip().lower()
    except Exception as e:
        log.error(f"Whisper error: {e}")
        return ""
