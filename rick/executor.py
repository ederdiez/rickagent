import datetime
import time
import os
import webbrowser
import urllib.parse

from .logging_setup import log
from .memory import NotesManager
from .reminders import ReminderManager
from .system_utils import (
    hotkey, wayland_type, screenshot, volumen, sistema_info, proceso_info,
    buscar_archivo, ejecutar_cmd, obtener_clima, traducir, clipboard_leer,
    clipboard_escribir, run_cmd, _has, resolver_ruta, tamaño_legible
)


class ActionExecutor:
    def __init__(self, cfg: dict, notes: NotesManager, reminders: ReminderManager):
        self.cfg       = cfg
        self.notes     = notes
        self.reminders = reminders
        self.cwd       = os.path.expanduser("~")
        self._hablar   = None      # inyectado después

    def _resolve(self, path: str = "") -> str:
        return resolver_ruta(path, self.cwd)

    def set_hablar(self, fn):
        self._hablar = fn

    def hablar(self, text: str):
        if self._hablar:
            self._hablar(text)

    def run_silent(self, tool_name: str, params: dict) -> str:
        """Ejecuta una herramienta sin hablar. Para uso del agentic loop."""
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
        """
        Ejecuta la acción y retorna una cadena de resultado opcional
        (usada en algunos flujos para inyectar info de vuelta al TTS).
        """
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
        }
        fn = handlers.get(a)
        if fn:
            return fn(p)
        log.warning(f"Acción desconocida: {a}")
        return None

    def _abrir_app(self, p):
        import subprocess
        from difflib import get_close_matches
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
            except:
                pass

        # Si falló, buscar apps similares en PATH
        try:
            import os
            path_dirs = os.environ.get("PATH", "").split(":")
            available_apps = set()
            for path_dir in path_dirs:
                try:
                    for exe in os.listdir(path_dir):
                        available_apps.add(exe.lower())
                except:
                    pass

            matches = get_close_matches(app, available_apps, n=1, cutoff=0.6)
            if matches:
                matched_app = matches[0]
                self.hablar(f"Abriendo {matched_app}...")
                subprocess.Popen([matched_app], stderr=subprocess.DEVNULL)
                return None
        except:
            pass

        self.hablar(f"No encontré la aplicación {app}.")
        return None

    def _abrir_url(self, p):
        webbrowser.open(p.get("url", "https://google.com"))
        return None

    def _buscar_web(self, p):
        q = urllib.parse.quote_plus(p.get("query", ""))
        webbrowser.open(f"https://www.google.com/search?q={q}")
        return None

    def _screenshot(self, p):
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.expanduser(f"~/screenshot_{ts}.png")
        ok   = screenshot(ruta)
        self.hablar(f"Captura guardada en {ruta}" if ok else "Instala grim o scrot para capturas.")
        return None

    def _sistema_info(self, p):
        info = sistema_info()
        self.hablar(info)
        return info

    def _proceso_info(self, p):
        info = proceso_info(p.get("nombre", ""))
        self.hablar(info)
        return info

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
        return None

    def _reiniciar(self, p):
        d = p.get("delay", 5)
        self.hablar(f"Reiniciando en {d} segundos.")
        time.sleep(d)
        run_cmd(["sudo", "reboot"])
        return None

    def _vol_subir(self, p):
        volumen("subir", p.get("cantidad", 10))
        return None

    def _vol_bajar(self, p):
        volumen("bajar", p.get("cantidad", 10))
        return None

    def _vol_mute(self, p):
        volumen("mute")
        return None

    def _escribir(self, p):
        time.sleep(0.4)
        wayland_type(p.get("texto", ""))
        return None

    def _atajo(self, p):
        hotkey(p.get("combo", ""))
        return None

    def _nueva_pestana(self, p):
        hotkey("ctrl+t")
        return None

    def _cerrar_ventana(self, p):
        hotkey("alt+F4")
        return None

    def _minimizar(self, p):
        if _has("hyprctl"):
            run_cmd(["hyprctl", "dispatch", "movetoworkspacesilent", "special"])
        else:
            hotkey("super+h")
        return None

    def _maximizar(self, p):
        if _has("hyprctl"):
            run_cmd(["hyprctl", "dispatch", "fullscreen", "1"])
        else:
            hotkey("super+Up")
        return None

    def _clipboard_leer(self, p):
        contenido = clipboard_leer()
        self.hablar(contenido[:400])
        return contenido

    def _clipboard_escribir(self, p):
        result = clipboard_escribir(p.get("texto", ""))
        self.hablar(result)
        return None

    def _crear_archivo(self, p):
        import shutil
        ruta = self._resolve(p.get("ruta", "~/nuevo.txt"))
        contenido = p.get("contenido", "")
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            msg = f"Archivo creado: {os.path.basename(ruta)}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude crear el archivo: {e}"
            self.hablar(msg)
            return msg

    def _leer_archivo(self, p):
        ruta = self._resolve(p.get("ruta", ""))
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
            resumen = contenido[:600] if contenido else "El archivo está vacío."
            self.hablar(resumen)
            return contenido
        except FileNotFoundError:
            msg = "No encontré ese archivo."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"Error al leer: {e}"
            self.hablar(msg)
            return msg

    def _mover_archivo(self, p):
        import shutil
        origen  = self._resolve(p.get("origen", ""))
        destino = self._resolve(p.get("destino", ""))
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.move(origen, destino)
            msg = f"Movido a {os.path.basename(destino)}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude mover: {e}"
            self.hablar(msg)
            return msg

    def _copiar_archivo(self, p):
        import shutil
        origen  = self._resolve(p.get("origen", ""))
        destino = self._resolve(p.get("destino", ""))
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.copy2(origen, destino)
            msg = f"Copiado a {os.path.basename(destino)}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude copiar: {e}"
            self.hablar(msg)
            return msg

    def _borrar_archivo(self, p):
        import shutil
        ruta = self._resolve(p.get("ruta", ""))
        try:
            if os.path.isdir(ruta):
                shutil.rmtree(ruta)
            else:
                os.remove(ruta)
            msg = f"Eliminado {os.path.basename(ruta)}."
            self.hablar(msg)
            return msg
        except FileNotFoundError:
            msg = "No encontré ese archivo."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude eliminar: {e}"
            self.hablar(msg)
            return msg

    def _crear_carpeta(self, p):
        ruta = self._resolve(p.get("ruta", ""))
        try:
            os.makedirs(ruta, exist_ok=True)
            msg = f"Carpeta creada: {os.path.basename(ruta)}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude crear la carpeta: {e}"
            self.hablar(msg)
            return msg

    def _listar_dir(self, p):
        ruta = self._resolve(p.get("ruta", "."))
        try:
            items = sorted(os.listdir(ruta), key=lambda x: (not os.path.isdir(os.path.join(ruta, x)), x.lower()))
            if not items:
                msg = "La carpeta está vacía."
                self.hablar(msg)
                return msg

            lines = []
            for name in items:
                full = os.path.join(ruta, name)
                is_dir = os.path.isdir(full)
                try:
                    stat = os.stat(full)
                    size = tamaño_legible(stat.st_size) if not is_dir else ""
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                except:
                    size = ""
                    mtime = ""
                tag = "📁" if is_dir else " "
                lines.append(f"{tag} {name}/" if is_dir else f" {name}  {size:>8}  {mtime}")

            output = "\n".join(lines)

            dirs_n = sum(1 for n in items if os.path.isdir(os.path.join(ruta, n)))
            files_n = len(items) - dirs_n
            voice = f"{dirs_n} carpetas, {files_n} archivos."
            self.hablar(voice)
            return output
        except PermissionError:
            msg = f"Sin permiso para listar {ruta}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude listar: {e}"
            self.hablar(msg)
            return msg

    def _ir(self, p):
        destino = self._resolve(p.get("directorio", "."))
        if not os.path.isdir(destino):
            if os.path.isfile(destino):
                destino = os.path.dirname(destino)
            else:
                self.hablar(f"No encontré el directorio {p.get('directorio', '')}.")
                return f"Directorio no existe: {destino}"
        self.cwd = destino
        basename = os.path.basename(destino)
        self.hablar(f"En {basename}.")
        return f"CWD → {destino}"

    def _info_dir(self, p):
        ruta = self._resolve(p.get("ruta", "."))
        if not os.path.isdir(ruta):
            self.hablar("Eso no es un directorio.")
            return "No es un directorio."
        try:
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
                    except:
                        pass
            largest.sort(reverse=True, key=lambda x: x[0])
            top5 = "\n".join(f"  {tamaño_legible(s)}  {p}" for s, p in largest[:5])
            exts = sorted(by_ext.items(), key=lambda x: -x[1])[:8]
            ext_str = ", ".join(f"{ext}: {n}" for ext, n in exts)
            voice = f"{file_count} archivos, {dir_count} carpetas, {tamaño_legible(total_size)} en total."
            self.hablar(voice)
            return (
                f"📊 Info: {ruta}\n"
                f"  Archivos: {file_count}  Carpetas: {dir_count}\n"
                f"  Tamaño total: {tamaño_legible(total_size)}\n"
                f"  Tipos: {ext_str}\n"
                f"  Top 5 más grandes:\n{top5}"
            )
        except PermissionError:
            msg = f"Sin permiso para analizar {ruta}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"Error analizando directorio: {e}"
            self.hablar(msg)
            return msg

    def _renombrar(self, p):
        origen  = self._resolve(p.get("origen", ""))
        destino = self._resolve(p.get("destino", ""))
        try:
            os.rename(origen, destino)
            msg = f"Renombrado a {os.path.basename(destino)}."
            self.hablar(msg)
            return msg
        except Exception as e:
            msg = f"No pude renombrar: {e}"
            self.hablar(msg)
            return msg

    def _buscar_archivo(self, p):
        result = buscar_archivo(
            p.get("nombre", "*"),
            self._resolve(p.get("directorio", ".")),
            p.get("profundidad", 3),
        )
        self.hablar(result)
        return result

    def _nota_guardar(self, p):
        msg = self.notes.save(p.get("titulo", "sin título"), p.get("contenido", ""))
        self.hablar(msg)
        return msg

    def _nota_leer(self, p):
        msg = self.notes.read(p.get("titulo"))
        self.hablar(msg)
        return msg

    def _nota_borrar(self, p):
        msg = self.notes.delete(p.get("titulo", ""))
        self.hablar(msg)
        return msg

    def _recordatorio(self, p):
        msg = self.reminders.add(p.get("mensaje", "Recordatorio"), int(p.get("segundos", 60)))
        self.hablar(msg)
        return msg

    def _clima(self, p):
        info = obtener_clima(p.get("ciudad", "Madrid"))
        self.hablar(info)
        return info

    def _traducir(self, p):
        traduccion = traducir(p.get("texto", ""), p.get("idioma_destino", "es"))
        self.hablar(traduccion)
        return traduccion

    def _ejecutar_python(self, p) -> str:
        """Ejecuta código Python en un subprocess, retorna stdout+stderr."""
        import tempfile
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
                except:
                    pass
        except Exception as e:
            return f"Error ejecutando Python: {e}"

    def _escribir_y_ejecutar(self, p) -> str:
        """Escribe un archivo en /tmp y lo ejecuta."""
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
            except:
                pass
            return result or "Script ejecutado sin output."
        except Exception as e:
            return f"Error escribiendo/ejecutando script: {e}"

    def _leer_dir_recursivo(self, p) -> str:
        """Lista árbol de directorio con profundidad controlada."""
        ruta = self._resolve(p.get("ruta", "."))
        profundidad = p.get("profundidad", 3)
        if not os.path.isdir(ruta):
            return f"El directorio no existe: {ruta}"
        try:
            resultado = []
            for root, dirs, files in os.walk(ruta):
                depth = root.replace(ruta, "").count(os.sep)
                if depth >= profundidad:
                    dirs.clear()
                    continue
                indent = "  " * depth
                resultado.append(f"{indent}{os.path.basename(root)}/")
                for f in sorted(files)[:20]:
                    resultado.append(f"{indent}  {f}")
                if len(files) > 20:
                    resultado.append(f"{indent}  ... y {len(files) - 20} más")
            return "\n".join(resultado[:300]) or "Directorio vacío."
        except Exception as e:
            return f"Error listando directorio: {e}"

    def _buscar_en_archivos(self, p) -> str:
        """Grep en archivos dentro de un directorio."""
        patron = p.get("patron", "")
        directorio = self._resolve(p.get("directorio", "."))
        extension = p.get("extension", "")
        if not patron.strip():
            return "Error: patrón vacío."
        try:
            ext_flag = f"--include='*{extension}'" if extension else ""
            cmd = f"grep -rn {ext_flag} {repr(patron)} {repr(directorio)} 2>/dev/null | head -50"
            result = ejecutar_cmd(cmd, timeout=15)
            return result or "No se encontraron coincidencias."
        except Exception as e:
            return f"Error buscando en archivos: {e}"

    def _git_cmd(self, p) -> str:
        """Ejecuta un comando git básico."""
        subcmd = p.get("subcmd", "status")
        directorio = self._resolve(p.get("directorio", "."))
        safe_cmds = {"status", "log", "diff", "add", "commit", "push", "pull",
                     "clone", "init", "branch", "checkout", "show", "remote"}
        try:
            first_word = subcmd.split()[0].lower()
            if first_word not in safe_cmds:
                return f"Subcomando git no permitido: {first_word}"
            cmd = f"git -C {repr(directorio)} {subcmd}"
            result = ejecutar_cmd(cmd, timeout=60)
            return result or "Git comando ejecutado sin output."
        except Exception as e:
            return f"Error ejecutando git: {e}"
