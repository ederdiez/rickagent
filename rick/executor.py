import os
import json

from .logging_setup import log
from .memory import NotesManager
from .reminders import ReminderManager
from .system_utils import resolver_ruta
from .skills.base import discover, get_all

BOOKMARKS_FILE = os.path.expanduser("~/.rick/bookmarks.json")


class ActionExecutor:
    def __init__(self, cfg: dict, notes: NotesManager, reminders: ReminderManager):
        self.cfg       = cfg
        self.notes     = notes
        self.reminders = reminders
        self._cwd      = os.path.expanduser("~")
        self._dir_stack: list[str] = []
        self._bookmarks: dict[str, str] = self._load_bookmarks()
        self._hablar   = None

        discover()
        self._skill_map = {s.name: s for s in get_all()}

    def resolve(self, path: str = "") -> str:
        return resolver_ruta(path, self._cwd)

    def say(self, msg: str) -> str:
        self.hablar(msg)
        return msg

    def set_hablar(self, fn):
        self._hablar = fn

    def hablar(self, text: str):
        if self._hablar:
            self._hablar(text)

    def cwd_pretty(self) -> str:
        home = os.path.expanduser("~")
        if self._cwd == home:
            return "~"
        if self._cwd.startswith(home + os.sep):
            return "~" + self._cwd[len(home):]
        return self._cwd

    def _cd(self, destino: str) -> str:
        if self._cwd != destino:
            self._dir_stack.append(self._cwd)
        self._cwd = destino
        self.hablar(f"En {self.cwd_pretty()}.")
        return f"CWD → {self._cwd}"

    # --- properties for skills ---

    @property
    def cwd(self) -> str:
        return self._cwd

    @cwd.setter
    def cwd(self, val: str):
        self._cwd = val

    @property
    def dir_stack(self) -> list:
        return self._dir_stack

    @property
    def bookmarks(self) -> dict:
        return self._bookmarks

    def save_bookmarks(self):
        os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
        with open(BOOKMARKS_FILE, "w") as f:
            json.dump(self._bookmarks, f, indent=2)

    # --- persistence ---

    def _load_bookmarks(self) -> dict:
        try:
            with open(BOOKMARKS_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    # --- skill integration ---

    def get_tool_definitions(self) -> list[dict]:
        from .skills.base import get_tool_defs
        return get_tool_defs()

    def run_silent(self, tool_name: str, params: dict) -> str:
        prev = self._hablar
        self._hablar = None
        try:
            result = self.run(tool_name, params)
            return result if isinstance(result, str) else "OK"
        except Exception as e:
            return f"Error ejecutando {tool_name}: {e}"
        finally:
            self._hablar = prev

    def run(self, accion: str, params: dict) -> str | None:
        a = accion.upper()
        p = params or {}

        if a in ("CONVERSAR", "ERROR"):
            return None

        skill = self._skill_map.get(a)
        if skill:
            return skill.run(self, p)

        log.warning(f"Acción desconocida: {a}")
        return None
