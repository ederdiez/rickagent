import datetime
import json
import time
import os
import shlex
import shutil
import subprocess
import tempfile
import webbrowser
import urllib.parse
from difflib import get_close_matches

from .logging_setup import log
from .memory import NotesManager
from .reminders import ReminderManager
from .system_utils import (
    hotkey, wayland_type, screenshot, volumen, sistema_info, proceso_info,
    buscar_archivo, ejecutar_cmd, obtener_clima, traducir, clipboard_leer,
    clipboard_escribir, run_cmd, _has, resolver_ruta, tamaño_legible
)

BOOKMARKS_FILE = os.path.expanduser("~/.rick/bookmarks.json")


class ActionExecutor:
    def __init__(self, cfg: dict, notes: NotesManager, reminders: ReminderManager):
        self.cfg        = cfg
        self.notes      = notes
        self.reminders  = reminders
        self._cwd       = os.path.expanduser("~")
        self._dir_stack = []
        self._bookmarks = self._load_bookmarks()
        self._hablar    = None

    def _resolve(self, path: str = "") -> str:
        return resolver_ruta(path, self._cwd)

    def set_hablar(self, fn):
        self._hablar = fn

    def _say(self, msg: str) -> str:
        self.hablar(msg)
        return msg

    def _load_bookmarks(self) -> dict:
        try:
            with open(BOOKMARKS_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_bookmarks(self):
        os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
        with open(BOOKMARKS_FILE, "w") as f:
            json.dump(self._bookmarks, f, indent=2)

    def _cwd_pretty(self) -> str:
        home = os.path.expanduser("~")
        if self._cwd == home:
            return "~"
        if self._cwd.startswith(home + os.sep):
            return "~" + self._cwd[len(home):]
        return self._cwd

    @property
    def cwd(self) -> str:
        return self._cwd

    @cwd.setter
    def cwd(self, val: str):
        self._cwd = val

    def validate_tools(self, agent_tools: list[dict]):
        handler_names = {
            "ABRIR_APP", "ABRIR_URL", "BUSCAR_WEB", "SCREENSHOT", "SISTEMA_INFO",
            "PROCESO_INFO", "EJECUTAR_CMD", "APAGAR", "REINICIAR",
            "VOLUMEN_SUBIR", "VOLUMEN_BAJAR", "VOLUMEN_MUTE",
            "ESCRIBIR", "ATAJO", "NUEVA_PESTANA", "CERRAR_VENTANA",
            "MINIMIZAR", "MAXIMIZAR", "CLIPBOARD_LEER", "CLIPBOARD_ESCRIBIR",
            "CREAR_ARCHIVO", "LEER_ARCHIVO", "MOVER_ARCHIVO", "COPIAR_ARCHIVO",
            "BORRAR_ARCHIVO", "CREAR_CARPETA", "IR", "PWD", "INFO_DIR", "LISTAR_DIR",
            "RENOMBRAR", "BUSCAR_ARCHIVO", "NOTA_GUARDAR", "NOTA_LEER",
            "NOTA_BORRAR", "RECORDATORIO", "CLIMA", "TRADUCIR",
            "EJECUTAR_PYTHON", "ESCRIBIR_Y_EJECUTAR", "LEER_DIR_RECURSIVO",
            "BUSCAR_EN_ARCHIVOS", "GIT_CMD", "CONVERSAR", "ERROR", "MUSICA",
            "BOOKMARK_GUARDAR", "BOOKMARK_BORRAR", "BOOKMARK_LISTAR",
        }
        for tool in agent_tools:
            if tool["name"] not in handler_names:
                log.warning(f"Herramienta '{tool['name']}' en AGENT_TOOLS no tiene handler en executor")

    def hablar(self, text: str):
        if self._hablar:
            self._hablar(text)

    def run_silent(self, tool_name: str, params: dict) -> str:
        prev_hablar = self._hablar
        self._hablar = None
        try:
            result = self.run(tool_name, params)
            return result if isinstance(result, str) else "OK"
        except Exception as e:
            return f"Error ejecutando {tool_name}: {e}"
        finally:
            self._hablar = prev_hablar

    def run(self, accion: str, params: dict) -> str | None:
        a = accion.upper()
        p = params or {}
        handlers = {
            "ABRIR_APP":         self._abrir_app,
            "ABRIR_URL":         self._abrir_url,
            "BUSCAR_WEB":        self._buscar_web,
            "SCREENSHOT":        self._screenshot,
            "SISTEMA_INFO":      self._sistema_info,
            "PROCESO_INFO":      self._proceso_info,
            "EJECUTAR_CMD":      self._ejecutar_cmd,
            "APAGAR":            self._apagar,
            "REINICIAR":         self._reiniciar,
            "VOLUMEN_SUBIR":     self._vol_subir,
            "VOLUMEN_BAJAR":     self._vol_bajar,
            "VOLUMEN_MUTE":      self._vol_mute,
            "ESCRIBIR":          self._escribir,
            "ATAJO":             self._atajo,
            "NUEVA_PESTANA":     self._nueva_pestana,
            "CERRAR_VENTANA":    self._cerrar_ventana,
            "MINIMIZAR":         self._minimizar,
            "MAXIMIZAR":         self._maximizar,
            "CLIPBOARD_LEER":    self._clipboard_leer,
            "CLIPBOARD_ESCRIBIR":self._clipboard_escribir,
            "CREAR_ARCHIVO":     self._crear_archivo,
            "LEER_ARCHIVO":      self._leer_archivo,
            "MOVER_ARCHIVO":     self._mover_archivo,
            "COPIAR_ARCHIVO":    self._copiar_archivo,
            "BORRAR_ARCHIVO":    self._borrar_archivo,
            "CREAR_CARPETA":     self._crear_carpeta,
            "IR":                self._ir,
            "PWD":               self._pwd,
            "INFO_DIR":          self._info_dir,
            "LISTAR_DIR":        self._listar_dir,
            "RENOMBRAR":         self._renombrar,
            "BUSCAR_ARCHIVO":    self._buscar_archivo,
            "NOTA_GUARDAR":      self._nota_guardar,
            "NOTA_LEER":         self._nota_leer,
            "NOTA_BORRAR":       self._nota_borrar,
            "RECORDATORIO":      self._recordatorio,
            "CLIMA":             self._clima,
            "TRADUCIR":          self._traducir,
            "EJECUTAR_PYTHON":   self._ejecutar_python,
            "ESCRIBIR_Y_EJECUTAR": self._escribir_y_ejecutar,
            "LEER_DIR_RECURSIVO": self._leer_dir_recursivo,
            "BUSCAR_EN_ARCHIVOS": self._buscar_en_archivos,
            "GIT_CMD":           self._git_cmd,
            "CONVERSAR":         lambda p: None,
            "ERROR":             lambda p: None,
            "MUSICA":            self._musica,
            "BOOKMARK_GUARDAR":  self._bookmark_guardar,
            "BOOKMARK_BORRAR":   self._bookmark_borrar,
            "BOOKMARK_LISTAR":   self._bookmark_listar,
        }
        fn = handlers.get(a)
        if fn:
            return fn(p)
        log.warning(f"Acción desconocida: {a}")

    def _abrir_app(self, p):
        app = p.get("app", "").strip().lower()
        if not app:
            self.hablar("¿Qué aplicación quieres abrir?")
            return None
        try:
            subprocess.Popen([app], stderr=subprocess.DEVNULL)
            return None
        except FileNotFoundError:
            try:
                subprocess.Popen(["xdg-open", app], stderr=subprocess.DEVNULL)
                return None
            except Exception:
                pass
        try:
            path_dirs = os.environ.get("PATH", "").split(":")
            available_apps = set()
            for path_dir in path_dirs:
                try:
                    for exe in os.listdir(path_dir):
                        available_apps.add(exe.lower())
                except Exception:
                    pass
            matches = get_close_matches(app, available_apps, n=1, cutoff=0.6)
            if matches:
                self.hablar(f"Abriendo {matches[0]}...")
                subprocess.Popen([matches[0]], stderr=subprocess.DEVNULL)
                return None
        except Exception:
            pass
        self.hablar(f"No encontré la aplicación {app}.")

    def _abrir_url(self, p):
        webbrowser.open(p.get("url", "https://google.com"))

    def _buscar_web(self, p):
        q = urllib.parse.quote_plus(p.get("query", ""))
        webbrowser.open(f"https://www.google.com/search?q={q}")

    _MUSIC_URL = "https://www.youtube.com/watch?v=CFGLoQIhmow&list=RDCFGLoQIhmow&start_radio=1"

    def _musica(self, p):
        webbrowser.open(self._MUSIC_URL)
        self.hablar("Abriendo música, amo.")

    def _screenshot(self, p):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.expanduser(f"~/screenshot_{ts}.png")
        ok   = screenshot(ruta)
        self.hablar(f"Captura guardada en {ruta}" if ok else "Instala grim o scrot para capturas.")

    def _sistema_info(self, p):
        info = sistema_info()
        return self._say(info)

    def _proceso_info(self, p):
        info = proceso_info(p.get("nombre", ""))
        return self._say(info)

    def _ejecutar_cmd(self, p):
        out = ejecutar_cmd(p.get("cmd", "echo vacío"), p.get("timeout", 10))
        resumen = out[:300].replace("\n", ". ")
        self.hablar(resumen or "Comando ejecutado.")
        return out

    def _apagar(self, p):
        d = p.get("delay", 5)
        self.hablar(f"Apagando en {d} segundos.")
        time.sleep(d)
        run_cmd(["sudo", "shutdown", "-h", "now"])

    def _reiniciar(self, p):
        d = p.get("delay", 5)
        self.hablar(f"Reiniciando en {d} segundos.")
        time.sleep(d)
        run_cmd(["sudo", "reboot"])

    def _vol_subir(self, p):
        volumen("subir", p.get("cantidad", 10))

    def _vol_bajar(self, p):
        volumen("bajar", p.get("cantidad", 10))

    def _vol_mute(self, p):
        volumen("mute")

    def _escribir(self, p):
        time.sleep(0.4)
        wayland_type(p.get("texto", ""))

    def _atajo(self, p):
        hotkey(p.get("combo", ""))

    def _nueva_pestana(self, p):
        hotkey("ctrl+t")

    def _cerrar_ventana(self, p):
        hotkey("alt+F4")

    def _minimizar(self, p):
        if _has("hyprctl"):
            run_cmd(["hyprctl", "dispatch", "movetoworkspacesilent", "special"])
        else:
            hotkey("super+h")

    def _maximizar(self, p):
        if _has("hyprctl"):
            run_cmd(["hyprctl", "dispatch", "fullscreen", "1"])
        else:
            hotkey("super+Up")

    def _clipboard_leer(self, p):
        contenido = clipboard_leer()
        self.hablar(contenido[:400])
        return contenido

    def _clipboard_escribir(self, p):
        result = clipboard_escribir(p.get("texto", ""))
        self.hablar(result)

    def _crear_archivo(self, p):
        ruta = self._resolve(p.get("ruta", "~/nuevo.txt"))
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(p.get("contenido", ""))
            return self._say(f"Archivo creado: {os.path.basename(ruta)}.")
        except Exception as e:
            return self._say(f"No pude crear el archivo: {e}")

    def _leer_archivo(self, p):
        ruta = self._resolve(p.get("ruta", ""))
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
            resumen = contenido[:600] if contenido else "El archivo está vacío."
            self.hablar(resumen)
            return contenido
        except FileNotFoundError:
            return self._say("No encontré ese archivo.")
        except Exception as e:
            return self._say(f"Error al leer: {e}")

    def _mover_archivo(self, p):
        origen  = self._resolve(p.get("origen", ""))
        destino = self._resolve(p.get("destino", ""))
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.move(origen, destino)
            return self._say(f"Movido a {os.path.basename(destino)}.")
        except Exception as e:
            return self._say(f"No pude mover: {e}")

    def _copiar_archivo(self, p):
        origen  = self._resolve(p.get("origen", ""))
        destino = self._resolve(p.get("destino", ""))
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.copy2(origen, destino)
            return self._say(f"Copiado a {os.path.basename(destino)}.")
        except Exception as e:
            return self._say(f"No pude copiar: {e}")

    def _borrar_archivo(self, p):
        ruta = self._resolve(p.get("ruta", ""))
        try:
            if os.path.isdir(ruta):
                shutil.rmtree(ruta)
            else:
                os.remove(ruta)
            return self._say(f"Eliminado {os.path.basename(ruta)}.")
        except FileNotFoundError:
            return self._say("No encontré ese archivo.")
        except Exception as e:
            return self._say(f"No pude eliminar: {e}")

    def _crear_carpeta(self, p):
        ruta = self._resolve(p.get("ruta", ""))
        try:
            os.makedirs(ruta, exist_ok=True)
            return self._say(f"Carpeta creada: {os.path.basename(ruta)}.")
        except Exception as e:
            return self._say(f"No pude crear la carpeta: {e}")

    def _listar_dir(self, p):
        ruta = self._resolve(p.get("ruta", "."))
        try:
            items = sorted(os.listdir(ruta), key=lambda x: (not os.path.isdir(os.path.join(ruta, x)), x.lower()))
            if not items:
                return self._say("La carpeta está vacía.")

            C_DIR  = "\033[0;34m"
            C_EXE  = "\033[0;32m"
            C_LNK  = "\033[0;36m"
            C_HID  = "\033[2m"
            C_RST  = "\033[0m"
            C_DIM  = "\033[2m"
            C_BOLD = "\033[1m"

            home = os.path.expanduser("~")
            header_path = ruta.replace(home, "~")
            lines = [f"{C_BOLD}📂 {header_path}{C_RST}\n"]

            for name in items:
                full = os.path.join(ruta, name)
                is_hidden = name.startswith(".")
                try:
                    stat_info = os.stat(full)
                    size = tamaño_legible(stat_info.st_size)
                    mtime = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    size = "?"
                    mtime = ""

                is_dir  = os.path.isdir(full)
                is_lnk  = os.path.islink(full)
                is_exe  = os.access(full, os.X_OK) and not is_dir

                if is_dir:
                    color, icon, display = C_DIR, "📁", f"{name}/"
                elif is_lnk:
                    color, icon, display = C_LNK, "🔗", name
                elif is_exe:
                    color, icon, display = C_EXE, "⚡", name
                else:
                    color, icon, display = C_RST, " ", name

                if is_hidden:
                    color += C_HID

                link_target = f" → {os.readlink(full)}" if is_lnk else ""
                size_str = f"{size:>8}" if not is_dir else "       " + C_DIM + "DIR" + C_RST
                lines.append(f"{color}{icon} {display}{link_target}{C_RST}  {C_DIM}{size_str}  {mtime}{C_RST}")

            output = "\n".join(lines)
            dirs_n = sum(1 for n in items if os.path.isdir(os.path.join(ruta, n)))
            files_n = len(items) - dirs_n
            self.hablar(f"{dirs_n} carpetas, {files_n} archivos.")
            return output
        except PermissionError:
            return self._say(f"Sin permiso para listar {ruta}.")
        except Exception as e:
            return self._say(f"No pude listar: {e}")

    def _pwd(self, p):
        pretty = self._cwd_pretty()
        self.hablar(f"Estoy en {pretty}.")
        return f"PWD: {self._cwd}"

    def _find_dir_in(self, parent: str, name: str) -> str | None:
        try:
            candidates = [d for d in os.listdir(parent)
                         if os.path.isdir(os.path.join(parent, d))]
        except PermissionError:
            return None
        if not candidates:
            return None

        for c in candidates:
            if c == name:
                return os.path.join(parent, c)

        name_lower = name.lower()
        for c in candidates:
            if c.lower() == name_lower:
                return os.path.join(parent, c)

        matches = get_close_matches(name, candidates, n=1, cutoff=0.5)
        if matches:
            return os.path.join(parent, matches[0])

        return None

    def _cd(self, destino: str) -> str:
        if self._cwd != destino:
            self._dir_stack.append(self._cwd)
        self._cwd = destino
        self.hablar(f"En {self._cwd_pretty()}.")
        return f"CWD → {self._cwd}"

    def _ir(self, p):
        raw = (p.get("directorio") or ".").strip()

        if raw in ("--back", "-", "..-"):
            if not self._dir_stack:
                return self._say("No hay directorios anteriores.")
            prev = self._dir_stack.pop()
            if not os.path.isdir(prev):
                return self._say("El directorio anterior ya no existe.")
            self._cwd = prev
            return self._say(f"De vuelta en {self._cwd_pretty()}.")

        if raw in self._bookmarks:
            destino = self._bookmarks[raw]
            return self._cd(destino)

        destino = self._resolve(raw)
        if os.path.isdir(destino):
            return self._cd(destino)

        parent = os.path.dirname(destino)
        if parent and os.path.isdir(parent):
            match = self._find_dir_in(parent, os.path.basename(destino))
            if match:
                return self._cd(match)

        match = self._find_dir_in(self._cwd, raw)
        if match:
            return self._cd(match)

        home = os.path.expanduser("~")
        if self._cwd != home:
            match = self._find_dir_in(home, raw)
            if match:
                return self._cd(match)

        if os.path.isfile(destino):
            return self._cd(os.path.dirname(destino))

        return self._say(f"No encontré el directorio {raw}.")

    def _bookmark_guardar(self, p):
        name = p.get("nombre", "").strip()
        if not name:
            return self._say("Dime un nombre para el marcador.")
        self._bookmarks[name] = self._cwd
        self._save_bookmarks()
        return self._say(f"Guardé {self._cwd_pretty()} como '{name}'.")

    def _bookmark_borrar(self, p):
        name = p.get("nombre", "").strip()
        if name in self._bookmarks:
            del self._bookmarks[name]
            self._save_bookmarks()
            return self._say(f"Marcador '{name}' eliminado.")
        return self._say(f"No existe el marcador '{name}'.")

    def _bookmark_listar(self, p):
        if not self._bookmarks:
            return self._say("No tienes marcadores guardados.")
        lines = [f"  {k} → {v}" for k, v in self._bookmarks.items()]
        self.hablar(f"{len(self._bookmarks)} marcadores.")
        return "Marcadores:\n" + "\n".join(lines)

    def _info_dir(self, p):
        ruta = self._resolve(p.get("ruta", "."))
        if not os.path.isdir(ruta):
            return self._say("Eso no es un directorio.")
        try:
            home = os.path.expanduser("~")
            header_path = ruta.replace(home, "~")
            total_size = 0
            file_count = 0
            dir_count = 0
            largest = []
            by_ext = {}
            for root, dirs, files in os.walk(ruta):
                dir_count += len(dirs)
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        s = os.stat(fp)
                        total_size += s.st_size
                        file_count += 1
                        ext = os.path.splitext(f)[1].lower() or "(sin ext)"
                        by_ext[ext] = by_ext.get(ext, 0) + 1
                        largest.append((s.st_size, fp))
                    except Exception:
                        pass
            largest.sort(reverse=True, key=lambda x: x[0])
            top5 = "\n".join(f"  {tamaño_legible(s)}  {p}" for s, p in largest[:5])
            exts = sorted(by_ext.items(), key=lambda x: -x[1])[:8]
            ext_str = ", ".join(f"{ext}: {n}" for ext, n in exts)
            voice = f"{file_count} archivos, {dir_count} carpetas, {tamaño_legible(total_size)} en total."
            self.hablar(voice)
            return (
                f"\033[1m📊 {header_path}\033[0m\n"
                f"  Archivos: {file_count}  Carpetas: {dir_count}\n"
                f"  Tamaño total: {tamaño_legible(total_size)}\n"
                f"  Tipos: {ext_str}\n"
                f"  Top 5 más grandes:\n{top5}"
            )
        except PermissionError:
            return self._say(f"Sin permiso para analizar {ruta}.")
        except Exception as e:
            return self._say(f"Error analizando directorio: {e}")

    def _renombrar(self, p):
        origen  = self._resolve(p.get("origen", ""))
        destino = self._resolve(p.get("destino", ""))
        try:
            os.rename(origen, destino)
            return self._say(f"Renombrado a {os.path.basename(destino)}.")
        except Exception as e:
            return self._say(f"No pude renombrar: {e}")

    def _buscar_archivo(self, p):
        result = buscar_archivo(
            p.get("nombre", "*"),
            self._resolve(p.get("directorio", ".")),
            p.get("profundidad", 3),
        )
        return self._say(result)

    def _nota_guardar(self, p):
        return self._say(self.notes.save(p.get("titulo", "sin título"), p.get("contenido", "")))

    def _nota_leer(self, p):
        return self._say(self.notes.read(p.get("titulo")))

    def _nota_borrar(self, p):
        return self._say(self.notes.delete(p.get("titulo", "")))

    def _recordatorio(self, p):
        return self._say(self.reminders.add(p.get("mensaje", "Recordatorio"), int(p.get("segundos", 60))))

    def _clima(self, p):
        return self._say(obtener_clima(p.get("ciudad", "Madrid")))

    def _traducir(self, p):
        return self._say(traducir(p.get("texto", ""), p.get("idioma_destino", "es")))

    def _ejecutar_python(self, p) -> str:
        codigo = p.get("codigo", "")
        timeout = p.get("timeout", 30)
        if not codigo.strip():
            return "Error: código vacío."
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
                f.write(codigo)
                fname = f.name
            try:
                result = ejecutar_cmd(f"python3 {fname}", timeout)
                return result or "Código ejecutado sin output."
            finally:
                try:
                    os.unlink(fname)
                except Exception:
                    pass
        except Exception as e:
            return f"Error ejecutando Python: {e}"

    def _escribir_y_ejecutar(self, p) -> str:
        nombre = p.get("nombre", "script.py")
        contenido = p.get("contenido", "")
        interprete = p.get("interprete", "python3")
        timeout = p.get("timeout", 30)
        if not contenido.strip():
            return "Error: contenido vacío."
        try:
            ruta = f"/tmp/rick_{int(time.time())}_{nombre}"
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            os.chmod(ruta, 0o755)
            result = ejecutar_cmd(f"{interprete} {ruta}", timeout)
            try:
                os.unlink(ruta)
            except Exception:
                pass
            return result or "Script ejecutado sin output."
        except Exception as e:
            return f"Error escribiendo/ejecutando script: {e}"

    def _leer_dir_recursivo(self, p) -> str:
        ruta = self._resolve(p.get("ruta", "."))
        profundidad = p.get("profundidad", 3)
        if not os.path.isdir(ruta):
            return f"El directorio no existe: {ruta}"
        try:
            resultado = []
            home = os.path.expanduser("~")
            header = ruta.replace(home, "~")
            resultado.append(f"📂 {header}/")
            for root, dirs, files in os.walk(ruta):
                depth = root.replace(ruta, "").count(os.sep)
                if depth >= profundidad:
                    dirs.clear()
                    continue
                if depth == 0:
                    continue
                rel = root[len(ruta) + 1:]
                parts = rel.split(os.sep)
                prefix = "│   " * (len(parts) - 1) + "├── "
                resultado.append(f"{prefix}{os.path.basename(root)}/")
                files_sorted = sorted(files)[:20]
                n_files = len(files_sorted)
                for i, f in enumerate(files_sorted):
                    try:
                        sz = tamaño_legible(os.stat(os.path.join(root, f)).st_size)
                    except Exception:
                        sz = "?"
                    is_last = (i == n_files - 1)
                    file_prefix = prefix.replace("├── ", "│   ") + ("└── " if is_last else "├── ")
                    resultado.append(f"{file_prefix}{f}  ({sz})")
                if len(files) > 20:
                    resultado.append(f"{prefix.replace('├── ', '│   ')}└── ... y {len(files) - 20} archivos más")
            return "\n".join(resultado[:300]) or "Directorio vacío."
        except Exception as e:
            return f"Error listando directorio: {e}"

    def _buscar_en_archivos(self, p) -> str:
        patron = p.get("patron", "")
        directorio = self._resolve(p.get("directorio", "."))
        extension = p.get("extension", "")
        if not patron.strip():
            return "Error: patrón vacío."
        try:
            ext_flag = f"--include={shlex.quote('*' + extension)}" if extension else ""
            cmd = f"grep -rn {ext_flag} {shlex.quote(patron)} {shlex.quote(directorio)} 2>/dev/null | head -50"
            result = ejecutar_cmd(cmd, timeout=15)
            return result or "No se encontraron coincidencias."
        except Exception as e:
            return f"Error buscando en archivos: {e}"

    def _git_cmd(self, p) -> str:
        subcmd = p.get("subcmd", "status")
        directorio = self._resolve(p.get("directorio", "."))
        safe_cmds = {"status", "log", "diff", "add", "commit", "push", "pull",
                     "clone", "init", "branch", "checkout", "show", "remote"}
        try:
            first_word = subcmd.split()[0].lower()
            if first_word not in safe_cmds:
                return f"Subcomando git no permitido: {first_word}"
            cmd = f"git -C {shlex.quote(directorio)} {' '.join(shlex.quote(p) for p in subcmd.split())}"
            result = ejecutar_cmd(cmd, timeout=60)
            return result or "Git comando ejecutado sin output."
        except Exception as e:
            return f"Error ejecutando git: {e}"
