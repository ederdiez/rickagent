import subprocess
import os
import webbrowser
import urllib.parse
import datetime
from difflib import get_close_matches

from rick.skills.base import Skill, register
from rick.system_utils import screenshot, sistema_info, proceso_info, ejecutar_cmd, run_cmd


class AbrirAppSkill(Skill):
    name = "ABRIR_APP"
    description = "Abre una aplicación del sistema"
    prompt_line = 'ABRIR_APP{"app":"..."}'
    input_schema = {"type": "object", "properties": {
        "app": {"type": "string", "description": "Nombre del ejecutable"}
    }, "required": ["app"]}

    def run(self, executor, params):
        app = params.get("app", "").strip().lower()
        if not app:
            executor.hablar("¿Qué aplicación quieres abrir?")
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
            available = set()
            for pd in path_dirs:
                try:
                    for exe in os.listdir(pd):
                        available.add(exe.lower())
                except Exception:
                    pass
            matches = get_close_matches(app, available, n=1, cutoff=0.6)
            if matches:
                executor.hablar(f"Abriendo {matches[0]}...")
                subprocess.Popen([matches[0]], stderr=subprocess.DEVNULL)
                return None
        except Exception:
            pass
        executor.hablar(f"No encontré la aplicación {app}.")
        return None

register(AbrirAppSkill())


class AbrirUrlSkill(Skill):
    name = "ABRIR_URL"
    description = "Abre una URL en el navegador"
    prompt_line = 'ABRIR_URL{"url":"..."}'
    input_schema = {"type": "object", "properties": {
        "url": {"type": "string"}
    }, "required": ["url"]}

    def run(self, executor, params):
        webbrowser.open(params.get("url", "https://google.com"))
        return None

register(AbrirUrlSkill())


class BuscarWebSkill(Skill):
    name = "BUSCAR_WEB"
    description = "Busca en Google"
    prompt_line = 'BUSCAR_WEB{"query":"..."}'
    input_schema = {"type": "object", "properties": {
        "query": {"type": "string", "description": "Texto a buscar"}
    }, "required": ["query"]}

    def run(self, executor, params):
        q = urllib.parse.quote_plus(params.get("query", ""))
        webbrowser.open(f"https://www.google.com/search?q={q}")
        return None

register(BuscarWebSkill())


class MusicaSkill(Skill):
    name = "MUSICA"
    description = "Abre YouTube Music"
    prompt_line = 'MUSICA{"url":"..."}'
    input_schema = {"type": "object", "properties": {
        "url": {"type": "string"}
    }}

    _MUSIC_URL = "https://www.youtube.com/watch?v=CFGLoQIhmow&list=RDCFGLoQIhmow&start_radio=1"

    def run(self, executor, params):
        url = params.get("url", self._MUSIC_URL)
        webbrowser.open(url)
        executor.hablar("Abriendo música, amo.")
        return None

register(MusicaSkill())


class ScreenshotSkill(Skill):
    name = "SCREENSHOT"
    description = "Toma una captura de pantalla"
    prompt_line = 'SCREENSHOT{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.expanduser(f"~/screenshot_{ts}.png")
        ok = screenshot(ruta)
        executor.hablar(f"Captura guardada en {ruta}" if ok else "Instala grim o scrot para capturas.")
        return None

register(ScreenshotSkill())


class SistemaInfoSkill(Skill):
    name = "SISTEMA_INFO"
    description = "Muestra información del sistema (CPU, RAM, disco)"
    prompt_line = 'SISTEMA_INFO{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        info = sistema_info()
        return executor.say(info)

register(SistemaInfoSkill())


class ProcesoInfoSkill(Skill):
    name = "PROCESO_INFO"
    description = "Muestra información de un proceso"
    prompt_line = 'PROCESO_INFO{"nombre":"..."}'
    input_schema = {"type": "object", "properties": {
        "nombre": {"type": "string", "description": "Nombre del proceso"}
    }, "required": ["nombre"]}

    def run(self, executor, params):
        info = proceso_info(params.get("nombre", ""))
        return executor.say(info)

register(ProcesoInfoSkill())


class EjecutarCmdSkill(Skill):
    name = "EJECUTAR_CMD"
    description = "Ejecuta un comando de shell"
    prompt_line = 'EJECUTAR_CMD{"cmd":"...","timeout":10}'
    input_schema = {"type": "object", "properties": {
        "cmd": {"type": "string", "description": "Comando a ejecutar"},
        "timeout": {"type": "integer", "description": "Timeout en segundos", "default": 10}
    }, "required": ["cmd"]}

    def run(self, executor, params):
        out = ejecutar_cmd(params.get("cmd", "echo vacío"), params.get("timeout", 10))
        resumen = out[:300].replace("\n", ". ")
        executor.hablar(resumen or "Comando ejecutado.")
        return out

register(EjecutarCmdSkill())


class ApagarSkill(Skill):
    name = "APAGAR"
    description = "Apaga el sistema"
    prompt_line = 'APAGAR{"delay":5}'
    input_schema = {"type": "object", "properties": {
        "delay": {"type": "integer", "description": "Segundos de espera antes de apagar", "default": 5}
    }}

    def run(self, executor, params):
        import time
        d = params.get("delay", 5)
        executor.hablar(f"Apagando en {d} segundos.")
        time.sleep(d)
        run_cmd(["sudo", "shutdown", "-h", "now"])
        return None

register(ApagarSkill())


class ReiniciarSkill(Skill):
    name = "REINICIAR"
    description = "Reinicia el sistema"
    prompt_line = 'REINICIAR{"delay":5}'
    input_schema = {"type": "object", "properties": {
        "delay": {"type": "integer", "description": "Segundos de espera antes de reiniciar", "default": 5}
    }}

    def run(self, executor, params):
        import time
        d = params.get("delay", 5)
        executor.hablar(f"Reiniciando en {d} segundos.")
        time.sleep(d)
        run_cmd(["sudo", "reboot"])
        return None

register(ReiniciarSkill())
