import json
import datetime
import time

from .logging_setup import log


class ConversationMemory:
    """Mantiene el historial de la conversación actual y lo persiste en disco."""

    def __init__(self, history_file: str, max_turns: int):
        self.history_file = history_file
        self.max_turns = max_turns
        self.turns: list[dict] = []           # contexto actual (ventana deslizante)
        self.full_log: list[dict] = []        # log completo persistente
        self._last_save = 0.0                 # debounce
        self._load_log()

    def _load_log(self):
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                self.full_log = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.full_log = []

    def _save_log(self):
        now = time.monotonic()
        if now - self._last_save < 1.5:
            return
        self._last_save = now
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.full_log, f, ensure_ascii=False, indent=2)
        except OSError as e:
            log.warning(f"No se pudo guardar historial: {e}")

    def add_user(self, text: str):
        entry = {
            "role": "user",
            "content": text,
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self.turns.append(entry)
        self.full_log.append(entry)
        # Ventana deslizante: mantener solo los últimos N turnos
        if len(self.turns) > self.max_turns * 2:
            self.turns = self.turns[-(self.max_turns * 2):]
        self._save_log()

    def add_assistant(self, response: dict):
        voz = response.get("respuesta_voz", "")
        entry = {
            "role": "assistant",
            "content": voz,
            "action": response.get("accion", ""),
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self.turns.append(entry)
        self.full_log.append(entry)
        self._save_log()

    def build_prompt(self, new_user_input: str) -> str:
        """Construye el prompt multi-turno para Ollama."""
        lines = []
        for t in self.turns[-(self.max_turns * 2):]:
            role = "Usuario" if t["role"] == "user" else "RICK"
            lines.append(f"[{role}]: {t['content']}")
        lines.append(f"[Usuario]: {new_user_input}")
        lines.append("[RICK]: ")
        return "\n".join(lines)

    def build_messages(self) -> list[dict]:
        """Construye historial en formato messages[] de Anthropic API."""
        result = []
        for t in self.turns[-(self.max_turns * 2):]:
            result.append({
                "role": t["role"],
                "content": t["content"]
            })
        return result

    def print_history(self, n: int = 20):
        if not self.full_log:
            print("No hay historial guardado.")
            return
        print(f"\n{'─'*60}")
        print(f"  HISTORIAL (últimas {n} entradas)")
        print(f"{'─'*60}")
        for entry in self.full_log[-n:]:
            ts   = entry.get("ts", "")
            role = "👤 Tú  " if entry["role"] == "user" else "🤖 RICK"
            act  = f" [{entry['action']}]" if entry.get("action") else ""
            print(f"{role} {ts}{act}")
            print(f"       {entry['content'][:100]}")
        print(f"{'─'*60}\n")


class NotesManager:
    def __init__(self, notes_file: str):
        self.file = notes_file
        self.notes: dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                self.notes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.notes = {}

    def _save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def save(self, titulo: str, contenido: str) -> str:
        key = titulo.strip().lower()
        self.notes[key] = {
            "titulo": titulo,
            "contenido": contenido,
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._save()
        return f"Nota '{titulo}' guardada."

    def read(self, titulo: str | None = None) -> str:
        if titulo:
            key = titulo.strip().lower()
            if key in self.notes:
                n = self.notes[key]
                return f"Nota '{n['titulo']}' ({n['ts']}): {n['contenido']}"
            return f"No encontré nota '{titulo}'."
        if not self.notes:
            return "No hay notas guardadas."
        titles = [v["titulo"] for v in self.notes.values()]
        return "Tienes " + str(len(titles)) + " notas: " + ", ".join(titles) + "."

    def delete(self, titulo: str) -> str:
        key = titulo.strip().lower()
        if key in self.notes:
            del self.notes[key]
            self._save()
            return f"Nota '{titulo}' eliminada."
        return f"No encontré nota '{titulo}'."
