import time

from rick.skills.base import Skill, register
from rick.system_utils import hotkey, wayland_type, run_cmd, _has


class EscribirSkill(Skill):
    name = "ESCRIBIR"
    description = "Escribe texto en la ventana activa"
    prompt_line = 'ESCRIBIR{"texto":"..."}'
    input_schema = {"type": "object", "properties": {
        "texto": {"type": "string", "description": "Texto a escribir"}
    }, "required": ["texto"]}

    def run(self, executor, params):
        time.sleep(0.4)
        wayland_type(params.get("texto", ""))
        return None

register(EscribirSkill())


class AtajoSkill(Skill):
    name = "ATAJO"
    description = "Ejecuta un atajo de teclado (ej: ctrl+c)"
    prompt_line = 'ATAJO{"combo":"ctrl+c"}'
    input_schema = {"type": "object", "properties": {
        "combo": {"type": "string", "description": "Combinación de teclas"}
    }, "required": ["combo"]}

    def run(self, executor, params):
        hotkey(params.get("combo", ""))
        return None

register(AtajoSkill())


class NuevaPestanaSkill(Skill):
    name = "NUEVA_PESTANA"
    description = "Abre una nueva pestaña en el navegador"
    prompt_line = 'NUEVA_PESTANA{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        hotkey("ctrl+t")
        return None

register(NuevaPestanaSkill())


class CerrarVentanaSkill(Skill):
    name = "CERRAR_VENTANA"
    description = "Cierra la ventana activa"
    prompt_line = 'CERRAR_VENTANA{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        hotkey("alt+F4")
        return None

register(CerrarVentanaSkill())


class MinimizarSkill(Skill):
    name = "MINIMIZAR"
    description = "Minimiza la ventana activa"
    prompt_line = 'MINIMIZAR{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        if _has("hyprctl"):
            run_cmd(["hyprctl", "dispatch", "movetoworkspacesilent", "special"])
        else:
            hotkey("super+h")
        return None

register(MinimizarSkill())


class MaximizarSkill(Skill):
    name = "MAXIMIZAR"
    description = "Maximiza la ventana activa"
    prompt_line = 'MAXIMIZAR{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        if _has("hyprctl"):
            run_cmd(["hyprctl", "dispatch", "fullscreen", "1"])
        else:
            hotkey("super+Up")
        return None

register(MaximizarSkill())
