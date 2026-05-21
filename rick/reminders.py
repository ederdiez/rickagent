import threading

from .logging_setup import log


class ReminderManager:
    def __init__(self, hablar_fn):
        self.hablar = hablar_fn
        self.timers: list[threading.Timer] = []

    def add(self, mensaje: str, segundos: int) -> str:
        def _fire():
            log.info(f"Recordatorio: {mensaje}")
            self.hablar(f"Recordatorio: {mensaje}")
        t = threading.Timer(segundos, _fire)
        t.daemon = True
        t.start()
        self.timers.append(t)
        m, s = divmod(segundos, 60)
        h, m = divmod(m, 60)
        parts = []
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}min")
        if s: parts.append(f"{s}s")
        return f"Recordatorio en {' '.join(parts)}: '{mensaje}'."

    def cancel_all(self):
        for t in self.timers:
            t.cancel()
        self.timers.clear()
