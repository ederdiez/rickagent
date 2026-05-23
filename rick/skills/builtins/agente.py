import os
import tempfile
import time
import shlex

from rick.skills.base import Skill, register
from rick.system_utils import ejecutar_cmd


class EjecutarPythonSkill(Skill):
    name = "EJECUTAR_PYTHON"
    description = "Ejecuta código Python en un subprocess, retorna stdout+stderr"
    prompt_line = 'EJECUTAR_PYTHON{"codigo":"...","timeout":30}'
    input_schema = {"type": "object", "properties": {
        "codigo": {"type": "string", "description": "Código Python a ejecutar"},
        "timeout": {"type": "integer", "description": "Timeout en segundos", "default": 30}
    }, "required": ["codigo"]}

    def run(self, executor, params):
        codigo = params.get("codigo", "")
        timeout = params.get("timeout", 30)
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

register(EjecutarPythonSkill())


class EscribirYEjecutarSkill(Skill):
    name = "ESCRIBIR_Y_EJECUTAR"
    description = "Escribe un script en /tmp y lo ejecuta"
    prompt_line = 'ESCRIBIR_Y_EJECUTAR{"nombre":"script.py","contenido":"...","interprete":"python3","timeout":30}'
    input_schema = {"type": "object", "properties": {
        "nombre": {"type": "string", "description": "Nombre del script"},
        "contenido": {"type": "string", "description": "Contenido del script"},
        "interprete": {"type": "string", "description": "Intérprete (python3, bash, etc)", "default": "python3"},
        "timeout": {"type": "integer", "default": 30}
    }, "required": ["nombre", "contenido"]}

    def run(self, executor, params):
        nombre = params.get("nombre", "script.py")
        contenido = params.get("contenido", "")
        interprete = params.get("interprete", "python3")
        timeout = params.get("timeout", 30)
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

register(EscribirYEjecutarSkill())


class GitCmdSkill(Skill):
    name = "GIT_CMD"
    description = "Ejecuta comandos git (status, log, diff, add, commit, push, pull, etc.)"
    prompt_line = 'GIT_CMD{"subcmd":"status","directorio":"."}'
    input_schema = {"type": "object", "properties": {
        "subcmd": {"type": "string", "description": "Subcomando y args, ej: 'log --oneline -5'"},
        "directorio": {"type": "string", "description": "Directorio del repositorio"}
    }, "required": ["subcmd", "directorio"]}

    def run(self, executor, params):
        subcmd = params.get("subcmd", "status")
        directorio = executor.resolve(params.get("directorio", "."))
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

register(GitCmdSkill())
