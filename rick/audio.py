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
    """
    def __init__(self, cfg: dict):
        self.sr       = cfg["sample_rate"]
        self.channels = cfg["channels"]
        self.device   = cfg["mic_device"]
        self.thresh   = cfg["silence_db"]
        self.hold_ms  = cfg["vad_hold_ms"]
        self.prebuf_ms= cfg["vad_prebuf_ms"]
        self.max_s    = cfg["max_record_s"]
        self.min_ms   = cfg["min_speech_ms"]

    def record(self) -> np.ndarray | None:
        chunk_ms   = 80                                  # ms por chunk VAD
        chunk_n    = int(self.sr * chunk_ms / 1000)
        prebuf_n   = max(1, self.prebuf_ms // chunk_ms)  # chunks de pre-buffer
        hold_n     = max(1, self.hold_ms // chunk_ms)
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
